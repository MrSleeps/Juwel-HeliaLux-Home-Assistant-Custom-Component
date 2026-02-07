import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up binary sensor platform for Juwel Helialux."""
    _LOGGER.debug("Setting up binary sensors for Juwel Helialux.")
    
    # Get the coordinator from hass.data
    coordinator = hass.data[DOMAIN][entry.entry_id]
    tank_name = entry.data.get("tank_name", "Unknown Tank")
    tank_slug = slugify(tank_name)
    
    async_add_entities([
        ManualColorSimulationBinarySensor(coordinator, tank_slug),
        ManualDaytimeSimulationBinarySensor(coordinator, tank_slug),
    ])

    _LOGGER.debug("Binary sensors created and added.")


class ManualColorSimulationBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of the manual color simulation status."""

    def __init__(self, coordinator, tank_slug):
        """Initialize the sensor with a coordinator and tank slug."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{tank_slug}_manual_color_simulation"
        self._attr_translation_key = "manual_color_simulation"
        self._attr_has_entity_name = True
        self.entity_id = f"binary_sensor.{self._attr_unique_id}"
        self._attr_device_info = coordinator.device_info
        _LOGGER.debug("Translation key for %s: %s", self._attr_unique_id, self._attr_translation_key)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_write_ha_state()
        _LOGGER.debug("Final name for %s: %s", self._attr_unique_id, self.name)

    @property
    def is_on(self):
        """Return if the binary sensor is on or off."""
        return self.coordinator.data.get("manualColorSimulationEnabled") == "On"

    @property
    def device_class(self):
        return "power"


class ManualDaytimeSimulationBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of the manual daytime simulation status."""

    def __init__(self, coordinator, tank_slug):
        """Initialize the sensor with a coordinator and tank slug."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{tank_slug}_manual_daytime_simulation"
        self._attr_translation_key = "manual_daytime_simulation"
        self._attr_has_entity_name = True
        self.entity_id = f"binary_sensor.{self._attr_unique_id}"
        self._attr_device_info = coordinator.device_info  # CORRECT
        _LOGGER.debug("Translation key for %s: %s", self._attr_unique_id, self._attr_translation_key)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_write_ha_state()
        _LOGGER.debug("Final name for %s: %s", self._attr_unique_id, self.name)

    @property
    def is_on(self):
        """Return if the binary sensor is on or off."""
        return self.coordinator.data.get("manualDaytimeSimulationEnabled") == "On"

    @property
    def device_class(self):

        return "power"
