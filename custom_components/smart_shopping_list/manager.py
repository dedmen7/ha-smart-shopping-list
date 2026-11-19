"""Runs the list inside Home Assistant: names the acting user, stores every change and keeps the formula supply up to date."""

import asyncio
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, Context, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import shopping
from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION, SUPPLY_REFRESH_MINUTES
from .persistence import from_stored, to_stored
from .shopping import ListError, ShoppingState
from .supply import SupplySettings, SupplyStatus, feeds_from_events, supply_status
from .texts import text


class ShoppingManager:
    """Owns the list; every change goes through `_change` so storage and listeners stay in step."""

    def __init__(self, hass: HomeAssistant, *, names: dict[str, str]) -> None:
        self.hass = hass
        self.names = names
        self.state = ShoppingState()
        self.supply = SupplySettings()
        self.opened_at: datetime | None = None
        self.listed_for: datetime | None = None
        self.supply_status: SupplyStatus | None = None
        self._store: Store[dict[str, Any]] = Store(hass=hass, version=STORAGE_VERSION, key=STORAGE_KEY)
        self._lock = asyncio.Lock()
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribers: list[CALLBACK_TYPE] = []
        self._diary_unsubscribe: CALLBACK_TYPE | None = None

    async def async_start(self) -> None:
        stored = await self._store.async_load()
        if stored is not None:
            self.state, self.supply, self.opened_at, self.listed_for = from_stored(stored)
        self._unsubscribers.append(async_track_time_interval(hass=self.hass, action=self._async_refresh_tick, interval=timedelta(minutes=SUPPLY_REFRESH_MINUTES)))
        self._watch_diary()
        await self.async_refresh_supply()

    @callback
    def async_stop(self) -> None:
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        if self._diary_unsubscribe is not None:
            self._diary_unsubscribe()
            self._diary_unsubscribe = None

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    async def async_display_name(self, context: Context | None) -> str | None:
        user_id = None if context is None else context.user_id
        if user_id is None:
            return None
        if user_id in self.names:
            return self.names[user_id]
        user = await self.hass.auth.async_get_user(user_id)
        return None if user is None else user.name

    async def async_add(self, *, text_entry: str, context: Context | None) -> None:
        by, now = await self.async_display_name(context), dt_util.now()
        await self._change(lambda state: shopping.add_item(state, text=text_entry, by=by, now=now, new_id=_new_id))

    async def async_complete(self, *, item_id: str, context: Context | None) -> None:
        by, now = await self.async_display_name(context), dt_util.now()
        await self._change(lambda state: shopping.complete_item(state, item_id=item_id, by=by, now=now))

    async def async_reopen(self, *, item_id: str) -> None:
        await self._change(lambda state: shopping.reopen_item(state, item_id=item_id))

    async def async_update(self, *, item_id: str, name: str | None, quantity: int | None, category: str | None) -> None:
        await self._change(lambda state: shopping.update_item(state, item_id=item_id, name=name, quantity=quantity, category=category))

    async def async_remove(self, *, item_ids: list[str]) -> None:
        def change(state: ShoppingState) -> ShoppingState:
            for item_id in item_ids:
                state = shopping.remove_item(state, item_id=item_id)
            return state

        await self._change(change)

    async def async_clear_done(self) -> None:
        await self._change(shopping.clear_done)

    async def async_set_supply(self, settings: SupplySettings) -> None:
        async with self._lock:
            self.supply = settings
            await self._save()
        self._watch_diary()
        await self.async_refresh_supply()

    async def async_open_new_can(self) -> None:
        async with self._lock:
            self.opened_at = dt_util.now()
            await self._save()
        await self.async_refresh_supply()

    async def async_refresh_supply(self) -> None:
        if not self.supply.enabled or self.opened_at is None:
            self.supply_status = None
            self._notify()
            return
        now = dt_util.now()
        feeds = await self._async_feeds(start=min(self.opened_at, now - timedelta(days=7)), end=now)
        self.supply_status = supply_status(settings=self.supply, opened_at=self.opened_at, feeds=feeds, now=now)
        already_open = any(not item.done and shopping.product_key(item.name) == shopping.product_key(self.supply.product_name) for item in self.state.items)
        if self.supply_status is not None and self.supply_status.low and self.listed_for != self.opened_at and not already_open:
            by = text(self.hass.config.language, 'supply_added_by')

            def change(state: ShoppingState) -> ShoppingState:
                added = shopping.add_item(state, text=self.supply.product_name, by=by, now=now, new_id=_new_id)
                newest = added.items[-1]
                return shopping.update_item(added, item_id=newest.item_id, category='baby') if newest.category != 'baby' else added

            self.listed_for = self.opened_at
            await self._change(change)
            return
        self._notify()

    async def _async_feeds(self, *, start: datetime, end: datetime) -> list[tuple[datetime, int]]:
        entity_id = self.supply.diary_entity
        try:
            response = await self.hass.services.async_call(
                domain='calendar', service='get_events',
                service_data={'entity_id': entity_id, 'start_date_time': start, 'end_date_time': end},
                blocking=True, return_response=True,
            )
        except HomeAssistantError:
            return []
        return feeds_from_events((response or {}).get(entity_id, {}).get('events', []))

    async def _change(self, change: Callable[[ShoppingState], ShoppingState]) -> None:
        async with self._lock:
            try:
                updated = change(self.state)
            except ListError as error:
                raise ServiceValidationError(str(error), translation_domain=DOMAIN, translation_key=error.key) from error
            if updated == self.state:
                return
            self.state = updated
            await self._save()
        self._notify()

    async def _save(self) -> None:
        await self._store.async_save(to_stored(state=self.state, supply=self.supply, opened_at=self.opened_at, listed_for=self.listed_for))

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def _watch_diary(self) -> None:
        if self._diary_unsubscribe is not None:
            self._diary_unsubscribe()
        self._diary_unsubscribe = async_track_state_change_event(hass=self.hass, entity_ids=[self.supply.diary_entity], action=self._async_diary_changed)

    async def _async_diary_changed(self, _event: Event) -> None:
        await self.async_refresh_supply()

    async def _async_refresh_tick(self, _moment: datetime) -> None:
        await self.async_refresh_supply()


def _new_id() -> str:
    return uuid.uuid4().hex


def supply_attributes(status: SupplyStatus | None, settings: SupplySettings) -> dict[str, Any]:
    base = {'enabled': settings.enabled, 'can_grams': settings.can_grams, 'grams_per_100ml': settings.grams_per_100ml, 'warn_days': settings.warn_days,
            'product_name': settings.product_name, 'diary_entity': settings.diary_entity}
    if status is None:
        return {**base, 'opened_at': None}
    return {
        **base, 'opened_at': dt_util.as_local(status.opened_at).isoformat(), 'used_grams': round(status.used_grams), 'left_grams': round(status.left_grams),
        'grams_per_day': round(status.grams_per_day), 'days_left': None if status.days_left is None else round(status.days_left, 1),
        'empty_at': None if status.empty_at is None else dt_util.as_local(status.empty_at).isoformat(), 'low': status.low,
    }
