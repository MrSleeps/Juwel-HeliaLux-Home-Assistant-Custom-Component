import logging
from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTime
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up number entities for Helialux."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    tank_name = entry.data["tank_name"]
    tank_id = tank_name.lower().replace(" ", "_")

    # Initialize the numbers with min and max values from the entry data
    numbers = [
        HelialuxColorSimulationDuration(coordinator, entry, tank_name, tank_id),
        HelialuxDaytimeSimulationDuration(coordinator, entry, tank_name, tank_id)
    ]

    async_add_entities(numbers, update_before_add=True)

class HelialuxNumberEntity(NumberEntity):
    """Base class for Helialux number helpers."""

    def __init__(self, coordinator, entry, tank_name, tank_id, attribute, min_value, max_value, default_value):
        self.coordinator = coordinator
        self.entry = entry
        self.tank_name = tank_name  # Store tank_name for display (original casing)
        self.tank_id = tank_id  # Store tank_id for entity ID (lowercase)
        self._attr_native_step = 5  # Step increment in minutes
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._state = default_value  # Set the default duration
        self._attr_has_entity_name = True  # Enable automatic prefixing of tank_name
        self._attr_translation_placeholders = {"tank_name": tank_name}  # Pass tank_name for translations
        self._attr_unique_id = f"{entry.entry_id}_{attribute}_duration"
        self._attr_native_min_value = min_value  # Minimum value
        self._attr_native_max_value = max_value  # Maximum value
        self.entity_id = f"number.{tank_id}_{attribute}_duration"
        self._attr_device_info = coordinator.device_info
        # Use the translation_key attribute for automatic translation handling
        self._attr_translation_key = f"{attribute}_duration"

    @property
    def name(self):
        """Return the name of the entity, prefixed with the tank_name."""
        try:
            translated_name = self.hass.data["translations"][DOMAIN]["number"][self._attr_translation_key]["name"]
        except KeyError:
            _LOGGER.warning(f"Translations not found for key: number.{self._attr_translation_key}")
            translated_name = self._attr_translation_key.replace("_", " ").title()
        return f"{self.tank_name} {translated_name}"

    @property
    def native_value(self):
        """Return the current duration setting."""
        return self._state

    async def async_set_native_value(self, value):
        """Set the duration value."""
        self._state = int(value)
        self.async_write_ha_state()  # Ensure HA UI updates the new value
        _LOGGER.debug(f"Set {self.name} to {value} minutes")

    async def async_update(self):
        """Update the state from HA data."""
        await self.coordinator.async_refresh()
        self._update_state()

    def _update_state(self):
        """Update internal state from coordinator data."""
        self._state = self.native_value  # Use the stored value instead of raising an error

class HelialuxColorSimulationDuration(HelialuxNumberEntity):
    """Number entity for setting the manual color simulation duration."""

    def __init__(self, coordinator, entry, tank_name, tank_id):
        # Fetch dynamic min and max values from entry data or use defaults
        min_value = entry.data.get("color_simulation_min", 5)  # Fetch from configuration
        max_value = entry.data.get("color_simulation_max", 120)  # Fetch from configuration
        super().__init__(coordinator, entry, tank_name, tank_id, "manual_color_simulation", min_value, max_value, 60)  # Use the superclass to initialize

class HelialuxDaytimeSimulationDuration(HelialuxNumberEntity):
    """Number entity for setting the manual daytime simulation duration."""

    def __init__(self, coordinator, entry, tank_name, tank_id):
        # Fetch dynamic min and max values from entry data or use defaults
        min_value = entry.data.get("daytime_simulation_min", 5)  # Fetch from configuration
        max_value = entry.data.get("daytime_simulation_max", 120)  # Fetch from configuration
        super().__init__(coordinator, entry, tank_name, tank_id, "manual_daytime_simulation", min_value, max_value, 60)  # Use the superclass to initialize