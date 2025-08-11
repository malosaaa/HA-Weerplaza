"""Base entity for Weerplaza Weather."""
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, CONF_INSTANCE_NAME, CONF_LOCATION_PATH
from .coordinator import WeerplazaDataUpdateCoordinator


class WeerplazaBaseEntity(CoordinatorEntity[WeerplazaDataUpdateCoordinator]):
    """Base class for Weerplaza Weather entities."""

    _attr_has_entity_name = True # Use automatic naming based on device and entity name

    def __init__(self, coordinator: WeerplazaDataUpdateCoordinator) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        # Use the instance name from config entry for device identification
        self._instance_name = coordinator.config_entry.data[CONF_INSTANCE_NAME]
        self._location_path = coordinator.config_entry.data[CONF_LOCATION_PATH]

        # Link entities for this configured instance to one device
        # The unique identifier for the device should be based on the config entry ID
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=self._instance_name, # User-friendly name from config
            manufacturer=MANUFACTURER,
            model=f"Location: {self._location_path}",
            entry_type=None,
            configuration_url=f"https://www.weerplaza.nl/{self._location_path.strip('/')}/",
        )

    @property
    def available(self) -> bool:
        """Return True if coordinator is available and has successfully updated."""
        # Data can be None if no messages found, but coordinator might still be available
        # We consider it available if the coordinator itself is ready, even if data is temporarily None
        return self.coordinator.last_update_success_timestamp is not None
