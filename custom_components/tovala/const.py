"""Constants for the Tovala Smart Oven integration."""
from typing import Final

DOMAIN: Final = "tovala"

# Configuration constants
CONF_OVEN_ID: Final = "oven_id"

# Platforms
PLATFORMS: Final = ["sensor", "binary_sensor", "switch"]

# Default values
DEFAULT_SCAN_INTERVAL: Final = 10  # seconds

# Events
EVENT_TIMER_FINISHED: Final = "tovala_timer_finished"

# API constants
API_TIMEOUT: Final = 10
TOKEN_EXPIRY_BUFFER: Final = 60  # seconds before expiry to refresh
