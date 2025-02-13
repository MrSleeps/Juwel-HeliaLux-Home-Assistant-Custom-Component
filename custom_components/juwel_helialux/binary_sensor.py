import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .pyhelialux.pyHelialux import Controller as Helialux
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_PROTOCOL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up binary sensor platform for Juwel Helialux."""
    _LOGGER.debug("Setting up binary sensors for Juwel Helialux.")

    # Retrieve configuration values
    tank_host = entry.data[CONF_TANK_HOST]
    tank_protocol = entry.data[CONF_TANK_PROTOCOL]
    tank_url = f"{tank_protocol}://{tank_host}"
    tank_name = entry.data.get("tank_name", "Unknown Tank")
    controller = Helialux(tank_url)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    # Create the binary sensors
    async_add_entities([
        ManualColorSimulationBinarySensor(coordinator, tank_name, tank_protocol, tank_host),
        ManualDaytimeSimulationBinarySensor(coordinator, tank_name, tank_protocol, tank_host),
    ])

    _LOGGER.debug("Binary sensors created and added.")

class ManualColorSimulationBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of the manual color simulation status."""

    def __init__(self, coordinator, tank_name, tank_protocol, tank_host):
        """Initialize the sensor with a coordinator, tank name, protocol, and host."""
        super().__init__(coordinator)
        self._tank_name = tank_name
        self._tank_protocol = tank_protocol
        self._tank_host = tank_host
        self._attr_unique_id = f"{tank_name}_manual_color_simulation"
        self._attr_name = f"{tank_name} - Manual Color Simulation Enabled"
        # Use the coordinator's device_info
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self):
        """Return if the binary sensor is on or off."""
        return self.coordinator.data.get("manualColorSimulationEnabled") == "On"

    @property
    def device_class(self):
        """Return the device class of the binary sensor."""
        return "power"


class ManualDaytimeSimulationBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of the manual daytime simulation status."""

    def __init__(self, coordinator, tank_name, tank_protocol, tank_host):
        """Initialize the sensor with a coordinator, tank name, protocol, and host."""
        super().__init__(coordinator)
        self._tank_name = tank_name
        self._tank_protocol = tank_protocol
        self._tank_host = tank_host
        self._attr_unique_id = f"{tank_name}_manual_daytime_simulation"
        self._attr_name = f"{tank_name} - Manual Daytime Simulation Enabled"
        # Use the coordinator's device_info
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self):
        """Return if the binary sensor is on or off."""
        return self.coordinator.data.get("manualDaytimeSimulationEnabled") == "On"

    @property
    def device_class(self):
        """Return the device class of the binary sensor."""
        return "power"