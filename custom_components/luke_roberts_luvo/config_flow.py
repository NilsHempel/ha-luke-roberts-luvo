"""Config flow for Luke Roberts Luvo integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Luke Roberts Luvo"


def _is_mac_address(name: str) -> bool:
    """Check if a name looks like a MAC address."""
    parts = name.replace("-", ":").split(":")
    return len(parts) == 6 and all(len(p) == 2 for p in parts)


def _friendly_name(raw_name: str | None) -> str:
    """Return a friendly name, falling back to default if name is missing or a MAC."""
    if not raw_name or _is_mac_address(raw_name):
        return DEFAULT_NAME
    return raw_name


class LuvoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Luke Roberts Luvo."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle a Bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address.upper())
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm Bluetooth discovery."""
        if user_input is not None:
            title = _friendly_name(self._discovery_info.name)
            return self.async_create_entry(title=title, data={})

        self._set_confirm_only()
        name = _friendly_name(self._discovery_info.name)
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup by the user."""
        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address.upper())
            self._abort_if_unique_id_configured()

            # Find the discovery info for the selected device
            for info in async_discovered_service_info(self.hass):
                if info.address.upper() == address.upper():
                    title = _friendly_name(info.name)
                    return self.async_create_entry(title=title, data={})

            return self.async_create_entry(title=DEFAULT_NAME, data={})

        # Scan for available Luvo lamps
        devices: dict[str, str] = {}
        for info in async_discovered_service_info(self.hass):
            if SERVICE_UUID in [str(u).lower() for u in info.service_uuids]:
                name = info.name or info.address
                devices[info.address.upper()] = f"{name} ({info.address})"

        if not devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("address"): vol.In(devices)}
            ),
        )
