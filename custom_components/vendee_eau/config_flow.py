"""Config flow for the Vendee Eau integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    VendeeEauAuthError,
    VendeeEauClient,
    VendeeEauConnectionError,
    VendeeEauDataError,
)
from .const import (
    DEFAULT_NAME,
    DOMAIN,
)


class VendeeEauConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vendee Eau."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = VendeeEauClient(
                async_get_clientsession(self.hass),
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )

            try:
                await client.authenticate()
            except VendeeEauAuthError:
                errors["base"] = "invalid_auth"
            except (VendeeEauConnectionError, VendeeEauDataError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
