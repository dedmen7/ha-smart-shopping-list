"""The integration in a running Home Assistant: actions with the acting user, the to-do list, the status sensor and the formula supply."""

import hashlib
from datetime import timedelta
from pathlib import Path

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.auth.models import User
from homeassistant.core import Context, HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.smart_shopping_list import card_module_url
from custom_components.smart_shopping_list.const import DOMAIN

from .conftest import local

STATUS = 'sensor.smart_shopping_list_status'
TODO = 'todo.smart_shopping_list'


async def call(hass: HomeAssistant, service: str, user: User | None = None, **data: object) -> dict | None:
    context = Context(user_id=None if user is None else user.id)
    return await hass.services.async_call(DOMAIN, service, data, blocking=True, return_response=True, context=context)


def items(hass: HomeAssistant) -> list[dict]:
    return hass.states.get(STATUS).attributes['items']


async def test_adding_records_the_named_user_and_merges_duplicates(hass: HomeAssistant, entry: MockConfigEntry, parents: dict[str, User]) -> None:
    await call(hass, 'add_item', parents['Tom'], text='2x melk')
    await call(hass, 'add_item', parents['Janou'], text='Melk')
    await call(hass, 'add_item', parents['Janou'], text='bananen')
    listed = items(hass)
    assert [(item['name'], item['quantity'], item['category'], item['added_by']) for item in listed] == [('melk', 3, 'dairy', 'Tom'), ('bananen', 1, 'produce', 'Janou')]
    assert hass.states.get(STATUS).state == '2'


async def test_completing_shows_who_bought_it_and_when(hass: HomeAssistant, entry: MockConfigEntry, parents: dict[str, User], freezer: FrozenDateTimeFactory) -> None:
    await call(hass, 'add_item', parents['Tom'], text='melk')
    freezer.move_to(local('2026-11-19T18:32'))
    await call(hass, 'complete_item', parents['Janou'], item_id=items(hass)[0]['id'])
    item = items(hass)[0]
    assert (item['done'], item['done_by'], item['done_at']) == (True, 'Janou', local('2026-11-19T18:32').isoformat())
    await call(hass, 'reopen_item', parents['Tom'], item_id=item['id'])
    assert (items(hass)[0]['done'], items(hass)[0]['done_by']) == (False, None)


async def test_regulars_come_from_what_was_bought(hass: HomeAssistant, entry: MockConfigEntry, parents: dict[str, User]) -> None:
    for name in ['melk', 'melk', 'brood']:
        await call(hass, 'add_item', parents['Tom'], text=name)
        await call(hass, 'complete_item', parents['Tom'], item_id=next(item['id'] for item in items(hass) if not item['done']))
        await call(hass, 'clear_done')
    regulars = hass.states.get(STATUS).attributes['regulars']
    assert [(regular['name'], regular['purchases']) for regular in regulars] == [('melk', 2), ('brood', 1)]


async def test_a_refused_change_carries_a_translation_key(hass: HomeAssistant, entry: MockConfigEntry, parents: dict[str, User]) -> None:
    with pytest.raises(ServiceValidationError) as refused:
        await call(hass, 'add_item', parents['Tom'], text='   ')
    assert (refused.value.translation_domain, refused.value.translation_key) == (DOMAIN, 'empty_entry')


async def test_moving_to_another_aisle_is_remembered(hass: HomeAssistant, entry: MockConfigEntry, parents: dict[str, User]) -> None:
    await call(hass, 'add_item', parents['Tom'], text='Melkpoeder')
    item_id = items(hass)[0]['id']
    await call(hass, 'update_item', parents['Tom'], item_id=item_id, category='baby', quantity=2)
    await call(hass, 'remove_item', parents['Tom'], item_id=item_id)
    await call(hass, 'add_item', parents['Tom'], text='melkpoeder')
    assert items(hass)[0]['category'] == 'baby'


async def test_the_todo_list_mirrors_the_items_and_works_for_voice_and_the_app(hass: HomeAssistant, entry: MockConfigEntry, parents: dict[str, User]) -> None:
    await call(hass, 'add_item', parents['Tom'], text='2 melk')
    await hass.services.async_call('todo', 'add_item', {'item': 'brood'}, target={'entity_id': TODO}, blocking=True, context=Context(user_id=parents['Janou'].id))
    listed = await hass.services.async_call('todo', 'get_items', {}, target={'entity_id': TODO}, blocking=True, return_response=True)
    assert [item['summary'] for item in listed[TODO]['items']] == ['2× melk', 'brood']
    assert items(hass)[1]['added_by'] == 'Janou'
    await hass.services.async_call('todo', 'update_item', {'item': 'brood', 'status': 'completed'}, target={'entity_id': TODO}, blocking=True, context=Context(user_id=parents['Tom'].id))
    assert (items(hass)[1]['done'], items(hass)[1]['done_by']) == (True, 'Tom')
    assert hass.states.get(TODO).state == '1'
    listed = await hass.services.async_call('todo', 'get_items', {}, target={'entity_id': TODO}, blocking=True, return_response=True)
    assert [item.get('description') for item in listed[TODO]['items']] == ['Added by Tom', 'Bought by Tom · 09:00']
    await hass.services.async_call('todo', 'remove_item', {'item': '2× melk'}, target={'entity_id': TODO}, blocking=True)
    assert [item['name'] for item in items(hass)] == ['brood']


async def test_the_list_survives_a_restart(hass: HomeAssistant, entry: MockConfigEntry, parents: dict[str, User]) -> None:
    await call(hass, 'add_item', parents['Tom'], text='melk')
    await call(hass, 'complete_item', parents['Tom'], item_id=items(hass)[0]['id'])
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert (items(hass)[0]['done_by'], hass.states.get(STATUS).attributes['regulars'][0]['name']) == ('Tom', 'melk')


async def test_low_formula_is_put_on_the_list_once_per_can(hass: HomeAssistant, entry: MockConfigEntry, parents: dict[str, User], freezer: FrozenDateTimeFactory) -> None:
    diary = [{'summary': '100 ml', 'start': (local('2026-11-19T09:00') - timedelta(hours=4 * index)).isoformat()} for index in range(1, 43)]

    async def get_events(service_call: ServiceCall) -> dict:
        start, end = service_call.data['start_date_time'], service_call.data['end_date_time']
        return {'calendar.baby_feeding_diary': {'events': [event for event in diary if start.isoformat() <= event['start'] <= end.isoformat()]}}

    hass.services.async_register('calendar', 'get_events', get_events, supports_response='only')
    await call(hass, 'set_supply', parents['Tom'], enabled=True, can_grams=800, grams_per_100ml=15, warn_days=3, product_name='Flesvoeding', diary_entity='calendar.baby_feeding_diary')
    freezer.move_to(local('2026-11-13T09:00'))
    await call(hass, 'open_new_can', parents['Tom'])
    freezer.move_to(local('2026-11-19T09:00'))
    async_fire_time_changed(hass, local('2026-11-19T09:00') + timedelta(minutes=31))
    await hass.async_block_till_done()
    supply = hass.states.get(STATUS).attributes['supply']
    assert (supply['left_grams'], supply['low']) == (260, True)
    assert [(item['name'], item['category'], item['added_by']) for item in items(hass)] == [('Flesvoeding', 'baby', 'Supply check')]
    await call(hass, 'refresh_supply')
    assert len(items(hass)) == 1


async def test_the_card_url_changes_with_the_card_content() -> None:
    card = Path(__file__).parents[1] / 'custom_components' / 'smart_shopping_list' / 'frontend' / 'smart-shopping-list-card.js'
    assert card_module_url(card) == '/smart_shopping_list/smart-shopping-list-card.js?v=' + hashlib.sha256(card.read_bytes()).hexdigest()[:12]


async def test_set_up_through_the_user_interface(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={'source': 'user'})
    assert result['type'] == 'form'
    result = await hass.config_entries.flow.async_configure(result['flow_id'], {})
    assert (result['type'], result['title']) == ('create_entry', 'Smart Shopping List')


async def test_the_todo_descriptions_follow_the_language_and_name_older_days(hass: HomeAssistant, entry: MockConfigEntry, parents: dict[str, User], freezer: FrozenDateTimeFactory) -> None:
    hass.config.language = 'nl'
    await call(hass, 'add_item', parents['Janou'], text='melk')
    await call(hass, 'complete_item', parents['Janou'], item_id=items(hass)[0]['id'])
    freezer.move_to(local('2026-11-21T10:00'))
    await call(hass, 'add_item', parents['Tom'], text='kaas')
    listed = await hass.services.async_call('todo', 'get_items', {}, target={'entity_id': TODO}, blocking=True, return_response=True)
    assert [item.get('description') for item in listed[TODO]['items']] == ['Gehaald door Janou · 19 nov 09:00', 'Toegevoegd door Tom']
