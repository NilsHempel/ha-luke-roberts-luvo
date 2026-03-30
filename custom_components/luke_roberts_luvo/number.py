"""Number platform for Luke Roberts Luvo adaptive lighting parameters."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    COLOR_TEMP_MAX_KELVIN,
    COLOR_TEMP_MIN_KELVIN,
    DEFAULT_DAY_BRIGHTNESS,
    DEFAULT_DAY_COLOR_TEMP,
    DEFAULT_DAY_START_HOUR,
    DEFAULT_EVENING_START_HOUR,
    DEFAULT_NIGHT_BRIGHTNESS,
    DEFAULT_NIGHT_COLOR_TEMP,
    DEFAULT_NIGHT_HOUR,
    DOMAIN,
)
from .coordinator import LuvoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Luke Roberts Luvo number entities."""
    coordinator: LuvoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        LuvoAdaptiveNumber(
            coordinator, entry,
            key="day_start_hour",
            name="Adaptive Day Start",
            icon="mdi:weather-sunny",
            min_value=0,
            max_value=23,
            step=1,
            default=DEFAULT_DAY_START_HOUR,
            unit="h",
        ),
        LuvoAdaptiveNumber(
            coordinator, entry,
            key="evening_start_hour",
            name="Adaptive Evening Start",
            icon="mdi:weather-sunset",
            min_value=0,
            max_value=23,
            step=1,
            default=DEFAULT_EVENING_START_HOUR,
            unit="h",
        ),
        LuvoAdaptiveNumber(
            coordinator, entry,
            key="night_hour",
            name="Adaptive Night",
            icon="mdi:weather-night",
            min_value=0,
            max_value=23,
            step=1,
            default=DEFAULT_NIGHT_HOUR,
            unit="h",
        ),
        LuvoAdaptiveNumber(
            coordinator, entry,
            key="day_brightness",
            name="Adaptive Day Brightness",
            icon="mdi:brightness-7",
            min_value=1,
            max_value=100,
            step=5,
            default=DEFAULT_DAY_BRIGHTNESS,
            unit="%",
        ),
        LuvoAdaptiveNumber(
            coordinator, entry,
            key="night_brightness",
            name="Adaptive Night Brightness",
            icon="mdi:brightness-3",
            min_value=1,
            max_value=100,
            step=5,
            default=DEFAULT_NIGHT_BRIGHTNESS,
            unit="%",
        ),
        LuvoAdaptiveNumber(
            coordinator, entry,
            key="day_color_temp",
            name="Adaptive Day Color Temp",
            icon="mdi:thermometer",
            min_value=COLOR_TEMP_MIN_KELVIN,
            max_value=COLOR_TEMP_MAX_KELVIN,
            step=100,
            default=DEFAULT_DAY_COLOR_TEMP,
            unit="K",
        ),
        LuvoAdaptiveNumber(
            coordinator, entry,
            key="night_color_temp",
            name="Adaptive Night Color Temp",
            icon="mdi:thermometer-low",
            min_value=COLOR_TEMP_MIN_KELVIN,
            max_value=COLOR_TEMP_MAX_KELVIN,
            step=100,
            default=DEFAULT_NIGHT_COLOR_TEMP,
            unit="K",
        ),
    ])


class LuvoAdaptiveNumber(RestoreEntity, NumberEntity):
    """Number entity for an adaptive lighting parameter."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: LuvoCoordinator,
        entry: ConfigEntry,
        *,
        key: str,
        name: str,
        icon: str,
        min_value: float,
        max_value: float,
        step: float,
        default: float,
        unit: str,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._key = key
        self._default = default
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_value = default
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{entry.unique_id}_adaptive_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title or "Luke Roberts Luvo",
            connections={(dr.CONNECTION_BLUETOOTH, entry.unique_id)},
        )

    async def async_added_to_hass(self) -> None:
        """Restore previous value on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = float(last_state.state)
        # Register value with coordinator
        self._coordinator.adaptive_params[self._key] = self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        self._attr_native_value = value
        self._coordinator.adaptive_params[self._key] = value
        self.async_write_ha_state()
