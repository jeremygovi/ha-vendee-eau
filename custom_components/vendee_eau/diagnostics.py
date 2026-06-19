"""Diagnostics support for Vendee Eau."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
    "password",
    "username",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": {
            key: "**REDACTED**" if key in TO_REDACT else value
            for key, value in entry.data.items()
        },
        "last_update_success": coordinator.last_update_success,
        "data_keys": sorted((coordinator.data or {}).keys()),
        "context": (coordinator.data or {}).get("context"),
    }
