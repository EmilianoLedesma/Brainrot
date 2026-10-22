"""Explicit-unit retention analysis; no platform credentials or model calls."""

import csv
import io
import math
import re


def _number(value: str) -> float:
    result = float(value.strip().removesuffix("%"))
    if not math.isfinite(result):
        raise ValueError("Use finite numbers in the CSV.")
    return result


def _position(value: str, axis: str, duration: float) -> float:
    if axis == "seconds" and ":" in value:
        parts = value.strip().split(":")
        if len(parts) not in (2, 3):
            raise ValueError("Time must be seconds, mm:ss, or hh:mm:ss.")
        values = [_number(part) for part in parts]
        if any(part < 0 for part in values) or any(part >= 60 for part in values[1:]):
            raise ValueError("Time must be seconds, mm:ss, or hh:mm:ss.")
        return sum(part * 60 ** i for i, part in enumerate(reversed(values)))
    position = _number(value)
    return position if axis == "seconds" else position * duration / (100 if axis == "percent" else 1)


def _subtitles(text: str) -> list[tuple[float, float, str]]:
    cues = []
    stamp = r"(\d+:\d{2}:\d{2}[,.]\d{3})"
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        match = re.search(stamp + r"\s*-->\s*" + stamp, block)
        if not match:
            continue
        start, end = (_position(part.replace(",", "."), "seconds", 1) for part in match.groups())
        if end <= start:
            raise ValueError("Subtitle end times must follow their start times.")
        words = re.sub(r"<[^>]*>", "", block[match.end():]).strip()
        cues.append((start, end, " ".join(words.split())))
    if text.strip() and not cues:
        raise ValueError("Use timed SRT subtitles to match words to the retention curve.")
    return cues


def analyze(csv_text: str, *, axis: str, retention_unit: str, duration_seconds: float,
            transcript_srt: str = "", time_column: int = 0, retention_column: int = 1, allow_partial_start: bool = False) -> dict:
    if axis not in {"seconds", "percent", "fraction"} or retention_unit not in {"percent", "fraction"}:
        raise ValueError("Choose the units used by your export.")
    if not math.isfinite(duration_seconds) or not 1 <= duration_seconds <= 86_400:
        raise ValueError("Enter the video's actual duration in seconds.")
    if time_column == retention_column or min(time_column, retention_column) < 0:
        raise ValueError("Choose two different CSV columns.")
    if not csv_text.strip() or len(csv_text) > 250_000 or len(transcript_srt) > 250_000:
        raise ValueError("Use a nonempty CSV and files no larger than 250 KB each.")
    sample = csv_text.lstrip("\ufeff")
    # Delimiter detection does not infer units; a 90-second axis stays seconds.
    try:
        dialect = csv.Sniffer().sniff(sample[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    points = []
    headers = 0
    for line_number, row in enumerate(csv.reader(io.StringIO(sample), dialect), start=1):
        if not any(cell.strip() for cell in row):
            continue
        try:
            if max(time_column, retention_column) >= len(row):
                raise ValueError()
            x = _position(row[time_column], axis, duration_seconds)
            y = _number(row[retention_column]) * (100 if retention_unit == "fraction" else 1)
        except ValueError:
            if not points and headers < 5:
                headers += 1
                continue
            raise ValueError(f"Check the values and selected columns on CSV row {line_number}.") from None
        if not 0 <= x <= duration_seconds + 0.001 or not 0 <= y <= 1000:
            raise ValueError(f"CSV row {line_number} is outside the video timeline or retention range.")
        if points and x <= points[-1]["seconds"]:
            raise ValueError("CSV positions must increase, without duplicate timestamps.")
        points.append({"seconds": x, "retention": y})
        if len(points) > 5000:
            raise ValueError("Use an export with no more than 5,000 data points.")
    if len(points) < 3:
        raise ValueError("The CSV needs at least three numeric data rows. Check the selected columns and units.")
    if points[0]["seconds"] > 0.001 and not allow_partial_start:
        raise ValueError("The retention curve must start at zero so the opening can be measured.")
    cues = _subtitles(transcript_srt)
    cutoff = max(points[0]["seconds"], min(30.0, duration_seconds, points[-1]["seconds"]))
    opening = points[-1]["retention"]
    for left, right in zip(points, points[1:]):
        if left["seconds"] <= cutoff <= right["seconds"]:
            fraction = (cutoff - left["seconds"]) / (right["seconds"] - left["seconds"])
            opening = left["retention"] + fraction * (right["retention"] - left["retention"])
            break
    drops = []
    for left, right in zip(points, points[1:]):
        loss = left["retention"] - right["retention"]
        if loss <= 0:
            continue
        start, end = left["seconds"], right["seconds"]
        excerpt = " ".join(words for cue_start, cue_end, words in cues if cue_start < end and cue_end > start)
        drops.append({"start_seconds": start, "end_seconds": end, "loss_pp": round(loss, 3),
                      "rate_pp_per_second": round(loss / (end - start), 4), "excerpt": excerpt[:500] or None})
    # Rank by slope so uneven sampling doesn't make a long interval look like a cliff.
    drops.sort(key=lambda drop: drop["rate_pp_per_second"], reverse=True)
    return {"duration_seconds": duration_seconds, "axis": axis, "retention_unit": retention_unit,
            "points": points, "opening_seconds": cutoff, "opening_start_seconds": points[0]["seconds"],
            "opening_loss_pp": round(points[0]["retention"] - opening, 3),
            "last_observed_seconds": points[-1]["seconds"], "last_observed_retention": points[-1]["retention"],
            "drops": drops[:5]}
