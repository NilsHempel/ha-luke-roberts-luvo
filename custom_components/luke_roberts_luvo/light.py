"""Light platform for Luke Roberts Luvo."""

from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COLOR_TEMP_MAX_KELVIN, COLOR_TEMP_MIN_KELVIN, DOMAIN, MANUFACTURER, MODEL
from .coordinator import LuvoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Luke Roberts Luvo light."""
    coordinator: LuvoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LuvoLight(coordinator, entry)])


class LuvoLight(CoordinatorEntity[LuvoCoordinator], LightEntity):
    """Light entity for Luke Roberts Luvo."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_min_color_temp_kelvin = COLOR_TEMP_MIN_KELVIN
    _attr_max_color_temp_kelvin = COLOR_TEMP_MAX_KELVIN

    def __init__(self, coordinator: LuvoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title or "Luke Roberts Luvo",
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={(dr.CONNECTION_BLUETOOTH, entry.unique_id)},
        )

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self.coordinator.data.get("is_on", False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness (0-255)."""
        pct = self.coordinator.data.get("brightness", 100)
        return round(pct * 255 / 100)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        return self.coordinator.data.get("color_temp_kelvin")

    @property
    def effect_list(self) -> list[str]:
        """Return the list of available scenes as effects."""
        scenes = self.coordinator.data.get("scenes", {})
        return list(scenes.keys())

    @property
    def effect(self) -> str | None:
        """Return the current active scene."""
        return self.coordinator.data.get("current_scene_name")

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the light."""
        if ATTR_EFFECT in kwargs:
            scene_name = kwargs[ATTR_EFFECT]
            scenes = self.coordinator.data.get("scenes", {})
            scene_id = scenes.get(scene_name)
            if scene_id is not None:
                await self.coordinator.async_set_scene(scene_id)
                return

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            await self.coordinator.async_set_color_temp_kelvin(
                kwargs[ATTR_COLOR_TEMP_KELVIN]
            )

        if ATTR_BRIGHTNESS in kwargs:
            pct = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)
            await self.coordinator.async_set_brightness(pct)
            return

        if not kwargs:
            await self.coordinator.async_turn_on()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the light."""
        await self.coordinator.async_turn_off()
