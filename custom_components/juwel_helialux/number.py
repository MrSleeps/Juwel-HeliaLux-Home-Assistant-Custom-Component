import logging
from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTime
from homeassistant.helpers.storage import Store
from homeassistant.util import slugify
from .const import DOMAIN
import asyncio

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up number entities for Helialux via config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    tank_name = entry.data["tank_name"]
    tank_id = slugify(tank_name)

    numbers = [
        HelialuxColorSimulationDuration(hass, coordinator, entry, tank_name, tank_id),
        HelialuxDaytimeSimulationDuration(hass, coordinator, entry, tank_name, tank_id),
        HelialuxDaytimeSimulationPosition(hass, coordinator, entry, tank_name, tank_id)
    ]

    async_add_entities(numbers, update_before_add=True)


class HelialuxNumberEntity(NumberEntity):
    """Base class for Helialux number entities."""

    def __init__(self, hass, coordinator, entry, tank_name, tank_id, attribute, min_value, max_value, default_value, step=0.5, unit=UnitOfTime.HOURS):
        self.coordinator = coordinator
        self.entry = entry
        self.tank_name = tank_name
        self.tank_id = tank_id
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._state = float(default_value)
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{entry.entry_id}_{attribute}"
        self._attr_native_min_value = float(min_value)
        self._attr_native_max_value = float(max_value)
        self.entity_id = f"number.{tank_id}_{attribute}"
        self._attr_device_info = coordinator.device_info
        self._attr_translation_key = attribute

        # Initialize persistent storage
        self._store = Store(hass, 1, f"{DOMAIN}_{self._attr_unique_id}.json")

    @property
    def native_value(self):
        """Return the current value."""
        return self._state

    async def async_set_native_value(self, value):
        """Set the value."""
        self._state = float(value)
        # Store the value in the coordinator
        self.coordinator.data[f"{self._attr_translation_key}"] = self._state
        self.async_write_ha_state()
        await self._store.async_save({"value": self._state})
        _LOGGER.debug(f"Set {self.entity_id} to {value} {self._attr_native_unit_of_measurement}")

    async def async_update(self):
        """Update the state from HA data."""
        await self.coordinator.async_refresh()
        self._update_state()

    def _update_state(self):
        """Update internal state from coordinator data."""
        # Override in child classes if needed
        pass

    async def async_added_to_hass(self):
        """Load previously stored state when added to Home Assistant."""
        await super().async_added_to_hass()
        data = await self._store.async_load()
        if data and "value" in data:
            self._state = float(data["value"])
            _LOGGER.debug(f"Restored {self.entity_id} to {self._state} {self._attr_native_unit_of_measurement}")


class HelialuxColorSimulationDuration(HelialuxNumberEntity):
    """Number entity for setting the manual color simulation duration."""

    def __init__(self, hass, coordinator, entry, tank_name, tank_id):
        min_value = float(entry.data.get("color_simulation_min", 1))
        max_value = float(entry.data.get("color_simulation_max", 24))
        super().__init__(hass, coordinator, entry, tank_name, tank_id, 
                        "manual_color_simulation_duration", min_value, max_value, 12.0)


class HelialuxDaytimeSimulationDuration(HelialuxNumberEntity):
    """Number entity for setting the manual daytime simulation duration."""

    def __init__(self, hass, coordinator, entry, tank_name, tank_id):
        min_value = float(entry.data.get("daytime_simulation_min", 0.5))
        max_value = float(entry.data.get("daytime_simulation_max", 24))
        super().__init__(hass, coordinator, entry, tank_name, tank_id, 
                        "manual_daytime_simulation_duration", min_value, max_value, 1.0)


class HelialuxDaytimeSimulationPosition(HelialuxNumberEntity):
    """Number entity for setting the time position for manual daytime simulation."""
    
    def __init__(self, hass, coordinator, entry, tank_name, tank_id):
        # Time of day in hours (0-24)
        super().__init__(hass, coordinator, entry, tank_name, tank_id,
                        "daytime_simulation_position", 0.0, 24.0, 12.0, 
                        step=0.25, unit="hours")  # 15-minute increments
    
    @property
    def icon(self):
        return "mdi:clock-time-five"
    
    async def async_set_native_value(self, value):
        """Set the value and update the device if daytime simulation is active."""
        old_value = self._state
        self._state = float(value)
        
        # Store the value
        self.coordinator.data["daytime_simulation_position"] = self._state
        self.async_write_ha_state()
        await self._store.async_save({"value": self._state})
        
        _LOGGER.debug(f"Set {self.entity_id} to {value} hours")
        
        # Check if daytime simulation is currently active
        is_daytime_active = self.coordinator.data.get("manualDaytimeSimulationEnabled") == "On"
        
        if is_daytime_active:
            _LOGGER.debug("Daytime simulation is active, updating device position")
            
            # Convert hours to minutes since midnight
            target_minutes = int(self._state * 60)
            target_minutes = max(0, min(1440, target_minutes))
            
            # Get the current duration
            duration_entity = f"number.{self.tank_id}_manual_daytime_simulation_duration"
            duration_state = self.hass.states.get(duration_entity)
            
            if duration_state is None:
                duration_minutes = 60
            else:
                try:
                    duration_hours = float(duration_state.state)
                    duration_minutes = int(duration_hours * 60)
                    duration_minutes = max(1, min(1440, duration_minutes))
                except (ValueError, TypeError):
                    duration_minutes = 60
            
            # Format duration as HH:MM
            duration_hours = duration_minutes // 60
            duration_mins = duration_minutes % 60
            duration_formatted = f"{duration_hours:02d}:{duration_mins:02d}"
            
            # Update the device with new position while keeping simulation active
            try:
                await self.coordinator.helialux.update_daytime_simulation_position(
                    target_minutes=target_minutes,
                    duration=duration_formatted
                )
                _LOGGER.debug(f"Updated device position to {target_minutes} minutes")
                
                # Small delay then refresh
                await asyncio.sleep(0.5)
                await self.coordinator.async_refresh()
                
            except Exception as e:
                _LOGGER.error(f"Error updating daytime simulation position: {e}")
    
    def _update_state(self):
        """Update from coordinator if needed."""
        # If the device has a current simulated time position, we could read it here
        # For now, we just maintain the last set value
        pass