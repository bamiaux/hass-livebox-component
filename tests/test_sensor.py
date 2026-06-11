"""Tests for the Bbox sensor platform."""

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import homeassistant.helpers.entity_registry as er
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pytest_homeassistant_custom_component.common import load_json_object_fixture

from custom_components.livebox.coordinator import LiveboxDataUpdateCoordinator
from custom_components.livebox.sensor import LiveboxSensor, async_setup_entry


def _load_fixture(name: str) -> dict[str, Any]:
    """Load a typed test fixture."""
    return cast(dict[str, Any], load_json_object_fixture(name))


@pytest.mark.parametrize("AIOSysbus", ["3", "5", "7", "7.1", "7.2"], indirect=True)
async def test_sensors_state(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
):
    """Test the state of various sensors."""
    # Setup the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_tx")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_power_rx")
    assert state is not None

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_tx")
    assert state is not None
    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_fiber_rx")
    assert state is not None

    state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_callers")
    assert state is not None

    if AIOSysbus.__model in ["7"]:
        state = er.async_get(hass).async_get("sensor.pc_408_downlink_rate")
        assert state is not None
        state = er.async_get(hass).async_get("sensor.pc_408_uplink_rate")
        assert state is not None

    if AIOSysbus.__model in ["7.1"]:
        state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_rx")
        assert state is not None
        assert float(state.state) >= 0
        state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_tx")
        assert state is not None
        assert float(state.state) >= 0

    # entity_registry_enabled_default=False
    state = er.async_get(hass).async_get(f"sensor.{AIOSysbus.__unique_name}_wifi_tx")
    assert state is not None
    state = er.async_get(hass).async_get(f"sensor.{AIOSysbus.__unique_name}_wifi_rx")
    assert state is not None
    state = er.async_get(hass).async_get(
        f"sensor.{AIOSysbus.__unique_name}_ports_forwarding"
    )
    assert state is not None
    state = er.async_get(hass).async_get(
        f"sensor.{AIOSysbus.__unique_name}_dhcp_leases"
    )
    assert state is not None
    state = er.async_get(hass).async_get(
        f"sensor.{AIOSysbus.__unique_name}_guest_dhcp_leases"
    )
    assert state is not None


async def test_rate_sensors_match_issue_258_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test dynamic rate sensors keep distinct values from issue #258."""
    fixture = _load_fixture("issue_258_livebox_nautilus_diagnostics_sanitized.json")

    coordinator = LiveboxDataUpdateCoordinator(hass, config_entry)
    coordinator.unique_id = "issue258"
    coordinator.data = fixture["data"]["data"]
    config_entry.runtime_data = coordinator

    entities: list[LiveboxSensor] = []

    def _add_entities(
        new_entities: list[LiveboxSensor], update_before_add: bool = False
    ) -> None:
        del update_before_add
        entities.extend(new_entities)

    await async_setup_entry(
        hass, config_entry, cast(AddEntitiesCallback, _add_entities)
    )

    sensors = {entity.entity_description.key: entity for entity in entities}

    assert sensors["vap5g0priv_rate_rx"].native_value == 0.01
    assert sensors["vap5g0priv_rate_tx"].native_value == 0.06
    assert sensors["ETH0_rate_rx"].native_value == 0.01
    assert sensors["ETH0_rate_tx"].native_value == 0.0


@pytest.mark.parametrize("AIOSysbus", ["7.1"], indirect=True)
async def test_rate_sensors_use_megabits_per_second_math(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    AIOSysbus: AsyncMock,
) -> None:
    """Test rate sensors use Mbit/s math to match their declared unit."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    rx_state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_rx")
    assert rx_state is not None
    assert float(rx_state.state) == 0.01

    tx_state = hass.states.get(f"sensor.{AIOSysbus.__unique_name}_eth2_rate_tx")
    assert tx_state is not None
    assert float(tx_state.state) == 5.69


async def test_device_metric_sensors_are_created_for_wifi_clients(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test per-device Wi-Fi sensors expose the expected metrics."""
    coordinator = cast(
        LiveboxDataUpdateCoordinator,
        SimpleNamespace(
            unique_id="LIVEBOX",
            config_entry=SimpleNamespace(
                data={"host": "192.168.1.1", "port": 80},
                options={},
            ),
            signal_device_new="livebox-LIVEBOX-device-new",
            get_parent_device_identifier=lambda _device_key: ("livebox", "LIVEBOX"),
            data={
                "devices": {
                    "AA:BB:CC:DD:EE:FF": {
                        "Key": "AA:BB:CC:DD:EE:FF",
                        "Name": "Test device",
                        "InterfaceName": "vap5g0priv",
                        "SignalStrength": -41,
                        "SignalNoiseRatio": 32,
                        "LastDataDownlinkRate": 7777,
                        "LastDataUplinkRate": 8888,
                    }
                },
                "lan": [
                    {
                        "type": "Wireless",
                        "name": "5GHz (home)",
                        "extra_attributes": {
                            "associated_devices": {
                                "1": {
                                    "MACAddress": "AA:BB:CC:DD:EE:FF",
                                    "TxBytes": 321,
                                    "RxBytes": 654,
                                }
                            }
                        },
                    }
                ],
            },
        ),
    )
    config_entry.runtime_data = coordinator

    entities: list[LiveboxSensor] = []

    def _add_entities(
        new_entities: list[LiveboxSensor], update_before_add: bool = False
    ) -> None:
        del update_before_add
        entities.extend(new_entities)

    await async_setup_entry(
        hass, config_entry, cast(AddEntitiesCallback, _add_entities)
    )

    sensors = {entity.entity_description.key: entity for entity in entities}

    assert sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].native_value == 7777
    assert sensors["aa_bb_cc_dd_ee_ff_uplink_rate"].native_value == 8888
    assert sensors["aa_bb_cc_dd_ee_ff_tx_bytes"].native_value == 321
    assert sensors["aa_bb_cc_dd_ee_ff_rx_bytes"].native_value == 654
    assert sensors["aa_bb_cc_dd_ee_ff_signal_strength"].native_value == -41
    assert sensors["aa_bb_cc_dd_ee_ff_signal_noise_ratio"].native_value == 32
    assert sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].name == "Downlink Rate"
    assert sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].device_info is not None
    assert sensors["aa_bb_cc_dd_ee_ff_downlink_rate"].device_info["identifiers"] == {
        ("livebox", "AA:BB:CC:DD:EE:FF")
    }


async def test_lan_diagnostic_sensors_are_created(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Test LAN diagnostics expose Wi-Fi radios and Ethernet ports."""
    coordinator = cast(
        LiveboxDataUpdateCoordinator,
        SimpleNamespace(
            unique_id="LIVEBOX",
            config_entry=SimpleNamespace(
                data={"host": "192.168.1.1", "port": 80},
                options={},
            ),
            signal_device_new="livebox-LIVEBOX-device-new",
            get_parent_device_identifier=lambda _device_key: ("livebox", "LIVEBOX"),
            data={
                "devices": {},
                "lan": [
                    {
                        "name": "2.4GHz (primary)",
                        "status": True,
                        "type": "Wireless",
                        "extra_attributes": {
                            "channel": 6,
                            "ssid": "Livebox",
                            "last_change": "2026-06-11T18:40:13Z",
                            "associated_devices": {
                                "1": {"MACAddress": "AA:BB:CC:DD:EE:FF"},
                                "2": {"MACAddress": "11:22:33:44:55:66"},
                            },
                        },
                    },
                    {
                        "name": "2.4GHz (primary)",
                        "status": False,
                        "type": "Wireless",
                        "extra_attributes": {
                            "channel": 11,
                            "ssid": "Livebox Guest",
                            "last_change": "2026-06-11T18:41:13Z",
                            "associated_devices": None,
                        },
                    },
                    {
                        "name": "ETH0",
                        "status": True,
                        "type": "Ethernet",
                        "extra_attributes": {
                            "current_bitrate": 2500,
                            "last_change": "2026-06-11T19:38:36Z",
                            "port_state": "forwarding",
                        },
                    },
                    {
                        "name": "ETH3",
                        "status": False,
                        "type": "Ethernet",
                        "extra_attributes": {
                            "current_bitrate": 0,
                            "last_change": "2026-04-14T22:27:52Z",
                            "port_state": "disabled",
                        },
                    },
                    {
                        "name": "Living-Room-1",
                        "status": True,
                        "type": "Ethernet",
                        "extra_attributes": {
                            "current_bitrate": None,
                            "last_change": "2026-04-14T22:28:07Z",
                            "port_state": None,
                        },
                    },
                ],
            },
        ),
    )
    config_entry.runtime_data = coordinator

    entities: list[LiveboxSensor] = []

    def _add_entities(
        new_entities: list[LiveboxSensor], update_before_add: bool = False
    ) -> None:
        del update_before_add
        entities.extend(new_entities)

    await async_setup_entry(
        hass, config_entry, cast(AddEntitiesCallback, _add_entities)
    )

    sensors = {entity.entity_description.key: entity for entity in entities}

    primary = sensors["wifi_2_4ghz_primary_0_channel"]
    secondary = sensors["wifi_2_4ghz_primary_1_channel"]
    eth0 = sensors["ethernet_eth0_2_current_bitrate"]
    eth3 = sensors["ethernet_eth3_3_current_bitrate"]

    assert primary.native_value == 6
    assert primary.extra_state_attributes == {
        "status": True,
        "ssid": "Livebox",
        "last_change": "2026-06-11T18:40:13Z",
        "associated_devices_count": 2,
    }
    assert primary.entity_category is EntityCategory.DIAGNOSTIC
    assert secondary.native_value == 11
    secondary_attrs = secondary.extra_state_attributes
    assert secondary_attrs is not None
    assert secondary_attrs["associated_devices_count"] is None
    assert eth0.native_value == 2500
    assert eth0.extra_state_attributes == {
        "status": True,
        "port_state": "forwarding",
        "last_change": "2026-06-11T19:38:36Z",
    }
    assert eth3.native_value == 0
    eth3_attrs = eth3.extra_state_attributes
    assert eth3_attrs is not None
    assert eth3_attrs["port_state"] == "disabled"
    assert "ethernet_living_room_1_4_current_bitrate" not in sensors
