"""The Luke Roberts Luvo integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .config_flow import _friendly_name
from .const import DOMAIN
from .coordinator import LuvoCoordinator

PLATFORMS = [Platform.LIGHT, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Luke Roberts Luvo from a config entry."""
    # Fix title if it's a raw MAC address from initial discovery
    friendly = _friendly_name(entry.title)
    if friendly != entry.title:
        hass.config_entries.async_update_entry(entry, title=friendly)

    coordinator = LuvoCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
