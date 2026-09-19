"""Where the three strands go, and where they are meant to meet.

Year 1 is what this report evidences. Everything to the right of it is planned,
and the convergence band at the foot is the point of running three strands at
once rather than three unrelated projects.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *
import matplotlib.patches as mp

fig, ax = canvas(13.4, 7.6, 100, 58)

title(ax, 0.5, 57.6,
      'The three strands across the remaining years',
      'Each strand is carried on its own until it stands up by itself. They converge at the end, not at the start,\n'
      'because a strand that has not been characterised alone contributes nothing to a combined system.')

COLS = [(12.5, 27.5, 'Year 1, 2025–26', 'what this report evidences', 'new'),
        (41.5, 27.5, 'Year 2, 2026–27', 'the work that follows directly', 'tel'),
        (70.5, 27.5, 'Years 3 and 4', 'application and convergence', 'note')]
for x, w, t, s, c in COLS:
    ax.add_patch(mp.Rectangle((x, 44.5), w, 4.6, fc=F[c], ec='none', zorder=2))
    ax.text(x + w / 2, 47.6, t, ha='center', va='center', fontsize=9.8,
            fontweight='bold', zorder=3)
    ax.text(x + w / 2, 45.7, s, ha='center', va='center', fontsize=8.2,
            color='#333333', zorder=3)

LANES = [
    (33.0, 'NARROW-AISLE\nROBOT', 'tel',
     ('full-scale asymmetric platform built\n'
      '100 Hz wheel control, RMS 0.04–0.07 rad/s\n'
      'kinematics verified to machine precision\n'
      'odometry closure below 1 % to 10 m\n'
      'scanner limits measured, not assumed',
      'a test space large enough to close the\n'
      'mapping criteria\ninertial sensing and a fused pose estimate\n'
      'a matched symmetric baseline, to price\nthe asymmetry',
      'task attachments on one base: inventory\nscanning, environmental survey,\n'
      'surface disinfection, cargo transfer')),
    (21.5, 'ENVIRONMENTAL\nMONITORING', 'new',
     ('deployed across four zones, two radio-\nisolated installations, one database\n'
      'three concurrent channels, two control\npaths, recovers from a power cut unaided',
      'traceable calibration of every channel\n'
      'buffered store-and-forward, so an outage\ncosts latency rather than data\n'
      'transfer to cold-chain and ripening rooms',
      'warehouse-wide zone coverage, with the\n'
      'robot carrying the same sensor set as a\nmobile survey node')),
    (10.0, 'CONTACTLESS\nFATIGUE', 'note',
     ('hypothesis formulated\ncompleted literature survey\n'
      'no hardware built, no data collected\nand nothing measured',
      'single-subject capture rig at one fixed\npoint, an aisle end or a doorway\n'
      'each modality validated in the laboratory\nagainst a direct measure of fatigue',
      'fusion across modalities, and the test it\n'
      'has to pass: beat a baseline of ambient\nconditions and hours worked')),
]

for y, name, col, cells in LANES:
    ax.text(6.0, y + 5.0, name, ha='center', va='center', fontsize=9.2,
            fontweight='bold', color=P[col], zorder=6, linespacing=1.5)
    for (x, w, _, _, ccol), txt in zip(COLS, cells):
        box(ax, x, y, w, 10.0, txt, col, fc=col if ccol == 'new' else 'plain',
            fs=7.6)

# the convergence band
ax.add_patch(mp.FancyBboxPatch((0.5, 1.5), 98.0, 6.2,
                               boxstyle='round,pad=0.5', fc=F['cmd'],
                               ec=P['cmd'], lw=1.2, zorder=2))
ax.text(50.0, 4.6,
        'Where they meet. One autonomous base that navigates the aisle, carries the monitoring payload through it, and shares a\n'
        'facility-level picture with the fixed fatigue sensing at the aisle ends. Each of the three has to stand on its own first, which is\n'
        'why the convergence sits at the end of the plan rather than at the beginning of it.',
        ha='center', va='center', fontsize=8.4, zorder=3, linespacing=1.55)
for x in (25.0, 50.0, 75.0):
    arr(ax, (x, 9.6), (x, 8.4), 'cmd', lw=1.6)

save(fig, 'fig37_three_strand_roadmap.png')
