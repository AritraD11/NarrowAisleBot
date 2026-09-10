"""Generate the NarrowAisleBot deployed-electronics circuit diagram as SVG.

Every part, pin, rail and baud rate below is taken from the repo's own
hardware documentation, not from memory:

  docs/Master_Reference.md  2.3, 2.5, 3.1, 3.2, 4.1, 4.2, 4.3
  docs/Bench_Test_Map.md    "Discrete MOSFET board wiring",
                            "Full 8-channel wiring - all four encoders"
  docs/RMCS-2086_Encoder_Replacement.md
  README.md                 hardware table

Two documented facts that a generic mecanum-robot diagram would get wrong,
and which this one shows explicitly:

  1. The two FRONT motors no longer use their integrated RMCS-2086 encoders
     (those failed). They run GTK08 units, whose A/B wire colours differ from
     the rear RMCS-2086 encoders. Bench_Test_Map.md flags this as having
     already corrupted a channel once.
  2. The TXS0108E level shifter described in Master_Reference 4.4 is RETIRED.
     Deployed hardware is an 8-channel discrete-MOSFET (BSS138-style) board
     with LV+/LV-/HV+/HV- rails and no OE pin.
"""
import re
import subprocess
from pathlib import Path

OUT = Path("docs/hardware/nab_circuit_diagram.svg")
PNG = Path("docs/hardware/nab_circuit_diagram.png")

W, H = 1780, 1310

# Voltage-domain colours, used consistently for every wire and rail.
C_BATT = "#7B1E1E"   # 12.8 V raw battery
C_24 = "#D32F2F"     # 24 V motor rail
C_5 = "#EF6C00"      # 5 V logic / encoder rail
C_33 = "#1565C0"     # 3.3 V ESP32 domain
C_SIG = "#37474F"    # serial / USB data
C_ENC = "#6A1B9A"    # encoder quadrature signals
C_GND = "#212121"
C_BOX = "#FFFFFF"
C_EDGE = "#455A64"
C_INK = "#17202A"
C_MUTE = "#5D6D7E"
C_WARN = "#B71C1C"

s = []
add = s.append

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="DejaVu Sans, Arial, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

# arrowheads, one per colour
add("<defs>")
for name, col in [("b", C_BATT), ("v24", C_24), ("v5", C_5), ("v33", C_33),
                  ("sig", C_SIG), ("enc", C_ENC)]:
    add(f'<marker id="a_{name}" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
add("</defs>")


def box(x, y, w, h, title, lines, accent=C_EDGE, fill=C_BOX, ts=15, ls=11.5):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" '
        f'stroke="{accent}" stroke-width="2"/>')
    add(f'<rect x="{x}" y="{y}" width="{w}" height="5" rx="2.5" fill="{accent}"/>')
    add(f'<text x="{x+w/2}" y="{y+24}" font-size="{ts}" font-weight="bold" '
        f'fill="{C_INK}" text-anchor="middle">{title}</text>')
    for i, ln in enumerate(lines):
        add(f'<text x="{x+w/2}" y="{y+43+i*15}" font-size="{ls}" fill="{C_MUTE}" '
            f'text-anchor="middle">{ln}</text>')


def wire(pts, col, marker=None, width=2.6, dash=None):
    d = "M " + " L ".join(f"{x},{y}" for x, y in pts)
    m = f' marker-end="url(#a_{marker})"' if marker else ""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{width}" '
        f'stroke-linejoin="round"{da}{m}/>')


def vislen(t):
    """Rendered glyph count. Entities like &#8594; and <tspan> markup are one
    glyph or none, so len() on the raw string badly overestimates and the
    white label backing then paints over neighbouring text."""
    t = re.sub(r"<[^>]*>", "", t)
    t = re.sub(r"&(#\d+|[A-Za-z]+);", "x", t)
    return len(t)


def tag(x, y, text, col, size=11, anchor="middle", bold=True, bg=True):
    if bg:
        wpx = vislen(text) * size * 0.60 + 10
        add(f'<rect x="{x-wpx/2 if anchor=="middle" else x-5}" y="{y-size+1}" '
            f'width="{wpx}" height="{size+7}" rx="3" fill="#FFFFFF" opacity="0.95"/>')
    fw = "bold" if bold else "normal"
    add(f'<text x="{x}" y="{y+3}" font-size="{size}" font-weight="{fw}" '
        f'fill="{col}" text-anchor="{anchor}">{text}</text>')


def band(x, y, w, h, label, col):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="none" '
        f'stroke="{col}" stroke-width="1.4" stroke-dasharray="7 6" opacity="0.55"/>')
    add(f'<text x="{x+14}" y="{y+21}" font-size="13" font-weight="bold" '
        f'fill="{col}" opacity="0.85" letter-spacing="1.5">{label}</text>')


# ----------------------------------------------------------------- title
add(f'<text x="40" y="46" font-size="27" font-weight="bold" fill="{C_INK}">'
    f'NarrowAisleBot &#8212; deployed electronics</text>')
add(f'<text x="40" y="70" font-size="13.5" fill="{C_MUTE}">'
    f'Base chassis power distribution, drive control and odometry feedback. '
    f'Pin assignments per Master_Reference.md &#167;4 and Bench_Test_Map.md.</text>')

# legend
lx = 1180
add(f'<text x="{lx}" y="34" font-size="11.5" font-weight="bold" fill="{C_INK}">RAILS</text>')
for i, (col, txt) in enumerate([(C_BATT, "12.8 V battery"), (C_24, "24 V motor"),
                                (C_5, "5 V logic"), (C_33, "3.3 V ESP32"),
                                (C_SIG, "USB / serial"), (C_ENC, "encoder A/B")]):
    cx = lx + (i % 3) * 200
    cy = 52 + (i // 3) * 19
    add(f'<line x1="{cx}" y1="{cy}" x2="{cx+26}" y2="{cy}" stroke="{col}" stroke-width="3.4"/>')
    add(f'<text x="{cx+33}" y="{cy+4}" font-size="11.5" fill="{C_MUTE}">{txt}</text>')

# =====================================================================
# POWER BAND
# =====================================================================
band(30, 100, 1720, 300, "POWER DISTRIBUTION", C_BATT)

box(52, 150, 196, 104, "LiFePO&#8324; battery",
    ["SM12830SL", "12.8 V &#183; 30 Ah &#183; 384 Wh"], C_BATT)
box(310, 158, 150, 88, "SSR-50DD", ["solid state relay", "50 A &#183; 3&#8211;32 V trig"], C_BATT)

box(524, 118, 208, 80, "Boost converter", ["1200 W DC-DC", "12.8 V &#8594; 24 V"], C_24)
box(524, 218, 208, 80, "Buck converter", ["DFRobot 60 W", "12.8 V &#8594; 5 V"], C_5)
box(524, 318, 208, 66, "Pi 5 PSU", ["5 V supply"], C_5)

# battery -> SSR -> converters
wire([(248, 202), (306, 202)], C_BATT, "b")
wire([(460, 202), (492, 202), (492, 158), (520, 158)], C_BATT, "b")
wire([(460, 202), (492, 202), (492, 258), (520, 258)], C_BATT, "b")
wire([(492, 258), (492, 351), (520, 351)], C_BATT, "b")
tag(486, 130, "12.8 V", C_BATT)


def stub(x, y, text, col, direction="right"):
    """Labelled off-page rail connector, so power rails don't snake across
    the whole sheet to reach their consumers."""
    dx = 26 if direction == "right" else -26
    add(f'<path d="M {x},{y} L {x+dx},{y}" stroke="{col}" stroke-width="3.2" '
        f'fill="none" marker-end="url(#a_{"v24" if col == C_24 else "v5"})"/>')
    add(f'<circle cx="{x+dx*1.5}" cy="{y}" r="7" fill="#FFFFFF" stroke="{col}" '
        f'stroke-width="2.4"/>')
    ax = "start" if direction == "right" else "end"
    add(f'<text x="{x+dx*2.2}" y="{y+4}" font-size="11.5" font-weight="bold" '
        f'fill="{col}" text-anchor="{ax}">{text}</text>')


# 24 V and 5 V leave the power band as labelled rails and re-enter where used.
wire([(732, 158), (1150, 158)], C_24, None, 3.2)
tag(940, 148, "24 V rail", C_24)
stub(1150, 158, "A &#8594; both MDD20A VB+/VB&#8722;", C_24)

wire([(732, 258), (1150, 258)], C_5, None, 3.2)
tag(940, 248, "5 V rail", C_5)
stub(1150, 258, "B &#8594; 4&#215; encoder V<tspan font-size='8'>CC</tspan> &#183; shifter HV+", C_5)

# =====================================================================
# COMPUTE BAND
# =====================================================================
band(30, 420, 1720, 250, "COMPUTE &amp; COMMAND", C_SIG)

box(120, 452, 250, 152, "Raspberry Pi 5",
    ["Ubuntu 24.04 &#183; ROS 2 Jazzy", "8 GB &#183; Nav2 / slam_toolbox",
     "mecanum_teleop_asymmetric", "esp32_bridge &#183; scan_relay"], C_SIG)

box(520, 452, 236, 96, "YDLIDAR X4 Pro",
    ["/dev/ydlidar &#183; 128000 bd", "~430 pts @ ~11.35 Hz"], C_SIG)
box(520, 570, 236, 84, "Arduino Mega 2560",
    ["/dev/mega &#183; 115200 bd", "arm + UV lighting (v8)"], C_SIG)

box(880, 452, 250, 152, "ESP32-WROOM-32",
    ["/dev/esp32 &#183; 921600 bd", "hardware PCNT quadrature",
     "PID @ 50 Hz &#183; Kp50 Ki30 Kd3", "AMS1117 &#8594; 3.3 V domain"], C_33)

# Pi <-> peripherals
wire([(370, 500), (520, 500)], C_SIG, "sig")
tag(445, 490, "USB", C_SIG)
wire([(370, 560), (446, 560), (446, 612), (520, 612)], C_SIG, "sig")
tag(446, 640, "USB", C_SIG)
wire([(370, 528), (760, 528), (760, 528), (880, 528)], C_SIG)
add(f'<path d="M 756,528 L 880,528" fill="none" stroke="{C_SIG}" stroke-width="2.6" '
    f'marker-end="url(#a_sig)" marker-start="url(#a_sig)"/>')
tag(818, 518, "USB serial 921600", C_SIG)
tag(818, 546, "&#60;V,fr,fl,rr,rl&#62; / CSV telemetry", C_MUTE, 10, bold=False)

# Pi power in
wire([(628, 384), (628, 416), (245, 416), (245, 448)], C_5, "v5")
tag(430, 406, "5 V", C_5)

# 3.3 V out of ESP32 down to shifter LV+
wire([(1005, 604), (1005, 648)], C_33)
tag(1050, 630, "3.3 V &#8594; shifter LV+", C_33, 11)

# =====================================================================
# DRIVE BAND
# =====================================================================
band(30, 690, 1720, 470, "DRIVE &amp; ODOMETRY FEEDBACK", C_24)

# --- motor drivers
box(300, 726, 216, 96, "Cytron MDD20A #1",
    ["20 A cont. &#183; 6&#8211;30 V", "FR + FL"], C_24)
box(300, 852, 216, 96, "Cytron MDD20A #2",
    ["20 A cont. &#183; 6&#8211;30 V", "RR + RL"], C_24)

# --- motors
motors = [("FR", 726, "G4", "G16", "PCNT_0", "36 / 39", "&#8722;1"),
          ("FL", 806, "G17", "G18", "PCNT_1", "34 / 35", "+1"),
          ("RR", 886, "G19", "G21", "PCNT_2", "32 / 33", "&#8722;1"),
          ("RL", 966, "G22", "G23", "PCNT_3", "25 / 26", "+1")]

for name, y, pwm, dr, pcnt, gpio, sign in motors:
    box(64, y, 190, 62, f"Motor {name}",
        ["Rhino RMCS-2086", "24 V &#183; 60 RPM &#183; 1:47"], C_24, ts=13.5, ls=10)

# 24 V arrives at both drivers from rail A
add(f'<circle cx="586" cy="742" r="9" fill="#FFFFFF" stroke="{C_24}" stroke-width="2.4"/>')
add(f'<text x="586" y="746" font-size="11" font-weight="bold" fill="{C_24}" '
    f'text-anchor="middle">A</text>')
wire([(577, 742), (540, 742), (540, 762), (520, 762)], C_24, "v24")
wire([(540, 742), (540, 888), (520, 888)], C_24, "v24")
tag(600, 722, "24 V &#8594; VB+/VB&#8722;", C_24, 10.5, anchor="start")

# drivers -> motors
wire([(300, 762), (276, 762), (276, 757), (258, 757)], C_24, "v24")
wire([(300, 786), (276, 786), (276, 837), (258, 837)], C_24, "v24")
wire([(300, 888), (276, 888), (276, 917), (258, 917)], C_24, "v24")
wire([(300, 912), (276, 912), (276, 997), (258, 997)], C_24, "v24")
add(f'<text x="330" y="1204" font-size="10.5" fill="{C_MUTE}">'
    f'Motor leads: Red &#8594; MxA, Black &#8594; MxB, identical on all four. '
    f'Left/right direction handled in firmware via MOTOR_DIR_SIGN[].</text>')

# --- ESP32 GPIO -> drivers  (PWM/DIR, no level shifting needed)
box(660, 726, 200, 96, "PWM + DIR",
    ["3.3 V direct &#8212; MDD20A", "logic threshold 1.5 V", "no shifting required"],
    C_33, ts=13.5, ls=10)
wire([(980, 604), (980, 660), (760, 660), (760, 726)], C_33, "v33")
wire([(660, 774), (516, 774)], C_33, "v33")
wire([(660, 790), (580, 790), (580, 900), (516, 900)], C_33, "v33")

gp = [("FR", "G4 / G16", 745), ("FL", "G17 / G18", 761),
      ("RR", "G19 / G21", 777), ("RL", "G22 / G23", 793)]
for i, (nm, pins, yy) in enumerate(gp):
    add(f'<text x="1160" y="{745+i*17}" font-size="11.5" fill="{C_INK}">'
        f'<tspan font-weight="bold">{nm}</tspan>  PWM/DIR = {pins}</text>')
add(f'<text x="1160" y="726" font-size="12" font-weight="bold" fill="{C_33}">'
    f'ESP32 &#8594; driver pins</text>')

# --- level shifter
box(660, 900, 200, 116, "8-ch level shifter",
    ["discrete MOSFET", "(BSS138-style, no OE)",
     "LV+ 3.3 V &#183; HV+ 5 V", "H0&#8211;H7 / L0&#8211;L7"], C_ENC, ts=13.5, ls=10)
wire([(1005, 648), (1005, 880), (860, 880), (860, 900)], C_33)

# encoders -> shifter -> ESP32
box(64, 1046, 190, 84, "Encoders &#215;4",
    ["front FR/FL: GTK08", "rear RR/RL: RMCS-2086", "5 V quadrature"], C_ENC, ts=13.5, ls=10)


def arrive(cx, cy, target, col, letter, note):
    """Rail arriving from an off-page stub of the same letter."""
    add(f'<circle cx="{cx}" cy="{cy}" r="9" fill="#FFFFFF" stroke="{col}" stroke-width="2.4"/>')
    add(f'<text x="{cx}" y="{cy+4}" font-size="11" font-weight="bold" fill="{col}" '
        f'text-anchor="middle">{letter}</text>')
    wire([(cx, cy + 9), target], col, "v5" if col == C_5 else "v24")
    add(f'<text x="{cx+15}" y="{cy+4}" font-size="10.5" font-weight="bold" '
        f'fill="{col}">{note}</text>')


arrive(159, 1176, (159, 1130), C_5, "B", "5 V &#8594; encoder V<tspan font-size='8'>CC</tspan>")
arrive(700, 862, (700, 900), C_5, "B", "5 V &#8594; HV+")
wire([(254, 1088), (600, 1088), (600, 990), (660, 990)], C_ENC, "enc")
tag(430, 1078, "8 &#215; A/B @ 5 V", C_ENC)
wire([(860, 958), (940, 958), (940, 604)], C_ENC, "enc")
tag(945, 700, "8 &#215; A/B @ 3.3 V", C_ENC, 11, anchor="start")

# encoder channel map table
tx, ty = 1160, 830
add(f'<text x="{tx}" y="{ty}" font-size="12" font-weight="bold" fill="{C_ENC}">'
    f'Encoder channel map</text>')
rows = [("FR", "Green/White", "H0/H1", "L0/L1", "36 / 39", "PCNT_0", "&#8722;1"),
        ("FL", "Green/White", "H2/H3", "L2/L3", "34 / 35", "PCNT_1", "+1"),
        ("RR", "Yellow/Green", "H4/H5", "L4/L5", "32 / 33", "PCNT_2", "&#8722;1"),
        ("RL", "Yellow/Green", "H6/H7", "L6/L7", "25 / 26", "PCNT_3", "+1")]
hdr = ("", "A / B wire", "5 V", "3.3 V", "GPIO", "unit", "dir")
colx = [0, 34, 130, 178, 228, 292, 352]
add(f'<text x="{tx}" y="{ty+20}" font-size="10.5" fill="{C_MUTE}">' +
    "".join(f'<tspan x="{tx+colx[i]}">{h}</tspan>' for i, h in enumerate(hdr)) + '</text>')
BOLD = ' font-weight="bold"'
for r, row in enumerate(rows):
    yy = ty + 38 + r * 17
    cells = "".join(
        '<tspan x="{}"{}>{}</tspan>'.format(tx + colx[i], BOLD if i == 0 else "", c)
        for i, c in enumerate(row))
    add(f'<text y="{yy}" font-size="11" fill="{C_INK}">{cells}</text>')
add(f'<text x="{tx}" y="{ty+122}" font-size="10.5" fill="{C_WARN}">'
    f'Front and rear encoders use different A/B wire colours.</text>')
add(f'<text x="{tx}" y="{ty+137}" font-size="10.5" fill="{C_WARN}">'
    f'Verify against the physical wire, not memory.</text>')

# =====================================================================
# GROUND BUS
# =====================================================================
gy = 1258
wire([(60, gy), (1720, gy)], C_GND, None, 4.2)
add(f'<text x="60" y="{gy-14}" font-size="13" font-weight="bold" fill="{C_GND}">'
    f'COMMON GROUND BUS</text>')
add(f'<text x="300" y="{gy-14}" font-size="11.5" fill="{C_WARN}">'
    f'ESP32 GND &#183; boost GND &#183; buck GND &#183; both MDD20A logic GND &#183; '
    f'shifter LV&#8722;/HV&#8722; &#183; all 4 encoder Black &#8212; '
    f'every one of these on a single rail.</text>')
add(f'<text x="60" y="{gy+26}" font-size="11" fill="{C_MUTE}">'
    f'Missing any one of these connections produces phantom motor behaviour '
    f'(Master_Reference.md &#167;3.2). Pi GND reaches ESP32 GND through the USB cable.</text>')
for x in (150, 430, 700, 990, 1270, 1560):
    add(f'<line x1="{x}" y1="{gy-9}" x2="{x}" y2="{gy}" stroke="{C_GND}" stroke-width="2.2"/>')

# deployment note
add(f'<rect x="1160" y="452" width="560" height="96" rx="7" fill="#FFF8E1" '
    f'stroke="{C_WARN}" stroke-width="1.6"/>')
add(f'<text x="1178" y="475" font-size="12.5" font-weight="bold" fill="{C_WARN}">'
    f'Deployment note &#8212; ESP32 supply</text>')
for i, ln in enumerate([
        "Powering the ESP32 from Pi USB couples SMPS switching noise and",
        "PWM ground transients into the encoder counts. For deployment, cut",
        "VBUS in the Pi&#8594;ESP32 cable and feed VIN from the 5 V buck instead."]):
    add(f'<text x="1178" y="{494+i*16}" font-size="11" fill="{C_MUTE}">{ln}</text>')

add("</svg>")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(s))
print("wrote", OUT)

# Chromium applies a default body margin to a bare .svg document, which pushes
# the bottom of the canvas outside the screenshot viewport. Render through a
# zero-margin HTML wrapper so the full sheet is captured.
wrapper = OUT.with_suffix(".render.html")
wrapper.write_text(
    f'<!doctype html><meta charset="utf-8">'
    f'<style>html,body{{margin:0;padding:0;background:#fff}}'
    f'svg{{display:block}}</style>{OUT.read_text()}')

# The headless viewport comes out shorter than --window-size, so the bottom of
# the sheet lands below the fold. Render with slack, then crop to the real canvas.
SLACK = 200
chrome = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu",
                "--hide-scrollbars", "--force-device-scale-factor=2",
                f"--window-size={W},{H + SLACK}",
                f"--screenshot={PNG}", f"file://{wrapper.resolve()}"],
               check=True, capture_output=True)
wrapper.unlink()

from PIL import Image  # noqa: E402
shot = Image.open(PNG)
shot.crop((0, 0, W * 2, H * 2)).save(PNG)

import numpy as np  # noqa: E402
a = np.asarray(Image.open(PNG).convert("RGB")).astype(int)
rows = np.where((a.mean(axis=2) < 245).sum(axis=1) > 3)[0]
print(f"wrote {PNG}  content rows {rows.min()}..{rows.max()} of {H*2}")
assert rows.max() >= (gy + 20) * 2, (
    f"clipped: lowest drawn element is the ground-bus note at y={gy+26}, "
    f"but content stops at y={rows.max()/2}")
