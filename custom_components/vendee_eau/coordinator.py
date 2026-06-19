"""Data coordinator for the Vendee Eau integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    VendeeEauAuthError,
    VendeeEauClient,
    VendeeEauConnectionError,
    VendeeEauDataError,
)
from .const import (
    CONF_ABONNEMENT_ID,
    CONF_EQUIPEMENT_ID,
    CONF_POINT_INSTALLATION_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class VendeeEauDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Vendee Eau data updates."""

    def __init__(self, hass: HomeAssistant, entry_data: dict[str, Any]) -> None:
        self.client = VendeeEauClient(
            async_get_clientsession(hass),
            username=entry_data["username"],
            password=entry_data["password"],
            point_installation_id=entry_data.get(CONF_POINT_INSTALLATION_ID),
            equipement_id=entry_data.get(CONF_EQUIPEMENT_ID),
            abonnement_id=entry_data.get(CONF_ABONNEMENT_ID),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_data()
        except VendeeEauAuthError as err:
            raise UpdateFailed("Authentication failed") from err
        except (VendeeEauConnectionError, VendeeEauDataError) as err:
            raise UpdateFailed(str(err)) from err
