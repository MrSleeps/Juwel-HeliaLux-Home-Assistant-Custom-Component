import aiohttp
import asyncio
import logging
import re

_LOGGER = logging.getLogger(__name__)

STATUS_VARS_REGEX = re.compile(
    r"(?P<name>[a-zA-Z0-9]+)=((?P<number>\d+)|'(?P<string>[^']+)'|\[(?P<digit_list>(\d+,?)+)\]|\[(?P<string_list>(\"([^\"]+)\",?)+)\]);"
)

class Controller:
    """Base Representation of a HeliaLux SmartController"""

    def __init__(self, url):
        self._url = url
        self._session = None  # Initialize the session as None

    async def _get_session(self):
        """Create or reuse an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def nr_mins_to_formatted(self,duration):
        """Take a duration in minutes, and return an HH:MM formatted string."""
        hours = int(duration / 60)
        minutes = duration % 60
        return "%02d:%02d" % (hours, minutes)

    def normalize_brightness(self,val):
        """Normalize brightness from HA's 0-255 to Helialux's 0-100 scale."""
        if val < 0:
            return 0
        elif val > 255:
            return 100  # Max brightness in Helialux is 100
        else:
            return (val * 100) // 255  # Normalize to 0-100 range

    def parse_devvars(self,string):
        try:
            # Extract the 'info' array using regex
            match = re.search(r"info\s*=\s*\[([^\]]+)\];", string)
            if match:
                # Extract and clean values inside brackets
                info_str = match.group(1)
                info = [item.strip().strip("'") for item in info_str.split(",")]
                return {"info": info}
            else:
                _LOGGER.error("info array not found in devvars.js")
                return {}
        except Exception as e:
            _LOGGER.error(f"Error parsing devvars.js: {e}")
            return {}
        
    def parse_status_vars(self,status_vars):
        """Extract the variables and their values from a minimal javascript file."""
        output = {}
        for match in STATUS_VARS_REGEX.finditer(status_vars):
            if match["number"] is not None:
                value = int(match["number"])
            elif match["string"] is not None:
                value = match["string"]
            elif match["digit_list"] is not None:
                value = [int(x) for x in match["digit_list"].split(",")]
            elif match["string_list"] is not None:
                value = [x[1:-1] for x in match["string_list"].split(",")]  # strip the quotes
            else:
                assert False

            output[match["name"]] = value
        return output    

    async def _statusvars(self):
        """Fetch statusvars.js asynchronously."""
        session = await self._get_session()
        url = f"{self._url}/statusvars.js"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    _LOGGER.error(f"Failed to fetch statusvars.js: {response.status}")
                    return None
        except Exception as e:
            _LOGGER.error(f"Error fetching statusvars.js: {e}")
            return None

    async def _wpvars(self):
        """Fetch wpvars.js asynchronously."""
        session = await self._get_session()
        url = f"{self._url}/wpvars.js"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    _LOGGER.error(f"Failed to fetch wpvars.js: {response.status}")
                    return None
        except Exception as e:
            _LOGGER.error(f"Error fetching wpvars.js: {e}")
            return None

    async def _fetch_vars(self, filename):
        """Generic function to fetch and parse a JavaScript-based variable file."""
        session = await self._get_session()
        url = f"{self._url}/{filename}"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    _LOGGER.debug(f"Raw {filename} content: {content}")  # Log raw file contents
                    return content  # Do not parse, just return raw text
                else:
                    _LOGGER.error(f"Failed to fetch {filename}: {response.status}")
                    return None
        except Exception as e:
            _LOGGER.error(f"Error fetching {filename}: {e}")
            return None

    async def get_status(self):
        """Fetch the current status from the controller."""
        statusvars_text = await self._statusvars()
        _LOGGER.debug("Raw statusvars.js text: %s", statusvars_text)

        if statusvars_text:
            statusvars = self.parse_status_vars(statusvars_text)
            _LOGGER.debug("Parsed statusvars: %s", statusvars)

            return {
                "currentProfile": statusvars.get("profile", "offline"),  # Use .get() to avoid KeyError
                "currentWhite": statusvars["brightness"][0],
                "currentBlue": statusvars["brightness"][1],
                "currentGreen": statusvars["brightness"][2],
                "currentRed": statusvars["brightness"][3],
                "manualColorSimulationEnabled": "On" if statusvars["csimact"] == 1 else "Off",
                "manualDaytimeSimulationEnabled": "On" if statusvars["tsimact"] == 1 else "Off",
                "deviceTime": self.nr_mins_to_formatted(statusvars["tsimtime"]),
            }
        else:
            return None

    async def get_profiles(self):
        """Fetch the profile information from the controller."""
        wpvars_text = await self._wpvars()
        _LOGGER.debug("Raw wpvars.js text: %s", wpvars_text)

        if wpvars_text:
            wpvars = self.parse_status_vars(wpvars_text)
            _LOGGER.debug("Parsed wpvars: %s", wpvars)

            # Clean profile names (without prefixes) for display
            clean_profile_names = wpvars.get("profnames", [])
            # Full profile names (with prefixes) for device communication
            full_profile_names = [f"P{i+1} | {name}" for i, name in enumerate(clean_profile_names)]
            profile_selection = wpvars.get("profsel", [])

            # Debug the profile names
            _LOGGER.debug("Clean profile names: %s", clean_profile_names)
            _LOGGER.debug("Full profile names: %s", full_profile_names)
            _LOGGER.debug("Profile selection: %s", profile_selection)

            # Map clean profile names to their selection status
            profiles = {name: bool(selection) for name, selection in zip(clean_profile_names, profile_selection)}
            _LOGGER.debug(f"Profile names with selection status: {profiles}")

            return {
                "available_profiles": clean_profile_names,  # Clean names for display
                "full_profile_names": full_profile_names,   # Full names for device communication
                "current_profile": next(
                    (name for name, selected in profiles.items() if selected), "offline"
                ),  # Return the current active profile, default to 'offline'
            }
        else:
            return None

    async def device_info(self):
        """Fetch and return device hardware information."""
        devvars_text = await self._fetch_vars("devvars.js")
        _LOGGER.debug(f"Raw devvars.js content: {devvars_text}")  # Debug log
        statusvars_text = await self._statusvars()
        _LOGGER.debug(f"Raw statusvars.js content: {statusvars_text}")  # Debug log

        if not devvars_text:
            _LOGGER.error("Failed to retrieve devvars.js content.")
            return {}

        parsed_devvars = self.parse_devvars(devvars_text)
        parsed_statusvars = self.parse_status_vars(statusvars_text) if statusvars_text else {}
        _LOGGER.debug(f"Parsed devvars.js: {parsed_devvars}")  # Debug log

        if "info" not in parsed_devvars:
            _LOGGER.error("Missing key in parsed data: 'info'")
            return {}

        try:
            return {
                "device_type": parsed_devvars["info"][0] if len(parsed_devvars["info"]) > 0 else "Unknown",
                "hardware_version": parsed_devvars["info"][1] if len(parsed_devvars["info"]) > 1 else "Unknown",
                "firmware_version": parsed_devvars["info"][2] if len(parsed_devvars["info"]) > 2 else "Unknown",
                "ip_address": parsed_devvars["info"][3] if len(parsed_devvars["info"]) > 3 else "Unknown",
                "mac_address": parsed_devvars["info"][4] if len(parsed_devvars["info"]) > 4 else "Unknown",
                "light_channels": parsed_statusvars.get("lamp", "Unknown"),
            }
        except KeyError as e:
            _LOGGER.error(f"Missing key in parsed data: {e}")
            return {}



    async def set_manual_color(self, white, blue, green, red):
        """Set manual color asynchronously."""
        session = await self._get_session()
        url = f"{self._url}/stat"
        
        # Ensure manual color simulation is enabled first
        await self.start_manual_color_simulation(60)  # Set it for 60 minutes

        params = {
            "action": 10,
            "ch1": self.normalize_brightness(white),
            "ch2": self.normalize_brightness(blue),
            "ch3": self.normalize_brightness(green),
            "ch4": self.normalize_brightness(red),
        }

        _LOGGER.debug("Sending color update to Juwel: %s", params)

        try:
            async with session.post(url, data=params) as response:
                response_text = await response.text()
                _LOGGER.debug("Juwel Response: %s", response_text)
                if response.status != 200:
                    _LOGGER.error("Failed to set manual color: %d", response.status)
        except Exception as e:
            _LOGGER.error("Error setting manual color: %s", e)

    async def start_manual_color_simulation(self, duration=60):
        """Start manual color simulation asynchronously."""
        session = await self._get_session()
        url = f"{self._url}/stat"
        stimTime = self.nr_mins_to_formatted(duration)
        data = {"action": 14, "cswi": "true", "ctime": stimTime}
        try:
            _LOGGER.debug(data)
            async with session.post(url, data=data) as response:
                if response.status != 200:
                    _LOGGER.error(f"Failed to start manual color simulation: {response.status}")
        except Exception as e:
            _LOGGER.error(f"Error starting manual color simulation: {e}")

    async def stop_manual_color_simulation(self):
        """Stop manual color simulation asynchronously."""
        session = await self._get_session()
        url = f"{self._url}/stat"
        try:
            async with session.post(url, data={"action": 14, "cswi": "false"}) as response:
                if response.status != 200:
                    _LOGGER.error(f"Failed to stop manual color simulation: {response.status}")
            async with session.post(url, data={"action": 10}) as response:
                if response.status != 200:
                    _LOGGER.error(f"Failed to reset manual color: {response.status}")
        except Exception as e:
            _LOGGER.error(f"Error stopping manual color simulation: {e}")

    async def set_profile(self, profile_name, friendly_profile_name):
        """Set the active profile on the Helialux device."""
        session = await self._get_session()
        url = f"{self._url}/week.html"
        profile_name_two = profile_name
        _LOGGER.debug(f"Posting profile change to: {profile_name}")
        _LOGGER.debug(f"Posting url: {url}")

        # Prepare the data to send to the Helialux device
        data = {
            "key": "BU",
            "s0": profile_name_two,
            "s1": profile_name_two,
            "s2": profile_name_two,
            "s3": profile_name_two,
            "s4": profile_name_two,
            "s5": profile_name_two,
            "s6": profile_name_two,
        }

        try:
            # Set the Content-Type header to application/x-www-form-urlencoded
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            async with session.post(url, data=data, headers=headers) as response:
                response_text = await response.text()
                _LOGGER.debug(f"Response status: {response.status}")
                _LOGGER.debug(f"Response text: {response_text}")
                if response.status == 200:
                    _LOGGER.debug(f"Successfully set profile to: {profile_name}")
                    return True
                else:
                    _LOGGER.error(f"Failed to set profile: {response.status}")
                    return False
        except Exception as e:
            _LOGGER.error(f"Error setting profile: {e}")
            return False