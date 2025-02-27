import logging
from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTime
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up number entities for Helialux via config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    tank_name = entry.data["tank_name"]
    tank_id = tank_name.lower().replace(" ", "_")

    numbers = [
        HelialuxColorSimulationDuration(coordinator, entry, tank_name, tank_id),
        HelialuxDaytimeSimulationDuration(coordinator, entry, tank_name, tank_id)
    ]

    async_add_entities(numbers, update_before_add=True)


class HelialuxNumberEntity(NumberEntity):
    """Base class for Helialux number entities."""

    def __init__(self, coordinator, entry, tank_name, tank_id, attribute, min_value, max_value, default_value):
        self.coordinator = coordinator
        self.entry = entry
        self.tank_name = tank_name
        self.tank_id = tank_id
        self._attr_native_step = 0.5  # Step increment in hours
        self._attr_native_unit_of_measurement = UnitOfTime.HOURS
        self._state = default_value
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{entry.entry_id}_{attribute}_duration"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self.entity_id = f"number.{tank_id}_{attribute}_duration"
        self._attr_device_info = coordinator.device_info
        self._attr_translation_key = f"{attribute}_duration"

    @property
    def native_value(self):
        """Return the current duration setting."""
        return self._state

    async def async_set_native_value(self, value):
        """Set the duration value."""
        self._state = int(value)
        self.async_write_ha_state()
        _LOGGER.debug(f"Set {self.entity_id} to {value} minutes")

    async def async_update(self):
        """Update the state from HA data."""
        await self.coordinator.async_refresh()
        self._update_state()

    def _update_state(self):
        """Update internal state from coordinator data."""
        self._state = self.native_value


class HelialuxColorSimulationDuration(HelialuxNumberEntity):
    """Number entity for setting the manual color simulation duration."""

    def __init__(self, coordinator, entry, tank_name, tank_id):
        min_value = entry.data.get("color_simulation_min", 1)
        max_value = entry.data.get("color_simulation_max", 24)
        super().__init__(coordinator, entry, tank_name, tank_id, "manual_color_simulation", min_value, max_value, 12)


class HelialuxDaytimeSimulationDuration(HelialuxNumberEntity):
    """Number entity for setting the manual daytime simulation duration."""

    def __init__(self, coordinator, entry, tank_name, tank_id):
        min_value = entry.data.get("daytime_simulation_min", 1)
        max_value = entry.data.get("daytime_simulation_max", 24)
        super().__init__(coordinator, entry, tank_name, tank_id, "manual_daytime_simulation", min_value, max_value, 12)
