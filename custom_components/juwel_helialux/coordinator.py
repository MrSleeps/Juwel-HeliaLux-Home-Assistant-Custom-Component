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
        await self.async_refresh()  # Fetch initial data

        # Fetch device info from the Helialux controller
        _LOGGER.debug("Fetching device info from Helialux controller...")
        device_info = await self.helialux.device_info()
        _LOGGER.debug("Fetched device info: %s", device_info)  # Log fetched info

        if device_info:
            self.device_info["sw_version"] = device_info.get("firmware_version", "Unknown")
            self.device_info["hw_version"] = device_info.get("hardware_version", "Unknown")
            self.device_info["model"] = f"{device_info.get('device_type', 'Unknown')}"
            _LOGGER.debug("Updated Device Info: %s", self.device_info)
        else:
            _LOGGER.error("Failed to fetch device info from Helialux controller.")


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

            # Fetch device info and update the device_info dictionary
            device_info = await self.helialux.device_info()
            if device_info:
                self.device_info["sw_version"] = device_info.get("firmware_version", "0.0.0.0")
                self.device_info["hw_version"] = device_info.get("hardware_version", "0.0.0.0")
                self.device_info["model"] = f"{device_info.get('device_type', 'Unknown')}"
                _LOGGER.debug("Updated Device Info: %s", self.device_info)

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
            return merged_data  # ✅ Always return a dictionary

        except Exception as e:
            _LOGGER.error("Error fetching data from Helialux device: %s", e)
            return {}  # ✅ Always return an empty dictionary
        
    async def async_update(self):
        """Update the entity's state."""
        await self._async_update_data()  # Call the data update method
        self.async_write_ha_state()  # Notify Home Assistant to refresh the entity state        