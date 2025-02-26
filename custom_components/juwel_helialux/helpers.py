import logging
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers import entity_registry as er
from homeassistant.components.input_number import InputNumber

_LOGGER = logging.getLogger(__name__)

HELPER_TEMPLATE = {
    "manual_color_simulation_duration": {
        "name": "Manual Color Simulation Duration",
        "min": 0,
        "max": 24,
        "step": 0.5,
        "unit_of_measurement": "hours",
        "icon": "mdi:palette",
    },
    "manual_daylight_simulation_duration": {
        "name": "Manual Daylight Simulation Duration",
        "min": 0,
        "max": 24,
        "step": 0.5,
        "unit_of_measurement": "hours",
        "icon": "mdi:sun-clock",
    },
}

async def async_setup_helpers(hass, tank_name):
    """Ensure input_number helpers exist dynamically."""
    tank_name_clean = tank_name.lower().replace(" ", "_")  # Ensure valid entity ID format

    # Create the EntityComponent for the input_number domain
    component = EntityComponent(_LOGGER, 'input_number', hass)

    # Get the entity registry
    ent_reg = er.async_get(hass)

    for helper_id, config in HELPER_TEMPLATE.items():
        entity_id = f"input_number.{tank_name_clean}_{helper_id}"

        # Check if the helper already exists
        if ent_reg.async_get(entity_id):
            _LOGGER.info(f"✅ Helper {entity_id} already exists.")
            continue

        _LOGGER.info(f"🛠️ Creating helper {entity_id}...")

        # Create the InputNumber entity
        input_number_entity = InputNumber(
            config={
                "name": config["name"],
                "min": config["min"],
                "max": config["max"],
                "step": config["step"],
                "unit_of_measurement": config["unit_of_measurement"],
                "icon": config["icon"],
                "initial": config.get("initial", config["min"]),
            }
        )

        # Set the unique ID for the entity
        input_number_entity._attr_unique_id = entity_id

        # Add the entity to the component
        await component.async_add_entities([input_number_entity])

        # Link the entity to your integration in the entity registry
        ent_reg.async_update_entity(
            entity_id,
            platform="juwel_helialux",  # Set the platform to your integration
            integration="juwel_helialux",  # Set the integration to your integration
        )