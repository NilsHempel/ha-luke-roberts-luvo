"""DataUpdateCoordinator for Luke Roberts Luvo lamp."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_UUID,
    CMD_GET_SCENE,
    CMD_SET_BRIGHTNESS,
    CMD_SET_SCENE,
    DOMAIN,
    SCENE_LIST_END,
    SCENE_OFF,
    SCENE_ON_DEFAULT,
    SCENE_UUID,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)
SCENE_QUERY_TIMEOUT = 5.0


class LuvoCoordinator(DataUpdateCoordinator):
    """Coordinator for Luke Roberts Luvo BLE communication."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self._address: str = entry.unique_id
        self._scenes: dict[str, int] = {}
        self._current_scene_id: int | None = None
        self._current_scene_name: str | None = None
        self._brightness: int = 100
        self._is_on: bool = False
        self._scenes_loaded: bool = False
        self._lock = asyncio.Lock()

    def _get_ble_device(self):
        """Get the BLE device from HA's bluetooth integration."""
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._address.upper(), connectable=True
        )
        if not ble_device:
            raise UpdateFailed(f"Luvo lamp {self._address} not found via BLE")
        return ble_device

    async def _connect(self) -> BleakClient:
        """Establish a BLE connection."""
        ble_device = self._get_ble_device()
        client = await establish_connection(
            BleakClient, ble_device, ble_device.address
        )
        # Log all discovered services and characteristics for debugging
        for service in client.services:
            _LOGGER.debug("BLE Service: %s", service.uuid)
            for char in service.characteristics:
                _LOGGER.debug(
                    "  Characteristic: %s (properties: %s)",
                    char.uuid,
                    char.properties,
                )
        return client

    async def _enumerate_scenes(self, client: BleakClient) -> None:
        """Enumerate all scenes stored on the lamp via notification protocol."""
        self._scenes.clear()
        response_event = asyncio.Event()
        response_data: bytearray | None = None

        def notification_handler(_, data: bytearray) -> None:
            nonlocal response_data
            response_data = data
            response_event.set()

        await client.start_notify(API_UUID, notification_handler)

        try:
            next_scene_id = 0
            while next_scene_id != SCENE_LIST_END:
                response_event.clear()
                await client.write_gatt_char(
                    API_UUID,
                    CMD_GET_SCENE + bytes([next_scene_id]),
                    response=True,
                )

                try:
                    await asyncio.wait_for(
                        response_event.wait(), timeout=SCENE_QUERY_TIMEOUT
                    )
                except TimeoutError:
                    _LOGGER.warning(
                        "Timeout waiting for scene %d response", next_scene_id
                    )
                    break

                if response_data is None or len(response_data) < 4:
                    _LOGGER.warning("Invalid scene response: %s", response_data)
                    break

                status = response_data[0]
                if status != 0x00:
                    _LOGGER.debug("Scene query returned status %d, stopping", status)
                    break

                next_scene_id = response_data[2]
                scene_name = response_data[3:].decode("utf-8", errors="replace").strip()

                if scene_name:
                    current_id = next_scene_id if next_scene_id != SCENE_LIST_END else len(self._scenes) + 1
                    # The scene_id for setting is the index we queried, not the next_id
                    # We need to track which ID we asked for
                    self._scenes[scene_name] = len(self._scenes) + 1

                _LOGGER.debug(
                    "Found scene: '%s' (next=%d)", scene_name, next_scene_id
                )
        finally:
            await client.stop_notify(API_UUID)

        _LOGGER.info("Enumerated %d scenes: %s", len(self._scenes), list(self._scenes.keys()))

    def _build_service_dump(self, client: BleakClient) -> str:
        """Build a human-readable dump of all BLE services/characteristics."""
        lines = []
        for service in client.services:
            lines.append(f"Service: {service.uuid}")
            for char in service.characteristics:
                lines.append(f"  Char: {char.uuid} ({', '.join(char.properties)})")
        return "\n".join(lines) if lines else "No services discovered"

    async def _notify_diagnostic(self, message: str) -> None:
        """Create a persistent notification with diagnostic info."""
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "Luvo BLE Diagnostic",
                "message": message,
                "notification_id": "luvo_ble_diagnostic",
            },
        )

    async def _async_update_data(self) -> dict:
        """Poll the lamp for current state."""
        async with self._lock:
            try:
                client = await self._connect()
            except Exception as err:
                raise UpdateFailed(f"Could not connect to Luvo: {err}") from err

            try:
                # Diagnostic: dump all services and check for required characteristics
                service_dump = self._build_service_dump(client)
                _LOGGER.info("Luvo BLE services:\n%s", service_dump)

                api_char = None
                scene_char = None
                try:
                    api_char = client.services.get_characteristic(API_UUID)
                except Exception:
                    pass
                try:
                    scene_char = client.services.get_characteristic(SCENE_UUID)
                except Exception:
                    pass

                if not api_char or not scene_char:
                    diag_msg = (
                        f"**Required characteristics not found!**\n\n"
                        f"- API (`{API_UUID}`): {'FOUND' if api_char else 'MISSING'}\n"
                        f"- Scene (`{SCENE_UUID}`): {'FOUND' if scene_char else 'MISSING'}\n\n"
                        f"**Discovered services:**\n```\n{service_dump}\n```"
                    )
                    await self._notify_diagnostic(diag_msg)
                    raise UpdateFailed(
                        f"Required characteristics not found. "
                        f"API ({API_UUID}): {'found' if api_char else 'MISSING'}, "
                        f"Scene ({SCENE_UUID}): {'found' if scene_char else 'MISSING'}. "
                        f"Services dump sent to persistent notification."
                    )

                if not self._scenes_loaded:
                    await self._enumerate_scenes(client)
                    self._scenes_loaded = True

                scene_bytes = await client.read_gatt_char(SCENE_UUID)
                self._current_scene_id = scene_bytes[0] if scene_bytes else None
                self._is_on = self._current_scene_id != SCENE_OFF

                self._current_scene_name = None
                for name, sid in self._scenes.items():
                    if sid == self._current_scene_id:
                        self._current_scene_name = name
                        break
            except Exception as err:
                raise UpdateFailed(f"Error reading Luvo state: {err}") from err
            finally:
                await client.disconnect()

        return {
            "is_on": self._is_on,
            "brightness": self._brightness,
            "current_scene_id": self._current_scene_id,
            "current_scene_name": self._current_scene_name,
            "scenes": dict(self._scenes),
        }

    async def _send_command(self, command: bytes) -> None:
        """Send a BLE command to the lamp."""
        async with self._lock:
            try:
                client = await self._connect()
                try:
                    await client.write_gatt_char(API_UUID, command, response=True)
                finally:
                    await client.disconnect()
            except Exception as err:
                _LOGGER.error("Failed to send command to Luvo: %s", err)
                raise

    async def async_set_scene(self, scene_id: int) -> None:
        """Set the active scene."""
        await self._send_command(CMD_SET_SCENE + bytes([scene_id]))
        await self.async_request_refresh()

    async def async_set_brightness(self, brightness_pct: int) -> None:
        """Set brightness (0-100)."""
        brightness_pct = max(0, min(100, brightness_pct))
        await self._send_command(CMD_SET_BRIGHTNESS + bytes([brightness_pct]))
        self._brightness = brightness_pct
        await self.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the lamp on with default scene."""
        await self.async_set_scene(SCENE_ON_DEFAULT)

    async def async_turn_off(self) -> None:
        """Turn the lamp off."""
        await self.async_set_scene(SCENE_OFF)
