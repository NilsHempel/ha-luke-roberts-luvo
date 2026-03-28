"""Light platform for Luke Roberts Luvo."""

from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
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
    """Set up Luke Roberts Luvo lights."""
    coordinator: LuvoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        LuvoUplight(coordinator, entry),
        LuvoDownlight(coordinator, entry),
    ])


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Shared device info for all entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.title or "Luke Roberts Luvo",
        manufacturer=MANUFACTURER,
        model=MODEL,
        connections={(dr.CONNECTION_BLUETOOTH, entry.unique_id)},
    )


class LuvoUplight(CoordinatorEntity[LuvoCoordinator], LightEntity):
    """Uplight entity (RGB/HS color + brightness + scenes)."""

    _attr_has_entity_name = True
    _attr_name = "Uplight"
    _attr_supported_color_modes = {ColorMode.HS}
    _attr_color_mode = ColorMode.HS
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, coordinator: LuvoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the uplight."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_uplight"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        """Return true if the lamp is on."""
        return self.coordinator.data.get("is_on", False)

    @property
    def brightness(self) -> int | None:
        """Return the uplight brightness (0-255)."""
        pct = self.coordinator.data.get("uplight_brightness", 100)
        return round(pct * 255 / 100)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the uplight HS color."""
        hue_raw = self.coordinator.data.get("uplight_hue", 0)
        sat_raw = self.coordinator.data.get("uplight_saturation", 0)
        # Convert from device range to HA range
        # Device hue: 0-65535 -> HA hue: 0-360
        # Device sat: 0-255 -> HA sat: 0-100
        ha_hue = hue_raw * 360 / 65535
        ha_sat = sat_raw * 100 / 255
        return (ha_hue, ha_sat)

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
        """Turn on the uplight."""
        if ATTR_EFFECT in kwargs:
            scene_name = kwargs[ATTR_EFFECT]
            scenes = self.coordinator.data.get("scenes", {})
            scene_id = scenes.get(scene_name)
            if scene_id is not None:
                await self.coordinator.async_set_scene(scene_id)
                return

        # Gather current state for defaults
        hue_raw = self.coordinator.data.get("uplight_hue", 0)
        sat_raw = self.coordinator.data.get("uplight_saturation", 0)
        bri_pct = self.coordinator.data.get("uplight_brightness", 100)

        if ATTR_HS_COLOR in kwargs:
            ha_hue, ha_sat = kwargs[ATTR_HS_COLOR]
            hue_raw = round(ha_hue * 65535 / 360)
            sat_raw = round(ha_sat * 255 / 100)

        if ATTR_BRIGHTNESS in kwargs:
            bri_pct = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)

        if ATTR_HS_COLOR in kwargs or ATTR_BRIGHTNESS in kwargs:
            # If lamp is off, turn on first before sending intermediate command
            if not self.coordinator.data.get("is_on"):
                await self.coordinator.async_turn_on_lamp()
            await self.coordinator.async_set_uplight(hue_raw, sat_raw, bri_pct)
            return

        # Plain turn on: restore last manual uplight state if available, else default scene
        if (
            self.coordinator._uplight_hue is not None
            and self.coordinator._uplight_saturation is not None
            and self.coordinator._uplight_brightness is not None
        ):
            if not self.coordinator.data.get("is_on"):
                await self.coordinator.async_turn_on_lamp()
            await self.coordinator.async_set_uplight(
                self.coordinator._uplight_hue,
                self.coordinator._uplight_saturation,
                self.coordinator._uplight_brightness,
            )
        else:
            await self.coordinator.async_turn_on()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the lamp."""
        await self.coordinator.async_turn_off()


class LuvoDownlight(CoordinatorEntity[LuvoCoordinator], LightEntity):
    """Downlight entity (color temperature + brightness)."""

    _attr_has_entity_name = True
    _attr_name = "Downlight"
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_min_color_temp_kelvin = COLOR_TEMP_MIN_KELVIN
    _attr_max_color_temp_kelvin = COLOR_TEMP_MAX_KELVIN

    def __init__(self, coordinator: LuvoCoordinator, entry: ConfigEntry) -> None:
        """Initialize the downlight."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_downlight"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool:
        """Return true if the lamp is on."""
        return self.coordinator.data.get("is_on", False)

    @property
    def brightness(self) -> int | None:
        """Return the downlight brightness (0-255)."""
        pct = self.coordinator.data.get("downlight_brightness", 100)
        return round(pct * 255 / 100)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the downlight color temperature in Kelvin."""
        return self.coordinator.data.get("downlight_color_temp")

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the downlight."""
        kelvin = self.coordinator.data.get("downlight_color_temp", COLOR_TEMP_MIN_KELVIN)
        bri_pct = self.coordinator.data.get("downlight_brightness", 100)

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]

        if ATTR_BRIGHTNESS in kwargs:
            bri_pct = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)

        if ATTR_COLOR_TEMP_KELVIN in kwargs or ATTR_BRIGHTNESS in kwargs:
            # If lamp is off, turn on first before sending intermediate command
            if not self.coordinator.data.get("is_on"):
                await self.coordinator.async_turn_on_lamp()
            await self.coordinator.async_set_downlight(kelvin, bri_pct)
            return

        # Plain turn on: restore last manual downlight state if available, else default scene
        if (
            self.coordinator._downlight_color_temp is not None
            and self.coordinator._downlight_brightness is not None
        ):
            if not self.coordinator.data.get("is_on"):
                await self.coordinator.async_turn_on_lamp()
            await self.coordinator.async_set_downlight(
                self.coordinator._downlight_color_temp,
                self.coordinator._downlight_brightness,
            )
        else:
            await self.coordinator.async_turn_on()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the lamp."""
        await self.coordinator.async_turn_off()
