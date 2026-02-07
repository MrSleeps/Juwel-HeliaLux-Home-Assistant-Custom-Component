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
from homeassistant.util import slugify
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
        # FIX: Don't duplicate the tank_name in the name attribute
        # Just use a simple name since has_entity_name = True will handle it
        self._attr_name = "Combined Sensor"  # Just the entity name part
        tank_slug = slugify(tank_name)
        self._attr_unique_id = f"{tank_slug}_combined_sensor"  # Changed from _sensor to _combined_sensor
        self.tank_name = tank_name
        self._attr_device_info = coordinator.device_info
        self._attr_has_entity_name = True

    async def async_added_to_hass(self):
        """Called when the entity is added to Home Assistant."""
        try:
            self.async_write_ha_state()
            await self.coordinator.async_request_refresh()
            
            _LOGGER.debug("Entity initialization complete for %s", self.name)
            _LOGGER.debug("Coordinator data: %s", self.coordinator.data)
            _LOGGER.debug("Device info from coordinator: %s", self._attr_device_info)
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

        tank_slug = slugify(tank_name)
        
        self._attr_unique_id = f"{tank_slug}_{attribute}"
        self.entity_id = f"sensor.{tank_slug}_{attribute}"

        self.entity_description = SensorEntityDescription(
            key=attribute,
            translation_key=attribute,
            state_class=SensorStateClass.MEASUREMENT if unit else None,
            native_unit_of_measurement=unit,
        )

        self._attr_has_entity_name = True
        self._attr_translation_placeholders = {"tank_name": tank_name}
        self._attr_device_info = coordinator.device_info

        self._attribute = attribute
        self._default_value = default_value

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
        tank_slug = slugify(tank_name)
        
        self._attr_unique_id = f"{tank_slug}_profiles"
        self.entity_id = f"sensor.{tank_slug}_profiles"

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
    
    # Get coordinator from hass.data
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
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
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "device_time", default_value="00:00"),
    ]

    async_add_entities([main_sensor, profiles_sensor] + attribute_sensors, True)