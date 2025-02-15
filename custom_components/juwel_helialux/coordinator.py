import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_NAME, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL
from .pyhelialux.pyHelialux import Controller as Helialux

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
        _LOGGER.debug("Initializing Coordinator")

        url = f"{self.tank_protocol}://{self.tank_host}"
        self.helialux = Helialux(url)
        self.data = {}  
        # Set default device info (to be updated after first fetch)
        self.device_info = {
            "identifiers": {(DOMAIN, tank_name)},
            "name": tank_name,
            "manufacturer": "Juwel",
            "model": "Helialux",
            "sw_version": "Unknown",
            "hw_version": "Unknown",
            "configuration_url": url,
            "connections": set(),
        }

    async def async_config_entry_first_refresh(self):
        """Fetch initial data and store device info."""
        await self.async_refresh()  # ✅ Use async_refresh() instead of directly calling `_async_update_data`
        _LOGGER.debug("Device Info Initialized: %s", self.device_info)

    async def _async_update_data(self):
        """Fetch the latest data from the Helialux device."""
        try:
            # Fetch status data
            status_data = await self.helialux.get_status()
            _LOGGER.debug("Raw status data received from Helialux: %s", status_data)

            if not isinstance(status_data, dict):
                _LOGGER.error("Invalid status data format from Helialux, received: %s", type(status_data))
                status_data = {}

            # Fetch profile data
            profile_data = await self.helialux.get_profiles()
            _LOGGER.debug("Raw profile data received from Helialux: %s", profile_data)

            if not isinstance(profile_data, dict):
                _LOGGER.error("Invalid profile data format from Helialux, received: %s", type(profile_data))
                profile_data = {}

            _LOGGER.debug(f"Before updating HA: current_profile={self.data.get('current_profile', 'offline')}")

            # Merge status and profile data
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
            _LOGGER.debug(f"After updating HA: current_profile={merged_data.get('current_profile', 'offline')}")
            _LOGGER.debug(f"Raw statusvars.js profile: {status_data.get('currentProfile', 'offline')}")

            return merged_data  # ✅ Always return a dictionary

        except Exception as e:
            _LOGGER.error("Error fetching data from Helialux device: %s", e)
            return {}  # ✅ Always return an empty dictionary