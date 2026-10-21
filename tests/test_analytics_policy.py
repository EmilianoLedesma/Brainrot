from datetime import datetime, timedelta, timezone

import pytest

from brainrot.application.analytics import Performance, next_chapter

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


@pytest.mark.parametrize("retention,hours", [(20,48), (39.999,48), (40,24), (59.999,24), (60,12), (100,12)])
def test_retention_boundaries_preserve_the_existing_cadence(retention, hours):
    decision = next_chapter(retention, NOW, NOW)
    assert decision.action == "schedule" and decision.when == NOW + timedelta(hours=hours)


@pytest.mark.parametrize("retention", [0, 19.999])
def test_low_retention_drops_following_chapters(retention):
    assert next_chapter(retention, NOW, NOW).action == "drop"


def test_silence_waits_exactly_24_hours_then_uses_the_slow_cadence():
    assert next_chapter(None, NOW, NOW + timedelta(hours=24, microseconds=-1)).action == "wait"
    decision = next_chapter(None, NOW, NOW + timedelta(hours=24))
    assert decision.action == "schedule" and decision.when == NOW + timedelta(hours=48)


def test_performance_contract_is_platform_neutral():
    metric = Performance("youtube", "content-1", NOW, views=100, retention_pct=60, engagement=5)
    assert metric.retention_pct == 60


@pytest.mark.parametrize("retention", [-1,101,float("nan"),float("inf")])
def test_invalid_retention_cannot_drive_publishing(retention):
    with pytest.raises(ValueError):
        next_chapter(retention, NOW, NOW)
