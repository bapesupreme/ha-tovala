"""Tovala Smart Oven Integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_OVEN_ID
from .api import TovalaClient, TovalaAuthError, TovalaApiError
from .coordinator import TovalaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tovala from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    email = entry.data.get(CONF_EMAIL)
    password = entry.data.get(CONF_PASSWORD)
    oven_id = entry.data.get(CONF_OVEN_ID)

    session = async_get_clientsession(hass)
    client = TovalaClient(session, email=email, password=password)

    try:
        # Authenticate and determine which base URL works
        await client.login()
        _LOGGER.info("Successfully authenticated to Tovala API")
    except TovalaAuthError as err:
        raise ConfigEntryNotReady(f"Authentication failed: {err}") from err
    except TovalaApiError as err:
        raise ConfigEntryNotReady(f"Connection error: {err}") from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Unexpected error: {err}") from err

    # Try to get ovens and discover oven_id if not set
    if not oven_id:
        try:
            ovens = await client.list_ovens()
            _LOGGER.debug("list_ovens returned: %s", ovens)
            if ovens:
                # Try both possible locations for oven ID
                oven_id = ovens[0].get("id") or ovens[0].get("tovala", {}).get("id")
                _LOGGER.info("Discovered oven_id: %s", oven_id)
                if oven_id:
                    # Update config entry with discovered oven_id
                    hass.config_entries.async_update_entry(
                        entry, data={**entry.data, CONF_OVEN_ID: oven_id}
                    )
        except Exception as e:
            _LOGGER.error("Failed to discover ovens during setup: %s", e, exc_info=True)
            oven_id = None

    # Fetch custom recipes
    recipes = []
    try:
        recipes = await client.get_custom_recipes()
        _LOGGER.info("Fetched %d custom recipes", len(recipes))
    except Exception as e:
        _LOGGER.warning("Failed to fetch custom recipes: %s", e)

    # Create coordinator
    coordinator = TovalaCoordinator(hass, client, oven_id)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "recipes": recipes,
        "oven_id": oven_id,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Tovala config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
