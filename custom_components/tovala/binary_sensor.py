"""Binary sensor platform for Tovala Smart Oven."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TovalaCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Tovala binary sensors from a config entry."""
    coordinator: TovalaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    async_add_entities([TovalaTimerRunningBinarySensor(coordinator)])


class TovalaTimerRunningBinarySensor(
    CoordinatorEntity[TovalaCoordinator], BinarySensorEntity
):
    """Binary sensor for timer running status."""

    _attr_name = "Timer Running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: TovalaCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"tovala_{coordinator.oven_id}_timer_running"

    @property
    def is_on(self) -> bool:
        """Return true if the timer is running."""
        if not self.coordinator.data:
            return False
        
        remaining = int(
            self.coordinator.data.get("remaining")
            or self.coordinator.data.get("time_remaining")
            or 0
        )
        return remaining > 0

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
