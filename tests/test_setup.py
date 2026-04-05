"""Tests pour l'intégration Bbox2 utilisant config_entries."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.livebox.const import (
    CALLID,
    CONF_DISPLAY_DEVICES,
    CONF_LAN_TRACKING,
    CONF_TRACKING_TIMEOUT,
    CONF_WIFI_TRACKING,
    DEFAULT_DISPLAY_DEVICES,
    DEFAULT_LAN_TRACKING,
    DEFAULT_TRACKING_TIMEOUT,
    DEFAULT_WIFI_TRACKING,
    DOMAIN,
)

from .const import MOCK_USER_INPUT


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Test du setup via une config entry."""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_coordinator_refresh(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Test du setup via une config entry."""

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED

    coordinator = config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_remove_call_missed_service_lifecycle(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Test the missed-call service is registered once and removed on unload."""

    assert not hass.services.has_service(DOMAIN, "remove_call_missed")

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, "remove_call_missed")

    await hass.services.async_call(
        DOMAIN,
        "remove_call_missed",
        {CALLID: "123"},
        blocking=True,
    )

    AIOSysbus.voiceservice.async_clear_calllist.assert_awaited_once_with(
        {CALLID: "123"}
    )

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, "remove_call_missed")


@pytest.mark.parametrize("AIOSysbus", ["7"], indirect=True)
async def test_remove_call_missed_service_rejects_multiple_entries(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock | MagicMock,
) -> None:
    """Test the missed-call service refuses ambiguous multi-entry calls."""

    second_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=MOCK_USER_INPUT,
        unique_id="987654321098765",
        options={
            CONF_WIFI_TRACKING: DEFAULT_WIFI_TRACKING,
            CONF_LAN_TRACKING: DEFAULT_LAN_TRACKING,
            CONF_TRACKING_TIMEOUT: DEFAULT_TRACKING_TIMEOUT,
            CONF_DISPLAY_DEVICES: DEFAULT_DISPLAY_DEVICES,
        },
        title="Livebox Y (987654321098765)",
    )
    second_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.config_entries.async_setup(second_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "remove_call_missed",
            {CALLID: "123"},
            blocking=True,
        )
