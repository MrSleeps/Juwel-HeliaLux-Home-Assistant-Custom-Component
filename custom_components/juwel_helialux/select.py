import logging
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN, CONF_TANK_NAME

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Juwel Helialux select platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    tank_name = config_entry.data[CONF_TANK_NAME]
    profile_select = JuwelHelialuxProfileSelect(coordinator, tank_name)
    _LOGGER.debug("Created Profile Select entity: %s", profile_select)
    async_add_entities([profile_select], True)

class JuwelHelialuxProfileSelect(CoordinatorEntity, SelectEntity):
    """Select entity to allow choosing a profile from the Helialux controller."""

    def __init__(self, coordinator, tank_name):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{tank_name}_profile_select"
        self._attr_icon = "mdi:format-list-bulleted"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = []
        self._current_profile = None
        self._attr_has_entity_name = True 
        self._attr_translation_key = "profile"
        self._attr_device_info = coordinator.device_info
        _LOGGER.debug("Device info for select entity %s: %s", self._attr_unique_id, self._attr_device_info)

    @property
    def options(self):
        """Return available profile options (clean names for display)."""
        return self.coordinator.data.get("available_profiles", [])

    @property
    def current_option(self):
        """Return the currently selected profile (clean name)."""
        return self.coordinator.data.get("current_profile", "offline")

    async def async_select_option(self, option: str):
        """Change the profile when selected in Home Assistant."""
        _LOGGER.debug(f"Changing profile to: {option}")
        if not option or option not in self.options:
            _LOGGER.error(f"Invalid profile selected: {option}. Valid options are: {self.options}")
            return
        clean_profile_names = self.coordinator.data.get("available_profiles", [])
        full_profile_names = self.coordinator.data.get("full_profile_names", [])
        if not clean_profile_names or not full_profile_names:
            _LOGGER.error("Profile names are not available in coordinator data.")
            return
        try:
            index = clean_profile_names.index(option)
            full_profile_name = full_profile_names[index]
        except ValueError:
            _LOGGER.error(f"Profile '{option}' not found in available profiles.")
            return

        _LOGGER.debug(f"Attempting to change profile: {option} -> Full Name: {full_profile_name}")
        success = await self.coordinator.helialux.set_profile(full_profile_name, option)
        if not success:
            _LOGGER.error(f"Profile change failed for: {option} (Full Name: {full_profile_name})")
        if success:
            self.coordinator.data["current_profile"] = option
            self.async_write_ha_state()
            _LOGGER.debug(f"Profile changed successfully to {option}")
            await self.coordinator.async_request_refresh()            
        else:
            _LOGGER.error(f"Failed to change profile to: {option}")

    async def async_added_to_hass(self):
        """Ensure options are updated when the entity is added."""
        await super().async_added_to_hass()
        self._update_options()
        self.async_write_ha_state()

    def _handle_coordinator_update(self):
        """Ensure Home Assistant doesn't reset the profile."""
        new_profile = self.coordinator.data.get("current_profile", "offline")
        
        if new_profile != self.current_option:
            _LOGGER.debug(f"Fixing HA state: {self.current_option} -> {new_profile}")
            self._attr_current_option = new_profile
            self.async_write_ha_state()

        self._update_options()
        super()._handle_coordinator_update()

    def _update_options(self):
        """Update the available profile options."""
        new_options = self.coordinator.data.get("available_profiles", [])
        if new_options != self._attr_options:
            self._attr_options = new_options
            self.async_write_ha_state()