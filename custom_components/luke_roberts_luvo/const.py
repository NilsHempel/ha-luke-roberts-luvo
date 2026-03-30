"""Constants for the Luke Roberts Luvo integration."""

DOMAIN = "luke_roberts_luvo"

# BLE GATT UUIDs
SERVICE_UUID = "44092840-0567-11e6-b862-0002a5d5c51b"
API_UUID = "44092842-0567-11e6-b862-0002a5d5c51b"
SCENE_UUID = "44092844-0567-11e6-b862-0002a5d5c51b"

# Command prefixes (all start with 0xA0)
CMD_GET_SCENE = bytes([0xA0, 0x01, 0x01])
CMD_SET_SCENE = bytes([0xA0, 0x02, 0x05])
CMD_SET_BRIGHTNESS = bytes([0xA0, 0x01, 0x03])
CMD_SET_COLOR_TEMP = bytes([0xA0, 0x01, 0x04])

# Intermediate light command: 0xA0 0x01 0x02 <content_flag> <dur_hi> <dur_lo> ...
# content_flag 0x01 = uplight (HSB), content_flag 0x02 = downlight (kelvin)
CMD_INTERMEDIATE = bytes([0xA0, 0x01, 0x02])
CONTENT_UPLIGHT = 0x01
CONTENT_DOWNLIGHT = 0x02

# Duration 0x0000 = permanent override (until next scene change)
DURATION_PERMANENT = bytes([0x00, 0x00])

# Color temperature range (Kelvin) for the downlight
COLOR_TEMP_MIN_KELVIN = 2700
COLOR_TEMP_MAX_KELVIN = 4000

# Special scene IDs
SCENE_OFF = 0x00
SCENE_ON_DEFAULT = 0xFF
SCENE_LIST_END = 0xFF

MANUFACTURER = "Luke Roberts"
MODEL = "Luvo"

# Adaptive lighting defaults
DEFAULT_DAY_START_HOUR = 8
DEFAULT_EVENING_START_HOUR = 18
DEFAULT_NIGHT_HOUR = 22
DEFAULT_DAY_BRIGHTNESS = 100
DEFAULT_NIGHT_BRIGHTNESS = 10
DEFAULT_DAY_COLOR_TEMP = COLOR_TEMP_MAX_KELVIN  # 4000K
DEFAULT_NIGHT_COLOR_TEMP = COLOR_TEMP_MIN_KELVIN  # 2700K
ADAPTIVE_UPDATE_INTERVAL = 300  # seconds (5 minutes)
