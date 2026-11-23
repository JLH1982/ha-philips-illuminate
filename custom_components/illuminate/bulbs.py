"""A picture of 5 Christmas bulbs in the colours of each show, used as the light's icon while a show runs.

Home Assistant's brightness bar can only show one colour, so for a show the light's entity_picture
points at /api/illuminate/bulbs/<show>.svg instead. The pictures are generated here and contain
nothing but the colour pattern, so the view needs no login (browsers load <img> without HA's token).
"""

from __future__ import annotations

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .protocol import SHOWS

# Bump when the artwork changes, so browsers and Cloudflare don't keep an old copy
ART_VERSION = 1
URL = "/api/illuminate/bulbs/{show}.svg"

RED, GREEN, BLUE = "#e53935", "#43a047", "#1e88e5"
WARM, ORANGE, PURPLE, YELLOW = "#ffc56e", "#fb8c00", "#9c27b0", "#fdd835"
DIM_WARM = "#7a6040"  # a warm-white bulb between twinkles
MULTI = [RED, GREEN, BLUE, YELLOW, PURPLE]  # one of each colour

# Show number -> 5 bulb colours, left to right (worked out from the show names;
# the phone app has no pictures or colour data for its shows)
PATTERNS: dict[int, list[str]] = {
    1: MULTI,                                   # Chasing multi pattern from center to ends
    2: [WARM, WARM, DIM_WARM, WARM, WARM],      # Chasing warm white sections
    3: [BLUE, WARM, BLUE, WARM, BLUE],          # Chasing blue to warm white
    4: [RED, GREEN, WARM, RED, GREEN],          # Chasing red, green, warm white
    5: [RED, GREEN, RED, GREEN, RED],           # Chasing red and green
    6: MULTI,                                   # Chasing multi solid colors
    7: MULTI,                                   # Chasing multi pattern colors
    8: [RED, WARM, RED, WARM, RED],             # Bi-directional red and warm white chasing
    9: [BLUE, WARM, BLUE, WARM, BLUE],          # Bi-directional blue and warm white chasing
    10: MULTI,                                  # Bi-directional chasing multi colors
    11: [WARM, RED, WARM, GREEN, WARM],         # Chasing warm white thru multi
    12: [RED, WARM, GREEN, WARM, BLUE],         # Chasing multi thru warm white
    13: [WARM, DIM_WARM, WARM, DIM_WARM, WARM], # Twinkling warm white
    14: MULTI,                                  # Twinkling multi
    15: [WARM, DIM_WARM, WARM, WARM, DIM_WARM], # Slow twinkle
    16: MULTI,                                  # Fade in/out multi solid colors
    17: [WARM, RED, GREEN, BLUE, WARM],         # Fade in/out warm white to multi
    18: [ORANGE, PURPLE, ORANGE, PURPLE, ORANGE],  # Fade in/out orange to purple
    19: [ORANGE, PURPLE, ORANGE, PURPLE, ORANGE],  # Chasing orange and purple
    20: [RED, WARM, BLUE, RED, WARM],           # Chasing red, warm white, blue
    21: MULTI,                                  # Cycle through shows 1-17
}
assert set(PATTERNS) == set(range(1, len(SHOWS) + 1))


def picture_url(show: int) -> str:
    return URL.format(show=show) + f"?v={ART_VERSION}"


def render(colours: list[str]) -> str:
    """5 bulbs hanging from a wire. Sized for HA's round 40 px icon badge (it crops to a circle)."""
    xs = (16, 33, 50, 67, 84)
    # The wire sags in the middle, so each bulb hangs a little lower towards the centre
    tops = (50, 54, 55, 54, 50)
    bulbs = []
    for i, (x, top, colour) in enumerate(zip(xs, tops, colours)):
        # Each bulb is drawn around (0, 0) at the top of its socket, then moved and tilted into place
        bulbs.append(
            f'<g transform="translate({x} {top}) rotate({(-8, -4, 0, 4, 8)[i]}) scale(1.3)">'
            f'<circle cx="0" cy="14" r="9" fill="{colour}" opacity=".35"/>'  # glow
            '<rect x="-3" y="0" width="6" height="5" rx="1" fill="#2e5d34"/>'  # socket
            f'<path d="M0 4C-5 7-6 12-6 15A6 6 0 0 0 6 15C6 12 5 7 0 4Z" fill="{colour}"/>'
            '<ellipse cx="-2" cy="11" rx="1.4" ry="2.6" fill="#fff" opacity=".55"/>'  # shine
            "</g>"
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<circle cx="50" cy="50" r="50" fill="#13202e"/>'
        '<path d="M4 46Q50 66 96 46" fill="none" stroke="#2e5d34" stroke-width="2.5"/>'
        + "".join(bulbs)
        + "</svg>"
    )


class BulbPictureView(HomeAssistantView):
    url = URL
    name = "api:illuminate:bulbs"
    requires_auth = False  # only a picture of a colour pattern

    async def get(self, request: web.Request, show: str) -> web.Response:
        try:
            colours = PATTERNS[int(show)]
        except (KeyError, ValueError):
            return web.Response(status=404)
        return web.Response(
            text=render(colours),
            content_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=86400"},
        )


def register_view(hass: HomeAssistant) -> None:
    key = "illuminate_bulb_view"
    if not hass.data.get(key):
        hass.http.register_view(BulbPictureView())
        hass.data[key] = True
