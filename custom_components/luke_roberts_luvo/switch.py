"""Switch platform for Luke Roberts Luvo adaptive lighting."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import LuvoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Luke Roberts Luvo adaptive lighting switch."""
    coordinator: LuvoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LuvoAdaptiveLightingSwitch(coordinator, entry)])


class LuvoAdaptiveLightingSwitch(RestoreEntity, SwitchEntity):
    """Switch to enable/disable adaptive lighting schedule."""

    _attr_has_entity_name = True
    _attr_name = "Adaptive Lighting"
    _attr_icon = "mdi:theme-light-dark"

    def __init__(self, coordinator: LuvoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.unique_id}_adaptive_lighting"
        self._attr_is_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title or "Luke Roberts Luvo",
            connections={(dr.CONNECTION_BLUETOOTH, entry.unique_id)},
        )

    async def async_added_to_hass(self) -> None:
        """Restore previous state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state == "on":
            self._attr_is_on = True
        self._coordinator.adaptive_enabled = self._attr_is_on
        if self._attr_is_on:
            self._coordinator.start_adaptive_lighting()

    async def async_turn_on(self, **kwargs) -> None:
        """Enable adaptive lighting."""
        self._attr_is_on = True
        self._coordinator.adaptive_enabled = True
        self._coordinator.start_adaptive_lighting()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable adaptive lighting."""
        self._attr_is_on = False
        self._coordinator.adaptive_enabled = False
        self._coordinator.stop_adaptive_lighting()
        self.async_write_ha_state()
