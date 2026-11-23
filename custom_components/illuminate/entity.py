"""Shared base entity."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, IlluminateConfigEntry
from .protocol import State

# Read the real state back this long after the last command
# (the box takes a moment to report a new mode)
CONFIRM_DELAY = 1.5


class IlluminateEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: IlluminateConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._data = entry.runtime_data
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name="Illuminate lights",
            manufacturer="Philips / Seasonal Specialties",
            model="Illuminate Wi-Fi box (HF-A11)",
            sw_version=str(self.coordinator.data.firmware),
        )

    @property
    def state_data(self) -> State:
        return self.coordinator.data

    async def _send(self, *payloads: bytes, **expected: Any) -> None:
        """Send commands, show the expected state at once, and confirm it from the box shortly after."""
        for payload in payloads[:-1]:
            await self._data.box.send(payload)
        if payloads:
            await self._data.box.send_latest(payloads[-1])
        if expected:
            # Optimistic update: every entity of this box redraws immediately
            self.coordinator.async_set_updated_data(replace(self.coordinator.data, **expected))
        self._schedule_confirm()

    @callback
    def _schedule_confirm(self) -> None:
        if self._data.confirm_unsub:
            self._data.confirm_unsub()

        @callback
        def _confirm(_now) -> None:
            self._data.confirm_unsub = None
            self.hass.async_create_task(self.coordinator.async_refresh())

        self._data.confirm_unsub = async_call_later(self.hass, CONFIRM_DELAY, _confirm)
