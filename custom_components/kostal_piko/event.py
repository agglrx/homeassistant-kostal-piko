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
ATTR_ENV = "env"
ATTR_EVENT_ID = "event_id"
ATTR_TIMESTAMP = "timestamp"


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

    _attr_event_types = [EVENT_TYPE_INVERTER_EVENT]
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
        self._restored_event_id: tuple[int, int, str] | None = None
        self._seen_events: set[tuple[int, int, str]] = set()

    async def async_added_to_hass(self) -> None:
        """Register this entity on the Update Coordinator."""
        await super().async_added_to_hass()
        if last_state := await self.async_get_last_state():
            self._restored_event_id = self._event_id_from_attributes(
                last_state.attributes
            )
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
        self._trigger_event(EVENT_TYPE_INVERTER_EVENT, self._event_attributes(event))
        self.async_write_ha_state()
        return True

    @staticmethod
    def _event_id(event) -> tuple[int, int, str]:
        return (event.timestamp, event.code, event.env)

    @staticmethod
    def _event_attributes(event) -> dict[str, int | str]:
        return {
            ATTR_EVENT_ID: f"{event.timestamp}-{event.code}-{event.env}",
            ATTR_TIMESTAMP: event.timestamp,
            ATTR_DATE: event.date.isoformat(),
            ATTR_CODE: event.code,
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
