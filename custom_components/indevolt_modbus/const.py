"""Constants for the Indevolt integration."""

DOMAIN = "indevolt_modbus"
CONF_UNIT_ID = "unit_id"
DEFAULT_PORT = 8899
DEFAULT_UNIT_ID = 1
SCAN_INTERVAL = 30
CONF_FAST_POLL_INTERVAL = "fast_poll_interval"
CONF_MESSAGE_SPACING = "message_spacing"
MESSAGE_SPACING = 2
# Controls with documented meanings and useful user-facing ranges.
NUMBER_RANGES = {
    1138: (100, 10800),
    1142: (0, 100),
    1146: (0, 10800),
    1147: (0, 3600),
    1151: (0, 3600),
    1152: (0, 100),
    1154: (5, 100),
    7268: (0, 60),
    7270: (100, 2400),
}
SELECT_ADDRESSES = {1144, 1150, 7265}
SWITCH_ADDRESSES = {1143, 7266, 7267, 7272}
