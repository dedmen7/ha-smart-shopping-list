"""The status sensor the card reads: the items with who and when, the regulars and the formula supply."""

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ShoppingConfigEntry
from .const import REGULARS_SHOWN
from .manager import ShoppingManager, supply_attributes
from .shopping import CATEGORIES, regulars


async def async_setup_entry(hass: HomeAssistant, entry: ShoppingConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([ShoppingStatusSensor(entry.runtime_data)])


class ShoppingStatusSensor(SensorEntity):
    """State is the number of open items; the large attributes stay out of the recorder."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = 'status'
    _attr_unique_id = 'smart_shopping_list_status'
    _attr_icon = 'mdi:cart-outline'
    _unrecorded_attributes = frozenset({'items', 'regulars', 'supply', 'categories'})

    def __init__(self, manager: ShoppingManager) -> None:
        self.manager = manager
        self.entity_id = 'sensor.smart_shopping_list_status'

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.manager.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> int:
        return sum(1 for item in self.manager.state.items if not item.done)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self.manager.state
        return {
            'categories': list(CATEGORIES),
            'items': [{
                'id': item.item_id, 'name': item.name, 'quantity': item.quantity, 'category': item.category,
                'added_by': item.added_by, 'added_at': _local(item.added_at), 'done': item.done, 'done_by': item.done_by, 'done_at': _local(item.done_at),
            } for item in state.items],
            'regulars': [{'name': product.name, 'category': product.category, 'purchases': product.purchases, 'last_bought': _local(product.last_bought)}
                         for product in regulars(state, limit=REGULARS_SHOWN)],
            'supply': supply_attributes(self.manager.supply_status, self.manager.supply),
        }


def _local(moment: datetime | None) -> str | None:
    return None if moment is None else dt_util.as_local(moment).isoformat()
