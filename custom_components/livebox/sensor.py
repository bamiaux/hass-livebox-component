"""Sensor for Livebox router."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LiveboxConfigEntry
from .const import DOWNLOAD_ICON, PHONE_ICON, UPLOAD_ICON
from .coordinator import LiveboxDataUpdateCoordinator
from .entity import LiveboxEntity
from .helpers import find_item

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class LiveboxSensorEntityDescription(SensorEntityDescription):
    """Represents an Flow Sensor."""

    value_fn: Callable[..., Any]
    attrs: dict[str, Callable[..., Any]] | None = None
    rolling_value_path: str | None = None


def get_closure_value_fn(path: str) -> Callable[..., Any]:
    """Returns a closure function for value_fn of entities with variable name"""
    return lambda x: find_item(x, path)


SENSOR_TYPES: Final[list[LiveboxSensorEntityDescription]] = [
    LiveboxSensorEntityDescription(
        key="down",
        name="xDSL Download",
        icon=DOWNLOAD_ICON,
        translation_key="down_rate",
        value_fn=lambda x: find_item(x, "dsl_status.DownstreamCurrRate", 0),
        native_unit_of_measurement=UnitOfDataRate.KILOBITS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_RATE,
        attrs={
            "downstream_maxrate": lambda x: find_item(
                x, "dsl_status.DownstreamMaxRate"
            ),
            "downstream_lineattenuation": lambda x: find_item(
                x, "dsl_status.DownstreamLineAttenuation"
            ),
            "downstream_noisemargin": lambda x: find_item(
                x, "dsl_status.DownstreamNoiseMargin"
            ),
            "downstream_power": lambda x: find_item(x, "dsl_status.DownstreamPower"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="up",
        name="xDSL Upload",
        icon=UPLOAD_ICON,
        translation_key="up_rate",
        value_fn=lambda x: x.get("dsl_status", {}).get("UpstreamCurrRate", 0),
        native_unit_of_measurement=UnitOfDataRate.KILOBITS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DATA_RATE,
        attrs={
            "upstream_maxrate": lambda x: find_item(x, "dsl_status.UpstreamMaxRate"),
            "upstream_lineattenuation": lambda x: find_item(
                x, "dsl_status.UpstreamLineAttenuation"
            ),
            "upstream_noisemargin": lambda x: find_item(
                x, "dsl_status.UpstreamNoiseMargin"
            ),
            "upstream_power": lambda x: find_item(x, "dsl_status.UpstreamPower"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="wifi_rx",
        name="Wifi Rx",
        icon="mdi:wifi-arrow-down",
        value_fn=lambda x: find_item(x, "wifi_stats.RxBytes", 0),
        rolling_value_path="wifi_stats.RxBytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DATA_SIZE,
        translation_key="wifi_rx",
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="wifi_tx",
        name="Wifi Tx",
        icon="mdi:wifi-arrow-up",
        value_fn=lambda x: find_item(x, "wifi_stats.TxBytes", 0),
        rolling_value_path="wifi_stats.TxBytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DATA_SIZE,
        translation_key="wifi_tx",
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="fiber_power_rx",
        name="Fiber Power Rx",
        value_fn=lambda x: round(
            find_item(x, "fiber_status.SignalRxPower", 0) / 1000, 2
        ),
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        translation_key="fiber_power_rx",
        attrs={
            "Downstream max rate Gbps": lambda x: (
                find_item(x, "fiber_status.DownstreamMaxRate", 0) / 1000
            ),
            "Downstream current rate Gbps": lambda x: (
                find_item(x, "fiber_status.DownstreamCurrRate", 0) / 1000
            ),
            "Max bitrate (Gbps)": lambda x: (
                find_item(x, "fiber_status.MaxBitRateSupported", 0) / 1000
            ),
            "Temperature (°C)": lambda x: find_item(x, "fiber_status.Temperature"),
            "Voltage (V)": lambda x: find_item(x, "fiber_status.Voltage"),
            "Bias (mA)": lambda x: find_item(x, "fiber_status.Bias"),
            "ONU State": lambda x: find_item(x, "fiber_status.ONUState"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="fiber_power_tx",
        name="Fiber Power Tx",
        value_fn=lambda x: round(
            find_item(x, "fiber_status.SignalTxPower", 0) / 1000, 2
        ),
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        translation_key="fiber_power_tx",
        attrs={
            "Upstream max rate (Gbps)": lambda x: (
                find_item(x, "fiber_status.UpstreamMaxRate", 0) / 1000
            ),
            "Upstream current rate (Gbps)": lambda x: (
                find_item(x, "fiber_status.UpstreamCurrRate", 0) / 1000
            ),
            "Max bitrate (Gbps)": lambda x: (
                find_item(x, "fiber_status.MaxBitRateSupported", 0) / 1000
            ),
            "Tx power (dbm)": lambda x: find_item(x, "fiber_status.SignalTxPower"),
            "Temperature (°C)": lambda x: find_item(x, "fiber_status.Temperature"),
            "Voltage (V)": lambda x: find_item(x, "fiber_status.Voltage"),
            "Bias (mA)": lambda x: find_item(x, "fiber_status.Bias"),
            "ONU State": lambda x: find_item(x, "fiber_status.ONUState"),
        },
    ),
    LiveboxSensorEntityDescription(
        key="fiber_tx",
        name="Fiber Tx",
        icon=UPLOAD_ICON,
        value_fn=lambda x: find_item(x, "fiber_stats.TxBytes", 0),
        rolling_value_path="fiber_stats.TxBytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DATA_SIZE,
        translation_key="fiber_tx",
        attrs={"Tx errors": lambda x: find_item(x, "fiber_stats.TxErrors")},
    ),
    LiveboxSensorEntityDescription(
        key="fiber_rx",
        name="Fiber Rx",
        icon=DOWNLOAD_ICON,
        value_fn=lambda x: find_item(x, "fiber_stats.RxBytes", 0),
        rolling_value_path="fiber_stats.RxBytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DATA_SIZE,
        translation_key="fiber_rx",
        attrs={"Rx errors": lambda x: find_item(x, "fiber_stats.RxErrors")},
    ),
    LiveboxSensorEntityDescription(
        key="callers",
        name="Callers",
        icon=PHONE_ICON,
        value_fn=lambda x: len(x.get("callers", {})),
        state_class=SensorStateClass.TOTAL,
        translation_key="callers",
        attrs={"callers": lambda x: x.get("callers")},
    ),
    LiveboxSensorEntityDescription(
        key="upnp",
        name="Ports forwarding",
        value_fn=lambda x: len(x.get("upnp", {})),
        state_class=SensorStateClass.TOTAL,
        translation_key="upnp",
        attrs={"Ports": lambda x: x.get("upnp")},
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="dhcp_leases",
        name="DHCP Leases",
        value_fn=lambda x: len(x.get("dhcp_leases", {})),
        state_class=SensorStateClass.TOTAL,
        translation_key="dhcp_leases",
        attrs={"Leases": lambda x: x.get("dhcp_leases")},
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="guest_dhcp_leases",
        name="Guest DHCP Leases",
        value_fn=lambda x: len(x.get("guest_dhcp_leases", {})),
        state_class=SensorStateClass.TOTAL,
        translation_key="guest_dhcp_leases",
        attrs={"Leases": lambda x: x.get("guest_dhcp_leases")},
        entity_registry_enabled_default=False,
    ),
    LiveboxSensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="progress-clock",
        value_fn=lambda x: find_item(x, "infos.UpTime", 0),
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        translation_key="uptime",
        entity_registry_enabled_default=False,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LiveboxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    entities = []
    linktype = coordinator.data.get("wan_status", {}).get("LinkType", "").lower()

    sensor_stats = []
    for name, item in coordinator.data.get("stats", {}).items():
        sensor_stats.append(
            LiveboxSensorEntityDescription(
                key=f"{name}_rate_rx",
                name=f"{item['friendly_name']} Rate Rx",
                value_fn=get_closure_value_fn(f"stats.{name}.rate_rx"),
                translation_key=f"{name}_rate_rx",
                native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                state_class=SensorStateClass.MEASUREMENT,
                device_class=SensorDeviceClass.DATA_RATE,
            )
        )
        sensor_stats.append(
            LiveboxSensorEntityDescription(
                key=f"{name}_rate_tx",
                name=f"{item['friendly_name']} Rate Tx",
                value_fn=get_closure_value_fn(f"stats.{name}.rate_tx"),
                translation_key=f"{name}_rate_tx",
                native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
                state_class=SensorStateClass.MEASUREMENT,
                device_class=SensorDeviceClass.DATA_RATE,
            )
        )

    for description in SENSOR_TYPES + sensor_stats:
        if description.key in ["up", "down"] and linktype in ["gpon", "sfp"]:
            continue
        entities.append(LiveboxSensor(coordinator, description))

    async_add_entities(entities)


class LiveboxSensor(LiveboxEntity, SensorEntity):  # pyrefly: ignore[inconsistent-inheritance]
    """Representation of a livebox sensor."""

    def __init__(
        self,
        coordinator: LiveboxDataUpdateCoordinator,
        description: LiveboxSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)
        self._rolling_previous_reading = 0
        self._rolling_previous_uptime = 0
        self._rolling_rolls = 0

    def _get_rolling_native_value(
        self, description: LiveboxSensorEntityDescription
    ) -> int:
        """Return a monotonically increasing value for rolling 32-bit counters."""
        current_uptime = self.coordinator.data.get("infos", {}).get("UpTime") or 0
        current_reading = find_item(
            self.coordinator.data, cast(str, description.rolling_value_path), 0
        )

        if current_uptime < self._rolling_previous_uptime:
            self._rolling_previous_reading = 0
            self._rolling_rolls = 0

        if current_reading < self._rolling_previous_reading:
            _LOGGER.debug(
                "Rolling over 32-bit integer counter: %s",
                description.rolling_value_path,
            )
            self._rolling_rolls += 1

        self._rolling_previous_reading = current_reading
        self._rolling_previous_uptime = current_uptime

        return (self._rolling_rolls << 32) + current_reading

    @property
    def native_value(self) -> float | None:
        """Return the native value of the device."""
        description = cast(LiveboxSensorEntityDescription, self.entity_description)
        if description.rolling_value_path is not None:
            return self._get_rolling_native_value(description)
        return description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the device state attributes."""
        description = cast(LiveboxSensorEntityDescription, self.entity_description)
        if description.attrs:
            return {
                key: attr(self.coordinator.data)
                for key, attr in description.attrs.items()
            }
        return None
