# Philips Illuminate Wi-Fi box: local protocol

Decoded from the Philips Illuminate Android app (com.Zengge.LEDWifiPHILIPS 2.0.6) and checked
against a real box (firmware 6) in November 2026. Not official documentation.

- Hardware: Hi-Flying HF-A11 Wi-Fi module (web page on port 80, basic auth, realm "A11").
- Transport: TCP 5577, no authentication. It is the original LEDENET dialect of Magic Home.
- HA's built-in Magic Home integration handles on/off and colour. It doesn't know about the shows.

## Commands (hex)

| What | Bytes | Notes |
|---|---|---|
| Status query | `EF 01 77` | Reply is 13 bytes, see below |
| Power on / off | `CC 23 33` / `CC 24 33` | |
| Built-in show | `BB <show> <speed> 44` | show 0x25–0x39 (37–57); speed 1 = fastest … 54 = slowest (31 on firmware < 4) |
| Solid colour + warm white | `56 R G B WW AA` | The app's Brightness slider sends `56 00 00 00 <level> AA` (warm white only) |
| Multi-colour (static) | `88 <n> R G B … 55` | n colours |
| Custom show | `99` + 16×RGB (unused = `01 02 03`) + speed + type (`3A` jump / `3C` gradual / `3B` strobe-ish) + `FF 66` | 53 bytes |
| Music-mode colour | `78 R G B 00 EE` | |
| Set bulb count | `DD <n/25> <255-n/25> F0 22` | n = 25-300 in steps of 25 (the app's choices). The app reads the status back to check it took |

There is no general brightness command, so dimming only applies to warm white.

## Status reply

`66 f1 23 2e 21 10 RR GG BB WW 01 06 99`
- [2] `23` = on, `24` = off
- [3] current show/mode (0x25–0x39 = show 1–21)
- [4] `21` = running
- [5] speed
- [6..8] RGB, [9] warm white
- [10] bulb count / 25
- [11] firmware/model (6 here; ≥4 uses the 1–54 speed range)
- [12] `99` end marker

## Shows

| # | Byte | Name |
|---|---|---|
| 1 | 0x25 | Chasing multi pattern from center to ends |
| 2 | 0x26 | Chasing warm white sections |
| 3 | 0x27 | Chasing blue to warm white |
| 4 | 0x28 | Chasing red, green, warm white |
| 5 | 0x29 | Chasing red and green |
| 6 | 0x2A | Chasing multi solid colors |
| 7 | 0x2B | Chasing multi pattern colors |
| 8 | 0x2C | Bi-directional red and warm white chasing |
| 9 | 0x2D | Bi-directional blue and warm white chasing |
| 10 | 0x2E | Bi-directional chasing multi colors |
| 11 | 0x2F | Chasing warm white thru multi |
| 12 | 0x30 | Chasing multi thru warm white |
| 13 | 0x31 | Twinkling warm white |
| 14 | 0x32 | Twinkling multi |
| 15 | 0x33 | Slow twinkle |
| 16 | 0x34 | Fade in/out multi solid colors |
| 17 | 0x35 | Fade in/out warm white to multi |
| 18 | 0x36 | Fade in/out orange to purple |
| 19 | 0x37 | Chasing orange and purple |
| 20 | 0x38 | Chasing red, warm white, blue |
| 21 | 0x39 | Cycle through functions 1 - 17 |
