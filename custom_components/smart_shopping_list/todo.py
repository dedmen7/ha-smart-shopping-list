"""The list as a regular Home Assistant to-do list, so voice assistants and the To-do view keep working."""

from homeassistant.components.todo import TodoItem, TodoItemStatus, TodoListEntity, TodoListEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ShoppingConfigEntry
from .manager import ShoppingManager
from .shopping import parse_entry
from .texts import item_description


async def async_setup_entry(hass: HomeAssistant, entry: ShoppingConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([ShoppingTodoList(entry.runtime_data)])


class ShoppingTodoList(TodoListEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = 'list'
    _attr_unique_id = 'smart_shopping_list_todo'
    _attr_supported_features = TodoListEntityFeature.CREATE_TODO_ITEM | TodoListEntityFeature.UPDATE_TODO_ITEM | TodoListEntityFeature.DELETE_TODO_ITEM

    def __init__(self, manager: ShoppingManager) -> None:
        self.manager = manager
        self.entity_id = 'todo.smart_shopping_list'

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.manager.async_add_listener(self.async_write_ha_state))

    @property
    def todo_items(self) -> list[TodoItem]:
        """Each item with who added it, or who bought it and when, as the description shown under it."""
        language, now = self.hass.config.language, dt_util.now()
        return [
            TodoItem(
                uid=item.item_id, summary=(str(item.quantity) + '× ' if item.quantity > 1 else '') + item.name,
                status=TodoItemStatus.COMPLETED if item.done else TodoItemStatus.NEEDS_ACTION,
                description=item_description(item, language=language, now=now),
            )
            for item in self.manager.state.items
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self.manager.async_add(text_entry=item.summary or '', context=self._context)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        current = next(entry for entry in self.manager.state.items if entry.item_id == item.uid)
        if item.summary is not None:
            quantity, name = parse_entry(item.summary.replace('×', 'x'))
            if (name, quantity) != (current.name, current.quantity):
                await self.manager.async_update(item_id=item.uid, name=name, quantity=quantity, category=None)
        if item.status == TodoItemStatus.COMPLETED and not current.done:
            await self.manager.async_complete(item_id=item.uid, context=self._context)
        elif item.status == TodoItemStatus.NEEDS_ACTION and current.done:
            await self.manager.async_reopen(item_id=item.uid)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        await self.manager.async_remove(item_ids=uids)
