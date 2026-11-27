"""Number of lights on the string (25-300). The box needs it so the shows' patterns fit the string."""

from __future__ import annotations

import asyncio

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IlluminateConfigEntry
from .entity import IlluminateEntity
from .protocol import BULB_COUNTS, cmd_bulb_count

# Like the phone app: wait briefly, then read the count back to check the box took it
READBACK_DELAY = 0.2


async def async_setup_entry(
    hass: HomeAssistant, entry: IlluminateConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([IlluminateBulbCount(entry)])


class IlluminateBulbCount(IlluminateEntity, SelectEntity):
    _attr_translation_key = "bulb_count"
    _attr_icon = "mdi:string-lights"
    # A set-once setting: listed under Configuration on the device page, not on auto dashboards
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = [str(n) for n in BULB_COUNTS]

    def __init__(self, entry: IlluminateConfigEntry) -> None:
        super().__init__(entry, "bulb_count")

    @property
    def current_option(self) -> str | None:
        count = str(self.state_data.bulbs)
        return count if count in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        count = int(option)
        box = self._data.box
        try:
            await box.send(cmd_bulb_count(count))
            await asyncio.sleep(READBACK_DELAY)
            state = await box.get_state()
        except (OSError, TimeoutError, ValueError) as err:
            raise HomeAssistantError(f"Couldn't set the number of lights on {box.host}: {err}") from err
        self.coordinator.async_set_updated_data(state)
        if state.bulbs != count:
            raise HomeAssistantError(
                f"The lights at {box.host} report {state.bulbs} lights after being set to {count}"
            )
