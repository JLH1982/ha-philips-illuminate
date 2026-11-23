"""The lights: on/off, colour wheel + warm white (RGBW), and the 21 built-in shows as effects."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IlluminateConfigEntry
from .bulbs import picture_url
from .entity import IlluminateEntity
from .protocol import EFFECTS, MODE_STATIC, SHOW_FIRST, cmd_colour, cmd_power, cmd_show

DEFAULT_RGBW = (0, 0, 0, 255)  # warm white


async def async_setup_entry(
    hass: HomeAssistant, entry: IlluminateConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([IlluminateLight(entry)])


def _split(rgbw: tuple[int, int, int, int]) -> tuple[tuple[int, int, int, int], int]:
    """Device values -> (colour scaled so the brightest channel is 255, brightness)."""
    peak = max(rgbw)
    if peak == 0:
        return DEFAULT_RGBW, 255
    return tuple(round(c * 255 / peak) for c in rgbw), peak  # type: ignore[return-value]


class IlluminateLight(IlluminateEntity, LightEntity):
    _attr_name = None  # the device name
    _attr_color_mode = ColorMode.RGBW
    _attr_supported_color_modes = {ColorMode.RGBW}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = EFFECTS

    def __init__(self, entry: IlluminateConfigEntry) -> None:
        super().__init__(entry, "light")
        self._last_rgbw, self._last_brightness = DEFAULT_RGBW, 255
        self._remember_colour()

    def _remember_colour(self) -> None:
        s = self.state_data
        if s.show is None and max(s.red, s.green, s.blue, s.white):
            self._last_rgbw, self._last_brightness = _split((s.red, s.green, s.blue, s.white))

    def _handle_coordinator_update(self) -> None:
        self._remember_colour()
        super()._handle_coordinator_update()

    @property
    def is_on(self) -> bool:
        return self.state_data.is_on

    @property
    def effect(self) -> str | None:
        show = self.state_data.show
        return EFFECTS[show - 1] if show else None

    @property
    def entity_picture(self) -> str | None:
        # While a show runs, the icon becomes 5 bulbs in the show's colours.
        # A solid colour keeps the normal bulb icon, tinted by Home Assistant.
        show = self.state_data.show
        return picture_url(show) if show else None

    @property
    def rgbw_color(self) -> tuple[int, int, int, int]:
        return self._last_rgbw

    @property
    def brightness(self) -> int:
        # Shows always run at full brightness
        return 255 if self.state_data.show else self._last_brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        payloads = [] if self.is_on else [cmd_power(True)]
        expected: dict[str, Any] = {"is_on": True}

        if ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] in EFFECTS:
            show = EFFECTS.index(kwargs[ATTR_EFFECT]) + 1
            payloads.append(cmd_show(show, self._data.speed))
            expected.update(mode=SHOW_FIRST + show - 1, speed=self._data.speed)
        elif ATTR_RGBW_COLOR in kwargs or ATTR_BRIGHTNESS in kwargs:
            rgbw = kwargs.get(ATTR_RGBW_COLOR, self._last_rgbw)
            brightness = kwargs.get(ATTR_BRIGHTNESS, self._last_brightness)
            base, _ = _split(tuple(int(c) for c in rgbw))
            self._last_rgbw, self._last_brightness = base, brightness
            red, green, blue, white = (round(c * brightness / 255) for c in base)
            payloads.append(cmd_colour(red, green, blue, white))
            expected.update(mode=MODE_STATIC, red=red, green=green, blue=blue, white=white)

        if payloads:
            await self._send(*payloads, **expected)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send(cmd_power(False), is_on=False)
