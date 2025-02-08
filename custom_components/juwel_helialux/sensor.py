import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.components.select import SelectEntity
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_NAME, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL
from .pyhelialux.pyHelialux import Controller as Helialux

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up multiple sensor entities from a config entry."""
    tank_name = config_entry.data[CONF_TANK_NAME]
    tank_host = config_entry.data[CONF_TANK_HOST]
    tank_protocol = config_entry.data[CONF_TANK_PROTOCOL]
    update_interval = config_entry.data.get(CONF_UPDATE_INTERVAL, 1)

    coordinator = JuwelHelialuxCoordinator(hass, tank_host, tank_protocol, update_interval)
    await coordinator.async_config_entry_first_refresh()

    # Create main sensor (with all attributes)
    main_sensor = JuwelHelialuxSensor(coordinator, tank_name)

    # Create individual sensors with default values
    attribute_sensors = [
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "current_profile", default_value="offline"),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "white", default_value=0),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "blue", default_value=0),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "green", default_value=0),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "red", default_value=0),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "manualColorSimulationEnabled", default_value=False),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "manualDaytimeSimulationEnabled", default_value=False),
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "device_time", default_value=None),
    ]

     # Create the profiles sensor
    profiles_sensor = JuwelHelialuxProfilesSensor(coordinator, tank_name)

    # Create the profile select entity
    profile_select = JuwelHelialuxProfileSelect(coordinator, tank_name)   

    # Add all sensors to Home Assistant
    #async_add_entities([main_sensor] + attribute_sensors, True)
    async_add_entities([main_sensor, profiles_sensor, profile_select] + attribute_sensors, True)

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
        _LOGGER.debug("Init started")
        url = f"{self.tank_protocol}://{self.tank_host}" if "://" not in self.tank_protocol else f"{self.tank_protocol}{self.tank_host}"
        self.helialux = Helialux(url)

    async def _async_update_data(self):
        try:
            # Fetch status data
            status_data = await self.helialux.get_status()
            _LOGGER.debug("Raw status data received from Helialux: %s", status_data)

            # Fetch profile data
            profile_data = await self.helialux.get_profiles()
            _LOGGER.debug("Raw profile data received from Helialux: %s", profile_data)

            # Merge status and profile data
            merged_data = {}
            if isinstance(status_data, dict):
                merged_data.update({
                    "current_profile": status_data.get("currentProfile", "offline"),
                    "device_time": status_data.get("deviceTime", "00:00"),
                    "white": status_data.get("currentWhite", 0),
                    "blue": status_data.get("currentBlue", 0),
                    "green": status_data.get("currentGreen", 0),
                    "red": status_data.get("currentRed", 0),
                    "manualColorSimulationEnabled": status_data.get("manualColorSimulationEnabled", False),
                    "manualDaytimeSimulationEnabled": status_data.get("manualDaytimeSimulationEnabled", False),
                })

            if isinstance(profile_data, dict):
                merged_data.update({
                    "available_profiles": profile_data.get("profile_names", []),
                    "active_profiles": profile_data.get("profile_selection", [])
                })

            return merged_data

        except Exception as e:
            _LOGGER.error("Error fetching data from Helialux device: %s", e)
            return {}

class JuwelHelialuxSensor(CoordinatorEntity, SensorEntity):
    """Main sensor containing all data as attributes."""

    def __init__(self, coordinator, tank_name):
        super().__init__(coordinator)
        self._attr_name = f"{tank_name} Sensor"
        self._attr_unique_id = f"{tank_name}_sensor"

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

    def __init__(self, coordinator, tank_name, attribute, default_value=None):
        """Initialize the sensor."""
        super().__init__(coordinator)

        # 1️⃣ Translation key should be STATIC so HA applies translations
        self._attr_translation_key = attribute  

        # 2️⃣ Keep tank name UNIQUE for multiple devices, but remove integration prefix
        self._attr_unique_id = f"{tank_name}_{attribute}"  

        # 3️⃣ Remove 'juwel_helialux_' prefix but allow user-friendly names
        self._attr_has_entity_name = True  
        # Pass the tank name as a placeholder to the translation system
        self._attr_entity_registry_enabled_default = True
        self._attr_entity_category = None
#        self._attr_extra_state_attributes = {"tank_name": }  # Pass the tank name to HA
#        self._attr_name = f"{tank_name} {{}}" # added
        self._attr_translation_placeholders = {"tank_name": tank_name}
        self._attribute = attribute
        self._default_value = default_value


    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or {}  # Ensure data is always a dictionary
        return data.get(self._attribute, self._default_value)
 

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or {}  # Ensure data is always a dictionary
        return data.get(self._attribute, self._default_value)

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
        self._attr_name = f"{tank_name} Profiles"
        self._attr_unique_id = f"{tank_name}_profiles"
        self._attr_icon = "mdi:format-list-bulleted"  # Optional: Add an icon for the sensor

    @property
    def state(self):
        """Return the number of available profiles."""
        profiles = self.coordinator.data.get("available_profiles", [])
        return len(profiles)  # Return the count of profiles as the state

    @property
    def extra_state_attributes(self):
        """Return the list of available profiles as attributes."""
        profiles = self.coordinator.data.get("available_profiles", [])
        active_profiles = self.coordinator.data.get("active_profiles", [])
        return {
            "available_profiles": profiles,  # List of all profile names
            "active_profiles": active_profiles  # List of active profiles (if applicable)
        }        

class JuwelHelialuxProfileSelect(CoordinatorEntity, SelectEntity):
    """Select entity for choosing a profile on the Helialux controller."""

    def __init__(self, coordinator, tank_name):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_name = f"{tank_name} Profile"
        self._attr_unique_id = f"{tank_name}_profile_select"
        self._attr_icon = "mdi:format-list-bulleted"
        self._attr_options = []  # Will be populated with available profiles

    @property
    def current_option(self):
        """Return the currently selected profile."""
        return self.coordinator.data.get("current_profile", "offline")

    async def async_select_option(self, option: str):
        """Change the selected option and update the external server."""
        _LOGGER.debug(f"Setting profile to {option}")
        
        try:
            # Access the Helialux controller from the coordinator's data
            helialux_controller = self.coordinator.data.get("controller")
            
            if helialux_controller:
                # Set the profile using the controller's method
                await helialux_controller.set_profile(option)
                # Update the coordinator with the selected profile
                self.coordinator.data["current_profile"] = option
                _LOGGER.debug(f"Profile set to {option} successfully.")
            else:
                _LOGGER.error("Helialux controller not available.")
        
        except Exception as e:
            _LOGGER.error(f"Failed to set profile to {option}: {e}")
        
        # Refresh the coordinator data to reflect the change
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """Update the options when the entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self._update_options()

    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._update_options()
        super()._handle_coordinator_update()

    def _update_options(self):
        """Update the available profile options."""
        profiles = self.coordinator.data.get("available_profiles", [])
        self._attr_options = profiles