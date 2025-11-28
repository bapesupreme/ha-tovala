"""Data update coordinator for Tovala Smart Oven."""
from __future__ import annotations

from datetime import timedelta, datetime
from typing import Any, Optional
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, EVENT_TIMER_FINISHED
from .api import TovalaClient, TovalaApiError

_LOGGER = logging.getLogger(__name__)


class TovalaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Tovala oven data."""

    def __init__(self, hass: HomeAssistant, client: TovalaClient, oven_id: str) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.oven_id = oven_id
        self._last_reported_remaining = None
        self._last_meal_id = None
        self._cached_meal_details = None

    def _extract_meal_id(self, barcode: str) -> Optional[str]:
        """Extract meal_id from barcode.

        Tovala meal barcodes: "133A254|463|5E34BF80" or "133A254|13251|5E34BF80|A"
        Manual modes: "manual-mini-toast-4", "Bake at 400° for 15:00"
        """
        if not barcode:
            return None

        # Try to extract meal ID from Tovala barcode format
        parts = barcode.split("|")
        if len(parts) >= 2:
            potential_meal_id = parts[1]
            # Check if it's numeric (meal IDs are numeric)
            if potential_meal_id.isdigit():
                return potential_meal_id

        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Tovala API."""
        if not self.oven_id:
            _LOGGER.warning("No oven_id configured yet")
            return {}

        try:
            data = await self.client.oven_status(self.oven_id)
            _LOGGER.debug("Oven status received: %s", data)

            # Status response format:
            # Idle: {"state":"idle", "remote_control_enabled":true}
            # Cooking: {"state":"cooking", "estimated_start_time":"...", "estimated_end_time":"...", ...}
            state = data.get("state", "unknown")

            # Calculate remaining time from estimated_end_time
            remaining = 0
            if state == "cooking" and "estimated_end_time" in data:
                try:
                    end_time_str = data["estimated_end_time"]
                    # Parse ISO format: "2025-11-07T01:43:48.000003163Z"
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                    now = dt_util.utcnow()
                    delta = end_time - now
                    remaining = max(0, int(delta.total_seconds()))
                    _LOGGER.debug(
                        "Calculated remaining time: %d seconds (end_time=%s, now=%s)",
                        remaining, end_time, now
                    )
                except Exception as e:
                    _LOGGER.warning(
                        "Failed to parse estimated_end_time: %s - %s",
                        data.get("estimated_end_time"), e
                    )
                    remaining = 0

            _LOGGER.debug("Parsed state=%s, remaining=%s", state, remaining)

            # Fire event once when remaining crosses to 0
            if (
                self._last_reported_remaining
                and self._last_reported_remaining > 0
                and int(remaining) == 0
            ):
                _LOGGER.info("Timer finished for oven %s", self.oven_id)
                self.hass.bus.async_fire(
                    EVENT_TIMER_FINISHED,
                    {"oven_id": self.oven_id, "data": data}
                )

            self._last_reported_remaining = int(remaining)

            # Add calculated remaining to data for sensors
            data["remaining"] = remaining

            # Fetch meal details if cooking and barcode available
            barcode = data.get("barcode")
            meal_id = self._extract_meal_id(barcode) if barcode else None

            if meal_id:
                # New meal detected - fetch details
                if meal_id != self._last_meal_id:
                    _LOGGER.info(
                        "New meal detected: %s (previous: %s)",
                        meal_id, self._last_meal_id
                    )
                    meal_details = await self.client.meal_details(meal_id)
                    if meal_details:
                        self._cached_meal_details = meal_details
                        self._last_meal_id = meal_id
                        _LOGGER.info("Fetched meal details: %s", meal_details.get("title"))
                    else:
                        _LOGGER.warning(
                            "Failed to fetch meal details for meal_id %s", meal_id
                        )
            elif barcode and not meal_id:
                # Manual cooking mode (no meal_id in barcode)
                if barcode != self._last_meal_id:
                    _LOGGER.debug("Manual cooking mode: %s", barcode)
                    # Clear meal cache for manual modes
                    self._last_meal_id = barcode
                    self._cached_meal_details = None
            # else: No barcode means cooking finished (state=idle), keep cached meal details

            # Always include cached meal details if available (persists after cooking ends)
            if self._cached_meal_details:
                data["meal"] = self._cached_meal_details
                _LOGGER.debug(
                    "Including cached meal in data: %s",
                    self._cached_meal_details.get("title")
                )

            return data

        except TovalaApiError as err:
            raise UpdateFailed(f"Error fetching oven status: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error fetching oven status: %s", err, exc_info=True)
            raise UpdateFailed(f"Unexpected error: {err}") from err
