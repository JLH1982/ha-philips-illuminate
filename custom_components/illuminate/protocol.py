"""Local TCP protocol for Philips Illuminate Wi-Fi boxes (Seasonal Specialties / Zengge, HF-A11 module).

Decoded from the Android app com.Zengge.LEDWifiPHILIPS 2.0.6; see docs/PROTOCOL.md.
No Home Assistant imports, so this file can be tested on its own.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

PORT = 5577
TIMEOUT = 5

QUERY = bytes([0xEF, 0x01, 0x77])
MODE_STATIC = 0x41
SHOW_FIRST = 0x25  # show 1
SPEED_FASTEST = 1
SPEED_SLOWEST = 54  # firmware >= 4; older boxes use 31

SHOWS = [
    "Chasing multi pattern from center to ends",
    "Chasing warm white sections",
    "Chasing blue to warm white",
    "Chasing red, green, warm white",
    "Chasing red and green",
    "Chasing multi solid colors",
    "Chasing multi pattern colors",
    "Bi-directional red and warm white chasing",
    "Bi-directional blue and warm white chasing",
    "Bi-directional chasing multi colors",
    "Chasing warm white thru multi",
    "Chasing multi thru warm white",
    "Twinkling warm white",
    "Twinkling multi",
    "Slow twinkle",
    "Fade in/out multi solid colors",
    "Fade in/out warm white to multi",
    "Fade in/out orange to purple",
    "Chasing orange and purple",
    "Chasing red, warm white, blue",
    "Cycle through shows 1-17",
]
# Effect names shown in Home Assistant, numbered like the phone app
EFFECTS = [f"{i}: {name}" for i, name in enumerate(SHOWS, start=1)]


@dataclass
class State:
    is_on: bool
    mode: int
    speed: int
    red: int
    green: int
    blue: int
    white: int
    firmware: int

    @property
    def show(self) -> int | None:
        """Show number 1-21, or None for a solid colour."""
        n = self.mode - SHOW_FIRST + 1
        return n if 1 <= n <= len(SHOWS) else None


def parse_state(data: bytes) -> State:
    # 66 f1 <23 on|24 off> <mode> 21 <speed> R G B WW <bulbs/25> <firmware> 99
    if len(data) < 13 or data[0] != 0x66 or data[12] != 0x99:
        raise ValueError(f"unexpected status reply: {data.hex(' ')}")
    return State(
        is_on=data[2] == 0x23,
        mode=data[3],
        speed=data[5],
        red=data[6],
        green=data[7],
        blue=data[8],
        white=data[9],
        firmware=data[11],
    )


def cmd_power(on: bool) -> bytes:
    return bytes([0xCC, 0x23 if on else 0x24, 0x33])


def cmd_colour(red: int, green: int, blue: int, white: int) -> bytes:
    return bytes([0x56, red, green, blue, white, 0xAA])


def cmd_show(show: int, speed: int) -> bytes:
    if not 1 <= show <= len(SHOWS):
        raise ValueError(f"show must be 1-{len(SHOWS)}")
    speed = max(SPEED_FASTEST, min(SPEED_SLOWEST, speed))
    return bytes([0xBB, SHOW_FIRST + show - 1, speed, 0x44])


def speed_to_percent(speed: int) -> int:
    """Device speed (1 fastest .. 54 slowest) to 0-100 % (100 = fastest)."""
    speed = max(SPEED_FASTEST, min(SPEED_SLOWEST, speed))
    return round((SPEED_SLOWEST - speed) * 100 / (SPEED_SLOWEST - SPEED_FASTEST))


def percent_to_speed(percent: float) -> int:
    percent = max(0.0, min(100.0, percent))
    return round(SPEED_SLOWEST - percent * (SPEED_SLOWEST - SPEED_FASTEST) / 100)


class IlluminateBox:
    """Opens a short TCP connection per request; the box handles few connections at once."""

    def __init__(self, host: str, port: int = PORT) -> None:
        self.host = host
        self.port = port
        self._lock = asyncio.Lock()
        self._pending: bytes | None = None
        self._sender: asyncio.Task | None = None

    async def _exchange(self, payload: bytes, reply_len: int = 0) -> bytes:
        async with self._lock:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), TIMEOUT
            )
            try:
                writer.write(payload)
                await writer.drain()
                if reply_len:
                    return await asyncio.wait_for(reader.readexactly(reply_len), TIMEOUT)
                return b""
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass

    async def get_state(self) -> State:
        return parse_state(await self._exchange(QUERY, 13))

    async def send(self, payload: bytes) -> None:
        await self._exchange(payload)

    async def send_latest(self, payload: bytes) -> None:
        """Send without queueing up: while one command is in flight, newer ones replace
        each other and only the last is sent (dragging the colour wheel sends a stream)."""
        self._pending = payload
        if self._sender is None or self._sender.done():
            self._sender = asyncio.ensure_future(self._drain())
        await asyncio.shield(self._sender)

    async def _drain(self) -> None:
        while self._pending is not None:
            payload, self._pending = self._pending, None
            await self._exchange(payload)
