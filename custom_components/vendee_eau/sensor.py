"""Sensors for the Vendee Eau integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .consumption import (
    consumption_points_count,
    consumption_rows,
    consumption_total,
    latest_consumption,
    latest_consumption_date,
)
from .const import ATTRIBUTION, DOMAIN
from .coordinator import VendeeEauDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class VendeeEauSensorDescription(SensorEntityDescription):
    """Description of a Vendee Eau sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _consumption_payload(data: dict[str, Any]) -> dict[str, Any]:
    consumption = data.get("consumption")
    if not isinstance(consumption, dict):
        return {}
    return consumption


def _context_value(data: dict[str, Any], key: str) -> Any:
    context = data.get("context")
    if not isinstance(context, dict):
        return None
    return context.get(key)


def _latest_consumption_value(data: dict[str, Any]) -> Any:
    return latest_consumption(_consumption_payload(data))


def _latest_consumption_date(data: dict[str, Any]) -> Any:
    return latest_consumption_date(_consumption_payload(data))


def _count_consumption_points(data: dict[str, Any]) -> int:
    return consumption_points_count(_consumption_payload(data))


def _consumption_total(data: dict[str, Any]) -> Any:
    return consumption_total(_consumption_payload(data))


SENSOR_DESCRIPTIONS: tuple[VendeeEauSensorDescription, ...] = (
    VendeeEauSensorDescription(
        key="abonnement_id",
        translation_key="abonnement_id",
        value_fn=lambda data: _context_value(data, "abonnement_id"),
    ),
    VendeeEauSensorDescription(
        key="point_installation_id",
        translation_key="point_installation_id",
        value_fn=lambda data: _context_value(data, "point_installation_id"),
    ),
    VendeeEauSensorDescription(
        key="equipement_id",
        translation_key="equipement_id",
        value_fn=lambda data: _context_value(data, "equipement_id"),
    ),
    VendeeEauSensorDescription(
        key="latest_consumption",
        translation_key="latest_consumption",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=_latest_consumption_value,
    ),
    VendeeEauSensorDescription(
        key="latest_consumption_date",
        translation_key="latest_consumption_date",
        value_fn=_latest_consumption_date,
    ),
    VendeeEauSensorDescription(
        key="consumption_points",
        translation_key="consumption_points",
        value_fn=_count_consumption_points,
    ),
    VendeeEauSensorDescription(
        key="consumption_total",
        translation_key="consumption_total",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        value_fn=_consumption_total,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vendee Eau sensors."""
    coordinator: VendeeEauDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        VendeeEauSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class VendeeEauSensor(CoordinatorEntity[VendeeEauDataUpdateCoordinator], SensorEntity):
    """Representation of a Vendee Eau sensor."""

    entity_description: VendeeEauSensorDescription
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VendeeEauDataUpdateCoordinator,
        entry: ConfigEntry,
        description: VendeeEauSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Vendee Eau",
        }
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return official consumption history on the main consumption sensor."""
        if self.entity_description.key != "latest_consumption":
            return None

        consumption = _consumption_payload(self.coordinator.data or {})
        rows = consumption_rows(consumption)
        if not rows:
            return None

        return {
            "history": rows,
            "dataset_label": rows[-1].get("label"),
        }
