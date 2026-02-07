import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_NAME, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL
from .pyhelialux.pyHelialux import Controller as Helialux
import asyncio
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

class JuwelHelialuxCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Juwel Helialux device."""

    def __init__(self, hass, tank_host, tank_protocol, tank_name, update_interval):
        super().__init__(
            hass,
            _LOGGER,
            name="Juwel Helialux Sensor",
            update_interval=timedelta(minutes=update_interval),
        )
        self.tank_host = tank_host
        self.tank_protocol = tank_protocol
        self.tank_name = tank_name  # Store original name
        self.tank_slug = slugify(tank_name)  # Store slugified version
        self._manual_override = False
        self._override_until = None
        _LOGGER.debug("Initializing Coordinator - Tank Name: %s, Tank Slug: %s", tank_name, self.tank_slug)

        url = f"{self.tank_protocol}://{self.tank_host}"
        self.helialux = Helialux(url)
        self.data = {}  
        
        # Set default device info - use tank_slug for identifiers, tank_name for display
        self.device_info = {
            "identifiers": {(DOMAIN, self.tank_slug)},  # Use slug for identifier
            "name": tank_name,  # Use original name for display (NOT "tank_name" string!)
            "manufacturer": "Juwel",
            "model": "Helialux",
            "sw_version": "Unknown",
            "hw_version": "Unknown",
            "configuration_url": url,
            "connections": set(),
        }
        _LOGGER.debug("Device info created with name: %s", tank_name)

    async def set_manual_override(self, active: bool, duration: int = 5):
        """Control manual override mode."""
        self._manual_override = active
        if active:
            self._override_until = asyncio.get_event_loop().time() + duration
            _LOGGER.debug("Manual override active for %s seconds", duration)
        else:
            self._override_until = None
            _LOGGER.debug("Manual override deactivated")

    async def async_config_entry_first_refresh(self):
        """Fetch initial data and store device info."""
        await self.async_refresh()

        device_info = await self.helialux.device_info()
        _LOGGER.debug("Fetched device info: %s", device_info)

        if device_info:
            self.device_info.update({
                "sw_version": device_info.get("firmware_version", "Unknown"),
                "hw_version": device_info.get("hardware_version", "Unknown"),
                "model": device_info.get("device_type", "Helialux"),
            })

    async def _async_update_data(self):
        """Fetch the latest data from the Helialux device."""
        if self._manual_override and self._override_until:
            if asyncio.get_event_loop().time() < self._override_until:
                _LOGGER.debug("Skipping update due to manual override")
                return self.data
            else:
                self._manual_override = False
                self._override_until = None

        try:
            status_data = await self.helialux.get_status()
            profile_data = await self.helialux.get_profiles()

            if not isinstance(status_data, dict):
                _LOGGER.error("Invalid status data format")
                status_data = {}
            if not isinstance(profile_data, dict):
                _LOGGER.error("Invalid profile data format")
                profile_data = {}

            merged_data = {
                "current_profile": status_data.get("currentProfile", "offline"),
                "device_time": status_data.get("deviceTime", "00:00"),
                "white": status_data.get("currentWhite", 0),
                "blue": status_data.get("currentBlue", 0),
                "green": status_data.get("currentGreen", 0),
                "red": status_data.get("currentRed", 0),
                "manualColorSimulationEnabled": status_data.get("manualColorSimulationEnabled", False),
                "manualDaytimeSimulationEnabled": status_data.get("manualDaytimeSimulationEnabled", False),
                "available_profiles": profile_data.get("available_profiles", []),
                "full_profile_names": profile_data.get("full_profile_names", []),
            }

            _LOGGER.debug("Merged data: %s", merged_data)
            return merged_data

        except Exception as e:
            _LOGGER.error("Error fetching data: %s", e)
            return self.data or {}