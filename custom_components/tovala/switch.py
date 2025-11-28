"""Switch platform for Tovala Smart Oven - Custom Recipe Controls."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TovalaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tovala recipe switches from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    coordinator = data["coordinator"]
    recipes = data["recipes"]
    oven_id = data["oven_id"]

    if not recipes:
        _LOGGER.info("No custom recipes found, skipping switch creation")
        return

    entities = [
        TovalaRecipeSwitch(coordinator, client, oven_id, recipe["title"], recipe["barcode"])
        for recipe in recipes
    ]
    
    async_add_entities(entities)
    _LOGGER.info("Added %d recipe switches", len(entities))


class TovalaRecipeSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Tovala recipe switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TovalaCoordinator,
        client,
        oven_id: str,
        recipe_name: str,
        barcode: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._oven_id = oven_id
        self._recipe_name = recipe_name
        self._barcode = barcode
        self._attr_name = recipe_name
        self._attr_unique_id = f"tovala_{oven_id}_{barcode}"
        self._attr_icon = "mdi:food"
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._is_on

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on - start cooking the recipe."""
        try:
            _LOGGER.info("Starting recipe: %s (barcode: %s)", self._recipe_name, self._barcode)
            await self._client.start_cooking(self._oven_id, self._barcode)
            self._is_on = True
            self.async_write_ha_state()
            
            # Auto-reset after 1 second (momentary switch behavior)
            self.hass.loop.call_later(1, self._auto_reset)
            
            # Trigger coordinator refresh to update cooking state
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to start cooking %s: %s", self._recipe_name, e)
            self._is_on = False
            self.async_write_ha_state()
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off (no-op for recipes)."""
        self._is_on = False
        self.async_write_ha_state()

    def _auto_reset(self) -> None:
        """Auto-reset the switch to off state."""
        self._is_on = False
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "recipe_name": self._recipe_name,
            "barcode": self._barcode,
            "oven_id": self._oven_id,
        }
