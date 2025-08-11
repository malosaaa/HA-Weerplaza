"""Sensor platform for Weerplaza Weather integration."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import slugify # For creating clean unique IDs

from .const import (
    DOMAIN,
    CONF_INSTANCE_NAME,
    SCRAPED_DATA_KEYS,
)
from .coordinator import WeerplazaDataUpdateCoordinator
from .entity import WeerplazaBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Weerplaza sensor platform."""
    coordinator: WeerplazaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    instance_name_slug = slugify(entry.data[CONF_INSTANCE_NAME])

    entities = []

    # Main sensor for current conditions (e.g., current temperature)
    entities.append(WeerplazaMainSensor(coordinator, instance_name_slug))

    # Sensor for Warnings
    entities.append(WeerplazaWarningSensor(coordinator, instance_name_slug))

    # Sensor for Flash Message
    entities.append(WeerplazaFlashMessageSensor(coordinator, instance_name_slug))

    # Sensor for Hourly Forecast (as attributes)
    entities.append(WeerplazaHourlyForecastSensor(coordinator, instance_name_slug))

    # Sensor for Daily Forecast (as attributes)
    entities.append(WeerplazaDailyForecastSensor(coordinator, instance_name_slug))

    # Add diagnostic sensors
    entities.extend([
        WeerplazaDiagnosticSensor(coordinator, instance_name_slug, "last_update_status", "Last Update Status"),
        WeerplazaDiagnosticSensor(coordinator, instance_name_slug, "last_update_time", "Coordinator Last Update", SensorDeviceClass.TIMESTAMP),
        WeerplazaDiagnosticSensor(coordinator, instance_name_slug, "consecutive_errors", "Consecutive Update Errors"),
    ])

    async_add_entities(entities)


class WeerplazaMainSensor(WeerplazaBaseEntity, SensorEntity):
    """Representation of the main Weerplaza weather sensor (e.g., current temperature)."""

    _attr_has_entity_name = False # Sensor will be named after the device
    _attr_name = None # Use device name
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS # Assuming Celsius from the example

    def __init__(self, coordinator: WeerplazaDataUpdateCoordinator, instance_name_slug: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{instance_name_slug}_current_weather"

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor (e.g., current temperature)."""
        if self.coordinator.data and self.coordinator.data.get("current_temperature"):
            # Extract only the numeric part of the temperature string (e.g., "15°" -> "15")
            temp_str = self.coordinator.data["current_temperature"].replace('°', '').strip()
            try:
                return float(temp_str)
            except ValueError:
                _LOGGER.warning("Could not convert current temperature '%s' to float.", temp_str)
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes for the main sensor."""
        if not self.coordinator.data:
            return None

        attributes = {}
        # Add all scraped data as attributes to the main sensor for easy access
        for key in SCRAPED_DATA_KEYS:
            if key != "current_temperature" and key in self.coordinator.data: # current_temperature is the state
                attributes[key] = self.coordinator.data[key]

        attributes["last_update_attempt"] = dt_util.now() # Timestamp of the last coordinator update attempt
        return attributes

    @property
    def icon(self) -> str | None:
        """Return the icon based on current conditions (e.g., from hourly forecast)."""
        if self.coordinator.data and self.coordinator.data.get("hourly_forecast"):
            # Try to get icon based on the description of the first hourly forecast item
            first_hour_desc = self.coordinator.data["hourly_forecast"][0].get('description', '').lower()
            if "zon" in first_hour_desc:
                return "mdi:weather-sunny"
            if "bewolkt" in first_hour_desc:
                return "mdi:weather-cloudy"
            if "regen" in first_hour_desc or "buien" in first_hour_desc:
                return "mdi:weather-pouring"
            if "mist" in first_hour_desc:
                return "mdi:weather-fog"
            if "sneeuw" in first_hour_desc:
                return "mdi:weather-snowy"
            if "onweer" in first_hour_desc:
                return "mdi:weather-lightning-rainy"
        return "mdi:weather-partly-cloudy" # Default icon


class WeerplazaWarningSensor(WeerplazaBaseEntity, SensorEntity):
    """Sensor for Weerplaza warnings."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC # Or just leave it as default sensor
    _attr_name = "Warnings"

    def __init__(self, coordinator: WeerplazaDataUpdateCoordinator, instance_name_slug: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{instance_name_slug}_warnings"

    @property
    def native_value(self) -> StateType:
        """Return the state (warning code) of the sensor."""
        if self.coordinator.data and self.coordinator.data.get("warnings"):
            return self.coordinator.data["warnings"].get("code")
        return "Geen waarschuwing" # No warning

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes for warnings."""
        if self.coordinator.data and self.coordinator.data.get("warnings"):
            return self.coordinator.data["warnings"]
        return None

    @property
    def icon(self) -> str | None:
        """Return the icon based on warning status."""
        if self.coordinator.data and self.coordinator.data.get("warnings"):
            return "mdi:alert-outline"
        return "mdi:check-circle-outline"


class WeerplazaFlashMessageSensor(WeerplazaBaseEntity, SensorEntity):
    """Sensor for Weerplaza flash messages."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Flash Message"

    def __init__(self, coordinator: WeerplazaDataUpdateCoordinator, instance_name_slug: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{instance_name_slug}_flash_message"

    @property
    def native_value(self) -> StateType:
        """Return the state (flash message text) of the sensor."""
        if self.coordinator.data and self.coordinator.data.get("flash_message"):
            return self.coordinator.data["flash_message"].get("message")
        return "Geen flash bericht"

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes for flash message."""
        if self.coordinator.data and self.coordinator.data.get("flash_message"):
            return self.coordinator.data["flash_message"]
        return None

    @property
    def icon(self) -> str | None:
        """Return the icon based on flash message status."""
        if self.coordinator.data and self.coordinator.data.get("flash_message"):
            return "mdi:flash"
        return "mdi:information-outline"


class WeerplazaHourlyForecastSensor(WeerplazaBaseEntity, SensorEntity):
    """Sensor for Weerplaza hourly forecast."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Hourly Forecast"

    def __init__(self, coordinator: WeerplazaDataUpdateCoordinator, instance_name_slug: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{instance_name_slug}_hourly_forecast"

    @property
    def native_value(self) -> StateType:
        """Return the state (e.g., number of hourly entries) of the sensor."""
        if self.coordinator.data and self.coordinator.data.get("hourly_forecast"):
            return len(self.coordinator.data["hourly_forecast"])
        return 0

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes for hourly forecast."""
        if self.coordinator.data and self.coordinator.data.get("hourly_forecast"):
            return {"forecast": self.coordinator.data["hourly_forecast"]}
        return None

    @property
    def icon(self) -> str | None:
        return "mdi:clock-outline"


class WeerplazaDailyForecastSensor(WeerplazaBaseEntity, SensorEntity):
    """Sensor for Weerplaza daily forecast."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Daily Forecast"

    def __init__(self, coordinator: WeerplazaDataUpdateCoordinator, instance_name_slug: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{instance_name_slug}_daily_forecast"

    @property
    def native_value(self) -> StateType:
        """Return the state (e.g., number of daily entries) of the sensor."""
        if self.coordinator.data and self.coordinator.data.get("daily_forecast"):
            return len(self.coordinator.data["daily_forecast"])
        return 0

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes for daily forecast."""
        if self.coordinator.data and self.coordinator.data.get("daily_forecast"):
            return {"forecast": self.coordinator.data["daily_forecast"]}
        return None

    @property
    def icon(self) -> str | None:
        return "mdi:calendar-today"


class WeerplazaDiagnosticSensor(WeerplazaBaseEntity, SensorEntity):
    """Representation of a Weerplaza Diagnostic Sensor."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False # Override base to allow custom naming

    def __init__(
        self,
        coordinator: WeerplazaDataUpdateCoordinator,
        instance_name_slug: str,
        data_key: str,
        name: str,
        device_class: SensorDeviceClass | None = None
    ) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._data_key = data_key
        self._attr_unique_id = f"{instance_name_slug}_diag_{data_key}"
        # Manually set name, using instance name for clarity
        self._attr_name = f"{coordinator.config_entry.data[CONF_INSTANCE_NAME]} {name}"
        self._attr_device_class = device_class

    @property
    def native_value(self) -> StateType:
        """Return the state of the diagnostic sensor."""
        if self._data_key == "last_update_status":
            return "OK" if not self.coordinator.last_update_error else "Error"
        elif self._data_key == "last_update_time":
            # This is the timestamp of the coordinator's last *successful* run
            return self.coordinator.last_update_success_timestamp
        elif self._data_key == "consecutive_errors":
            return self.coordinator.error_count
        return None

    # Diagnostics are always available if the coordinator exists.
    # Override base availability which depends on last_update_success
    @property
    def available(self) -> bool:
        return self.coordinator is not None
