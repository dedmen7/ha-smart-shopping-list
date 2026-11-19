"""Shared fixtures: a Home Assistant in Amsterdam time with the integration set up and two named users."""

from collections.abc import AsyncGenerator
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_shopping_list.const import CONF_NAMES, DOMAIN

AMSTERDAM = ZoneInfo('Europe/Amsterdam')


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    return None


def local(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=AMSTERDAM)


@pytest.fixture
async def parents(hass: HomeAssistant) -> dict[str, User]:
    """Tom is an administrator; Janou is a regular user, like in the household this was built for."""
    tom = await hass.auth.async_create_user(name='Smolenaers', group_ids=['system-admin'])
    janou = await hass.auth.async_create_user(name='Janou', group_ids=['system-users'])
    return {'Tom': tom, 'Janou': janou}


@pytest.fixture
async def entry(hass: HomeAssistant, parents: dict[str, User], freezer: FrozenDateTimeFactory) -> AsyncGenerator[MockConfigEntry]:
    await hass.config.async_set_time_zone('Europe/Amsterdam')
    freezer.move_to(local('2026-11-19T09:00'))
    config_entry = MockConfigEntry(domain=DOMAIN, title='Smart Shopping List', data={}, options={CONF_NAMES: {parents['Tom'].id: 'Tom'}})
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    yield config_entry
