"""Philips Illuminate Wi-Fi Christmas lights (local control)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .bulbs import register_view
from .protocol import IlluminateBox, State

_LOGGER = logging.getLogger(__name__)
DOMAIN = "illuminate"
PLATFORMS = [Platform.LIGHT, Platform.NUMBER]
SCAN_INTERVAL = timedelta(seconds=15)
DEFAULT_SPEED = 16  # what the box reported when first probed


@dataclass
class IlluminateData:
    box: IlluminateBox
    coordinator: DataUpdateCoordinator[State]
    # Speed to use for the next show. Kept here because the box only reports
    # a meaningful speed while a show is running.
    speed: int = DEFAULT_SPEED
    confirm_unsub: Callable[[], None] | None = None


type IlluminateConfigEntry = ConfigEntry[IlluminateData]


async def async_setup_entry(hass: HomeAssistant, entry: IlluminateConfigEntry) -> bool:
    box = IlluminateBox(entry.data[CONF_HOST])

    async def _update() -> State:
        try:
            return await box.get_state()
        except (OSError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Can't reach the lights at {box.host}: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name=f"Illuminate {box.host}",
        update_method=_update,
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    data = IlluminateData(box=box, coordinator=coordinator)
    if coordinator.data.show is not None:
        data.speed = coordinator.data.speed
    entry.runtime_data = data

    register_view(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IlluminateConfigEntry) -> bool:
    if entry.runtime_data.confirm_unsub:
        entry.runtime_data.confirm_unsub()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
