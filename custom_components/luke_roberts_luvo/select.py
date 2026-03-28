"""Select platform for Luke Roberts Luvo scene switching."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LuvoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Luke Roberts Luvo scene select."""
    coordinator: LuvoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LuvoSceneSelect(coordinator, entry)])


class LuvoSceneSelect(CoordinatorEntity[LuvoCoordinator], SelectEntity):
    """Select entity for Luvo scene switching."""

    _attr_has_entity_name = True
    _attr_name = "Scene"
    _attr_icon = "mdi:palette"

    def __init__(self, coordinator: LuvoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the scene select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_scene"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
        )

    @property
    def options(self) -> list[str]:
        """Return the list of available scenes."""
        scenes = self.coordinator.data.get("scenes", {})
        return list(scenes.keys()) if scenes else ["Unknown"]

    @property
    def current_option(self) -> str | None:
        """Return the currently active scene."""
        return self.coordinator.data.get("current_scene_name")

    async def async_select_option(self, option: str) -> None:
        """Set the selected scene."""
        scenes = self.coordinator.data.get("scenes", {})
        scene_id = scenes.get(option)
        if scene_id is not None:
            await self.coordinator.async_set_scene(scene_id)
