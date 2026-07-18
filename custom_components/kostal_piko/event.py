"""Kostal Piko events."""
import logging

import kostal

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EVENTS_KEY, PikoUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

EVENT_TYPE_INVERTER_EVENT = "inverter_event"


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


class KostalPikoEvent(CoordinatorEntity[PikoUpdateCoordinator], EventEntity):
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
        self._seen_events: set[tuple[int, int, str]] = set()

    async def async_added_to_hass(self) -> None:
        """Register this entity on the Update Coordinator."""
        await super().async_added_to_hass()
        self.coordinator.start_fetch_events()
        self._seen_events.update(self._event_ids(self.coordinator.data))
        _LOGGER.debug(
            "Kostal Piko event entity added with %i existing events already seen",
            len(self._seen_events),
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
            self._seen_events.update(self._event_ids(self.coordinator.data))
            self._initialized = True
            _LOGGER.debug(
                "Initialized Kostal Piko event entity with %i baseline events",
                len(self._seen_events),
            )
            self.async_write_ha_state()
            return

        new_events = 0
        for event in reversed(events):
            event_id = self._event_id(event)
            if event_id in self._seen_events:
                continue

            self._seen_events.add(event_id)
            new_events += 1
            _LOGGER.debug(
                "Triggering Kostal Piko event: timestamp=%s code=%s env=%s",
                event.timestamp,
                event.code,
                event.env,
            )
            self._trigger_event(
                EVENT_TYPE_INVERTER_EVENT,
                {
                    "timestamp": event.timestamp,
                    "date": event.date.isoformat(),
                    "code": event.code,
                    "env": event.env,
                },
            )
            self.async_write_ha_state()

        if new_events == 0:
            _LOGGER.debug(
                "No new Kostal Piko events found; %i events are already seen",
                len(self._seen_events),
            )

    @staticmethod
    def _event_ids(data) -> set[tuple[int, int, str]]:
        if data is None or EVENTS_KEY not in data:
            return set()
        return {KostalPikoEvent._event_id(event) for event in data[EVENTS_KEY]}

    @staticmethod
    def _event_id(event) -> tuple[int, int, str]:
        return (event.timestamp, event.code, event.env)
