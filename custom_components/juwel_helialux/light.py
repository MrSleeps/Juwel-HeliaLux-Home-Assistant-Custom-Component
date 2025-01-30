import logging
from homeassistant.components.light import (
    LightEntity,
    ColorMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN  # Ensure DOMAIN is correctly defined

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the Juwel Helialux light platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Debug log to confirm coordinator contents
    _LOGGER.debug("Coordinator contents: %s", dir(coordinator))
    
    if not hasattr(coordinator, "helialux"):
        _LOGGER.error("Coordinator is missing the 'helialux' attribute!")
        return

    tank_name = entry.title
    async_add_entities([JuwelHelialuxLight(coordinator, tank_name)], True)


class JuwelHelialuxLight(CoordinatorEntity, LightEntity):
    """Representation of a Juwel Helialux Light in Home Assistant."""

    def __init__(self, coordinator, tank_name):
        """Initialize the light entity."""
        super().__init__(coordinator)

        # Use the 'self.helialux' from the coordinator
        self._controller = coordinator.helialux  # Using the existing 'Helialux' instance
        self._attr_name = f"{tank_name} Light"
        self._attr_unique_id = f"juwel_helialux_{tank_name.lower().replace(' ', '_')}"

        # Supported color modes
        self._attr_supported_color_modes = {ColorMode.RGBW}
        self._attr_color_mode = ColorMode.RGBW

        self._attr_is_on = False
        self._attr_brightness = None
        self._attr_rgbw_color = (0, 0, 0, 0)

#    async def async_update(self):
#        """Fetch the latest status from the controller."""
#        _LOGGER.debug("Updating Juwel Helialux light state")
#        status = await self._controller.get_status()

#        if status:
#            # Extract brightness levels from RGBW channels
#            red, green, blue, white = (
#                status["currentRed"],
#                status["currentGreen"],
#                status["currentBlue"],
#                status["currentWhite"],
#            )

            # Convert RGBW values (0-100) to Home Assistant brightness (0-255)
#            brightness = max(red, green, blue, white) * 255 // 100 if any([red, green, blue, white]) else 0

#            self._attr_is_on = brightness > 0
#            self._attr_brightness = brightness
#            self._attr_rgbw_color = (
#                int(red * 255 / 100),
#                int(green * 255 / 100),
#                int(blue * 255 / 100),
#                int(white * 255 / 100),
#            )

    async def async_update(self):
        """Fetch the latest status from the controller."""
        _LOGGER.debug("Updating Juwel Helialux light state")
        status = await self._controller.get_status()

        if status:
            # Extract RGBW values from the controller (they are in the range 0-100)
            red, green, blue, white = (
                status["currentRed"],
                status["currentGreen"],
                status["currentBlue"],
                status["currentWhite"],
            )

            # Convert RGBW values (0-100) to Home Assistant scale (0-255)
            red = int(red * 255 / 100)
            green = int(green * 255 / 100)
            blue = int(blue * 255 / 100)
            white = int(white * 255 / 100)

            # Calculate brightness as the maximum value of RGBW
            brightness = max(red, green, blue, white)

            self._attr_is_on = brightness > 0
            self._attr_brightness = brightness
            self._attr_rgbw_color = (red, green, blue, white)

            _LOGGER.debug("Updated state - RGBW: %s, Brightness: %d", self._attr_rgbw_color, self._attr_brightness)




    async def async_turn_on(self, **kwargs):
        """Turn the light on with optional parameters."""
        _LOGGER.debug("Turning on Juwel Helialux light with kwargs: %s", kwargs)

        brightness = kwargs.get("brightness", 255)
        rgbw_color = kwargs.get("rgbw_color", (255, 255, 255, 255))

        # Convert HA brightness (0-255) to Juwel's (0-100)
        brightness_juwel = brightness * 100 // 255

        # Calculate the scaling factor for RGBW values based on brightness
        scale_factor = brightness_juwel / 100.0  # scale to range [0, 1]

        # Convert RGBW values (0-255) to Juwel's (0-100)
        red, green, blue, white = (
            int(rgbw_color[0] * 100 // 255 * scale_factor),
            int(rgbw_color[1] * 100 // 255 * scale_factor),
            int(rgbw_color[2] * 100 // 255 * scale_factor),
            int(rgbw_color[3] * 100 // 255 * scale_factor),
        )

        # Debugging output
        _LOGGER.debug("Converted RGBW values (scaled): Red: %d, Green: %d, Blue: %d, White: %d",
                      red, green, blue, white)

        # Ensure all values are within the range of 0-100
        red = max(0, min(100, red))
        green = max(0, min(100, green))
        blue = max(0, min(100, blue))
        white = max(0, min(100, white))

        _LOGGER.debug(
            "Final RGBW values after clamping: Red: %d, Green: %d, Blue: %d, White: %d",
            red, green, blue, white,
        )

        # Now set the manual color with the adjusted values
        await self._controller.start_manual_color_simulation(60)  # Ensure it's running
        await self._controller.set_manual_color(white, blue, green, red)


        self._attr_is_on = True
        self._attr_brightness = brightness
        self._attr_rgbw_color = rgbw_color

        self.async_write_ha_state()





#    async def async_turn_on(self, **kwargs):
#        """Turn the light on with optional parameters."""
#        _LOGGER.debug("Turning on Juwel Helialux light with kwargs: %s", kwargs)

        # Set RGBW to 100% when turning the light on
#        red, green, blue, white = 100, 100, 100, 100

        # Ensure full brightness (100% of RGBW)
#        brightness = kwargs.get("brightness", 255)  # Default to max brightness

        # Convert HA brightness (0-255) to Juwel's (0-100)
#        brightness_juwel = brightness * 100 // 255

        # Log the color and brightness settings
#        _LOGGER.debug(
#            "Setting colors - Red: %d, Green: %d, Blue: %d, White: %d (Juwel scale)",
#            red, green, blue, white,
#        )

        # Set the light to 100% RGBW values
#        await self._controller.set_manual_color(white, blue, green, red)

        # Start manual color simulation with 60 minutes duration
#        await self._controller.start_manual_color_simulation(60)

        # Update internal state to reflect the changes
#        self._attr_is_on = True
#        self._attr_brightness = brightness
#        self._attr_rgbw_color = (red, green, blue, white)

#        # Update Home Assistant state
#        self.async_write_ha_state()


    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug("Turning off Juwel Helialux light")

        # Stop manual color simulation before setting colors to zero
        await self._controller.stop_manual_color_simulation()
        await self._controller.set_manual_color(0, 0, 0, 0)

        self._attr_is_on = False
        self._attr_brightness = 0
        self._attr_rgbw_color = (0, 0, 0, 0)

        self.async_write_ha_state()