#!/usr/bin/env python3
"""ESP32 pin-level circuit diagram, generated from the firmware.

The GPIO numbers are read from aislebot_esp32.ino (the #define block and the
MOTOR_DIR_SIGN / ENC_DIR_SIGN tables) at run time, so the drawing cannot drift
from the code. The shifter channel order is read from Bench_Test_Map.md and the
script stops if the two disagree.

Sources for everything that is not in the firmware:
  docs/Bench_Test_Map.md      "Full 8-channel wiring": H/L channels, wire colours, power
  docs/Master_Reference.md    2.5, 3.1, 3.2, 4.1, 4.2: drivers, power rails, ground bus
  docs/Hardware_Roadmap.md    VIN-from-buck fix "never actually done"

Run from anywhere:  python3 docs/hardware/esp32_pin_circuit.py
Then:               node docs/hardware/render_svg_png.js docs/hardware/esp32_pin_circuit.svg 2
"""
import html
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MONO = bool(os.environ.get("MONO"))      # MONO=1 writes a black-and-white copy
OUT = Path(__file__).resolve().parent / ("esp32_pin_circuit_mono.svg" if MONO else "esp32_pin_circuit.svg")

# ----------------------------------------------------------------- read the code
ino = (ROOT / "aislebot_esp32.ino").read_text(encoding="utf-8")


def define(name):
    m = re.search(rf"#define\s+{name}\s+(\d+)", ino)
    if not m:
        sys.exit(f"{name} not found in aislebot_esp32.ino")
    return int(m.group(1))


def table(name):
    m = re.search(rf"{name}\[NUM_MOTORS\]\s*=\s*\{{([^}}]*)\}}", ino)
    if not m:
        sys.exit(f"{name} not found in aislebot_esp32.ino")
    return [int(v) for v in re.findall(r"[+-]?\d+", m.group(1))]


MOTORS = ["FR", "FL", "RR", "RL"]
PWM = [define(f"PWM{i}_PIN") for i in range(1, 5)]
DIR = [define(f"DIR{i}_PIN") for i in range(1, 5)]
ENC_A = [define(f"ENC{i}_A_PIN") for i in range(1, 5)]
ENC_B = [define(f"ENC{i}_B_PIN") for i in range(1, 5)]
MSIGN, ESIGN = table("MOTOR_DIR_SIGN"), table("ENC_DIR_SIGN")
cpr = [float(v) for v in re.findall(r"([\d.]+)f", re.search(r"ENCODER_CPR\[NUM_MOTORS\]\s*=\s*\{([^}]*)\}", ino).group(1))]
if MSIGN != ESIGN:
    sys.exit("MOTOR_DIR_SIGN and ENC_DIR_SIGN differ in the firmware, that is a runaway fault")
fw_version = re.search(r"Motor Controller\s+(v[\d.]+)", ino).group(1)

# shifter channels from the bench doc, checked against the firmware
bench = (ROOT / "docs" / "Bench_Test_Map.md").read_text(encoding="utf-8")
rows = re.findall(r"\|\s*(FR|FL|RR|RL)\s*\|\s*(\w+)\s*\|\s*([AB])\s*\|\s*\*\*H(\d)\*\*\s*\|\s*\*\*L(\d)\*\*\s*\|\s*(\d+)\s*\|", bench)
if len(rows) != 8:
    sys.exit(f"expected 8 shifter rows in Bench_Test_Map.md, found {len(rows)}")
WIRE = {}      # (motor, 'A'|'B') -> (colour, channel)
for motor, colour, sig, h, l, gpio in rows:
    i = MOTORS.index(motor)
    want = (ENC_A if sig == "A" else ENC_B)[i]
    if int(gpio) != want or h != l:
        sys.exit(f"Bench_Test_Map says {motor} {sig} is GPIO {gpio} on H{h}/L{l}; firmware has GPIO {want}")
    WIRE[(motor, sig)] = (colour, int(l))
for i in range(4):
    if WIRE[(MOTORS[i], "A")][1] != 2 * i or WIRE[(MOTORS[i], "B")][1] != 2 * i + 1:
        sys.exit("shifter channel order is not L0..L7 in motor order")

INPUT_ONLY = {34, 35, 36, 39}
BOARD_NAME = {36: "36 (SP)", 39: "39 (SN)"}


def gp(n):
    return "GPIO" + BOARD_NAME.get(n, str(n)) + ("*" if n in INPUT_ONLY else "")


# ----------------------------------------------------------------- drawing kit
C = dict(ink="#172126", mute="#52606A", rule="#9AA7AE", p5="#E65100", p24="#C62828", p33="#1565C0",
         enc="#6A1B9A", gnd="#212121", box="#FFFFFF", fill="#F3F6F4", hw="#E3E8E2")
if MONO:
    C.update(mute="#444444", rule="#8C8C8C", p5="#1A1A1A", p24="#1A1A1A", p33="#1A1A1A",
             enc="#1A1A1A", fill="#FFFFFF", hw="#EEEEEE")
W, H = 1820, 1020
out = []
add = out.append


def esc(s):
    return html.escape(s, quote=False)


def text(x, y, s, size=13, weight=400, color=None, anchor="start", mono=False):
    fam = 'font-family="IBM Plex Mono, Consolas, Courier New, monospace"' if mono else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color or C["ink"]}" '
        f'text-anchor="{anchor}" {fam}>{esc(s)}</text>')


def line(pts, color, w=2.0, dash=None):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round"{da}/>')


def rect(x, y, w, h, fill=None, stroke=None, sw=1.6, rx=4, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill or C["box"]}" '
        f'stroke="{stroke or C["ink"]}" stroke-width="{sw}"{da}/>')


def dot(x, y, color=None):
    add(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{color or C["ink"]}"/>')


def flag(x, y, kind, up=True):
    """Power net flag at the end of a stub. kind: +5V, +24V, +3V3, GND."""
    if kind == "GND":
        # ground symbol: three shrinking bars hanging away from the stub end
        for k, half in enumerate((11, 7, 3)):
            yy = y + (-k * 4 if up else k * 4)
            add(f'<line x1="{x - half}" y1="{yy}" x2="{x + half}" y2="{yy}" stroke="{C["gnd"]}" stroke-width="2"/>')
        return
    col = {"+5V": C["p5"], "+24V": C["p24"], "+3V3": C["p33"]}[kind]
    d = -1 if up else 1
    add(f'<line x1="{x - 12}" y1="{y}" x2="{x + 12}" y2="{y}" stroke="{col}" stroke-width="2.4"/>')
    text(x, y + d * 7 + (0 if up else 10), kind, 12, 600, col, "middle", True)


# ----------------------------------------------------------------- geometry
EX, EW = 100, 240           # encoder blocks
SX, SW = 440, 140           # level shifter
BX, BW = 780, 280           # ESP32 body
DX, DW = 1220, 200          # drivers
MX, MW = 1560, 200          # motors
ROW = [200 + 100 * i for i in range(4)]       # A row of each motor, B is +40

# title
text(100, 52, "ESP32 pin-level circuit", 28, 600)
text(100, 76, f"Pin numbers are read from aislebot_esp32.ino {fw_version} when this file is generated. "
     "Shifter wiring from Bench_Test_Map.md, power from Master_Reference.md.", 14, 400, C["mute"])

# legend (colour key, meaningless in the mono copy)
lx, ly = 1180, 38
for i, (col, lab) in enumerate([] if MONO else [(C["enc"], "5 V encoder signal"), (C["p33"], "3.3 V logic"),
                                (C["p24"], "24 V motor lead"), (C["p5"], "+5V net"), (C["gnd"], "GND net")]):
    xx = lx + (i % 3) * 200
    yy = ly + (i // 3) * 24
    line([(xx, yy), (xx + 34, yy)], col, 3)
    text(xx + 44, yy + 5, lab, 13)

# ---- encoders
for i, m in enumerate(MOTORS):
    base = ROW[i]
    gtk = i < 2
    rect(EX, base - 30, EW, 90, C["fill"], C["ink"])
    text(EX + 12, base - 8, f"{m} encoder", 14, 600)
    text(EX + 12, base + 12, ("GTK08, 1000 PPR" if gtk else "RMCS-2086, 500 line"), 12, 400, C["mute"])
    text(EX + 12, base + 28, f"{int(cpr[i])} counts/rev", 12, 400, C["mute"])
    # power stubs: red wire +5V, black wire GND
    line([(EX, base), (EX - 34, base)], C["p24"], 2.6)
    flag(EX - 34, base, "+5V", up=True)
    line([(EX, base + 40), (EX - 34, base + 40)], C["gnd"], 2.6)
    flag(EX - 34, base + 40, "GND", up=False)
    for sig, yy in (("A", base), ("B", base + 40)):
        colour = WIRE[(m, sig)][0].lower()
        sw = "#FFFFFF" if MONO else {"green": "#2E9E4F", "white": "#FFFFFF", "yellow": "#E6B800"}[colour]
        add(f'<circle cx="{EX + EW - 74}" cy="{yy - 4}" r="5" fill="{sw}" stroke="{C["ink"]}" stroke-width="1"/>')
        text(EX + EW - 12, yy, f"{sig}  {colour}", 13, 500, C["ink"], "end")
        line([(EX + EW, yy), (SX, yy)], C["enc"], 2.4)
        dot(EX + EW, yy, C["enc"])

# ---- level shifter
rect(SX, 150, SW, 440, C["hw"], C["ink"], 2)
text(SX + SW / 2, 172, "8-ch level shifter", 14, 600, None, "middle")
text(SX + SW / 2, 188, "BSS138, no OE pin", 11, 400, C["mute"], "middle")
for ch in range(8):
    i, sig = divmod(ch, 2)
    yy = ROW[i] + 40 * sig
    text(SX + 10, yy + 4, f"H{ch}", 13, 500, None, "start", True)
    text(SX + SW - 10, yy + 4, f"L{ch}", 13, 500, None, "end", True)
    line([(SX + SW, yy), (BX, yy)], C["p33"], 2.4)
    dot(SX, yy, C["enc"])
    dot(SX + SW, yy, C["p33"])
# shifter power
for x, kind, lab in ((SX + 30, "+5V", "HV+"), (SX + 110, "+3V3", "LV+")):
    line([(x, 150), (x, 126)], C["p5"] if kind == "+5V" else C["p33"], 2.4)
    flag(x, 126, kind, up=True)
    text(x + 8, 144, lab, 11, 500, C["mute"], "start", True)
for x, lab in ((SX + 30, "HV−"), (SX + 110, "LV−")):
    line([(x, 590), (x, 614)], C["gnd"], 2.4)
    flag(x, 614, "GND", up=False)
    text(x, 580, lab, 11, 500, C["mute"], "middle", True)

# ---- ESP32
BY, BH = 110, 540
rect(BX, BY, BW, BH, C["hw"], C["ink"], 2.4)
text(BX + BW / 2, BY + 24, "ESP32-WROOM-32", 16, 600, None, "middle")
text(BX + BW / 2, BY + 42, "Robocraze 38-pin, CP2102", 12, 400, C["mute"], "middle")
for i, m in enumerate(MOTORS):
    base = ROW[i]
    text(BX + 12, base + 4, gp(ENC_A[i]), 13, 500, None, "start", True)
    text(BX + 12, base + 44, gp(ENC_B[i]), 13, 500, None, "start", True)
    text(BX + BW / 2 + 4, base + 24, f"PCNT {i}", 12, 600, C["enc"], "middle")
    text(BX + BW - 12, base + 4, gp(PWM[i]), 13, 500, None, "end", True)
    text(BX + BW - 12, base + 44, gp(DIR[i]), 13, 500, None, "end", True)
    dot(BX, base, C["p33"])
    dot(BX, base + 40, C["p33"])
# 3V3 and GND pins
line([(BX, 170), (BX - 40, 170)], C["p33"], 2.4)
flag(BX - 40, 170, "+3V3", up=True)
text(BX + 12, 174, "3V3", 13, 500, None, "start", True)
line([(BX, 610), (BX - 40, 610)], C["gnd"], 2.4)
flag(BX - 40, 610, "GND", up=False)
text(BX + 12, 614, "GND", 13, 500, None, "start", True)
# USB
line([(BX + BW / 2, BY + BH), (BX + BW / 2, 710)], C["ink"], 2.4)
text(BX + BW / 2 + 10, 686, "UART0: GPIO1 TXD, GPIO3 RXD", 12, 400, C["mute"])
rect(BX + 20, 710, BW - 40, 74, C["hw"], C["ink"], 2)
text(BX + BW / 2, 732, "USB to Raspberry Pi 5", 13, 600, None, "middle")
text(BX + BW / 2, 750, "/dev/esp32, 921600 baud", 12, 400, C["mute"], "middle")
text(BX + BW / 2, 768, "also powers the ESP32 today", 12, 400, C["mute"], "middle")

# ---- drivers and motors
drv = [(160, 372, "MDD20A #1", "FR + FL", "top"), (382, 582, "MDD20A #2", "RR + RL", "bottom")]
for d, (y0, y1, name, who, side) in enumerate(drv):
    rect(DX, y0, DW, y1 - y0, C["fill"], C["ink"], 2)
    cy = (ROW[2 * d] + 40 + ROW[2 * d + 1]) / 2
    text(DX + DW / 2, cy - 2, name, 14, 600, None, "middle")
    text(DX + DW / 2, cy + 14, who, 12, 400, C["mute"], "middle")
    for k in range(2):
        i = 2 * d + k
        base = ROW[i]
        for j, (pin, gpio, lab) in enumerate(((f"PWM{k + 1}", PWM[i], "PWM"), (f"DIR{k + 1}", DIR[i], "DIR"))):
            yy = base + 40 * j
            line([(BX + BW, yy), (DX, yy)], C["p33"], 2.4)
            dot(BX + BW, yy, C["p33"])
            dot(DX, yy, C["p33"])
            text(DX + 10, yy + 4, pin, 13, 500, None, "start", True)
            text((BX + BW + DX) / 2, yy - 6, f"{MOTORS[i]} {lab}", 12, 500, C["p33"], "middle")
        # outputs to the motor
        yA, yB = base, base + 20
        text(DX + DW - 10, yA + 4, f"M{k + 1}A", 13, 500, None, "end", True)
        text(DX + DW - 10, yB + 4, f"M{k + 1}B", 13, 500, None, "end", True)
        line([(DX + DW, yA), (MX, yA)], C["p24"], 2.8)
        line([(DX + DW, yB), (MX, yB)], C["gnd"], 2.8)
        rect(MX, base - 15, MW, 50, C["box"], C["ink"], 1.8)
        text(MX + 14, base + 6, f"{MOTORS[i]} motor", 14, 600)
        text(MX + 14, base + 24, "RMCS-2086, 24 V", 12, 400, C["mute"])
        text(MX + MW - 10, base + 24, f"dir sign {MSIGN[i]:+d}", 12, 600, C["mute"], "end")
    # driver logic ground
    gy = 360 if d == 0 else 570
    line([(DX, gy), (DX - 26, gy)], C["gnd"], 2.4)
    flag(DX - 26, gy, "GND", up=False)
    text(DX + 10, gy + 4, "GND", 13, 500, None, "start", True)
    # driver power
    if side == "top":
        for x, kind, lab in ((DX + 80, "+24V", "VB+"), (DX + 150, "GND", "VB−")):
            line([(x, y0), (x, y0 - 24)], C["p24"] if kind == "+24V" else C["gnd"], 2.4)
            flag(x, y0 - 24, kind, up=True)
            text(x, y0 + 15, lab, 11, 500, C["mute"], "middle", True)
    else:
        for x, kind, lab in ((DX + 80, "+24V", "VB+"), (DX + 150, "GND", "VB−")):
            line([(x, y1), (x, y1 + 24)], C["p24"] if kind == "+24V" else C["gnd"], 2.4)
            flag(x, y1 + 24, kind, up=False)
            text(x, y1 - 6, lab, 11, 500, C["mute"], "middle", True)

# ---- nets and notes
nx, ny = 100, 700
rect(nx, ny, 620, 266, C["fill"], C["rule"], 1.4, 4, "6 4")
text(nx + 14, ny + 24, "Where each net comes from", 14, 600)
nets = [("+5V", C["p5"], "DFRobot 60 W buck, 12.8 V in", "shifter HV+, all four encoder Red wires"),
        ("+24V", C["p24"], "1200 W boost, 12.8 V in", "both MDD20A VB+ and VB−"),
        ("+3V3", C["p33"], "ESP32 3V3 pin, on-board regulator", "shifter LV+"),
        ("GND", C["gnd"], "one common bus, no daisy chain", "ESP32, buck, boost, both MDD20A logic GND,")]
for k, (n, col, src, to) in enumerate(nets):
    yy = ny + 58 + k * 44
    text(nx + 14, yy, n, 14, 600, col, "start", True)
    text(nx + 80, yy, src, 13, 500)
    text(nx + 80, yy + 17, "to " + to if n != "GND" else to, 12, 400, C["mute"])
text(nx + 80, ny + 58 + 3 * 44 + 33, "shifter LV− and HV−, all four encoder Black wires", 12, 400, C["mute"])
text(nx + 14, ny + 252, "The Pi ground reaches the ESP32 ground through the USB cable.", 12, 400, C["mute"])

mx, my = 1220, 700
rect(mx, my, 540, 266, C["fill"], C["rule"], 1.4, 4, "6 4")
text(mx + 14, my + 24, "Read before wiring", 14, 600)
notes = [
    "* GPIO 34, 35, 36, 39 are input-only, with no internal pull-ups.",
    "No strapping pins (0, 2, 5, 12, 15) and no flash pins (6 to 11) are used.",
    f"MOTOR_DIR_SIGN = ENC_DIR_SIGN = {{{', '.join(f'{v:+d}' for v in MSIGN)}}} for FR, FL, RR, RL.",
    "They must match per motor, or the PID loop runs away.",
    "Front encoders (GTK08): Green is A, White is B. Rear (RMCS-2086):",
    "Yellow is A, Green is B. Check the wire, not the table.",
    "Motor leads: Red to MxA, Black to MxB on all four motors.",
    "VIN from the 5 V buck is a roadmap item, not done.",
]
for k, s in enumerate(notes):
    text(mx + 14, my + 52 + k * 22, s, 13, 400)

text(100, 996, "Not checked against the physical robot. Drawn from the firmware and the repo wiring docs.", 12, 400, C["mute"])

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="IBM Plex Sans, Segoe UI, Arial, sans-serif" role="img" '
       f'aria-label="ESP32 pin-level circuit: encoders through an 8-channel level shifter to GPIO 36, 39, 34, 35, 32, 33, 25, 26, '
       f'and GPIO 4, 16, 17, 18, 19, 21, 22, 23 to two MDD20A drivers and four motors">'
       f'<title>ESP32 pin-level circuit</title><rect width="{W}" height="{H}" fill="#FFFFFF"/>' + "".join(out) + "</svg>")
OUT.write_text(svg, encoding="utf-8")
print("wrote", OUT.relative_to(ROOT))
print("pins from firmware:", dict(PWM=PWM, DIR=DIR, ENC_A=ENC_A, ENC_B=ENC_B, sign=MSIGN))
