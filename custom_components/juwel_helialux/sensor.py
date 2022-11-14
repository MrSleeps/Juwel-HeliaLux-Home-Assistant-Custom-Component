"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL, STATE_CLOSED, STATE_CLOSING, STATE_OPEN, STATE_OPENING, STATE_UNKNOWN)
import voluptuous as vol
from datetime import timedelta, date, datetime
from requests import Session
import json
from typing import Pattern, Dict, Union
import logging
import requests
import requests.exceptions
from .const import DOMAIN, ENTITY_ID_FORMAT, DEFAULT_NAME, DEFAULT_DATE_FORMAT, ATTR_MEASUREMENT_DATE, ATTR_UNIT_OF_MEASUREMENT, MIN_TIME_BETWEEN_UPDATES, STATUS_VARS_REGEX

SCAN_INTERVAL = timedelta(minutes=1)
REQUIREMENTS = []
_LOGGER = logging.getLogger(__name__)
DOMAIN = 'sensor'


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_NAME): cv.string
})



def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    host = config.get(CONF_HOST)
    tank_name = config.get(CONF_NAME)
    juwel_data = JuwelApiData(host)
    juwel_data.update()
    if juwel_data is None:
        raise PlatformNotReady
    sensors = []
    sensors.append(JuwelSensor(juwel_data,host, tank_name, "currentProfile"))
    sensors.append(JuwelSensor(juwel_data,host, tank_name, "currentWhite"))
    sensors.append(JuwelSensor(juwel_data,host, tank_name, "currentBlue"))
    sensors.append(JuwelSensor(juwel_data,host, tank_name, "currentRed"))
    sensors.append(JuwelSensor(juwel_data,host, tank_name, "currentGreen"))
    add_entities(sensors, True)

class JuwelSensor(Entity):
    def __init__(self, juwel_data, host, tank_name, measurement):
        self._host = host
        self._name = tank_name
        self._tank_name = tank_name
        self._juwel_data = juwel_data
        self._measurement = measurement
        self._measurement_date = None
        self._unit_of_measurement = None
        self._state = None
        self._icon = None
        _LOGGER.debug("Debug:=%s", tank_name)
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name
    @property
    def tank_name(self):
        """Return the name of the sensor."""
        return self._tank_name        
    @property
    def juwel_data(self):
        return self._juwel_data

    @property
    def host(self):
        return self._host

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._state   

    @property
    def measurement(self):
        return self._measurement

    @property
    def measurement_date(self):
        return self._measurement_date

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement
        
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return{
            ATTR_MEASUREMENT_DATE: self._measurement_date,
            ATTR_UNIT_OF_MEASUREMENT: self._unit_of_measurement
        }
        
    def update(self):
        self._juwel_data.update()

        data = self._juwel_data.result

        if self._host == CONF_HOST or self._host is None:
            _LOGGER.error("Need a host (no http)!")
            
        if self._name == CONF_NAME or self._name is None:
            _LOGGER.error("Need to give your tank a name")

        if data is None or self._measurement not in data:
            self._state = STATE_UNKNOWN
        else:
            self._state = data[self._measurement]
            self._measurement_date = datetime.today().strftime(DEFAULT_DATE_FORMAT)
          
        if self._measurement == "currentProfile":
            self._icon = 'mdi:fishbowl-outline'
            self._name = self._tank_name + ' Current Profile'
            self._unit_of_measurement = ""
        if self._measurement == "currentWhite":
            self._icon = 'mdi:brightness-percent'
            self._name = self._tank_name + ' White'
            self._unit_of_measurement = "%"
        if self._measurement == "currentBlue":
            self._icon = 'mdi:brightness-percent'
            self._name = self._tank_name + ' Blue'
            self._unit_of_measurement = "%"
        if self._measurement == "currentRed":
            self._icon = 'mdi:brightness-percent'
            self._name = self._tank_name + ' Red'
            self._unit_of_measurement = "%"
        if self._measurement == "currentGreen":
            self._icon = 'mdi:brightness-percent'
            self._name = self._tank_name + ' Green'
            self._unit_of_measurement = "%"            

class JuwelApiData:
    def __init__(self, host):
        self._host = host
        self.juwel = Controller(url="http://"+self._host)
        self.result = {}

    @Throttle(SCAN_INTERVAL)
    def update(self):
        result = {}

        try:
            juwelData = self.juwel.get_status()
            self.result["currentProfile"] = juwelData['currentProfile']
            self.result["currentWhite"] = juwelData['currentWhite']
            self.result["currentBlue"] = juwelData['currentBlue']
            self.result["currentRed"] = juwelData['currentRed']
            self.result["currentGreen"] = juwelData['currentGreen']
            _LOGGER.debug("Debug:=%s", juwelData)
        except Exception as Argument:
            _LOGGER.error("Something broke: %s",Argument)
            self.result = "Could not retrieve data."


def parse_status_vars(status_vars):
    """Extract the variables and their values from a minimal javascript file."""
    output = {}
    for match in STATUS_VARS_REGEX.finditer(status_vars):
        if match['number'] is not None:
            value = int(match['number'])
        elif match['string'] is not None:
            value = match['string']
        elif match['digit_list'] is not None:
            value = [int(x) for x in match['digit_list'].split(",")]
        elif match['string_list'] is not None:
            value = [x[1:-1] for x in match['string_list'].split(",")] # strip the quotes
        else:
            assert(False)

        output[match['name']] = value
        _LOGGER.debug("JUWEL OUTPUT: ",value)
    return output

def normalize_brightness(val):
    if val < 0:
        return 0
    elif val > 100:
        return 100
    else:
        return val

def nr_mins_to_formatted(duration):
    """Take a duration in minutes, and return an HH:MM formatted string."""
    hours = int(duration / 60)
    minutes = duration % 60
    return "%02d:%02d" % (hours, minutes)

class Controller:
    """Base Representation of a HeliaLux SmartController"""

    def __init__(self, url):
        self._url = url

    def _statusvars(self):
        offlinevalue = "lang=1;lamp='4Ch';profNum=1;profile='Offline';tsimtime=860;tsimact=0;csimact=0;brightness=[0,0,0,0];times=[0,0,705,720,1200,1230,1260,1350,1439];CH1=[0,0,0,0,0,0,0,0,0];CH2=[5,0,0,0,0,0,0,0,0];CH3=[0,0,0,0,0,0,0,0,0];CH4=[0,0,0,0,0,0,0,0,0];"
        _LOGGER.info("Fetching state from Juwel controller")
        try:
            response = requests.get(self._url + "/statusvars.js", verify=False, timeout=10)
            response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xxx
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _LOGGER.info("Juwel controller appears to be offline")
            return parse_status_vars(offlinevalue)
        except requests.exceptions.HTTPError:
            _LOGGER.info("Juwel controller appears to be offline")
            return parse_status_vars(offlinevalue)
        else:
            _LOGGER.info("Juwel Response: ",response.content.decode("utf-8"))
            return parse_status_vars(response.content.decode("utf-8"))            


    def get_status(self):
        """Fetch the current status from the controller."""
        statusvars = self._statusvars()
        return { 
            "currentProfile": statusvars["profile"], 
            "currentWhite": statusvars["brightness"][0],
            "currentBlue": statusvars["brightness"][1],
            "currentGreen": statusvars["brightness"][2],
            "currentRed": statusvars["brightness"][3],
            "manualColorSimulationEnabled": statusvars["csimact"] == 1,
            "manualDaytimeSimulationEnabled": statusvars["tsimact"] == 1,
            "deviceTime": nr_mins_to_formatted(statusvars["tsimtime"]),
        }

    def start_manual_color_simulation(self, duration=60):
        requests.post(self._url + "/stat",{"action": 14, "cswi": "true", "ctime": nr_mins_to_formatted(duration)})

    def set_manual_color(self, white,blue,green,red):
        params = {"action": 10}
        if white is not None:
            params["ch1"] = normalize_brightness(white)
        if blue is not None:
            params["ch2"] = normalize_brightness(blue)
        if green is not None:
            params["ch3"] = normalize_brightness(green)
        if red is not None:
            params["ch4"] = normalize_brightness(red)
        requests.post(self._url + "/stat", params)

    def stop_manual_color_simulation(self):
        requests.post(self._url + "/stat", {"action": 14, "cswi": "false"})
        requests.post(self._url + "/stat", {"action": 10})
