from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .coordinator import JuwelHelialuxCoordinator 
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL
from homeassistant.util import slugify
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    """Set up the Juwel Helialux integration."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("Juwel Helialux integration initialized")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry for the Juwel Helialux integration."""
    _LOGGER.debug("Setting up config entry: %s", entry.entry_id)

    hass.data.setdefault(DOMAIN, {})

    tank_name = entry.data.get("tank_name", "Default Tank")
    tank_host = entry.data[CONF_TANK_HOST]
    tank_protocol = entry.data.get(CONF_TANK_PROTOCOL, "http")
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, 30)

    _LOGGER.debug(f"Config entry tank_name: {tank_name}")
    _LOGGER.debug(f"Config entry data: {entry.data}")

    # Create the coordinator - pass the actual tank_name
    coordinator = JuwelHelialuxCoordinator(hass, tank_host, tank_protocol, tank_name, update_interval)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    _LOGGER.debug("Forwarding setup for platforms")
    try:
        await hass.config_entries.async_forward_entry_setups(
            entry, ["sensor", "light", "select", "binary_sensor", "number", "switch"]
        )
        _LOGGER.debug("Platform setup forwarded successfully.")
    except Exception as e:
        _LOGGER.error("Error forwarding platform setup: %s", e)

    return True


async def async_unload_entry(hass, entry):
    """Handle removal of a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "light", "select", "binary_sensor", "number", "switch"]
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.debug("Config entry unloaded and coordinator removed")
    else:
        _LOGGER.warning("Failed to unload some platforms for config entry: %s", entry.entry_id)

    return unload_ok