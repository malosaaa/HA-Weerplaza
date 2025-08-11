"""Constants for the Weerplaza Weather integration."""
from typing import Final
from datetime import timedelta
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

DOMAIN: Final = "weerplaza"
PLATFORMS: Final[list[str]] = ["sensor"]
MANUFACTURER: Final = "Weerplaza"

# Configuration Keys
CONF_LOCATION_PATH: Final = "location_path"
CONF_INSTANCE_NAME: Final = "instance_name" # User-defined name for the device/instance
CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL: Final = 300  # seconds (5 minutes)
MIN_SCAN_INTERVAL: Final = 60      # seconds

# API Details
BASE_URL: Final = "https://www.weerplaza.nl/"
API_TIMEOUT: Final = 20 # Increased timeout for scraping

# Data Keys from scraping (used for sensor selection and attributes)
# These should match the keys returned by the api.py parser
SCRAPED_DATA_KEYS: Final[list[str]] = [
    "warnings",          # List of warning dicts
    "flash_message",     # Dict for flash message
    "hourly_forecast",   # List of hourly forecast dicts
    "daily_forecast",    # List of daily forecast dicts
    "current_temperature", # Extracted from hourly forecast for main sensor state
]

# Sensor configuration schema (if you wanted to allow enabling/disabling specific sensors)
# For simplicity, we'll just expose all data as attributes of a few main sensors.
# SENSOR_SCHEMA = vol.Schema({
#     vol.Optional(key, default=True): cv.boolean
#     for key in SCRAPED_DATA_KEYS
# })

# Diagnostics
DIAG_CONFIG_ENTRY = "config_entry"
DIAG_OPTIONS = "options"
DIAG_COORDINATOR_DATA = "coordinator_data"
