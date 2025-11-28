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
    
    entities = []
    
    # Add recipe switches
    if recipes:
        entities.extend([
            TovalaRecipeSwitch(coordinator, client, oven_id, recipe["title"], recipe["barcode"])
            for recipe in recipes
        ])
        _LOGGER.info("Added %d recipe switches", len(recipes))
    else:
        _LOGGER.info("No custom recipes found")
    
    # Always add oven power switch
    entities.append(TovalaOvenPowerSwitch(coordinator, client, oven_id))
    _LOGGER.info("Added oven power switch")
    
    async_add_entities(entities)

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


class TovalaOvenPowerSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Tovala oven power switch."""
    _attr_has_entity_name = True
    def __init__(
        self,
        coordinator: TovalaCoordinator,
        client,
        oven_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._oven_id = oven_id
        self._attr_name = "Oven Power"
        self._attr_unique_id = f"tovala_{oven_id}_power"
        self._attr_icon = "mdi:power"
    @property
    def is_on(self) -> bool:
        """Return true if oven is on."""
        if self.coordinator.data:
            state = self.coordinator.data.get("state", "").lower()
            # Consider oven "on" if it's in any active state
            return state in ["cooking", "preheating", "warming", "ready"]
        return False
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the oven on - not supported (use recipe switches instead)."""
        _LOGGER.warning("Oven power on not supported - oven turns on automatically when starting a recipe")
        # Oven turns on automatically when you start cooking a recipe
        # There's no standalone "turn on" or "preheat" command
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the oven off (cancel current cook)."""
        try:
            _LOGGER.info("Turning oven off (canceling cook)")
            await self._client.cancel_cook(self._oven_id)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to turn oven off: %s", e)
            raise
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {"oven_id": self._oven_id}
        if self.coordinator.data:
            attrs.update({
                "current_state": self.coordinator.data.get("state"),
                "temperature": self.coordinator.data.get("temperature"),
                "time_remaining": self.coordinator.data.get("time_remaining"),
            })
        return attrs
