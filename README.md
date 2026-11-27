# Philips Illuminate for Home Assistant

Local control of **Philips Illuminate Wi-Fi Christmas lights** (made by Seasonal Specialties) from
Home Assistant. No cloud and no phone app needed: Home Assistant talks to the lights' Wi-Fi box
directly on your network.

- **On/off**, a **colour wheel** and **warm white** (RGBW), with brightness
- All **21 built-in shows** as light effects, named and numbered like in the Philips app
- A **show speed** slider (0-100 %)
- The **number of lights** on the string (25-300), which the box needs so the shows fit the string
- While a show runs, the light's icon becomes 5 little bulbs in that show's colours
- Changes made in the Philips app show up in Home Assistant within 15 seconds

## Requirements

- A Philips Illuminate light set with the Wi-Fi box (the one the "Philips Illuminate" app controls;
  inside is a Hi-Flying HF-A11 Wi-Fi module)
- The box already on your Wi-Fi (set it up once with the Philips app)
- A **fixed IP address** for the box (a DHCP reservation in your router)
- Home Assistant 2024.11 or newer (tested on 2026.10)

## Install

**HACS (recommended):** HACS → ⋮ → *Custom repositories* → add
`https://github.com/JLH1982/ha-philips-illuminate` as type *Integration* → install
**Philips Illuminate** → restart Home Assistant.

**Manually:** copy `custom_components/illuminate` into your Home Assistant `config/custom_components/`
folder and restart Home Assistant.

## Set up

Settings → Devices & services → **Add integration** → **Philips Illuminate** → enter the box's IP address.
Repeat for each box.

You get three entities per box:

| Entity | What it does |
|---|---|
| `light.illuminate_lights` | On/off, colour + warm white, brightness, and the shows as effects |
| `number.illuminate_lights_show_speed` | Show speed; changing it restarts the running show at the new speed |
| `select.illuminate_lights_number_of_lights` | How many lights are on the string (25-300, in steps of 25), like the app's "Number of lights" setting. It's under *Configuration* on the device page |

### Example: run a show at sunset

```yaml
automation:
  - alias: Christmas lights at sunset
    triggers:
      - trigger: sun
        event: sunset
    actions:
      - action: light.turn_on
        target:
          entity_id: light.illuminate_lights
        data:
          effect: "14: Twinkling multi"
```

## Good to know

- **Brightness:** the box has no brightness setting, so dimming scales the colour values.
  Shows always run at full brightness.
- **One connection at a time:** the box handles very few connections, so the integration opens a short
  connection per command and only sends the latest colour while you drag the colour wheel.
- **Home Assistant's built-in Magic Home integration** can switch these boxes on and off and set a colour
  (it's the same protocol family), but it doesn't know the Illuminate shows.

## How it works

The box listens on TCP port 5577 with no password. The commands are a few bytes each, for example
`CC 23 33` turns the lights on and `BB <show> <speed> 44` starts a show. The full command list is in
[docs/PROTOCOL.md](docs/PROTOCOL.md). `custom_components/illuminate/protocol.py` has no Home Assistant
imports, so it can be used on its own:

```python
import asyncio
from protocol import IlluminateBox, cmd_power, cmd_show

async def main():
    box = IlluminateBox("192.168.1.50")
    print(await box.get_state())
    await box.send(cmd_power(True))
    await box.send(cmd_show(14, 20))  # "Twinkling multi"

asyncio.run(main())
```

Tests for the protocol code (no Home Assistant needed): `python3 -m unittest discover tests`

## Disclaimer

Not affiliated with or endorsed by Philips, Signify or Seasonal Specialties. "Philips" and
"Illuminate" are trademarks of their owners. The protocol was worked out for interoperability with
lights you own; use at your own risk.

## License

[MIT](LICENSE)
