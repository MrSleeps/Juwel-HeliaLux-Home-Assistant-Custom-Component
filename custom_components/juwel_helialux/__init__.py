from homeassistant.core import HomeAssistant  # Add this line
from homeassistant.config_entries import ConfigEntry  # Add this line
from .sensor import JuwelHelialuxCoordinator 
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    hass.data.setdefault(DOMAIN, {})  # Ensure DOMAIN is always in hass.data
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry for the Juwel Helialux integration."""
    _LOGGER.debug("Setting up config entry: %s", entry.entry_id)  # Log entry setup

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    tank_name = entry.data.get("tank_name", "Default Tank")  # Add this line
    tank_host = entry.data["tank_host"]
    tank_protocol = entry.data.get("tank_protocol", "http")
    update_interval = entry.options.get("update_interval", 1)

    # Create and store the coordinator
    coordinator = JuwelHelialuxCoordinator(hass, tank_host, tank_protocol, tank_name, update_interval)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator  # Store it

    _LOGGER.debug("Forwarding setup for binary_sensor platform")
    # Add logging to confirm forwarding
    try:
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "light", "select", "binary_sensor"])
        _LOGGER.debug("Binary sensor setup forwarded successfully.")
    except Exception as e:
        _LOGGER.error("Error forwarding setup for binary sensors: %s", e)

    return True

async def async_unload_entry(hass, entry):
    """Handle removal of an entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor","light", "binary_sensor"])
    return unload_ok