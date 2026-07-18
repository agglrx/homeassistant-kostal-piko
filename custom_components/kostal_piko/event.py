"""Kostal Piko events."""
import logging

import kostal

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EVENTS_KEY, PikoUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

EVENT_TYPE_INVERTER_EVENT = "inverter_event"
ATTR_CODE = "code"
ATTR_DATE = "date"
ATTR_DESCRIPTION = "description"
ATTR_ENV = "env"
ATTR_EVENT_ID = "event_id"
ATTR_TIMESTAMP = "timestamp"

EVENT_CODE_DESCRIPTIONS = {
    3000: "Internal system fault",
    3003: "Internal communication fault",
    3006: "Internal communication fault between grid monitoring and control system",
    3010: "Internal system fault",
    3011: "Internal system fault related to power curtailment",
    3012: "Internal communication fault between control system and communications PCB",
    3013: "Internal system fault",
    3014: "DC varistor defective",
    3017: "Excess temperature AC/DC power stage",
    3018: "Excess temperature of processor",
    3019: "Overvoltage on PV generator",
    3020: "Power curtailment through external specifications (grid operator)",
    3021: "Power curtailment due to a grid fault (increased grid frequency)",
    3022: "Overcurrent at PV generator",
    3023: "Internal system fault",
    3024: "Internal system fault",
    3025: "Overvoltage on PV generator",
    3026: "Overcurrent at PV generator",
    3027: "Internal system fault",
    3028: "Excess temperature AC/DC power stage",
    3029: "Excess temperature of processor",
    3030: "Excess temperature AC/DC power stage",
    3031: "Internal AC system fault",
    3032: "Overcurrent at PV generator",
    3033: "Internal system fault",
    3034: "Internal system fault",
    3035: "Internal system fault",
    3036: "Internal system fault",
    3037: "Internal system fault",
    3038: "Incorrect parameterization",
    3039: "Internal system fault",
    3045: "Internal intermediate circuit fault",
    3046: "Internal intermediate circuit fault",
    3047: "Internal system fault",
    3048: "Internal system fault",
    3049: "Internal system fault",
    3050: "Internal system fault",
    3051: "Internal AC system fault",
    3052: "Internal AC system fault",
    3053: "Internal system fault",
    3054: "Internal system fault",
    3055: "Internal system fault",
    3056: "Internal system fault",
    3057: "Internal system fault",
    3059: "Internal system fault",
    3060: "Internal system fault",
    3061: "Incorrect parameterization",
    3062: "Incorrect parameterization",
    3063: "Internal system fault",
    3064: "Internal system fault",
    3065: "Internal system fault",
    3066: "Internal system fault",
    3068: "Internal system fault",
    3070: "Internal system fault",
    3071: "Internal system fault",
    3072: "Internal AC system fault",
    3073: "Internal AC system fault",
    3074: "Internal AC system fault",
    3075: "Internal AC system fault",
    3076: "Internal AC system fault",
    3079: "Internal AC system fault",
    3080: "Internal system fault",
    3082: "Internal system fault",
    3083: "Internal system fault",
    3084: "Internal system fault",
    3085: "Internal system fault",
    3086: "Power curtailment due to a grid fault (increased AC voltage)",
    3087: "Internal system fault",
    3088: "Fan unit dirty",
    3089: "Fan unit dirty",
    3090: "Internal system fault",
    3091: "Fan not correctly connected",
    3092: "Fan not correctly connected",
    3093: "Incorrect parameterization",
    3094: "Incorrect parameterization",
    3095: "Incorrect calibration",
    3096: "Incorrect dimensioning of PV generator",
    3097: "Incorrect parameterization",
    3098: "Grid functionality not available",
    3101: "Internal system fault",
    3102: "Internal system fault",
    3103: "Internal system fault",
    3104: "Internal system fault",
    3105: "Internal system fault",
    3106: "Incorrect input on communication board or incorrect wiring",
    4100: "Internal software fault",
    4101: "Increased DC current L1",
    4102: "Increased DC current L2",
    4103: "Increased DC current L3",
    4104: "Increased DC current L1",
    4105: "Increased DC current L2",
    4106: "Increased DC current L3",
    4110: "Internal software fault",
    4121: "Internal system fault",
    4122: "Internal system fault",
    4130: "Internal system fault",
    4131: "Internal system fault",
    4150: "Increased grid frequency",
    4151: "Grid frequency too low",
    4157: "Increased grid frequency",
    4158: "Increased grid frequency",
    4159: "Increased grid frequency",
    4160: "Increased grid frequency",
    4161: "Grid frequency too low",
    4170: "One phase is not connected or circuit breaker is off",
    4180: "PE cable not connected",
    4181: "PE cable not connected",
    4185: "Internal software fault",
    4200: "Increased grid voltage",
    4201: "Grid voltage too low",
    4210: "Increased grid voltage",
    4211: "Grid voltage too low",
    4220: "Voltage mean value of the last 10 minutes too high",
    4221: "Voltage mean value of the last 10 minutes too high",
    4290: "The grid frequency has changed too quickly",
    4300: "Internal system fault",
    4301: "Internal system fault",
    4302: "Internal system fault",
    4303: "Internal system fault",
    4304: "Internal system fault",
    4321: "Defective EEPROM, forbidden memory access",
    4322: "Software error",
    4323: "Residual current",
    4324: "Parameter error",
    4325: "Parameter error",
    4422: "Parameter error",
    4424: "Parameter error",
    4425: "Residual current",
    4450: "Insulation fault",
    4451: "Internal system fault",
    4452: "Insulation fault",
    4475: "Internal system fault",
    4476: "Weak PV supply",
    4800: "Internal system fault",
    4801: "Insulation fault",
    4802: "Internal system fault",
    4803: "Insulation fault",
    4804: "Insulation fault",
    4805: "Internal system fault",
    4810: "Internal system fault",
    4830: "Hardware fault",
    4850: "Energy supply company",
    4920: "Measuring system fault",
    4921: "Measuring system fault",
    4922: "Measuring chain assignment fault",
    7503: "Internal system fault",
}

EVENT_CODE_DESCRIPTION_RANGES = (
    (4340, 4354, "Internal system fault"),
    (4360, 4421, "Residual current"),
    (4805, 4810, "Internal system fault"),
    (4870, 7500, "Internal system fault"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Kostal Piko platform with its events."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    device_info = DeviceInfo(
        configuration_url=entry.data[CONF_HOST],
        identifiers={(DOMAIN, coordinator.data[kostal.InfoVersions.SERIAL_NUMBER])},
        manufacturer="Kostal",
        model=coordinator.data[kostal.SettingsGeneral.INVERTER_MAKE],
        name=coordinator.data[kostal.SettingsGeneral.INVERTER_NAME],
        sw_version=coordinator.data[kostal.InfoVersions.VERSION_FW],
        hw_version=coordinator.data[kostal.InfoVersions.VERSION_HW],
    )

    async_add_entities([KostalPikoEvent(coordinator, device_info)])


class KostalPikoEvent(
    CoordinatorEntity[PikoUpdateCoordinator], EventEntity, RestoreEntity
):
    """A Kostal Piko event entity updated using a DataUpdateCoordinator."""

    _attr_has_entity_name = True
    _attr_name = "Event"

    def __init__(
        self,
        coordinator: PikoUpdateCoordinator,
        deviceInfo: DeviceInfo,
    ) -> None:
        """Create a new KostalPikoEvent entity for inverter events."""
        super().__init__(coordinator)
        self._attr_device_info = deviceInfo
        self._attr_unique_id = (
            f"{coordinator.data[kostal.InfoVersions.SERIAL_NUMBER]}_events"
        )
        self._initialized = False
        self._event_types = {EVENT_TYPE_INVERTER_EVENT}
        self._restored_event_id: tuple[int, int, str] | None = None
        self._seen_events: set[tuple[int, int, str]] = set()

    async def async_added_to_hass(self) -> None:
        """Register this entity on the Update Coordinator."""
        await super().async_added_to_hass()
        if last_state := await self.async_get_last_state():
            self._restored_event_id = self._event_id_from_attributes(
                last_state.attributes
            )
            if last_state.state not in (None, "unknown", "unavailable"):
                self._event_types.add(last_state.state)
            if self._restored_event_id is not None:
                self._seen_events.add(self._restored_event_id)

        self.coordinator.start_fetch_events()
        _LOGGER.debug(
            "Kostal Piko event entity added with restored event id %s",
            self._restored_event_id,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister this entity from the Update Coordinator."""
        self.coordinator.stop_fetch_events()
        await super().async_will_remove_from_hass()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and EVENTS_KEY in self.coordinator.data
        )

    @property
    def event_types(self) -> list[str]:
        """Return the possible event types."""
        return sorted(self._event_types)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None or EVENTS_KEY not in self.coordinator.data:
            _LOGGER.debug("Kostal Piko coordinator update has no event data yet")
            return

        events = self.coordinator.data[EVENTS_KEY]
        if not self._initialized:
            self._initialized = True
            new_events = self._import_startup_events(events)
        else:
            new_events = self._trigger_unseen_events(events)

        if new_events == 0:
            _LOGGER.debug(
                "No new Kostal Piko events found; %i events are already seen",
                len(self._seen_events),
            )

    def _import_startup_events(self, events) -> int:
        """Import existing inverter memory without replaying restored events."""
        if self._restored_event_id is None:
            _LOGGER.debug(
                "Importing %i Kostal Piko startup events; no restored event id found",
                len(events),
            )
            return self._trigger_unseen_events(events)

        restored_event_found = False
        new_events = 0
        for event in reversed(events):
            event_id = self._event_id(event)
            if not restored_event_found:
                self._seen_events.add(event_id)
                if event_id == self._restored_event_id:
                    restored_event_found = True
                continue

            if self._trigger_inverter_event(event):
                new_events += 1

        if restored_event_found:
            _LOGGER.debug(
                "Imported %i Kostal Piko startup events newer than restored event id %s",
                new_events,
                self._restored_event_id,
            )
            return new_events

        _LOGGER.debug(
            "Restored event id %s was not found in inverter memory; importing all %i events",
            self._restored_event_id,
            len(events),
        )
        self._seen_events.clear()
        self._seen_events.add(self._restored_event_id)
        return self._trigger_unseen_events(events)

    def _trigger_unseen_events(self, events) -> int:
        """Trigger events that have not already been observed."""
        new_events = 0
        for event in reversed(events):
            if self._trigger_inverter_event(event):
                new_events += 1
        return new_events

    def _trigger_inverter_event(self, event) -> bool:
        event_id = self._event_id(event)
        if event_id in self._seen_events:
            return False

        self._seen_events.add(event_id)
        _LOGGER.debug(
            "Triggering Kostal Piko event: timestamp=%s code=%s env=%s",
            event.timestamp,
            event.code,
            event.env,
        )
        event_type = self._event_type(event)
        self._event_types.add(event_type)
        self._trigger_event(event_type, self._event_attributes(event))
        self.async_write_ha_state()
        return True

    @staticmethod
    def _event_id(event) -> tuple[int, int, str]:
        return (event.timestamp, event.code, event.env)

    @staticmethod
    def _event_type(event) -> str:
        return event_label(event.code)

    @staticmethod
    def _event_attributes(event) -> dict[str, int | str]:
        return {
            ATTR_EVENT_ID: f"{event.timestamp}-{event.code}-{event.env}",
            ATTR_TIMESTAMP: event.timestamp,
            ATTR_DATE: event.date.isoformat(),
            ATTR_CODE: event.code,
            ATTR_DESCRIPTION: event_description(event.code),
            ATTR_ENV: event.env,
        }

    @staticmethod
    def _event_id_from_attributes(attributes) -> tuple[int, int, str] | None:
        timestamp = attributes.get(ATTR_TIMESTAMP)
        code = attributes.get(ATTR_CODE)
        env = attributes.get(ATTR_ENV)
        if timestamp is None or code is None or env is None:
            return None

        try:
            return (int(timestamp), int(code), str(env))
        except (TypeError, ValueError):
            return None


def event_label(code: int) -> str:
    """Return the display label for a Kostal Piko event code."""
    return f"{code}: {event_description(code)}"


def event_description(code: int) -> str:
    """Return the manual description for a Kostal Piko event code."""
    if code in EVENT_CODE_DESCRIPTIONS:
        return EVENT_CODE_DESCRIPTIONS[code]

    for start, end, description in EVENT_CODE_DESCRIPTION_RANGES:
        if start <= code <= end:
            return description

    return "Unknown event"
