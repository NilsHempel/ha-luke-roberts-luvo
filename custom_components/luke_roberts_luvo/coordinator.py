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
    CMD_INTERMEDIATE,
    CMD_SET_BRIGHTNESS,
    CMD_SET_SCENE,
    COLOR_TEMP_MAX_KELVIN,
    COLOR_TEMP_MIN_KELVIN,
    CONTENT_DOWNLIGHT,
    CONTENT_UPLIGHT,
    DOMAIN,
    DURATION_PERMANENT,
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

        # Uplight state (HSB) — None means "unknown / scene-controlled"
        self._uplight_brightness: int | None = None
        self._uplight_hue: int | None = None
        self._uplight_saturation: int | None = None

        # Downlight state (color temp + brightness) — None means "unknown / scene-controlled"
        self._downlight_brightness: int | None = None
        self._downlight_color_temp: int | None = None

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
            queried_id = 0
            while True:
                response_event.clear()
                await client.write_gatt_char(
                    API_UUID,
                    CMD_GET_SCENE + bytes([queried_id]),
                    response=True,
                )

                try:
                    await asyncio.wait_for(
                        response_event.wait(), timeout=SCENE_QUERY_TIMEOUT
                    )
                except TimeoutError:
                    _LOGGER.warning(
                        "Timeout waiting for scene %d response", queried_id
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
                    self._scenes[scene_name] = queried_id

                _LOGGER.debug(
                    "Found scene: '%s' (id=%d, next=%d)",
                    scene_name, queried_id, next_scene_id,
                )

                if next_scene_id == SCENE_LIST_END:
                    break
                queried_id = next_scene_id
        finally:
            await client.stop_notify(API_UUID)

        _LOGGER.info("Enumerated %d scenes: %s", len(self._scenes), self._scenes)

    async def _async_update_data(self) -> dict:
        """Poll the lamp for current state."""
        async with self._lock:
            try:
                client = await self._connect()
            except Exception as err:
                raise UpdateFailed(f"Could not connect to Luvo: {err}") from err

            try:
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
            "uplight_brightness": self._uplight_brightness,
            "uplight_hue": self._uplight_hue,
            "uplight_saturation": self._uplight_saturation,
            "downlight_brightness": self._downlight_brightness,
            "downlight_color_temp": self._downlight_color_temp,
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

    def _clear_intermediate_state(self) -> None:
        """Clear locally-tracked uplight/downlight state after a scene change."""
        self._uplight_hue = None
        self._uplight_saturation = None
        self._uplight_brightness = None
        self._downlight_color_temp = None
        self._downlight_brightness = None

    async def async_set_scene(self, scene_id: int) -> None:
        """Set the active scene and clear intermediate state."""
        await self._send_command(CMD_SET_SCENE + bytes([scene_id]))
        self._clear_intermediate_state()
        self._is_on = scene_id != SCENE_OFF
        self._current_scene_id = scene_id
        if self.data:
            self.data["is_on"] = self._is_on
        await self.async_request_refresh()

    async def async_turn_on_lamp(self) -> None:
        """Turn the lamp on with default scene without clearing intermediate state.

        Used internally before sending intermediate uplight/downlight commands
        so that state set right after turn-on is not wiped.
        Includes a short pause to let the lamp process the scene before the
        intermediate command is sent.
        """
        await self._send_command(CMD_SET_SCENE + bytes([SCENE_ON_DEFAULT]))
        self._is_on = True
        if self.data:
            self.data["is_on"] = True
        await asyncio.sleep(0.5)

    async def async_set_brightness(self, brightness_pct: int) -> None:
        """Set overall brightness (0-100)."""
        brightness_pct = max(0, min(100, brightness_pct))
        await self._send_command(CMD_SET_BRIGHTNESS + bytes([brightness_pct]))
        self._brightness = brightness_pct
        await self.async_request_refresh()

    async def async_set_uplight(
        self, hue: int, saturation: int, brightness: int
    ) -> None:
        """Set uplight HSB color permanently.

        hue: 0-65535 (maps to 0-360 degrees)
        saturation: 0-255
        brightness: 0-100
        """
        hue = max(0, min(65535, hue))
        saturation = max(0, min(255, saturation))
        brightness = max(0, min(100, brightness))
        cmd = (
            CMD_INTERMEDIATE
            + bytes([CONTENT_UPLIGHT])
            + DURATION_PERMANENT
            + bytes([saturation])
            + hue.to_bytes(2, byteorder="big")
            + bytes([brightness])
        )
        _LOGGER.debug(
            "Uplight command: hue=%d sat=%d bri=%d -> %s",
            hue, saturation, brightness, cmd.hex(),
        )
        await self._send_command(cmd)
        self._uplight_hue = hue
        self._uplight_saturation = saturation
        self._uplight_brightness = brightness
        await self.async_request_refresh()

    async def async_set_downlight(self, kelvin: int, brightness: int) -> None:
        """Set downlight color temperature and brightness permanently.

        kelvin: 2700-4000
        brightness: 0-100
        """
        kelvin = max(COLOR_TEMP_MIN_KELVIN, min(COLOR_TEMP_MAX_KELVIN, kelvin))
        brightness = max(0, min(100, brightness))
        cmd = (
            CMD_INTERMEDIATE
            + bytes([CONTENT_DOWNLIGHT])
            + DURATION_PERMANENT
            + kelvin.to_bytes(2, byteorder="big")
            + bytes([brightness])
        )
        _LOGGER.debug(
            "Downlight command: kelvin=%d bri=%d -> %s",
            kelvin, brightness, cmd.hex(),
        )
        await self._send_command(cmd)
        self._downlight_color_temp = kelvin
        self._downlight_brightness = brightness
        await self.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the lamp on with default scene (clears intermediate state)."""
        await self.async_set_scene(SCENE_ON_DEFAULT)

    async def async_turn_off(self) -> None:
        """Turn the lamp off."""
        await self.async_set_scene(SCENE_OFF)
