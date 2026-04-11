"""Lightweight unit tests for Livebox sensor rolling-counter behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from custom_components.livebox.sensor import SENSOR_TYPES, LiveboxSensor


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> None:
    """Avoid pulling the Home Assistant test harness into pure unit tests."""


def _coordinator(rx_bytes: int, uptime: int = 100) -> Any:
    """Build the minimum coordinator shape required by LiveboxSensor."""
    return cast(
        Any,
        SimpleNamespace(
            data={"infos": {"UpTime": uptime}, "wifi_stats": {"RxBytes": rx_bytes}},
            config_entry=SimpleNamespace(data={}),
            unique_id="unit-test-livebox",
        ),
    )


def test_wifi_rx_rolling_counter_state_is_per_entity() -> None:
    """Rolling counters should not leak rollover state across entities."""
    description = next(item for item in SENSOR_TYPES if item.key == "wifi_rx")

    entity_a = LiveboxSensor(_coordinator(4294967290), description)
    assert entity_a.native_value == 4294967290

    entity_a.coordinator = _coordinator(5)
    assert entity_a.native_value == 4294967301

    entity_b = LiveboxSensor(_coordinator(5), description)
    assert entity_b.native_value == 5
