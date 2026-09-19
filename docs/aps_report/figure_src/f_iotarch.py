"""Environmental monitoring and control architecture.

Every part number, port, cadence and route here is taken from the project
report for that system rather than from an earlier sketch of it. Four things
the earlier hand-drawn version had wrong are corrected: the broker carries the
Wi-Fi telemetry only, the long-range radio reaches the database through its own
service, the cellular link is bidirectional rather than outbound, and there are
two dashboard control endpoints rather than one.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *

fig, ax = canvas(13.4, 8.4, 100, 66)

title(ax, 0.5, 65.6,
      'Environmental monitoring and control architecture',
      'Five sensing devices and two actuators on one edge node, three communication channels that run at the same\n'
      'time rather than as a failover chain, and a local server with no cloud dependency. Each channel has its own route.')

# ── columns ──────────────────────────────────────────────────────────
band(ax, 0.5, 8.5, 31.0, 44.5, '', 'tel')
head(ax, 0.5, 47.0, 31.0, 6.0, 'EDGE NODE', 'tel',
     sub='Arduino UNO R4 WiFi (Renesas RA4M1)\nfive sensing devices, two actuators')

band(ax, 36.0, 8.5, 25.5, 44.5, '', 'note')
head(ax, 36.0, 47.0, 25.5, 6.0, 'TRANSPORT', 'note',
     sub='three channels, concurrent\nrather than failover')

band(ax, 65.5, 8.5, 33.5, 44.5, '', 'new')
head(ax, 65.5, 47.0, 33.5, 6.0, 'LOCAL SERVER', 'new',
     sub='Raspberry Pi 5, Docker\nfour zones, one database')

# ── edge node ────────────────────────────────────────────────────────
S, X = 23.5, 6.8
s1 = box(ax, X, 42.2, S, 4.0, r'CO$_2$ 400–5000 ppm, temperature, RH', 'tel',
         fs=7.6, hdr='SCD40   I²C 0x62')
s2 = box(ax, X, 37.6, S, 4.0, 'PM2.5 and PM10, µg/m³', 'tel', fs=7.6,
         hdr='MPM10-AS   I²C 0x4D')
s3 = box(ax, X, 33.0, S, 4.0, 'gas index 0–500, plus a threshold flag', 'tel',
         fs=7.6, hdr='MQ-135   A0 + D2')
s4 = box(ax, X, 28.4, S, 4.0, '240–370 nm photodiode', 'bad', fc='bad', fs=7.6,
         hdr='GUVA-S12SD   A1', tc=P['bad'])
s5 = box(ax, X, 23.8, S, 4.0, 'eight rotating status screens', 'tel', fs=7.6,
         hdr='LCD1602   I²C 0x27')

ax.plot([5.6, 30.6], [22.2, 22.2], color=P['grey'], lw=0.8, ls=':', zorder=3)

a1 = box(ax, X, 17.4, S, 4.0, 'switches the UV-C lamp mains', 'cmd', fc='cmd',
         fs=7.6, hdr='Opto-isolated relay   D9')
a2 = box(ax, X, 12.8, S, 4.0, 'speed command out, tachometer back', 'cmd',
         fc='cmd', fs=7.6, hdr='120 mm 4-pin fan   PWM D6, tach D3')

for y0, y1, lab, yl in ((23.8, 46.2, 'Sensing\n(I²C and\nanalogue)', 35.0),
                        (12.8, 21.4, 'Actuators\n(one with\nfeedback)', 17.1)):
    ax.plot([5.6, 5.6], [y0 + 2.0, y1 - 2.0], color=P['grey'], lw=0.9, zorder=3)
    ax.text(4.8, yl, lab, ha='right', va='center', fontsize=7.6,
            color='#333333', zorder=5, linespacing=1.45)
for b in (s1, s2, s3, s4, s5, a1, a2):
    ax.plot([5.6, b[0]], [b[1] + b[3] / 2] * 2, color=P['grey'], lw=0.9, zorder=3)

caveat(ax, 16.0, 11.3,
       'The ultraviolet channel is reported in mW/cm² with its responsivity\n'
       'coefficient still set to 1, so the figure is a voltage relabelled.',
       fs=7.4, ha='center')

# ── transport ────────────────────────────────────────────────────────
c1 = box(ax, 37.3, 40.0, 22.9, 6.0, 'full JSON, canonical keys', 'note',
         fc='note', fs=7.8, hdr=r'1.  Wi-Fi $\rightarrow$ MQTT,  every 5 s', hfs=8.2)
c2 = box(ax, 37.3, 29.5, 22.9, 8.6,
         'abbreviated JSON, ≤240 B\n'
         r'RYLR998 $\rightarrow$ UNO R4 Minima gateway' '\n'
         '9600 baud UART into the Pi\nSF9, BW 125 kHz, CR 4/5, preamble 12',
         'note', fc='note', fs=7.5, hdr=r'2.  LoRa,  every 30 s', hfs=8.2)
c3 = box(ax, 37.3, 19.5, 22.9, 8.0,
         'Quectel EC200U, plain text\nalerts and a summary out,\ncommands in from a handset',
         'note', fc='note', fs=7.6,
         hdr='3.  Cellular SMS,  on alert + 30 min', hfs=8.0)
ax.text(48.7, 15.4,
        'A failover chain has to detect failure before it\n'
        'can switch, and detection is the first thing to\nfail in a dead network.',
        ha='center', va='center', fontsize=7.5, color=P['note'], zorder=5,
        linespacing=1.5)

# ── server ───────────────────────────────────────────────────────────
v1 = box(ax, 67.0, 41.6, 30.5, 4.0, 'MQTT broker, the Wi-Fi telemetry only',
         'new', fs=7.6, hdr='Mosquitto   :1883')
v2 = box(ax, 67.0, 34.0, 14.6, 6.0,
         'systemd, not in a\ncontainer; LoRa ingest\nand command injection',
         'new', fs=7.4, hdr='Gateway service   :5000')
v3 = box(ax, 82.9, 34.0, 14.6, 6.0,
         'ingestion pipeline and\nthe MQTT control\nendpoint', 'new', fs=7.4,
         hdr='Node-RED   :1880')
v4 = box(ax, 67.0, 27.0, 30.5, 4.6,
         'one schema for both transports, distinguished by a source tag',
         'new', fs=7.6, hdr='InfluxDB 2.x   :8086 in the container, :8087 on the host')
v5 = box(ax, 67.0, 20.0, 30.5, 4.6, '23 panels, per-zone templating, in-panel controls',
         'new', fs=7.6, hdr='Grafana   :3000')
v6 = box(ax, 67.0, 13.0, 30.5, 4.6,
         'the same command vocabulary on every channel', 'cmd', fc='cmd',
         fs=7.6, hdr='Operator controls, over MQTT or over LoRa')

# ── telemetry wiring ─────────────────────────────────────────────────
ax.plot([31.9, 31.9], [24.4, 44.2], color=P['tel'], lw=1.3, zorder=4)
for b in (s1, s2, s3, s4):
    ax.plot([b[0] + b[2], 31.9], [b[1] + b[3] / 2] * 2, color=P['tel'], lw=1.0, zorder=4)
for b, yy in ((c1, 43.0), (c2, 33.8), (c3, 24.4)):
    arr(ax, (31.9, yy), (b[0], yy), 'tel', lw=1.2)

arr(ax, R(c1), (67.0, 43.6), 'tel')
route(ax, [R(c2), (63.8, 33.8), (63.8, 37.0), (67.0, 37.0)], 'tel')
arr(ax, (74.3, 41.6), (74.3, 40.0), 'tel', lw=1.2)
arr(ax, (90.2, 41.6), (90.2, 40.0), 'tel', lw=1.2)
arr(ax, (74.3, 34.0), (74.3, 31.6), 'tel', lw=1.2)
arr(ax, (90.2, 34.0), (90.2, 31.6), 'tel', lw=1.2)
arr(ax, B(v4), T(v5), 'tel', lw=1.2)
arr(ax, B(v5), T(v6), 'tel', lw=1.2)

# ── the two dashboard control paths, and the SMS one ─────────────────
route(ax, [L(v6), (64.6, 15.3), (64.6, 7.0), (34.0, 7.0), (34.0, 19.4),
           (a1[0] + a1[2], 19.4)], 'cmd')
ax.plot([34.0, 34.0], [7.0, 14.8], color=P['cmd'], lw=1.4, zorder=6)
arr(ax, (34.0, 14.8), (a2[0] + a2[2], 14.8), 'cmd')
ax.text(49.3, 7.0, 'operator commands, over MQTT or over LoRa', ha='center',
        va='center', fontsize=7.6, color=P['cmd'], zorder=8,
        bbox=dict(fc='white', ec='none', pad=0.2))
arr(ax, (37.3, 22.2), (32.6, 22.2), 'cmd', lw=1.2)
ax.text(34.9, 21.4, 'SMS commands', ha='center', va='top', fontsize=7.0,
        color=P['cmd'], zorder=8)

# ── zones and legend ─────────────────────────────────────────────────
summ(ax, 0.5, 0.8, 46.0, 5.0,
     'Two models, four zones, one database. Model A is network 18 at 915 MHz and\n'
     'serves zones 1 and 2; Model B is network 19 at 868 MHz and serves zones 3 and 4.\n'
     'Model B writes into Model A’s database, so one set of dashboards covers both.',
     'grey', fs=7.6)
legend(ax, 51.0, 0.8, 48.0, 5.0,
       [('tel', 'Sensor data and telemetry (edge $\\rightarrow$ server)', '-'),
        ('cmd', 'Actuator command (server or handset $\\rightarrow$ edge)', '-')])

save(fig, 'fig34_iot_architecture.png')
