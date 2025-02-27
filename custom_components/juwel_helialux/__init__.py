from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .sensor import JuwelHelialuxCoordinator 
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry for the Juwel Helialux integration."""
    _LOGGER.debug("Setting up config entry: %s", entry.entry_id)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    tank_name = entry.data.get("tank_name", "Default Tank")
    tank_host = entry.data["tank_host"]
    tank_protocol = entry.data.get("tank_protocol", "http")
    update_interval = entry.options.get("update_interval", 30)
    coordinator = JuwelHelialuxCoordinator(hass, tank_host, tank_protocol, tank_name, update_interval)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    _LOGGER.debug("Forwarding setup for binary_sensor platform")
    try:
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "light", "select", "binary_sensor","number","switch"])
        _LOGGER.debug("Binary sensor setup forwarded successfully.")
    except Exception as e:
        _LOGGER.error("Error forwarding setup for binary sensors: %s", e)

    return True

async def async_unload_entry(hass, entry):
    """Handle removal of an entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "light", "select", "binary_sensor","number","switch"])
    return unload_ok