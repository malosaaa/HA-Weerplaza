"""The Weerplaza Weather integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WeerplazaApiClient
from .const import DOMAIN, CONF_LOCATION_PATH, PLATFORMS, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL
from .coordinator import WeerplazaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weerplaza Weather from a config entry."""
    _LOGGER.debug("Setting up Weerplaza Weather entry: %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})

    location_path = entry.data[CONF_LOCATION_PATH]
    
    # Create the API client instance and pass the Home Assistant aiohttp_client session.
    # This is the correct and recommended way to get the client session for external HTTP requests
    # in Home Assistant integrations.
    api_client = WeerplazaApiClient(hass.async_create_clientsession())

    # Get scan interval from options, fallback to data then default
    scan_interval_seconds = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    coordinator = WeerplazaDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        api_client=api_client, # Pass the api_client instance here
    )

    # Store the config entry in the coordinator (you might need this later)
    # This line is redundant as config_entry is already passed to coordinator's __init__
    # coordinator.config_entry = entry

    # Fetch initial data so we have it when entities are set up
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms (sensor)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up listener for options updates (scan interval)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Weerplaza Weather entry: %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Successfully unloaded Weerplaza Weather entry: %s", entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Reloading Weerplaza Weather entry due to options update: %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id) # Reload entry to apply new options
