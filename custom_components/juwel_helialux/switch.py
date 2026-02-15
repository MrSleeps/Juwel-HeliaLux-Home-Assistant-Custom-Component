import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.util import slugify
from .const import DOMAIN
import asyncio

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up switches for Helialux via config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    tank_name = entry.data["tank_name"]
    tank_id = slugify(tank_name)

    switches = [
        HelialuxManualColorSimulationSwitch(coordinator, tank_name, tank_id),
        HelialuxManualDaytimeSimulationSwitch(coordinator, tank_name, tank_id)
    ]

    async_add_entities(switches, update_before_add=True)


class HelialuxSwitch(SwitchEntity):
    """Base class for Helialux switches."""

    def __init__(self, coordinator, tank_name, tank_id, attribute):
        self.coordinator = coordinator
        self.tank_name = tank_name
        self.tank_id = tank_id
        self._state = False
        self._attr_device_info = coordinator.device_info
        self._attr_has_entity_name = True 
        self._attr_translation_key = attribute
        self._attr_unique_id = f"{tank_id}_{attribute}" 
        self.entity_id = f"switch.{tank_id}_{attribute}"
        self._update_state()

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        raise NotImplementedError

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        raise NotImplementedError

    @property
    def is_on(self):
        """Return True if switch is on."""
        return self._state

    async def async_update(self):
        """Update switch state from coordinator."""
        await self.coordinator.async_refresh()
        self._update_state()

    def _update_state(self):
        """Update internal state from coordinator data."""
        raise NotImplementedError


class HelialuxManualColorSimulationSwitch(HelialuxSwitch):
    """Switch for manual color simulation."""

    def __init__(self, coordinator, tank_name, tank_id):
        super().__init__(coordinator, tank_name, tank_id, "manual_color_simulation")

    async def async_turn_on(self, **kwargs):
        """Turn on manual color simulation using the duration set in number helper."""
        try:
            # Get duration from number entity (in hours)
            duration_entity = f"number.{self.tank_id}_manual_color_simulation_duration"
            duration_state = self.coordinator.hass.states.get(duration_entity)
            
            if duration_state is None:
                _LOGGER.warning("Duration number entity not found, using default 12 hours")
                duration_minutes = 720  # Default to 12 hours in minutes
            else:
                try:
                    duration_hours = float(duration_state.state)
                    duration_minutes = int(duration_hours * 60)
                    duration_minutes = max(1, min(1440, duration_minutes))  # Clamp between 1 min and 24 hours
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(f"Invalid duration value: {duration_state.state}, using default 12 hours. Error: {e}")
                    duration_minutes = 720

            _LOGGER.debug(f"Starting manual color simulation for {duration_minutes} minutes")
            await self.coordinator.helialux.start_manual_color_simulation(duration_minutes)
            
            # Set manual override to prevent updates during simulation
            await self.coordinator.set_manual_override(True, duration_minutes * 60)  # Convert to seconds
            await self.coordinator.async_refresh()
            self._update_state()
            
        except Exception as e:
            _LOGGER.error(f"Error starting manual color simulation: {e}")
            raise

    async def async_turn_off(self, **kwargs):
        """Turn off manual color simulation."""
        await self.coordinator.helialux.stop_manual_color_simulation()
        await self.coordinator.set_manual_override(False)
        await self.coordinator.async_refresh()
        self._update_state()

    def _update_state(self):
        """Update the switch state based on coordinator data."""
        self._state = self.coordinator.data.get("manualColorSimulationEnabled") == "On"


class HelialuxManualDaytimeSimulationSwitch(HelialuxSwitch):
    """Switch for manual daytime simulation (simulates time of day in fast motion)."""

    def __init__(self, coordinator, tank_name, tank_id):
        super().__init__(coordinator, tank_name, tank_id, "manual_daytime_simulation")

    async def async_turn_on(self, **kwargs):
        """Turn on manual daytime simulation."""
        try:
            _LOGGER.debug("Attempting to turn ON manual daytime simulation")
            
            # Get the target time position from the number entity (in hours, 0-24)
            time_position_entity = f"number.{self.tank_id}_daytime_simulation_position"
            time_position_state = self.coordinator.hass.states.get(time_position_entity)
            
            if time_position_state is None:
                _LOGGER.warning("Time position number entity not found, using current time")
                from datetime import datetime
                now = datetime.now()
                target_time_minutes = (now.hour * 60) + now.minute
            else:
                try:
                    target_hours = float(time_position_state.state)
                    target_time_minutes = int(target_hours * 60)
                    target_time_minutes = max(0, min(1440, target_time_minutes))
                    _LOGGER.debug(f"Target time position: {target_hours} hours ({target_time_minutes} minutes)")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(f"Invalid time position value: {time_position_state.state}, using current time. Error: {e}")
                    from datetime import datetime
                    now = datetime.now()
                    target_time_minutes = (now.hour * 60) + now.minute

            # Get the duration from the number entity (in hours)
            duration_entity = f"number.{self.tank_id}_manual_daytime_simulation_duration"
            duration_state = self.coordinator.hass.states.get(duration_entity)
            
            if duration_state is None:
                _LOGGER.warning("Duration number entity not found, using default 1 hour")
                duration_minutes = 60
            else:
                try:
                    duration_hours = float(duration_state.state)
                    duration_minutes = int(duration_hours * 60)
                    duration_minutes = max(1, min(1440, duration_minutes))
                    _LOGGER.debug(f"Duration: {duration_hours} hours ({duration_minutes} minutes)")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(f"Invalid duration value: {duration_state.state}, using default 1 hour. Error: {e}")
                    duration_minutes = 60

            # Format duration as HH:MM
            duration_hours = duration_minutes // 60
            duration_mins = duration_minutes % 60
            duration_formatted = f"{duration_hours:02d}:{duration_mins:02d}"

            _LOGGER.debug(f"Starting manual daytime simulation at position {target_time_minutes} for duration {duration_formatted}")
            
            # First, ensure any existing simulation is completely stopped
            if self._state:
                _LOGGER.debug("Daytime simulation already active, stopping first")
                await self.coordinator.helialux.stop_manual_daytime_simulation()
                await asyncio.sleep(2)
            
            # Start the simulation with both parameters
            await self.coordinator.helialux.start_manual_daytime_simulation(
                target_minutes=target_time_minutes,
                duration=duration_formatted
            )
            
            # Force refreshes
            await asyncio.sleep(1)
            await self.coordinator.async_refresh()
            self._update_state()
            
            await asyncio.sleep(0.5)
            await self.coordinator.async_refresh()
            self._update_state()
            
            _LOGGER.debug(f"State after turning ON: {self._state}")
            
        except Exception as e:
            _LOGGER.error(f"Error starting manual daytime simulation: {e}")
            raise

    async def async_turn_off(self, **kwargs):
        """Turn off manual daytime simulation."""
        try:
            _LOGGER.debug("Attempting to turn OFF manual daytime simulation")
            
            await self.coordinator.helialux.stop_manual_daytime_simulation()
            
            # Force multiple refreshes
            await asyncio.sleep(1)
            await self.coordinator.async_refresh()
            self._update_state()
            
            await asyncio.sleep(0.5)
            await self.coordinator.async_refresh()
            self._update_state()
            
            _LOGGER.debug(f"State after turning OFF: {self._state}")
            
        except Exception as e:
            _LOGGER.error(f"Error stopping manual daytime simulation: {e}")
            raise

    def _update_state(self):
        """Update the switch state based on coordinator data."""
        old_state = self._state
        raw_value = self.coordinator.data.get("manualDaytimeSimulationEnabled")
        self._state = raw_value == "On"
        
        if old_state != self._state:
            _LOGGER.debug(f"Daytime simulation state changed: {old_state} -> {self._state} (raw value: {raw_value})")