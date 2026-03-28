# Luke Roberts Luvo - Home Assistant Integration

Custom Home Assistant integration for the [Luke Roberts Luvo](https://luke-roberts.com) ceiling lamp via Bluetooth Low Energy (BLE).

## Features

- **Scene switching** - Select any scene stored on the lamp
- **On/Off control** - Turn the lamp on and off
- **Brightness control** - Adjust overall brightness (0-100%)
- **Auto-discovery** - Automatically detects the lamp via BLE
- **HACS compatible** - Easy installation via HACS

## Requirements

- Home Assistant 2024.5.0 or newer
- Bluetooth adapter (built-in on Raspberry Pi 4/5)
- Luke Roberts Luvo lamp within BLE range

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) and select **Custom repositories**
3. Add `https://github.com/nilshempel/ha-luke-roberts-luvo` as an **Integration**
4. Search for "Luke Roberts Luvo" and install it
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/luke_roberts_luvo` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

After installation, the lamp should be automatically discovered if it's powered on and within BLE range. You can also add it manually:

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "Luke Roberts Luvo"
3. Select your lamp from the list

## Entities

The integration creates the following entities for each lamp:

| Entity | Type | Description |
|--------|------|-------------|
| Light | `light` | Main light entity with on/off, brightness, and scene selection (via effects) |
| Scene | `select` | Dedicated scene picker for easy switching |

### Scenes

Scenes stored on the lamp are automatically enumerated at startup. They appear as:
- **Effects** on the light entity (use the effect dropdown in the light card)
- **Options** on the scene select entity

To update the scene list after changing scenes in the Luke Roberts app, reload the integration.

## BLE Protocol

This integration communicates directly with the lamp via BLE GATT. No cloud, no bridge, no additional hardware required.

- **Service UUID**: `44092840-0567-11e6-b862-0002a5d5c51b`
- **Chip**: Nordic nRF52832 (Bluetooth 4.2)
