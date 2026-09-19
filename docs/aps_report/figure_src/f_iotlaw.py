"""The actuation law as the deployed firmware implements it, and the defects a
source-level audit of that firmware found.

Panel (b) is the verified register rather than an earlier summary of it. One
entry in circulation was wrong and is not repeated here: the fan tachometer
calculation does divide by its sample window, and the residual error is a small
high bias from loop latency rather than a gross over-read.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mp

fig = plt.figure(figsize=(13.2, 5.6))
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.22], wspace=0.16,
                      left=0.055, right=0.985, top=0.775, bottom=0.135)

# ── (a) the law ──────────────────────────────────────────────────────
ax = fig.add_subplot(gs[0, 0])
idx = np.linspace(0, 600, 2400)
fan = np.where(idx < 200, 0.0, np.clip(128 + (255 - 128) * (idx - 200) / 300, 0, 255))
ax.axvspan(150, 200, color=P['cmd'], alpha=0.14, zorder=1)
ax.plot(idx, fan, color=P['tel'], lw=2.2, zorder=4, solid_capstyle='round')
ax.axvline(150, color=P['new'], ls='--', lw=1.1, zorder=3)
ax.axvline(200, color=P['bad'], ls='--', lw=1.1, zorder=3)
ax.plot([143], [0], 'o', ms=7, mfc=P['new'], mec='white', mew=1.2, zorder=6)
ax.annotate('dashboard capture:\nindex 143, lamp off',
            xy=(143, 0), xytext=(250, 46), fontsize=8.2, color=P['new'],
            zorder=7, linespacing=1.4,
            arrowprops=dict(arrowstyle='-', color=P['new'], lw=0.9))
ax.text(175, 244, 'hysteresis\ndead band', ha='center', va='top', fontsize=8.2,
        color='#7a3e00', zorder=7, linespacing=1.4,
        bbox=dict(fc='white', ec='none', pad=0.2))
ax.text(146, 118, 'lamp OFF below 150', rotation=90, ha='right', va='center',
        fontsize=8.0, color=P['new'], zorder=7)
ax.text(204, 118, 'lamp ON above 200', rotation=90, ha='left', va='center',
        fontsize=8.0, color=P['bad'], zorder=7)
ax.set_xlim(0, 600)
ax.set_ylim(-14, 272)
ax.set_xlabel('MQ-135 gas index  (rescaled ADC count, uncalibrated)', fontsize=9)
ax.set_ylabel('fan command  (0–255)', fontsize=9)
ax.set_title('(a)  The control law as implemented', fontsize=10.5,
             fontweight='bold', loc='left', pad=8)
ax.tick_params(labelsize=8.4)
for sp in ('top', 'right'):
    ax.spines[sp].set_visible(False)
ax.grid(alpha=0.22, lw=0.6)
fig.text(0.055, 0.035,
         'Alerts fire on a bare threshold with no dead band, on all three channels at once: '
         r'38 °C  ·  1200 ppm CO$_2$  ·  gas index 200  ·  55 µg/m³ PM2.5.',
         ha='left', va='bottom', fontsize=8.2, color=P['bad'])

# ── (b) the register ─────────────────────────────────────────────────
bx = fig.add_subplot(gs[0, 1])
bx.set_xlim(0, 100)
bx.set_ylim(0, 100)
bx.axis('off')
bx.set_title('(b)  What a source-level audit of the firmware found',
             fontsize=10.5, fontweight='bold', loc='left', pad=8)

ITEMS = [
    ('The gas index is not an air quality index',
     'a linear rescale of a raw analogue count; a calibration runs at\nboot and its result is never used'),
    ('Ultraviolet irradiance is uncalibrated',
     'reported in mW/cm² with the responsivity coefficient still at 1,\nso the number is a voltage relabelled'),
    ('Lamp-failure detection is not implemented',
     'irradiance reaches the display and both payloads; nothing acts\non it, so a dead lamp raises nothing'),
    ('An operator off-command does not clear automatic mode',
     'LIGHT OFF and FAN OFF actuate, then the closed loop reverts\nthem on its next pass'),
    ('The alert path has no dead band while the control path does',
     'a reading sitting near a threshold flaps, and each transition\nsends a message'),
    ('The cellular inbox poll busy-waits',
     'a fixed five seconds on every call, called every ten, so a node\nwith a working modem spends half its time in that loop'),
]
y = 96.0
for hdr, body in ITEMS:
    bx.plot([1.6], [y - 0.4], marker='o', ms=4.4, color=P['bad'], zorder=5)
    bx.text(5.0, y, hdr, ha='left', va='top', fontsize=8.6, fontweight='bold',
            color=P['bad'], zorder=5)
    bx.text(5.0, y - 4.3, body, ha='left', va='top', fontsize=8.0,
            color='#222222', zorder=5, linespacing=1.45)
    y -= 15.0

bx.add_patch(mp.FancyBboxPatch((1.0, 0.5), 98.0, 7.0, boxstyle='round,pad=0.6',
                               fc='none', ec=P['grey'], lw=0.9, ls='--',
                               zorder=2, transform=bx.transData))
bx.text(50.0, 4.0,
        'None of these stops the system running. Several stop its outputs being quoted as measurements.',
        ha='center', va='center', fontsize=8.2, color='#333333', zorder=3)

fig.suptitle('The actuation law, and the defects a source-level audit found',
             x=0.055, y=0.975, ha='left', fontsize=13.5, fontweight='bold')
fig.text(0.055, 0.905,
         'Every entry in panel (b) was checked against the firmware rather than inherited from an earlier summary.',
         ha='left', va='top', fontsize=10.5, color='#222222')
save(fig, 'fig39_iot_control_law.png')
