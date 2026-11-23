"""Show speed, 0-100 % (100 = fastest). Changing it restarts the running show at the new speed."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IlluminateConfigEntry
from .entity import IlluminateEntity
from .protocol import cmd_show, percent_to_speed, speed_to_percent


async def async_setup_entry(
    hass: HomeAssistant, entry: IlluminateConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([IlluminateSpeed(entry)])


class IlluminateSpeed(IlluminateEntity, NumberEntity):
    _attr_translation_key = "speed"
    _attr_icon = "mdi:speedometer"
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, entry: IlluminateConfigEntry) -> None:
        super().__init__(entry, "speed")

    def _handle_coordinator_update(self) -> None:
        if self.state_data.show is not None:
            self._data.speed = self.state_data.speed  # pick up changes made in the phone app
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> int:
        return speed_to_percent(self._data.speed)

    async def async_set_native_value(self, value: float) -> None:
        self._data.speed = percent_to_speed(value)
        show = self.state_data.show
        if show is not None and self.state_data.is_on:
            await self._send(cmd_show(show, self._data.speed), speed=self._data.speed)
        else:
            self.async_write_ha_state()
