import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN, CONF_LOCATION_PATH, CONF_INSTANCE_NAME, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

class WeerplazaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_INSTANCE_NAME, default="My Location"): cv.string,
                    vol.Required(CONF_LOCATION_PATH, default="nederland/utrecht/19344"): cv.string,
                    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=60)),
                    vol.Optional("debug_mode", default=False): cv.boolean,
                })
            )

        unique_id = user_input[CONF_LOCATION_PATH].strip('/')
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title=user_input[CONF_INSTANCE_NAME], data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WeerplazaOptionsFlowHandler(config_entry)


class WeerplazaOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        # FIX: Uses underscore to prevent HA protected property crash
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, 
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        debug_mode = self._config_entry.options.get(
            "debug_mode",
            self._config_entry.data.get("debug_mode", False)
        )

        schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): vol.All(vol.Coerce(int), vol.Range(min=60)),
            vol.Optional("debug_mode", default=debug_mode): cv.boolean,
        })

        return self.async_show_form(step_id="init", data_schema=schema)
