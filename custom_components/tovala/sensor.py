"""Sensor platform for Tovala Smart Oven."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TovalaCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tovala sensors from a config entry."""
    coordinator: TovalaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    async_add_entities([
        TovalaRemainingTimeSensor(coordinator),
        TovalaLastCookSensor(coordinator),
    ])


class TovalaRemainingTimeSensor(CoordinatorEntity[TovalaCoordinator], SensorEntity):
    """Sensor for remaining cooking time."""

    _attr_name = "Time Remaining"
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_device_class = SensorDeviceClass.DURATION

    def __init__(self, coordinator: TovalaCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"tovala_{coordinator.oven_id}_remaining"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return 0
        return int(
            self.coordinator.data.get("remaining")
            or self.coordinator.data.get("time_remaining")
            or 0
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        attrs = {}

        # Cooking state
        state = self.coordinator.data.get("state")
        if state:
            attrs["cooking_state"] = state

        # Barcode
        barcode = self.coordinator.data.get("barcode")
        if barcode:
            attrs["barcode"] = barcode

        # Meal details (if available)
        meal = self.coordinator.data.get("meal")
        if meal:
            attrs["meal_id"] = meal.get("id")
            attrs["meal_title"] = meal.get("title")
            attrs["meal_subtitle"] = meal.get("subtitle", "")

            # Get first image URL if available
            images = meal.get("images", [])
            if images and len(images) > 0:
                # Construct full URL from CDN path
                image_url = images[0].get("url", "")
                if image_url.startswith("//"):
                    image_url = f"https:{image_url}"
                attrs["meal_image"] = image_url

            # Ingredients
            ingredients = meal.get("ingredients")
            if ingredients:
                attrs["meal_ingredients"] = ingredients

        # End time (if cooking)
        estimated_end_time = self.coordinator.data.get("estimated_end_time")
        if estimated_end_time:
            attrs["estimated_end_time"] = estimated_end_time

        return attrs


class TovalaLastCookSensor(CoordinatorEntity[TovalaCoordinator], SensorEntity):
    """Sensor for last cooking session."""

    _attr_name = "Last Cook"
    _attr_icon = "mdi:history"

    def __init__(self, coordinator: TovalaCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"tovala_{coordinator.oven_id}_last_cook"
        self._history = []

    async def async_update(self) -> None:
        """Fetch cooking history."""
        await super().async_update()
        # Fetch history less frequently (only when coordinator updates)
        if self.coordinator.last_update_success:
            try:
                history = await self.coordinator.client.cooking_history(
                    self.coordinator.oven_id, limit=10
                )
                self._history = history
            except Exception:
                pass  # History is optional, don't fail

    @property
    def native_value(self) -> str:
        """Return the last cook barcode or meal name."""
        if not self._history:
            return "No history"

        last = self._history[0]
        barcode = last.get("barcode", "Unknown")

        # If there's a meal_id, try to show something more meaningful
        meal_id = last.get("meal_id")
        if meal_id:
            return f"Meal #{meal_id}"

        return barcode

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return cooking history as attributes."""
        if not self._history:
            return {}

        attrs = {}

        # Last cook details
        if self._history:
            last = self._history[0]
            attrs["last_cook_barcode"] = last.get("barcode", "")
            attrs["last_cook_meal_id"] = last.get("meal_id")
            attrs["last_cook_start_time"] = last.get("start_time", "")
            attrs["last_cook_end_time"] = last.get("end_time", "")
            attrs["last_cook_status"] = last.get("status", "")

        # Recent history (up to 10 most recent)
        attrs["recent_history"] = [
            {
                "barcode": cook.get("barcode", ""),
                "meal_id": cook.get("meal_id"),
                "start_time": cook.get("start_time", ""),
                "end_time": cook.get("end_time", ""),
                "status": cook.get("status", ""),
            }
            for cook in self._history[:10]
        ]

        return attrs
