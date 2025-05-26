import logging
from homeassistant.components.light import (
    LightEntity,
    ColorMode,
)
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Juwel Helialux light platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, 1)
    coordinator.update_interval = timedelta(seconds=15)

    _LOGGER.debug("Coordinator contents: %s", dir(coordinator))

    if not hasattr(coordinator, "helialux"):
        _LOGGER.error("Coordinator is missing the 'helialux' attribute!")
        return

    await coordinator.async_config_entry_first_refresh()

    _LOGGER.debug("Coordinator initial data: %s", coordinator.data)

    tank_name = entry.title
    async_add_entities([JuwelHelialuxLight(coordinator, tank_name)], True)


class JuwelHelialuxLight(CoordinatorEntity, LightEntity):
    """Representation of a Juwel Helialux Light in Home Assistant."""

    def __init__(self, coordinator, tank_name):
        """Initialize the light entity."""
        super().__init__(coordinator)#
        self._controller = coordinator.helialux
        self._attr_unique_id = f"{tank_name.lower().replace(' ', '_')}_light"
        self.entity_id = f"light.{self._attr_unique_id}"
        self._attr_has_entity_name = True 
        self._attr_translation_key = "light_name"
        self._attr_supported_color_modes = {ColorMode.RGBW}
        self._attr_color_mode = ColorMode.RGBW
        self._attr_is_on = False
        self._attr_brightness = None
        self._attr_rgbw_color = (0, 0, 0, 0)
        self._attr_device_info = coordinator.device_info


    @property
    def is_on(self):
        """Return true if light is on (any RGBW value is greater than 0)."""
        if not self.coordinator.data:
            _LOGGER.warning("Coordinator data is None, returning False for is_on")
            return False
        raw_red = self.coordinator.data.get("red", 0)
        raw_green = self.coordinator.data.get("green", 0)
        raw_blue = self.coordinator.data.get("blue", 0)
        raw_white = self.coordinator.data.get("white", 0)

        return raw_red > 0 or raw_green > 0 or raw_blue > 0 or raw_white > 0

    @property
    def rgbw_color(self):
        """Return RGBW color values converted to Home Assistant's scale (0-255)."""
        if not self.coordinator.data:
            _LOGGER.warning("Coordinator data is None, returning default RGBW (0,0,0,0)")
            return (0, 0, 0, 0)
        raw_red = self.coordinator.data.get("red", 0)
        raw_green = self.coordinator.data.get("green", 0)
        raw_blue = self.coordinator.data.get("blue", 0)
        raw_white = self.coordinator.data.get("white", 0)

        # If the light is off (all values are 0), return black
        if raw_red == 0 and raw_green == 0 and raw_blue == 0 and raw_white == 0:
            return (0, 0, 0, 0)

        # Convert from 0-100 scale to 0-255
        converted_red = int(raw_red * 2.55)
        converted_green = int(raw_green * 2.55)
        converted_blue = int(raw_blue * 2.55)
        converted_white = int(raw_white * 2.55)

        return (converted_red, converted_green, converted_blue, converted_white)

    @property
    def brightness(self):
        """Return the brightness of the light, based on the highest RGBW value."""
        if not self.coordinator.data:
            _LOGGER.warning("Coordinator data is None, returning default brightness 0")
            return 0

        raw_red = self.coordinator.data.get("red", 0)
        raw_green = self.coordinator.data.get("green", 0)
        raw_blue = self.coordinator.data.get("blue", 0)
        raw_white = self.coordinator.data.get("white", 0)

        # If the light is off (all values are 0), return brightness 0
        if raw_red == 0 and raw_green == 0 and raw_blue == 0 and raw_white == 0:
            return 0

        # Convert to Home Assistant's scale (0-255) and calculate brightness
        max_rgbw_value = max(
            raw_red * 2.55,
            raw_green * 2.55,
            raw_blue * 2.55,
            raw_white * 2.55,
        )

        # Return the brightness based on the highest value
        return int(max_rgbw_value)

    async def async_turn_on(self, **kwargs):
        """Turn the light on with optional parameters."""
        _LOGGER.debug("Turn on called with: %s", kwargs)
        
        # Get target values with defaults
        brightness = kwargs.get("brightness", 255)
        rgbw_color = kwargs.get("rgbw_color", (255, 255, 255, 255))
        
        # Convert to device scale (0-100)
        white = min(100, max(0, rgbw_color[3] / 2.55))
        blue = min(100, max(0, rgbw_color[2] / 2.55))
        green = min(100, max(0, rgbw_color[1] / 2.55))
        red = min(100, max(0, rgbw_color[0] / 2.55))
        
        # Apply brightness scaling if needed
        if brightness < 255:
            scale = brightness / 255.0
            white = min(100, white * scale)
            blue = min(100, blue * scale)
            green = min(100, green * scale)
            red = min(100, red * scale)

        _LOGGER.debug("Setting light to W:%d B:%d G:%d R:%d", white, blue, green, red)
        
        # Enable manual override for 5 seconds
        await self.coordinator.set_manual_override(True, 5)
        
        try:
            # Get duration from number entity (same approach as in switch.py)
            duration_entity = f"number.{self._attr_unique_id.split('_light')[0]}_manual_color_simulation_duration"
            duration_state = self.coordinator.hass.states.get(duration_entity)
            duration_minutes = int(float(duration_state.state) * 60) if duration_state else 720  # Default to 12 hours if not found
            
            _LOGGER.debug("Using manual color simulation duration: %s minutes", duration_minutes)
            
            # Set the light state with the configured duration
            await self._controller.start_manual_color_simulation(duration_minutes)            
            await self._controller.set_manual_color(white, blue, green, red)
            
            # Update local state immediately
            self._attr_is_on = True
            self._attr_brightness = brightness
            self._attr_rgbw_color = rgbw_color
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("Error setting light state: %s", e)
            await self.coordinator.set_manual_override(False)
            raise

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug("Turning off Juwel Helialux light")
        try:
            # Get duration from number entity (same approach as in switch.py)
            duration_entity = f"number.{self._attr_unique_id.split('_light')[0]}_manual_color_simulation_duration"
            duration_state = self.coordinator.hass.states.get(duration_entity)
            duration_minutes = int(float(duration_state.state) * 60) if duration_state else 720  # Default to 12 hours if not found
            
            _LOGGER.debug("Using manual color simulation duration: %s minutes", duration_minutes)
            
            await self._controller.start_manual_color_simulation(duration_minutes)
            await self._controller.set_manual_color(0, 0, 0, 0)
            self._attr_is_on = False
            self._attr_brightness = 0
            self._attr_rgbw_color = (0, 0, 0, 0)
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Error turning off light: %s", e)
            raise