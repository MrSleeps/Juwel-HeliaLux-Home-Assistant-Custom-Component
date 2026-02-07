import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.util import slugify
from .pyhelialux.pyHelialux import Controller as Helialux
from .const import DOMAIN

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
        self._attr_device_info = coordinator.device_info  # CORRECT
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
            duration_entity = f"number.{self.tank_id}_manual_color_simulation_duration"
            duration_state = self.coordinator.hass.states.get(duration_entity)
            
            if duration_state is None:
                _LOGGER.warning("Duration number entity not found, using default 1 hour")
                duration = 60  # Default to 1 hour in minutes
            else:
                try:
                    duration = float(duration_state.state) * 60  # Convert hours to minutes
                    duration = max(1, min(1440, duration))  # Clamp between 1 min and 24 hours
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(f"Invalid duration value: {duration_state.state}, using default 1 hour. Error: {e}")
                    duration = 60

            _LOGGER.debug(f"Starting manual color simulation for {duration} minutes")
            await self.coordinator.helialux.start_manual_color_simulation(int(duration))
            await self.coordinator.async_refresh()
            self._update_state()
            
        except Exception as e:
            _LOGGER.error(f"Error starting manual color simulation: {e}")
            raise

    async def async_turn_off(self, **kwargs):
        """Turn off manual color simulation."""
        await self.coordinator.helialux.stop_manual_color_simulation()
        await self.coordinator.async_refresh()
        self._update_state()

    def _update_state(self):
        """Update the switch state based on coordinator data."""
        self._state = self.coordinator.data.get("manualColorSimulationEnabled") == "On"


class HelialuxManualDaytimeSimulationSwitch(HelialuxSwitch):
    """Switch for manual daytime simulation."""

    def __init__(self, coordinator, tank_name, tank_id):
        super().__init__(coordinator, tank_name, tank_id, "manual_daytime_simulation")

    async def async_turn_on(self, **kwargs):
        """Turn on manual daytime simulation using the duration set in number helper."""
        duration_entity = f"number.{self.tank_id}_manual_daytime_simulation_duration"
        duration_state = self.coordinator.hass.states.get(duration_entity)
        duration = int(duration_state.state) * 60 if duration_state else 60  # Convert hours to minutes

        _LOGGER.debug(f"Starting manual daytime simulation for {duration} minutes")

        await self.coordinator.helialux.start_manual_daytime_simulation(duration)
        await self.coordinator.async_refresh()
        self._update_state()

    async def async_turn_off(self, **kwargs):
        """Turn off manual daytime simulation."""
        await self.coordinator.helialux.stop_manual_daytime_simulation()
        await self.coordinator.async_refresh()
        self._update_state()

    def _update_state(self):
        """Update the switch state based on coordinator data."""
        self._state = self.coordinator.data.get("manualDaytimeSimulationEnabled") == "On"