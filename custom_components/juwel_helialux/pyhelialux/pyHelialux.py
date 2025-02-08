import aiohttp
import asyncio
import logging
import re

_LOGGER = logging.getLogger(__name__)

STATUS_VARS_REGEX = re.compile(
    r"(?P<name>[a-zA-Z0-9]+)=((?P<number>\d+)|'(?P<string>[^']+)'|\[(?P<digit_list>(\d+,?)+)\]|\[(?P<string_list>(\"([^\"]+)\",?)+)\]);"
)


def parse_status_vars(status_vars):
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


def normalize_brightness(val):
    """Normalize brightness from HA's 0-255 to Helialux's 0-100 scale."""
    if val < 0:
        return 0
    elif val > 255:
        return 100  # Max brightness in Helialux is 100
    else:
        return (val * 100) // 255  # Normalize to 0-100 range



def nr_mins_to_formatted(duration):
    """Take a duration in minutes, and return an HH:MM formatted string."""
    hours = int(duration / 60)
    minutes = duration % 60
    return "%02d:%02d" % (hours, minutes)


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

    async def get_status(self):
        """Fetch the current status from the controller."""
        statusvars_text = await self._statusvars()
        _LOGGER.debug("Raw statusvars.js text: %s", statusvars_text)

        if statusvars_text:
            statusvars = parse_status_vars(statusvars_text)
            _LOGGER.debug("Parsed statusvars: %s", statusvars)

            return {
                "currentProfile": statusvars.get("profile", "offline"),  # Use .get() to avoid KeyError
                "currentWhite": statusvars["brightness"][0],
                "currentBlue": statusvars["brightness"][1],
                "currentGreen": statusvars["brightness"][2],
                "currentRed": statusvars["brightness"][3],
                "manualColorSimulationEnabled": statusvars["csimact"] == 1,
                "manualDaytimeSimulationEnabled": statusvars["tsimact"] == 1,
                "deviceTime": nr_mins_to_formatted(statusvars["tsimtime"]),
            }
        else:
            return None

    async def get_profiles(self):
        """Fetch the profile information from the controller."""
        wpvars_text = await self._wpvars()
        _LOGGER.debug("Raw wpvars.js text: %s", wpvars_text)

        if wpvars_text:
            wpvars = parse_status_vars(wpvars_text)
            _LOGGER.debug("Parsed wpvars: %s", wpvars)

            return {
                "profile_names": wpvars.get("profnames", []),
                "profile_selection": wpvars.get("profsel", []),
            }
        else:
            return None

    async def set_manual_color(self, white, blue, green, red):
        """Set manual color asynchronously."""
        session = await self._get_session()
        url = f"{self._url}/stat"
        
        # Ensure manual color simulation is enabled first
        await self.start_manual_color_simulation(60)  # Set it for 60 minutes

        params = {
            "action": 10,
            "ch1": normalize_brightness(white),
            "ch2": normalize_brightness(blue),
            "ch3": normalize_brightness(green),
            "ch4": normalize_brightness(red),
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
        stimTime = nr_mins_to_formatted(duration)
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

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()