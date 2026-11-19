"""Formula supply: how much powder is left in the open can, based on the bottles given since it was opened."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.smart_shopping_list.supply import SupplySettings, feeds_from_events, supply_status

AMSTERDAM = ZoneInfo('Europe/Amsterdam')
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=AMSTERDAM)
SETTINGS = SupplySettings(enabled=True, can_grams=800, grams_per_100ml=15.0, warn_days=3)


def bottles(*, days: int, per_day: int, ml: int, until: datetime = NOW) -> list[tuple[datetime, int]]:
    step = timedelta(hours=24 / per_day)
    return [(until - step * (index + 1), ml) for index in range(days * per_day)]


def test_nothing_is_known_before_a_can_is_opened() -> None:
    assert supply_status(settings=SETTINGS, opened_at=None, feeds=bottles(days=2, per_day=6, ml=100), now=NOW) is None


def test_powder_left_and_days_follow_the_bottles_since_opening() -> None:
    opened = NOW - timedelta(days=2)
    status = supply_status(settings=SETTINGS, opened_at=opened, feeds=bottles(days=7, per_day=6, ml=100), now=NOW)
    assert status.used_grams == 180
    assert status.left_grams == 620
    assert status.grams_per_day == 90
    assert status.days_left == pytest.approx(620 / 90)
    assert status.empty_at == NOW + timedelta(days=620 / 90)
    assert status.low is False


def test_the_supply_is_low_within_the_warning_days() -> None:
    opened = NOW - timedelta(days=6)
    status = supply_status(settings=SETTINGS, opened_at=opened, feeds=bottles(days=7, per_day=6, ml=100), now=NOW)
    assert status.left_grams == 260
    assert status.low is True


def test_a_young_history_averages_over_the_days_it_covers() -> None:
    feeds = bottles(days=2, per_day=6, ml=100)
    status = supply_status(settings=SETTINGS, opened_at=NOW - timedelta(days=2), feeds=feeds, now=NOW)
    assert status.grams_per_day == 90


def test_an_empty_can_never_goes_below_zero() -> None:
    status = supply_status(settings=SETTINGS, opened_at=NOW - timedelta(days=30), feeds=bottles(days=30, per_day=8, ml=150), now=NOW)
    assert status.left_grams == 0
    assert status.days_left == 0
    assert status.low is True


def test_without_recent_bottles_the_days_left_are_unknown() -> None:
    status = supply_status(settings=SETTINGS, opened_at=NOW - timedelta(hours=1), feeds=[], now=NOW)
    assert (status.left_grams, status.grams_per_day, status.days_left, status.low) == (800, 0, None, False)


@pytest.mark.parametrize(('summary', 'amount'), [('70 cc', 70), ('70 ml', 70), ('  95ML ', 95), ('Consultatiebureau', None), ('cc', None)])
def test_feeds_are_read_from_diary_events(summary: str, amount: int | None) -> None:
    events = [{'summary': summary, 'start': '2026-11-19T10:00:00+01:00'}, {'summary': '60 cc', 'start': 'not a date'}]
    expected = [] if amount is None else [(datetime(2026, 11, 19, 10, 0, tzinfo=AMSTERDAM), amount)]
    assert feeds_from_events(events) == expected


@pytest.mark.parametrize('settings', [
    {'can_grams': 0}, {'can_grams': 5001}, {'grams_per_100ml': 0}, {'grams_per_100ml': 40.5}, {'warn_days': -1}, {'warn_days': 15},
])
def test_unreasonable_settings_are_refused(settings: dict) -> None:
    with pytest.raises(ValueError):
        SupplySettings(enabled=True, **settings)
