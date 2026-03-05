"""DataUpdateCoordinator for Weerplaza Weather."""
import logging
from datetime import timedelta, datetime
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import WeerplazaApiClient, WeerplazaApiClientError, WeerplazaApiNoDataError
from .const import DOMAIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, CONF_LOCATION_PATH

_LOGGER = logging.getLogger(__name__)


class WeerplazaDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any] | None]):
    """Class to manage fetching Weerplaza data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: WeerplazaApiClient, # API client is now passed in
    ):
        """Initialize the coordinator."""
        self.config_entry = config_entry
        self.api_client = api_client
        self.location_path = config_entry.data[CONF_LOCATION_PATH]
        self._error_count = 0
        self._last_update_error = False
        self.last_update_success_timestamp = None
        self.last_data: Dict[str, Any] | None = None  # Initialize variable to store the last successful data

        # Get scan interval from options, fallback to data then default
        scan_interval_seconds = config_entry.options.get(
            CONF_SCAN_INTERVAL,
            config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"Weerplaza Coordinator {config_entry.title}",
            update_interval=timedelta(seconds=scan_interval_seconds),
        )

    @property
    def error_count(self) -> int:
        """Return the number of consecutive errors."""
        return self._error_count

    @property
    def last_update_error(self) -> bool:
        """Return if the last update resulted in an error."""
        return self._last_update_error

    async def _async_update_data(self) -> Dict[str, Any] | None:
        """Fetch data from API endpoint."""
        _LOGGER.debug("Fetching Weerplaza data for %s", self.location_path)
        try:
            # Returns dict on success, None if no message div found
            data = await self.api_client.async_scrape_data(self.location_path)

            if data is not None:
                self.last_update_success_timestamp = dt_util.now()
                # Only update self.last_data if the new data is different
                # This helps prevent unnecessary state updates if content hasn't changed
                if data != self.last_data:
                    self.last_data = data
                    _LOGGER.debug("New data fetched for %s", self.location_path)
                else:
                    _LOGGER.debug("Data has not changed since last update for %s", self.location_path)

            elif self.last_data is not None:
                _LOGGER.debug("No new data found, keeping last known data for %s", self.location_path)
                # If no new data is found but we have old data, return old data
                # This ensures sensors don't go 'unavailable' if the website temporarily has no content
                return self.last_data

            self._error_count = 0
            self._last_update_error = False
            return data # Return the fetched data (could be None if no data found initially)
        except WeerplazaApiNoDataError:
            # Valid scenario if location has no current warnings/forecasts, don't treat as failure
            _LOGGER.debug("No data/content found for %s, likely no current items.", self.location_path)
            self._error_count = 0
            self._last_update_error = False
            if self.last_data is not None:
                return self.last_data # Keep the last known data
            return None # Or return None if there was no previous data
        except WeerplazaApiClientError as err:
            self._error_count += 1
            self._last_update_error = True
            _LOGGER.error("Error communicating with/parsing weerplaza.nl for %s: %s", self.location_path, err)
            # Raise UpdateFailed so entities know update failed
            raise UpdateFailed(f"Error fetching/parsing data: {err}") from err
