import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_NAME, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL
from .pyhelialux.pyHelialux import Controller as Helialux

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up multiple sensor entities from a config entry."""
    tank_name = config_entry.data[CONF_TANK_NAME]
    tank_host = config_entry.data[CONF_TANK_HOST]
    tank_protocol = config_entry.data[CONF_TANK_PROTOCOL]
    update_interval = config_entry.data.get(CONF_UPDATE_INTERVAL, 5)  # Default to 5 minutes

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
        JuwelHelialuxAttributeSensor(coordinator, tank_name, "deviceTime", default_value=None),
    ]

    # Add all sensors to Home Assistant
    async_add_entities([main_sensor] + attribute_sensors, True)

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
            data = await self.helialux.get_status()  # ✅ Await async function directly
            _LOGGER.debug("Raw data received from Helialux: %s", data)

            if not isinstance(data, dict):  # Ensure data is a dictionary
                _LOGGER.warning(
                    "Unexpected data format from Helialux device, defaulting to empty dict. Received: %s", type(data)
                )
                return {}

            # Ensure we always include profile and color data
            profile = data.get("currentProfile", "offline")
            color_data = {
                "red": data.get("currentRed", 0),
                "green": data.get("currentGreen", 0),
                "blue": data.get("currentBlue", 0),
                "white": data.get("currentWhite", 0),
            }

            # Merge profile and color data to retain all attributes
            self.data.update({"profile": profile, **color_data})  # Ensure no data is lost

            return self.data

        except Exception as e:
            _LOGGER.error("Error fetching data from Helialux device: %s", e)
            return {}  # Ensure empty dictionary on failure

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
            "current_profile": self.coordinator.data.get("profile", "offline")
        }

        # Merge the color and profile data together
        return {**self.coordinator.data, **color_data, **profile_data}

    async def async_remove(self):
        """Cleanup resources when the entity is removed."""
        _LOGGER.debug(f"Removing entity: {self.entity_id}")
        await super().async_remove()

class JuwelHelialuxAttributeSensor(CoordinatorEntity, SensorEntity):
    """Creates a sensor for each individual attribute."""

    def __init__(self, coordinator, tank_name, attribute, default_value=None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{tank_name} {attribute}"
        self._attr_unique_id = f"{tank_name}_{attribute}"
        self._attribute = attribute
        self._default_value = default_value  # Default value if no data is available

    @property
    def state(self):
        data = self.coordinator.data or {}  # Ensure data is always a dictionary
        # Return the attribute value, or a default if not found
        return data.get(self._attribute, self._default_value)

    async def async_remove(self):
        """Cleanup resources when the entity is removed."""
        _LOGGER.debug(f"Removing entity: {self.entity_id}")
        await super().async_remove()
