import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfTemperature, EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from .const import DOMAIN, CONF_INSTANCE_NAME, CONF_LOCATION_PATH

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    instance_name = entry.data[CONF_INSTANCE_NAME]
    location_path = entry.data[CONF_LOCATION_PATH]
    instance_slug = slugify(instance_name)

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=instance_name,
        manufacturer="Weerplaza",
        model=f"Location: {location_path}",
        configuration_url=f"https://www.weerplaza.nl/{location_path.strip('/')}/",
    )

    entities = [
        WeerplazaMasterSensor(coordinator, instance_name, instance_slug, device_info),
        WeerplazaDiagnosticSensor(coordinator, instance_name, instance_slug, device_info, "Status"),
        WeerplazaDiagnosticSensor(coordinator, instance_name, instance_slug, device_info, "Laatste Update")
    ]

    async_add_entities(entities)

class WeerplazaMasterSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:weather-partly-cloudy"

    def __init__(self, coordinator, name, slug, device_info):
        super().__init__(coordinator)
        self._attr_name = f"weerplaza {name} current weather"
        self._attr_unique_id = f"{slug}_master_weather"
        self._attr_device_info = device_info

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("current_temperature")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = self.coordinator.data or {}
        return {
            "current_weather": data.get("current_weather", {}),
            "hourly_forecast": data.get("hourly_forecast", []),
            "daily_forecast_summary": data.get("daily_forecast_summary", []),
            "daypart_forecast": data.get("daypart_forecast", []),
            "flash_message": data.get("flash_message", {}),
            "flash_detection": data.get("flash_detection"),
            "flash_range": data.get("flash_range"),
            "rain": data.get("rain"),
            "alerts": data.get("alerts"),
            "astro": data.get("astro", {}),
            "moon_phases": data.get("moon_phases", [])
        }

class WeerplazaDiagnosticSensor(CoordinatorEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, name, slug, device_info, sensor_type):
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self._attr_name = f"{name} {sensor_type}"
        self._attr_unique_id = f"{slug}_{sensor_type.lower().replace(' ', '_')}"
        self._attr_device_info = device_info

        if sensor_type == "Laatste Update":
            self._attr_icon = "mdi:clock"
        else:
            self._attr_icon = "mdi:check-network"

    @property
    def native_value(self):
        if self.sensor_type == "Status":
            return "Fout" if self.coordinator._error_count > 0 else "OK"
        if self.sensor_type == "Laatste Update":
            data = self.coordinator.data or {}
            if "laatste_scrape_tijd" not in data and data:
                 return "Uit Cache (Wacht op timer)"
            return data.get("laatste_scrape_tijd", "Onbekend")
