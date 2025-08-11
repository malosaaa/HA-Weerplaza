"""Config flow for Weerplaza Weather integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    WeerplazaApiClient,
    WeerplazaApiConnectionError,
    WeerplazaApiNoDataError,
    WeerplazaApiParsingError,
    WeerplazaApiClientError,
)
from .const import (
    DOMAIN,
    CONF_LOCATION_PATH,
    CONF_INSTANCE_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Schema for user input step
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_INSTANCE_NAME): str,
    vol.Required(CONF_LOCATION_PATH): str,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
})


async def validate_input(hass, location_path: str) -> None:
    """Validate the user input allows us to connect and parse."""
    session = async_get_clientsession(hass)
    client = WeerplazaApiClient(session)
    # Perform a test scrape - raises exceptions on failure
    await client.async_scrape_data(location_path)


class WeerplazaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Weerplaza Weather."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            # Use location_path as unique ID for config entry to prevent duplicates
            unique_id = user_input[CONF_LOCATION_PATH].strip('/')
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                _LOGGER.info("Validating Weerplaza location path: %s", user_input[CONF_LOCATION_PATH])
                await validate_input(self.hass, user_input[CONF_LOCATION_PATH])
            except WeerplazaApiConnectionError:
                errors["base"] = "cannot_connect"
            except WeerplazaApiNoDataError:
                errors[CONF_LOCATION_PATH] = "invalid_location_path" # Specific error for 404 etc.
            except WeerplazaApiParsingError:
                errors["base"] = "parse_error" # Website structure might have changed
            except WeerplazaApiClientError:
                errors["base"] = "unknown_api_error"
            except Exception as e: # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during validation: %s", e)
                errors["base"] = "unknown"
            else:
                # Input validated, create entry with data and options
                return self.async_create_entry(
                    title=user_input[CONF_INSTANCE_NAME], # Use user's name for title
                    data={
                        CONF_INSTANCE_NAME: user_input[CONF_INSTANCE_NAME],
                        CONF_LOCATION_PATH: user_input[CONF_LOCATION_PATH],
                    },
                    options={
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    }
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    # Add Options Flow Handler for subsequent configuration
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return WeerplazaOptionsFlowHandler(config_entry)


class WeerplazaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Weerplaza Weather."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        # Load current options or provide defaults
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> config_entries.FlowResult:
        """Manage the main options step (scan interval)."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            if not isinstance(scan_interval, int) or scan_interval < MIN_SCAN_INTERVAL:
                errors[CONF_SCAN_INTERVAL] = "interval_too_short"
            else:
                self.options[CONF_SCAN_INTERVAL] = scan_interval
                _LOGGER.debug("Updating options for %s: %s", self.config_entry.entry_id, self.options)
                # Create the entry with the combined options
                return self.async_create_entry(title="", data=self.options)

        # Show form for scan interval
        schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
