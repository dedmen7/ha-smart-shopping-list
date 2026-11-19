"""Setup in the user interface; the options name the people who use the list."""

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import CONF_NAMES, DOMAIN


class ShoppingConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title='Smart Shopping List', data={})
        return self.async_show_form(step_id='user', data_schema=vol.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ShoppingOptionsFlow()


class ShoppingOptionsFlow(OptionsFlow):
    """One field per person who can log in: the name the list shows for them."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        users = [user for user in await self.hass.auth.async_get_users() if user.is_active and not user.system_generated]
        names = dict(self.config_entry.options.get(CONF_NAMES, {}))
        if user_input is not None:
            chosen = {user.id: str(user_input.get(user.name, '')).strip() for user in users}
            return self.async_create_entry(data={CONF_NAMES: {user_id: name for user_id, name in chosen.items() if name}})
        schema = {vol.Optional(user.name, default=names.get(user.id, user.name)): str for user in users}
        return self.async_show_form(step_id='init', data_schema=vol.Schema(schema))
