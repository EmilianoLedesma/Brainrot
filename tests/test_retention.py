import math

import pytest
from fastapi.testclient import TestClient

from brainrot import api, retention


def analyze(csv_text="seconds,retention\n0,100\n30,80\n90,60", **options):
    return retention.analyze(csv_text, **{"axis": "seconds", "retention_unit": "percent", "duration_seconds": 90, **options})


def test_short_seconds_axis_is_not_mistaken_for_percentages():
    result = analyze()
    assert result["points"][-1]["seconds"] == 90
    assert result["opening_loss_pp"] == 20
    assert result["last_observed_retention"] == 60


@pytest.mark.parametrize("axis,csv", [
    ("percent", "position,retention\n0%,100%\n25%,80%\n100%,60%"),
    ("fraction", "position,retention\n0,100\n0.25,80\n1,60"),
    ("seconds", "position,retention\n00:00,100\n00:30,80\n02:00,60"),
])
def test_explicit_units_produce_equivalent_reports(axis, csv):
    result = analyze(csv, axis=axis, duration_seconds=120)
    assert result["opening_loss_pp"] == 20
    assert [point["seconds"] for point in result["points"]] == [0, 30, 120]


def test_fractional_retention_and_rewatching_are_preserved():
    result = analyze("0,1.15\n30,1.25\n90,0.9", retention_unit="fraction")
    assert result["opening_loss_pp"] == -10
    assert result["points"][0]["retention"] == pytest.approx(115)


def test_opening_interpolates_and_drops_rank_by_rate_not_total_loss():
    result = analyze("0,100\n20,90\n40,80\n42,74\n90,60")
    assert result["opening_loss_pp"] == 15
    assert result["drops"][0]["start_seconds"] == 40
    assert result["drops"][0]["loss_pp"] == 6
    assert result["drops"][0]["rate_pp_per_second"] == 3


def test_subtitle_excerpt_corresponds_to_drop_interval():
    srt = "1\n00:00:00,000 --> 00:00:30,000\nThe opening promise.\n\n2\n00:00:30,000 --> 00:01:30,000\nThe payoff."
    result = analyze(transcript_srt=srt)
    assert result["drops"][0]["excerpt"] == "The opening promise."
    assert result["drops"][1]["excerpt"] == "The payoff."


def test_semicolon_delimiter_bom_and_selected_columns():
    result = analyze("\ufefflabel;watch;position\na;100;0\nb;80;30\nc;60;90", time_column=2, retention_column=1)
    assert result["opening_loss_pp"] == 20


def test_incomplete_export_does_not_claim_completion_or_extrapolate():
    result = analyze("0,100\n10,95\n20,90")
    assert result["opening_seconds"] == 20
    assert result["last_observed_seconds"] == 20
    assert result["last_observed_retention"] == 90


@pytest.mark.parametrize("csv_text", [
    "", "0,100\n90,60", "0,100\n30,NaN\n90,60", "0,100\n30,inf\n90,60",
    "0,100\n30,80\n91,60", "0,100\n-1,80\n90,60", "0,100\n30,80\n30,60",
    "0,100\n60,80\n30,60", "1,100\n30,80\n90,60", "0,100\n30,-1\n90,60",
    "0,100\n30,wrong\n90,60", "0,100\n30,80\n90", "00:00,100\n00:90,80\n01:30,60",
])
def test_invalid_curve_is_rejected_instead_of_silently_reinterpreted(csv_text):
    with pytest.raises(ValueError):
        analyze(csv_text)


@pytest.mark.parametrize("options", [
    {"axis": "guess"}, {"duration_seconds": math.nan}, {"duration_seconds": 0},
    {"retention_unit": "guess"}, {"time_column": 1}, {"transcript_srt": "Untimed text."},
    {"transcript_srt": "1\n00:00:20,000 --> 00:00:10,000\nInvalid cue."},
])
def test_invalid_configuration_is_rejected(options):
    with pytest.raises(ValueError):
        analyze(**options)


def test_size_and_point_limits():
    with pytest.raises(ValueError, match="250 KB"):
        analyze("x" * 250_001)
    with pytest.raises(ValueError, match="5,000"):
        analyze("\n".join(f"{index},80" for index in range(5001)), duration_seconds=5001)


def test_api_requires_auth_and_reports_user_friendly_validation(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "test-key")
    http = TestClient(api.app)
    payload = {"csv_text": "0,100\n30,80\n90,60", "axis": "seconds", "duration_seconds": 90}
    assert http.post("/insights/retention", json=payload).status_code == 401
    headers = {"X-API-Key": "test-key"}
    response = http.post("/insights/retention", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["opening_loss_pp"] == 20
    payload["csv_text"] = "0,100\n30,80\n30,60"
    response = http.post("/insights/retention", json=payload, headers=headers)
    assert response.status_code == 422
    assert response.json()["detail"] == "CSV positions must increase, without duplicate timestamps."
    payload["duration_seconds"] = "NaN"
    assert http.post("/insights/retention", json=payload, headers=headers).status_code == 422
