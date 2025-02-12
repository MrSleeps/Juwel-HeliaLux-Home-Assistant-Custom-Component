import logging
from datetime import timedelta
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_NAME, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL
from .pyhelialux.pyHelialux import Controller as Helialux

_LOGGER = logging.getLogger(__name__)

async def _async_update_data(self):
    """Fetch the latest data from the Helialux device."""
    try:
        # Fetch status data
        status_data = await self.helialux.get_status()
        _LOGGER.debug("Raw status data received from Helialux: %s", status_data)

        if not isinstance(status_data, dict):
            _LOGGER.error("Invalid status data format from Helialux, received: %s", type(status_data))
            status_data = {}

        # Fetch profile data
        profile_data = await self.helialux.get_profiles()
        _LOGGER.debug("Raw profile data received from Helialux: %s", profile_data)

        if not isinstance(profile_data, dict):
            _LOGGER.error("Invalid profile data format from Helialux, received: %s", type(profile_data))
            profile_data = {}

        _LOGGER.debug(f"Before updating HA: current_profile={self.data.get('current_profile', 'offline')}")

        # Merge status and profile data
        merged_data = {
            "current_profile": status_data.get("currentProfile", "offline"),
            "device_time": status_data.get("deviceTime", "00:00"),
            "white": status_data.get("currentWhite", 0),
            "blue": status_data.get("currentBlue", 0),
            "green": status_data.get("currentGreen", 0),
            "red": status_data.get("currentRed", 0),
            "manualColorSimulationEnabled": status_data.get("manualColorSimulationEnabled", False),
            "manualDaytimeSimulationEnabled": status_data.get("manualDaytimeSimulationEnabled", False),
            "available_profiles": profile_data.get("available_profiles", []),
            "full_profile_names": profile_data.get("full_profile_names", []),
        }

        _LOGGER.debug("Merged data: %s", merged_data)
        _LOGGER.debug(f"After updating HA: current_profile={merged_data.get('current_profile', 'offline')}")
        _LOGGER.debug(f"Raw statusvars.js profile: {status_data.get('currentProfile', 'offline')}")

        return merged_data  # ✅ Always return a dictionary

    except Exception as e:
        _LOGGER.error("Error fetching data from Helialux device: %s", e)
        return {}  # ✅ Always return an empty dictionary

class JuwelHelialuxCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Juwel Helialux device."""

    def __init__(self, hass, tank_host, tank_protocol, update_interval):
        super().__init__(
            hass,
            _LOGGER,
            name="Juwel Helialux Sensor",
            update_interval=timedelta(minutes=update_interval),
        )
        self.tank_host = tank_host
        self.tank_protocol = tank_protocol
        _LOGGER.debug("Initializing Coordinator")

        url = f"{self.tank_protocol}://{self.tank_host}"
        self.helialux = Helialux(url)
        self.data = {}  
        # Set default device info (to be updated after first fetch)
        self.device_info = {
            "identifiers": {(DOMAIN, self.tank_host)},
            "name": tank_host,
            "manufacturer": "Juwel",
            "model": "Unknown",
            "sw_version": "Unknown",
            "hw_version": "Unknown",
            "configuration_url": url,
            "connections": set(),
        }

    async def async_config_entry_first_refresh(self):
        """Fetch initial data and store device info."""
        await self.async_refresh()  # ✅ Use async_refresh() instead of directly calling `_async_update_data`
        _LOGGER.debug("Device Info Initialized: %s", self.device_info)

    async def _async_update_data(self):
        """Fetch the latest data from the Helialux device."""
        try:
            # Fetch status data
            status_data = await self.helialux.get_status()
            _LOGGER.debug("Raw status data received from Helialux: %s", status_data)

            if not isinstance(status_data, dict):
                _LOGGER.error("Invalid status data format from Helialux, received: %s", type(status_data))
                status_data = {}

            # Fetch profile data
            profile_data = await self.helialux.get_profiles()
            _LOGGER.debug("Raw profile data received from Helialux: %s", profile_data)

            if not isinstance(profile_data, dict):
                _LOGGER.error("Invalid profile data format from Helialux, received: %s", type(profile_data))
                profile_data = {}

            _LOGGER.debug(f"Before updating HA: current_profile={self.data.get('current_profile', 'offline')}")

            # Merge status and profile data
            merged_data = {
                "current_profile": status_data.get("currentProfile", "offline"),
                "device_time": status_data.get("deviceTime", "00:00"),
                "white": status_data.get("currentWhite", 0),
                "blue": status_data.get("currentBlue", 0),
                "green": status_data.get("currentGreen", 0),
                "red": status_data.get("currentRed", 0),
                "manualColorSimulationEnabled": status_data.get("manualColorSimulationEnabled", False),
                "manualDaytimeSimulationEnabled": status_data.get("manualDaytimeSimulationEnabled", False),
                "available_profiles": profile_data.get("available_profiles", []),
                "full_profile_names": profile_data.get("full_profile_names", []),
            }

            _LOGGER.debug("Merged data: %s", merged_data)
            _LOGGER.debug(f"After updating HA: current_profile={merged_data.get('current_profile', 'offline')}")
            _LOGGER.debug(f"Raw statusvars.js profile: {status_data.get('currentProfile', 'offline')}")

            return merged_data  # ✅ Always return a dictionary

        except Exception as e:
            _LOGGER.error("Error fetching data from Helialux device: %s", e)
            return {}  # ✅ Always return an empty dictionary

class JuwelHelialuxSensor(CoordinatorEntity, SensorEntity):
    """Main sensor containing all data as attributes."""

    def __init__(self, coordinator, tank_name):
        super().__init__(coordinator)
        self._attr_name = f"{tank_name} Sensor"  # Changed to "tankname_sensor"
        self._attr_unique_id = f"{tank_name}_sensor"  # Changed to "tankname_sensor"
        self.tank_name = tank_name
        self.device_info_data = {}  # Placeholder for device info
        self._attr_device_info = {}  # Will be set after fetching device info

    async def _initialize_device_info(self):
        """Fetch and initialize device info during initialization."""
        try:
            # Fetch device info from the coordinator
            self.device_info_data = await self.coordinator.helialux.device_info() or {}
            _LOGGER.debug("Fetched device info during init: %s", self.device_info_data)
            
            if not self.device_info_data:
                _LOGGER.error("Device info is empty or invalid, setting default values")
                self.device_info_data = {
                    "device_type": "HeliaLux SmartControl",
                    "light_channels": "Unknown",
                    "hardware_version": "v0.0.0",
                    "firmware_version": "9.9.9",
                    "mac_address": "00:00:00:00:00:00",
                }

            # Proceed to initialize device info only if data is valid
            device_type = self.device_info_data.get("device_type", "HeliaLux SmartControl")
            lamp_model = self.device_info_data.get("light_channels", "Unknown")
            combined_model = f"{device_type} {lamp_model}".strip()  # Example: "HeliaLux SmartControl 4Ch"
            _LOGGER.debug("Combined Model: %s", combined_model)

            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self.tank_name)},
                name=self.tank_name,
                manufacturer="Juwel",
                model=combined_model,
                sw_version=self.device_info_data.get("hardware_version", "v0.0.0"),
                hw_version=self.device_info_data.get("firmware_version", "9.9.9"),
                configuration_url=f"{self.coordinator.tank_protocol}://{self.coordinator.tank_host}",
                connections={(self.device_info_data.get("mac_address", "00:00:00:00:00:00"),)},  # Fixed syntax
            )
            _LOGGER.debug("Initialized DeviceInfo: %s", self._attr_device_info)
            return True  # Successfully initialized
        except Exception as e:
            _LOGGER.error("Error initializing device info: %s", str(e))
            self._attr_device_info = None  # Ensure it's set to None in case of error
            return False

    # Ensure that async_added_to_hass checks for valid _attr_device_info
    async def async_added_to_hass(self):
        """Called when the entity is added to Home Assistant."""
        try:
            # Await the initialization of device info
            device_info_initialized = await self._initialize_device_info()
            _LOGGER.debug("Entity initialization complete for %s", self.name)

            if not device_info_initialized:
                _LOGGER.error("Failed to initialize device info for %s", self.name)
                return

            # Ensure _attr_device_info is set before trying to write state
            if self._attr_device_info is None:
                _LOGGER.error("Device info is not set properly, cannot write state for %s", self.name)
                return

            # Write the initial state (DO NOT AWAIT THIS)
            _LOGGER.debug("Writing initial state for entity %s", self.name)
            self.async_write_ha_state()  # Remove the 'await' here

            # Force Coordinator refresh after initialization
            await self.coordinator.async_request_refresh()

            # Additional debug logs
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
        # Combine the profile and color data with the existing data from the coordinator
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

        # Merge the color and profile data together
        return {**self.coordinator.data, **color_data, **profile_data, **time_data}

    async def async_remove(self):
        """Cleanup resources when the entity is removed."""
        _LOGGER.debug(f"Removing entity: {self.entity_id}")
        await super().async_remove()

class JuwelHelialuxAttributeSensor(CoordinatorEntity, SensorEntity):
    """Creates a sensor for each individual attribute."""

    SENSOR_ICONS = {
        "red": "mdi:palette",
        "green": "mdi:palette",
        "blue": "mdi:palette",
        "white": "mdi:palette",
    }

    def __init__(self, coordinator, tank_name, attribute, default_value=None, SensorStateClass="", unit=""):
        """Initialize the sensor."""
        super().__init__(coordinator)

        # Set the sensor name and unique ID
        self._attr_name = f"{tank_name}_{attribute}"  # Changed to "tankname_attribute"
        self._attr_unique_id = f"{tank_name}_{attribute}"  # Changed to "tankname_attribute"

        # Additional sensor properties
        self._attribute = attribute
        self._default_value = default_value
        self._attr_state_class = SensorStateClass  # Assign SensorStateClass
        self._attr_native_unit_of_measurement = unit or None  # Ensure unit is set
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{tank_name}_sensor")},
            "name": f"{tank_name} Sensor",
            "manufacturer": "Juwel",
            "model": "Helialux",
        }

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or {}
        return data.get(self._attribute, self._default_value if data.get(self._attribute) is None else data.get(self._attribute))

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return self.SENSOR_ICONS.get(self._attribute, "mdi:eye")  # Default to mdi:palette if not found

    async def async_remove(self):
        """Cleanup resources when the entity is removed."""
        _LOGGER.debug(f"Removing entity: {self.entity_id}")
        await super().async_remove()

class JuwelHelialuxProfilesSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display available profiles from the Helialux controller."""

    def __init__(self, coordinator, tank_name):
        """Initialize the profiles sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{tank_name}_profiles"  # Changed to "tankname_profiles"
        self._attr_unique_id = f"{tank_name}_profiles"  # Changed to "tankname_profiles"
        self._attr_icon = "mdi:format-list-bulleted"  # Optional: Add an icon for the sensor
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{tank_name}_sensor")},
            "name": f"{tank_name} Sensor",
            "manufacturer": "Juwel",
            "model": "Helialux",
        }        

    @property
    def state(self):
        """Return the number of available profiles."""
        if not self.coordinator.data:
            _LOGGER.warning("Coordinator data is None, returning 0 profiles")
            return 0  # ✅ Prevent crash

        profiles = self.coordinator.data.get("available_profiles", [])
        return len(profiles)

    @property
    def extra_state_attributes(self):
        """Return the list of available profiles as attributes."""
        profiles = self.coordinator.data.get("available_profiles", [])
        active_profiles = self.coordinator.data.get("active_profiles", [])
        return {
            "available_profiles": profiles,  # List of all profile names
            "active_profiles": active_profiles  # List of active profiles (if applicable)
        }
    
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up multiple sensor entities from a config entry."""
    tank_name = config_entry.data[CONF_TANK_NAME]
    tank_host = config_entry.data[CONF_TANK_HOST]
    tank_protocol = config_entry.data[CONF_TANK_PROTOCOL]
    update_interval = config_entry.data.get(CONF_UPDATE_INTERVAL, 1)

    coordinator = JuwelHelialuxCoordinator(hass, tank_host, tank_protocol, update_interval)

    # Ensure `coordinator.data` is never None
    if coordinator.data is None:
        coordinator.data = {}

    await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("Coordinator data before entity creation: %s", coordinator.data)

    # Create main sensor and profile sensor
    main_sensor = JuwelHelialuxSensor(coordinator, tank_name)
    profiles_sensor = JuwelHelialuxProfilesSensor(coordinator, tank_name)

    # Create attribute sensors with correct names and unique IDs
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

    # Add all sensors to Home Assistant
    async_add_entities([main_sensor, profiles_sensor] + attribute_sensors, True)