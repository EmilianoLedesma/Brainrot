"""Platform-neutral performance values and the existing chapter pacing policy."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from typing import Literal

PACING = ((60.0, timedelta(hours=12)), (40.0, timedelta(hours=24)), (0.0, timedelta(hours=48)))
ABANDON_BELOW_PCT = 20.0
METRICS_GRACE = timedelta(hours=24)


def _retention(value: float) -> None:
    if not isfinite(value) or not 0 <= value <= 100:
        raise ValueError("retention must be between 0 and 100")


@dataclass(frozen=True)
class Performance:
    platform: str
    content_id: str
    measured_at: datetime
    views: int = 0
    retention_pct: float | None = None
    engagement: float | None = None

    def __post_init__(self):
        if not self.platform or not self.content_id or self.views < 0:
            raise ValueError("performance needs a platform, content id and nonnegative views")
        if self.measured_at.tzinfo is None:
            raise ValueError("measurement timestamp must include a timezone")
        if self.retention_pct is not None:
            _retention(self.retention_pct)
        if self.engagement is not None and (not isfinite(self.engagement) or self.engagement < 0):
            raise ValueError("engagement must be finite and nonnegative")


@dataclass(frozen=True)
class PaceDecision:
    action: Literal["wait", "schedule", "drop"]
    when: datetime | None = None


def gap_for(retention_pct: float) -> timedelta:
    _retention(retention_pct)
    return next(gap for threshold, gap in PACING if retention_pct >= threshold)


def next_chapter(retention_pct: float | None, published_at: datetime, now: datetime) -> PaceDecision:
    if retention_pct is None:
        if now - published_at < METRICS_GRACE:
            return PaceDecision("wait")
        gap = PACING[-1][1]
    else:
        _retention(retention_pct)
        if retention_pct < ABANDON_BELOW_PCT:
            return PaceDecision("drop")
        gap = gap_for(retention_pct)
    return PaceDecision("schedule", published_at + gap)
