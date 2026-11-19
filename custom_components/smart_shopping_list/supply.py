"""Formula supply: powder left in the open can and the days until it runs out, from the bottles given since opening."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

AVERAGE_WINDOW = timedelta(days=7)
DIARY_AMOUNT = re.compile(r'^\s*(\d+)\s*(cc|ml)\s*$', re.IGNORECASE)


@dataclass(frozen=True)
class SupplySettings:
    enabled: bool = False
    can_grams: int = 800
    grams_per_100ml: float = 15.0
    warn_days: int = 3
    product_name: str = 'Flesvoeding'
    diary_entity: str = 'calendar.baby_feeding_diary'

    def __post_init__(self) -> None:
        if not 1 <= self.can_grams <= 5000:
            raise ValueError('A can holds between 1 and 5000 grams.')
        if not 0 < self.grams_per_100ml <= 40:
            raise ValueError('Use between 0 and 40 grams of powder per 100 ml.')
        if not 0 <= self.warn_days <= 14:
            raise ValueError('Warn between 0 and 14 days ahead.')


@dataclass(frozen=True)
class SupplyStatus:
    opened_at: datetime
    used_grams: float
    left_grams: float
    grams_per_day: float
    days_left: float | None
    empty_at: datetime | None
    low: bool


def supply_status(*, settings: SupplySettings, opened_at: datetime | None, feeds: list[tuple[datetime, int]], now: datetime) -> SupplyStatus | None:
    if opened_at is None:
        return None
    grams = settings.grams_per_100ml / 100
    used = sum(amount for start, amount in feeds if opened_at <= start <= now) * grams
    left = max(0.0, settings.can_grams - used)
    recent = [(start, amount) for start, amount in feeds if now - AVERAGE_WINDOW <= start <= now]
    per_day = 0.0
    if recent:
        # A short history is averaged over the days it covers, rounded up to whole days.
        covered_days = min(AVERAGE_WINDOW.days, max(1, -(-(now - min(start for start, _ in recent)) // timedelta(days=1))))
        per_day = sum(amount for _, amount in recent) * grams / covered_days
    days_left = None if per_day == 0 else left / per_day
    empty_at = None if days_left is None else now + timedelta(days=days_left)
    return SupplyStatus(
        opened_at=opened_at, used_grams=used, left_grams=left, grams_per_day=per_day, days_left=days_left, empty_at=empty_at,
        low=days_left is not None and days_left <= settings.warn_days,
    )


def feeds_from_events(events: list[dict[str, Any]]) -> list[tuple[datetime, int]]:
    feeds = []
    for event in events:
        match = DIARY_AMOUNT.match(str(event.get('summary', '')))
        try:
            start = datetime.fromisoformat(str(event.get('start', '')))
        except ValueError:
            continue
        if match is not None and start.tzinfo is not None:
            feeds.append((start, int(match.group(1))))
    return feeds
