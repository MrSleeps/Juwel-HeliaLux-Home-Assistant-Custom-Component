import logging
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up switches for Helialux via config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    tank_name = entry.data["tank_name"]
    tank_id = tank_name.lower().replace(" ", "_")  # Ensure a valid entity ID format

    switches = [
        HelialuxManualColorSimulationSwitch(coordinator, tank_name, tank_id),
        HelialuxManualDaytimeSimulationSwitch(coordinator, tank_name, tank_id)
    ]

    async_add_entities(switches, update_before_add=True)


class HelialuxSwitch(SwitchEntity):
    """Base class for Helialux switches."""

    def __init__(self, coordinator, tank_name, tank_id, attribute):
        self.coordinator = coordinator
        self.tank_name = tank_name  # Store tank_name for display
        self.tank_id = tank_id  # Store tank_id for entity ID
        self._state = False
        self._attr_device_info = coordinator.device_info  # ✅ Link to the same device as sensors
        self._attr_has_entity_name = True  # ✅ Enable automatic prefixing
        self._attr_translation_key = attribute  # ✅ Set translation key
        self._attr_translation_placeholders = {"tank_name": tank_name}  # ✅ Allow dynamic translation
        self._attr_unique_id = f"{tank_id}_{attribute}"  # ✅ Unique entity ID
        self.entity_id = f"switch.{tank_id}_{attribute}"

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
        duration_entity = f"number.{self.tank_id}_manual_color_simulation_duration"
        duration_state = self.coordinator.hass.states.get(duration_entity)
        duration = int(duration_state.state) * 60 if duration_state else 60  # Convert hours to minutes

        _LOGGER.debug(f"Starting manual color simulation for {duration} minutes")  # Debugging log

        await self.coordinator.helialux.start_manual_color_simulation(duration)
        await self.coordinator.async_refresh()
        self._update_state()

    async def async_turn_off(self, **kwargs):
        """Turn off manual color simulation."""
        await self.coordinator.helialux.stop_manual_color_simulation()
        await self.coordinator.async_refresh()
        self._update_state()

    def _update_state(self):
        """Update the switch state based on coordinator data."""
        self._state = self.coordinator.data.get("manualColorSimulationEnabled", False)


class HelialuxManualDaytimeSimulationSwitch(HelialuxSwitch):
    """Switch for manual daytime simulation."""

    def __init__(self, coordinator, tank_name, tank_id):
        super().__init__(coordinator, tank_name, tank_id, "manual_daytime_simulation")

    async def async_turn_on(self, **kwargs):
        """Turn on manual daytime simulation using the duration set in number helper."""
        duration_entity = f"number.{self.tank_id}_manual_daytime_simulation_duration"
        duration_state = self.coordinator.hass.states.get(duration_entity)
        duration = int(duration_state.state) * 60 if duration_state else 60  # Convert hours to minutes

        _LOGGER.debug(f"Starting manual daytime simulation for {duration} minutes")  # Debugging log

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
        self._state = self.coordinator.data.get("manualDaytimeSimulationEnabled", False)