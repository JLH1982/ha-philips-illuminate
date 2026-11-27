"""Tests for custom_components/illuminate/protocol.py. Needs no Home Assistant:
python3 -m unittest discover tests"""

import asyncio
import importlib.util
import pathlib
import sys
import unittest

# Load protocol.py on its own (importing the package would need Home Assistant)
_PATH = pathlib.Path(__file__).parents[1] / "custom_components" / "illuminate" / "protocol.py"
_spec = importlib.util.spec_from_file_location("illuminate_protocol", _PATH)
protocol = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = protocol
_spec.loader.exec_module(protocol)

# A real status reply: on, show 10 (0x2e), speed 16, no colour, 1 x 25 bulbs, firmware 6
REPLY = bytes.fromhex("66f1232e2110" "00000000" "01" "06" "99")


class ParseState(unittest.TestCase):
    def test_real_reply(self):
        s = protocol.parse_state(REPLY)
        self.assertTrue(s.is_on)
        self.assertEqual(s.show, 10)
        self.assertEqual(s.speed, 16)
        self.assertEqual(s.bulbs, 25)
        self.assertEqual(s.firmware, 6)

    def test_off_and_static_colour(self):
        s = protocol.parse_state(bytes.fromhex("66f124412110" "00ff0000" "01" "06" "99"))
        self.assertFalse(s.is_on)
        self.assertIsNone(s.show)  # 0x41 = solid colour
        self.assertEqual((s.red, s.green, s.blue, s.white), (0, 255, 0, 0))

    def test_rejects_garbage(self):
        for bad in (b"", REPLY[:12], b"\x00" + REPLY[1:], REPLY[:12] + b"\x00"):
            with self.assertRaises(ValueError):
                protocol.parse_state(bad)


class Commands(unittest.TestCase):
    def test_power(self):
        self.assertEqual(protocol.cmd_power(True).hex(), "cc2333")
        self.assertEqual(protocol.cmd_power(False).hex(), "cc2433")

    def test_colour(self):
        self.assertEqual(protocol.cmd_colour(1, 2, 3, 4).hex(), "5601020304aa")

    def test_show_range_and_speed_clamp(self):
        self.assertEqual(protocol.cmd_show(1, 16).hex(), "bb251044")
        self.assertEqual(protocol.cmd_show(21, 999).hex(), "bb393644")  # speed clamped to 54
        for bad in (0, 22):
            with self.assertRaises(ValueError):
                protocol.cmd_show(bad, 10)

    def test_bulb_count(self):
        self.assertEqual(protocol.cmd_bulb_count(25).hex(), "dd01fef022")
        self.assertEqual(protocol.cmd_bulb_count(300).hex(), "dd0cf3f022")
        for bad in (0, 10, 30, 325):
            with self.assertRaises(ValueError):
                protocol.cmd_bulb_count(bad)

    def test_bulb_count_in_status(self):
        # A real reply from a box set to 75 lights (3 x 25)
        s = protocol.parse_state(bytes.fromhex("66f124412125ff00a10003" "06" "99"))
        self.assertEqual(s.bulbs, 75)

    def test_effect_names(self):
        self.assertEqual(len(protocol.EFFECTS), 21)
        self.assertEqual(protocol.EFFECTS[13], "14: Twinkling multi")


class Speed(unittest.TestCase):
    def test_ends(self):
        self.assertEqual(protocol.speed_to_percent(1), 100)
        self.assertEqual(protocol.speed_to_percent(54), 0)
        self.assertEqual(protocol.percent_to_speed(100), 1)
        self.assertEqual(protocol.percent_to_speed(0), 54)

    def test_round_trip(self):
        for speed in range(1, 55):
            self.assertLessEqual(abs(protocol.percent_to_speed(protocol.speed_to_percent(speed)) - speed), 1)


class FakeBox(unittest.IsolatedAsyncioTestCase):
    """IlluminateBox against a local fake box on a random port."""

    async def asyncSetUp(self):
        self.received = []

        async def handle(reader, writer):
            data = await reader.read(64)
            self.received.append(data)
            if data == protocol.QUERY:
                writer.write(REPLY)
                await writer.drain()
            writer.close()

        self.server = await asyncio.start_server(handle, "127.0.0.1", 0)
        self.box = protocol.IlluminateBox("127.0.0.1", self.server.sockets[0].getsockname()[1])

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def test_get_state(self):
        self.assertEqual((await self.box.get_state()).show, 10)

    async def test_send_latest_skips_stale_commands(self):
        # Many colour changes fired at once: the first goes out, the rest collapse to the newest
        await asyncio.gather(*(self.box.send_latest(protocol.cmd_colour(i, 0, 0, 0)) for i in range(20)))
        await asyncio.sleep(0.05)
        self.assertLess(len(self.received), 20)
        self.assertEqual(self.received[-1], protocol.cmd_colour(19, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
