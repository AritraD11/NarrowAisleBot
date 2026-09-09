import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp

# (layer, grade, evidence one-liner, band)  band: 'good' | 'break' | 'never'
L = [
 ('Motor control — ESP32, PID + feedforward, 100 Hz', 'good',
  'all four motors 0.043–0.046 rad/s RMS, zero saturation, zero sign fault'),
 ('Encoders and wiring',                                            'good',
  'travel-spread ratio 1.00 on a non-rotating square'),
 ('Asymmetric mecanum kinematics',                                  'good',
  'forward model reproduces ground-truth twist to 1.7e-16 over 20 000 random twists'),
 ('Odometry integration',                                           'good',
  'offline re-integration from raw encoders diverges 0.0054 m peak, 0.0000 m final'),
 ('Wheel-odometry physical accuracy',                               'good',
  '4.582 m closed to 3.1 mm (0.07 %); 0.229 m over 21.85 m (1.27 %), on spec'),
 ('map→odom — the SLAM front end',                                  'break',
  'one correction per pose-graph node, every node; 6.8× spread across identical drives'),
 ('An accepted commissioning map',                                  'break',
  'every map ever built grades FOLDED; one of four sub-criteria met, once'),
 ('AMCL localisation on a saved map',                               'never',
  'the whole block has never executed; a launch-topology fault made it impossible'),
 ('Global planner — NavFn',                                         'ok-starved',
  'plans successfully, runs at 1.25 Hz against 5 Hz requested'),
 ('Local controller — MPPI, omnidirectional model',                 'ok-starved',
  'goals reached in 25.9 s and 21.0 s; control loop 7.5–13.7 Hz against 20 Hz'),
 ('Safety chain — collision_monitor to wheels',                     'ok-starved',
  'confirmed end to end; stale-scan warnings under CPU load'),
 ('Operator dashboard',                                             'good',
  'click pixel to world coordinate exact to 1e-6 at three device pixel ratios'),
 ('Named-location library',                                         'never',
  'designed, no code written'),
]

COL = {'good': C['fixed'], 'break': C['defect'], 'never': C['grey'],
       'ok-starved': C['command']}
MARK = {'good': '✓', 'break': '✗', 'never': '·', 'ok-starved': '~'}

fig, ax = plt.subplots(figsize=(10.6, 6.0))
GAP = 1.35          # extra room between layer 5 and layer 6, where the cliff is
TOP = len(L) + GAP
ax.set_xlim(0, 100); ax.set_ylim(-0.6, TOP + 3.0); ax.axis('off')

def ypos(i):
    return TOP - i - (GAP if i >= 5 else 0)

for i, (name, band, ev) in enumerate(L):
    y = ypos(i)
    col = COL[band]
    # the status chip: width carries the message, not a uniform box
    w = {'good': 5.2, 'ok-starved': 3.6, 'break': 5.2, 'never': 2.2}[band]
    ax.add_patch(mp.Rectangle((1.5, y-0.30), w, 0.60, fc=col,
                              ec='none', alpha=0.92 if band != 'never' else 0.5))
    ax.text(1.5+w/2, y, MARK[band], ha='center', va='center', fontsize=10,
            color='white', fontweight='bold')
    ax.text(8.4, y, name, ha='left', va='center', fontsize=8.6,
            fontweight='bold' if band == 'break' else 'normal',
            color=col if band in ('break',) else 'k')
    ax.text(46, y, ev, ha='left', va='center', fontsize=7.3, color=C['neutral'])

# the cliff
CLIFF = (ypos(4) + ypos(5)) / 2.0
ax.plot([1.5, 99], [CLIFF, CLIFF], color=C['defect'], lw=1.5, ls=(0, (7, 4)))
ax.text(1.5, CLIFF + 0.30, 'everything below the LiDAR is measured and good',
        fontsize=8.2, color=C['fixed'], style='italic')
ax.text(1.5, CLIFF - 0.30, 'everything from the LiDAR up is broken, starved, or has never run',
        fontsize=8.2, color=C['defect'], style='italic', va='top')

ax.text(1.5, TOP + 2.45,
        'The break is at exactly one component, and it is not where three months of effort went.',
        fontsize=9.6, fontweight='bold')
ax.text(1.5, TOP + 1.75,
        'On the longest drive in the project, wheel odometry came back 0.229 m from the mark — '
        '1.27 %, dead on its own spec —\nand the SLAM estimate took that and made it 0.477 m worse. '
        'The cheapest sensor on the robot is the most trustworthy one.',
        fontsize=8.0, color=C['neutral'], va='top')

for lbl, band, x in [('measured, reproduced', 'good', 4), ('works but CPU-starved', 'ok-starved', 30),
                     ('broken', 'break', 56), ('never executed', 'never', 72)]:
    ax.add_patch(mp.Rectangle((x, -0.45), 2.0, 0.5, fc=COL[band], ec='none',
                              alpha=0.92 if band != 'never' else 0.5))
    ax.text(x+2.7, -0.20, lbl, fontsize=7.6, va='center')

plt.tight_layout()
plt.savefig(f'{FIGDIR}/fig22_layer_audit.png', bbox_inches='tight')
print('ok')
