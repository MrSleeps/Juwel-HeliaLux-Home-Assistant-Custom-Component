import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorEntityDescription, 
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_NAME, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL
from .coordinator import JuwelHelialuxCoordinator
_LOGGER = logging.getLogger(__name__)

ENTITY_DESCRIPTIONS = {
    "red": SensorEntityDescription(key="red"),
    "green": SensorEntityDescription(key="green"),
    "blue": SensorEntityDescription(key="blue"),
    "white": SensorEntityDescription(key="white"),
    "current_profile": SensorEntityDescription(key="current_profile"),
    "manualColorSimulationEnabled": SensorEntityDescription(key="manualColorSimulationEnabled"),
    "manualDaytimeSimulationEnabled": SensorEntityDescription(key="manualDaytimeSimulationEnabled"),
    "device_time": SensorEntityDescription(key="device_time"),
}

class JuwelHelialuxSensor(CoordinatorEntity, SensorEntity):
    """Main sensor containing all data as attributes."""

    def __init__(self, coordinator, tank_name):
        super().__init__(coordinator)
        self._attr_name = f"{tank_name} Combined Sensor"
        self._attr_unique_id = f"{tank_name}_sensor"
        self.tank_name = tank_name
        self.device_info_data = {}
        self._attr_device_info = coordinator.device_info

    async def _initialize_device_info(self):
        """Fetch and initialize device info during initialization."""
        try:
            self.device_info_data = await self.coordinator.helialux.device_info() or {}
            _LOGGER.debug("Fetched device info during init: %s", self.device_info_data)
            
            if not self.device_info_data:
                _LOGGER.error("Device info is empty or invalid, setting default values")
                self.device_info_data = {
                    "device_type": "HeliaLux SmartControl",
                    "light_channels": "Unknown",
                    "hardware_version": "v0.0.0",
                    "firmware_version": '9.9.9',
                    "mac_address": "00:00:00:00:00:00",
                }

            device_type = self.device_info_data.get("device_type", "HeliaLux SmartControl")
            lamp_model = self.device_info_data.get("light_channels", "Unknown")
            combined_model = f"{device_type} {lamp_model}".strip()
            _LOGGER.debug("Combined Model: %s", combined_model)

            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self.tank_name)},
                name=self.tank_name,
                manufacturer="Juwel",
                model=combined_model,
                sw_version=self.device_info_data.get("hardware_version", "v0.0.0"),
                hw_version=self.device_info_data.get("firmware_version", "v9.9.9"),
                configuration_url=f"{self.coordinator.tank_protocol}://{self.coordinator.tank_host}",
                connections={(self.device_info_data.get("mac_address", "00:00:00:00:00:00"),)},
            )
            _LOGGER.debug("Initialized DeviceInfo: %s", self._attr_device_info)
            return True
        except Exception as e:
            _LOGGER.error("Error initializing device info: %s", str(e))
            self._attr_device_info = None
            return False

    async def async_added_to_hass(self):
        """Called when the entity is added to Home Assistant."""
        try:
            device_info_initialized = await self._initialize_device_info()
            _LOGGER.debug("Entity initialization complete for %s", self.name)

            if not device_info_initialized:
                _LOGGER.error("Failed to initialize device info for %s", self.name)
                return

            if self._attr_device_info is None:
                _LOGGER.error("Device info is not set properly, cannot write state for %s", self.name)
                return

            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()

            _LOGGER.debug("Coordinator data: %s", self.coordinator.data)
            _LOGGER.debug("Device info initialized: %s", device_info_initialized)
        except Exception as e:
            _LOGGER.error("Error during async_added_to_hass for %s: %s", self.name, str(e))

    @property
    def state(self):
        """Return 'online' if data is available, otherwise 'offline'."""
        return "online" if self.coordinator.data else "offline"    

    @property
    def extra_state_attributes(self):
        """Return all available attributes including colors and profile."""
        color_data = {
            "red": self.coordinator.data.get("red", 0),
            "green": self.coordinator.data.get("green", 0),
            "blue": self.coordinator.data.get("blue", 0),
            "white": self.coordinator.data.get("white", 0),
        }

        profile_data = {
            "current_profile": self.coordinator.data.get("current_profile", "offline")
        }
        
        time_data = {
            "device_time": self.coordinator.data.get("device_time", "00:00")
        }        

        return {**self.coordinator.data, **color_data, **profile_data, **time_data}

    async def async_remove(self):
        """Cleanup resources when the entity is removed."""
        _LOGGER.debug(f"Removing entity: {self.entity_id}")
        await super().async_remove()

class JuwelHelialuxAttributeSensor(CoordinatorEntity, SensorEntity):
    """Creates a sensor for each individual attribute."""

    SENSOR_ICONS = {
        "red": "mdi:brightness-percent",
        "green": "mdi:brightness-percent",
        "blue": "mdi:brightness-percent",
        "white": "mdi:brightness-percent",
        "manualDaytimeSimulationEnabled": "mdi:sun-clock",
        "manualColorSimulationEnabled": "mdi:palette",
        "device_time": "mdi:clock-time-five",
    }

    SENSOR_TYPE_FALLBACKS = {
        "red": "Light Intensity Sensor",
        "green": "Light Intensity Sensor",
        "blue": "Light Intensity Sensor",
        "white": "Light Intensity Sensor",
        "current_profile": "Current Lighting Profile",
        "manualColorSimulationEnabled": "Manual Color Simulation",
        "manualDaytimeSimulationEnabled": "Manual Daytime Simulation",
    }    

    def __init__(self, coordinator, tank_name, attribute, default_value=None, SensorStateClass="", unit=""):
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{tank_name}_{attribute}"
        self.entity_id = f"sensor.{tank_name.lower()}_{attribute}"

        self.entity_description = SensorEntityDescription(
            key=attribute,
            translation_key=attribute,
            state_class=SensorStateClass.MEASUREMENT if unit else None,
            native_unit_of_measurement=unit,
        )

        self._attr_has_entity_name = True
        self._attr_translation_placeholders = {"tank_name": tank_name}

        self._attribute = attribute
        self._default_value = default_value
        self._attr_device_info = coordinator.device_info

        _LOGGER.debug("Device info for %s: %s", self._attr_unique_id, self._attr_device_info)        

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or {}
        return data.get(self._attribute, self._default_value if data.get(self._attribute) is None else data.get(self._attribute))

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return self.SENSOR_ICONS.get(self._attribute, "mdi:eye")

    async def async_remove(self):
        """Cleanup resources when the entity is removed."""
        _LOGGER.debug(f"Removing entity: {self.entity_id}")
        await super().async_remove()

class JuwelHelialuxProfilesSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display available profiles from the Helialux controller."""

    def __init__(self, coordinator, tank_name, attribute):
        super().__init__(coordinator)
        self._attr_unique_id = f"{tank_name}_profiles"
        self.entity_id = f"sensor.{tank_name.lower()}_profiles"

        self.entity_description = SensorEntityDescription(
            key="profiles",
            translation_key="profiles",
        )

        self._attr_has_entity_name = True
        self._attr_translation_placeholders = {"tank_name": tank_name}
        self._attr_device_info = coordinator.device_info

    @property
    def state(self):
        """Return the number of available profiles."""
        if not self.coordinator.data:
            _LOGGER.warning("Coordinator data is None, returning 0 profiles")
            return 0

        profiles = self.coordinator.data.get("available_profiles", [])
        return len(profiles)

    @property
    def extra_state_attributes(self):
        """Return the list of available profiles as attributes."""
        profiles = self.coordinator.data.get("available_profiles", [])
        active_profiles = self.coordinator.data.get("active_profiles", [])
        return {
            "available_profiles": profiles,
            "active_profiles": active_profiles
        }
    
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up multiple sensor entities from a config entry."""
    tank_name = config_entry.data[CONF_TANK_NAME]
    tank_host = config_entry.data[CONF_TANK_HOST]
    tank_protocol = config_entry.data[CONF_TANK_PROTOCOL]
    update_interval = config_entry.data.get(CONF_UPDATE_INTERVAL, 1)
    coordinator = JuwelHelialuxCoordinator(hass, tank_host, tank_protocol, tank_name, update_interval)
    if coordinator.data is None:
        coordinator.data = {}

    await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("Coordinator data before entity creation: %s", coordinator.data)

    main_sensor = JuwelHelialuxSensor(coordinator, tank_name)
    profiles_sensor = JuwelHelialuxProfilesSensor(coordinator, tank_name, "available_profiles")

    attribute_sensors = [
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "current_profile", default_value="offline"),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "white", default_value=0, SensorStateClass=SensorStateClass.MEASUREMENT, unit="%"),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "blue", default_value=0, SensorStateClass=SensorStateClass.MEASUREMENT, unit="%"),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "green", default_value=0, SensorStateClass=SensorStateClass.MEASUREMENT, unit="%"),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "red", default_value=0, SensorStateClass=SensorStateClass.MEASUREMENT, unit="%"),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "manualColorSimulationEnabled", default_value=False),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "manualDaytimeSimulationEnabled", default_value=False),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "device_time", default_value="00:00"),
    ]

    async_add_entities([main_sensor, profiles_sensor] + attribute_sensors, True)