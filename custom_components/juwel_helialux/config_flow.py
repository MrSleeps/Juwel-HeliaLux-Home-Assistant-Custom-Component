import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import logging

from .const import DOMAIN, CONF_TANK_HOST, CONF_TANK_NAME, CONF_TANK_PROTOCOL, CONF_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class JuwelHelialuxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            if not user_input[CONF_TANK_HOST]:
                errors["base"] = "invalid_host"
            elif not user_input[CONF_TANK_NAME]:
                errors["base"] = "invalid_name"
            else:
                unique_id = f"{user_input[CONF_TANK_PROTOCOL]}://{user_input[CONF_TANK_HOST]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                if CONF_UPDATE_INTERVAL not in user_input:
                    user_input[CONF_UPDATE_INTERVAL] = 1

                return self.async_create_entry(
                    title=user_input[CONF_TANK_NAME],
                    data=user_input,
                )

        data_schema = vol.Schema({
            vol.Required(CONF_TANK_PROTOCOL, default="http"): vol.In(["http", "https"]),
            vol.Required(CONF_TANK_HOST): str,
            vol.Required(CONF_TANK_NAME): str,
            vol.Required(CONF_UPDATE_INTERVAL, default=1): vol.All(vol.Coerce(int), vol.Range(min=1)),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "tank_protocol": "Tank Protocol",
                "tank_host": "Tank Host",
                "tank_name": "Tank Name",
                "update_interval": "Update Interval (minutes)",
            },
        )

    @classmethod
    async def async_migrate_entry(cls, hass, config_entry: config_entries.ConfigEntry):
        """Migrate old config entry to the new version."""
        version = config_entry.version
        _LOGGER.debug(f"Migration process started for entry {config_entry.title}, current version: {version}")

        if version is None:
            version = 1
            _LOGGER.debug(f"No version found, assuming version 1 for migration.")

        if version == 1:
            _LOGGER.debug(f"Starting migration from version 1 to version 2 for {config_entry.title}")

            old_data = config_entry.data
            tank_name = old_data.get("name")

            if tank_name:
                _LOGGER.debug(f"Migrating sensor names for {tank_name}")

                old_data[f"{tank_name}_blue"] = old_data.pop(f"{tank_name}_blue", 0)
                old_data[f"{tank_name}_green"] = old_data.pop(f"{tank_name}_green", 0)
                old_data[f"{tank_name}_red"] = old_data.pop(f"{tank_name}_red", 0)
                old_data[f"{tank_name}_white"] = old_data.pop(f"{tank_name}_white", 0)
                old_data[f"{tank_name}_profile"] = old_data.pop(f"{tank_name}_current_profile", "None")
                old_data[f"{tank_name}_current_profile"] = old_data.pop(f"{tank_name}_current_profile", "None")

                for color in ["blue", "green", "red", "white"]:
                    old_data.pop(f"{tank_name}_{color}", None)

                _LOGGER.debug(f"Old sensor names for {tank_name} migrated and removed.")

                for color in ["blue", "green", "red", "white", "profile"]:
                    old_entity_id = f"sensor.{tank_name}_{color}"
                    _LOGGER.debug(f"Checking if old entity {old_entity_id} exists and needs removal.")
                    if hass.helpers.entity_registry.async_is_registered(old_entity_id):
                        _LOGGER.debug(f"Removing old entity: {old_entity_id}")
                        hass.helpers.entity_registry.async_remove(old_entity_id)
                    else:
                        _LOGGER.debug(f"Entity {old_entity_id} not found in registry.")

            _LOGGER.debug("Cleaning up old entities (if any).")
            for sensor in ['blue', 'green', 'red', 'white', 'profile']:
                entity_id = f"sensor.{tank_name}_{sensor}"
                if hass.helpers.entity_registry.async_is_registered(entity_id):
                    _LOGGER.debug(f"Removing old entity: {entity_id}")
                    hass.helpers.entity_registry.async_remove(entity_id)

            if "manualColorSimulationEnabled" not in old_data:
                old_data["manualColorSimulationEnabled"] = False
            if "manualDaytimeSimulationEnabled" not in old_data:
                old_data["manualDaytimeSimulationEnabled"] = False
            if "deviceTime" not in old_data:
                old_data["deviceTime"] = "00:00:00"
            if "profile" not in old_data:
                old_data["profile"] = "None"
            if "current_profile" not in old_data:
                old_data["current_profile"] = "None"

            if CONF_UPDATE_INTERVAL not in old_data:
                _LOGGER.debug(f"Update interval not found, setting to default 1 minute for {config_entry.title}")
                old_data[CONF_UPDATE_INTERVAL] = 1

            config_entry.version = 2

            hass.config_entries.async_update_entry(config_entry, data=old_data)

            _LOGGER.debug(f"Config entry {config_entry.title} migration to version 2 completed.")

        return True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return JuwelHelialuxOptionsFlow(config_entry)


class JuwelHelialuxOptionsFlow(config_entries.OptionsFlow):
    """Handle the options for the Juwel Helialux integration."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            new_data = {**self._config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)

            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_TANK_PROTOCOL, default=self._config_entry.data.get(CONF_TANK_PROTOCOL)): vol.In(["http", "https"]),
            vol.Required(CONF_TANK_HOST, default=self._config_entry.data.get(CONF_TANK_HOST)): str,
            vol.Required(CONF_TANK_NAME, default=self._config_entry.data.get(CONF_TANK_NAME)): str,
            vol.Optional(CONF_UPDATE_INTERVAL, default=self._config_entry.data.get(CONF_UPDATE_INTERVAL, 1)): vol.All(vol.Coerce(int), vol.Range(min=1)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )