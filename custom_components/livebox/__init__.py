"""Orange Livebox."""

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import CALLID, DOMAIN, PLATFORMS
from .coordinator import LiveboxDataUpdateCoordinator

type LiveboxConfigEntry = ConfigEntry[LiveboxDataUpdateCoordinator]

CALLMISSED_SCHEMA = vol.Schema({vol.Optional(CALLID): str})
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Livebox integration."""
    if not hass.services.has_service(DOMAIN, "remove_call_missed"):
        hass.services.async_register(
            DOMAIN,
            "remove_call_missed",
            _async_remove_cmissed,
            schema=CALLMISSED_SCHEMA,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LiveboxConfigEntry) -> bool:
    """Set up Livebox as config entry."""
    coordinator = LiveboxDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LiveboxConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and not _async_loaded_coordinators(hass):
        hass.services.async_remove(DOMAIN, "remove_call_missed")

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: LiveboxConfigEntry):
    """Reload device tracker if change option."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove config entry from a device."""
    return True


def _async_loaded_coordinators(
    hass: HomeAssistant,
) -> list[LiveboxDataUpdateCoordinator]:
    """Return loaded Livebox coordinators."""
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED and entry.runtime_data is not None
    ]


async def _async_remove_cmissed(call: ServiceCall) -> None:
    """Remove a missed call using the active Livebox coordinator."""
    coordinators = _async_loaded_coordinators(call.hass)

    if not coordinators:
        raise HomeAssistantError("No loaded Livebox config entry available")

    if len(coordinators) > 1:
        raise HomeAssistantError(
            "remove_call_missed is ambiguous with multiple "
            "Livebox config entries loaded"
        )

    coordinator = coordinators[0]
    await coordinator.api.voiceservice.async_clear_calllist(
        {CALLID: call.data.get(CALLID)}
    )
    await coordinator.async_refresh()
