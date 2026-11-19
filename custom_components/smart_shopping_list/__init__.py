"""Smart Shopping List: a shared shopping list with aisles, regulars, who and when, and a formula supply check."""

import hashlib
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CARD_FILENAME, CARD_URL_PATH, CONF_NAMES, DOMAIN
from .manager import ShoppingManager, archive_entries
from .shopping import CATEGORIES, MAXIMUM_QUANTITY
from .supply import SupplySettings

PLATFORMS = [Platform.SENSOR, Platform.TODO]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_FILE = Path(__file__).parent / 'frontend' / CARD_FILENAME
ITEM = {vol.Required('item_id'): cv.string}

type ShoppingConfigEntry = ConfigEntry[ShoppingManager]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    card_url = CARD_URL_PATH + '/' + CARD_FILENAME
    await hass.http.async_register_static_paths([StaticPathConfig(url_path=card_url, path=str(CARD_FILE), cache_headers=False)])
    if 'frontend' in hass.config.components:
        module_url = await hass.async_add_executor_job(card_module_url, CARD_FILE)
        add_extra_js_url(hass=hass, url=module_url)
    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ShoppingConfigEntry) -> bool:
    manager = ShoppingManager(hass, names=dict(entry.options.get(CONF_NAMES, {})))
    await manager.async_start()
    entry.runtime_data = manager
    entry.async_on_unload(manager.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry=entry, platforms=PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ShoppingConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry=entry, platforms=PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: ShoppingConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def card_module_url(card_file: Path) -> str:
    """The card URL with a content hash, so browsers and the phone apps load a new card after every update."""
    version = hashlib.sha256(card_file.read_bytes()).hexdigest()[:12]
    return CARD_URL_PATH + '/' + CARD_FILENAME + '?v=' + version


def _register_services(hass: HomeAssistant) -> None:
    def manager() -> ShoppingManager:
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError('Smart Shopping List is not loaded.', translation_domain=DOMAIN, translation_key='not_loaded')
        return entries[0].runtime_data

    def register(name: str, schema: dict, run: Callable[[ShoppingManager, ServiceCall], Awaitable[Any]]) -> None:
        async def handle(call: ServiceCall) -> ServiceResponse:
            await run(manager(), call)
            return {'open_items': sum(1 for item in manager().state.items if not item.done)}

        hass.services.async_register(domain=DOMAIN, service=name, service_func=handle, schema=vol.Schema(schema), supports_response=SupportsResponse.OPTIONAL)

    register('add_item', {vol.Required('text'): cv.string}, lambda target, call: target.async_add(text_entry=call.data['text'], context=call.context))
    register('complete_item', ITEM, lambda target, call: target.async_complete(item_id=call.data['item_id'], context=call.context))
    register('reopen_item', ITEM, lambda target, call: target.async_reopen(item_id=call.data['item_id']))
    register('remove_item', ITEM, lambda target, call: target.async_remove(item_ids=[call.data['item_id']]))
    register(
        'update_item',
        {**ITEM, vol.Optional('name'): cv.string, vol.Optional('quantity'): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAXIMUM_QUANTITY)), vol.Optional('category'): vol.In(CATEGORIES)},
        lambda target, call: target.async_update(item_id=call.data['item_id'], name=call.data.get('name'), quantity=call.data.get('quantity'), category=call.data.get('category')),
    )
    register('clear_done', {}, lambda target, call: target.async_clear_done())

    async def get_archive(call: ServiceCall) -> ServiceResponse:
        return {'items': archive_entries(manager().state)}

    hass.services.async_register(domain=DOMAIN, service='get_archive', service_func=get_archive, schema=vol.Schema({}), supports_response=SupportsResponse.ONLY)
    register('open_new_can', {}, lambda target, call: target.async_open_new_can())
    register('refresh_supply', {}, lambda target, call: target.async_refresh_supply())

    async def set_supply(target: ShoppingManager, call: ServiceCall) -> None:
        try:
            settings = SupplySettings(**call.data)
        except ValueError as error:
            raise ServiceValidationError(str(error), translation_domain=DOMAIN, translation_key='invalid_supply') from error
        await target.async_set_supply(settings)

    register('set_supply', {
        vol.Required('enabled'): cv.boolean,
        vol.Required('can_grams'): vol.All(vol.Coerce(int), vol.Range(min=1, max=5000)),
        vol.Required('grams_per_100ml'): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=40)),
        vol.Required('warn_days'): vol.All(vol.Coerce(int), vol.Range(min=0, max=14)),
        vol.Required('product_name'): vol.All(cv.string, vol.Length(min=1, max=100)),
        vol.Required('diary_entity'): cv.entity_id,
    }, set_supply)
