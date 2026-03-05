import logging
import os
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import Platform
from .const import DOMAIN, DEBUG_FILE_NAME
from .coordinator import WeerplazaCoordinator
from .cache import PersistentCache

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    cache = PersistentCache(hass, f"{DOMAIN}_{entry.entry_id}")
    initial_data = await cache.load()

    coordinator = WeerplazaCoordinator(
        hass,
        config_entry=entry,
        cache=cache,
        initial_data=initial_data
    )

    # --- L1 PERSISTENCE LOGIC ---
    if initial_data:
        # This is the "magic" line. It populates the coordinator 
        # BEFORE the sensors are even registered.
        coordinator.async_set_updated_data(initial_data)
        _LOGGER.info("Weerplaza initialized from persistent cache")
    else:
        _LOGGER.warning("No cache found for Weerplaza. Fetching initial data...")
        await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # --- Register Service Calls ---
    async def handle_manual_refresh(call: ServiceCall):
        await coordinator.async_request_refresh()

    async def handle_clear_cache(call: ServiceCall):
        await cache.clear()
        _LOGGER.info("Weerplaza cache cleared")

    hass.services.async_register(DOMAIN, "manual_refresh", handle_manual_refresh)
    hass.services.async_register(DOMAIN, "clear_cache", handle_clear_cache)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
