from .sensor import JuwelHelialuxCoordinator 
from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL

async def async_setup(hass, config):
    hass.data.setdefault(DOMAIN, {})  # Ensure DOMAIN is always in hass.data
    return True

async def async_setup_entry(hass, entry):
    """Set up a config entry for the Juwel Helialux integration."""
    
    # Ensure the integration's data storage exists
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Get device configuration from the entry
    tank_host = entry.data[CONF_TANK_HOST]
    tank_protocol = entry.data[CONF_TANK_PROTOCOL]
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, 1)  # Default: 5 minutes

    # Create and store the coordinator
    coordinator = JuwelHelialuxCoordinator(hass, tank_host, tank_protocol, update_interval)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator  # Store it

    # Forward setup to platforms (sensor, light)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "light"])
    
    return True



async def async_unload_entry(hass, entry):
    """Unload a config entry for the Juwel Helialux integration."""
    #unload_successful = await hass.config_entries.async_unload_platforms(entry, ["sensor", "light"])
    unload_successful = await hass.config_entries.async_unload_platforms(entry, ["sensor","light"])
    return unload_successful
