import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import matplotlib.patches as mp

# (layer, band, evidence where it exists, or the stated reason where it does not)
# bands: 'measured' | 'rate' | 'open'
L = [
 ('Motor control, ESP32, PID with feedforward, 100 Hz', 'measured',
  'per-wheel RMS 0.040-0.047 rad/s over 26 468 bench samples, 0.066-0.077 rad/s under\n'
  'chassis load over 35 248; no channel saturated in any recorded run'),
 ('Encoders and level-shifted return path', 'measured',
  'quadrature decoded on hardware counters; travel-spread ratio 1.00 on a\n'
  'non-rotating square'),
 ('Asymmetric mecanum kinematics', 'measured',
  'forward model inverts independently generated twists to 2.22e-16 worst case\n'
  'over 20 000 random cases, which is one unit in the last place'),
 ('Odometry integration', 'measured',
  'offline re-integration from the raw encoder record diverges 0.0054 m peak\n'
  'and 0.0000 m at the end of a complete drive'),
 ('Wheel-odometry closure against the floor', 'measured',
  '0.07 % over 4.582 m; 0.23, 0.29 and 0.91 % over 8.00 to 10.61 m;\n'
  '1.27 % over the longest route driven, about 18 m'),
 ('Yaw-consistency residual from the two diagonal pairs', 'measured',
  'median 0.035 rad/s while moving over four drives, p95 0.111-0.124,\n'
  'no sample above the 0.5 rad/s episode threshold'),
 ('Operator dashboard, screen to world transform', 'measured',
  'tapped pixel to world coordinate within 1e-6 of the analytic value at three\n'
  'device pixel ratios'),
 ('Global planner, NavFn', 'rate',
  'plans successfully on every goal attempted; runs at 1.25 Hz against the 5 Hz\n'
  'requested, limited by host CPU rather than by the planner'),
 ('Local controller, MPPI with an omnidirectional model', 'rate',
  'goals reached in 21.0 s and 25.9 s; control loop 7.5-13.7 Hz against 20 Hz\n'
  'requested, same host CPU limit'),
 ('Safety chain, collision monitor through to the wheels', 'rate',
  'confirmed end to end; issues stale-scan warnings under the same CPU load'),
 ('Scan matching into the pose estimate', 'open',
  'measured to increase closure error on three routes, most tightly at the 5 m cap where\n'
  'the same drive gave 16.2 mm on wheel odometry and 206.7 mm matched; corrections fire on a\n'
  '0.183 m odometry cadence, not on scan disagreement. Disabled on that evidence; perimeter A/B owed'),
 ('A commissioning map meeting all four acceptance criteria', 'open',
  'three of four met: verdict not folded, doubled walls 0.7-1.03 %, return to mark\n'
  '6.4-80.6 mm. Coverage fails at 77.6-84.6 % unclassified because the available\n'
  'test area permits a traversable loop of only a few metres'),
 ('Localisation against a previously saved map', 'open',
  'requires an accepted map, the row above; not yet exercised for that reason'),
 ('Inertial measurement and fused state estimation', 'open',
  'deliberately deferred. The unfused estimate is the baseline against which the\n'
  'sensing requirement is stated, and fitting the sensor first removes it'),
 ('Named-location library', 'open',
  'designed; implementation held behind an accepted map, which defines the\n'
  'coordinates it would store'),
]

COL  = {'measured': C['fixed'], 'rate': C['command'], 'open': C['neutral']}
MARK = {'measured': '●', 'rate': '◐', 'open': '○'}
FILL = {'measured': 0.92, 'rate': 0.92, 'open': 0.0}

fig, ax = plt.subplots(figsize=(11.4, 9.2))
GAP = 1.85          # extra space where measured evidence ends
first_open = min(i for i, r in enumerate(L) if r[1] == 'open')

# Row height follows the number of evidence lines, so a three-line reason does
# not run into the row beneath it.
heights = [0.62 + 0.42*ev.count('\n') for _, _, ev in L]
ys, cur = [], 0.0
for i, h in enumerate(heights):
    if i == first_open:
        cur += GAP
    cur += h
    ys.append(-cur + h/2)
TOP = 0.0

ax.set_xlim(0, 100); ax.set_ylim(min(ys)-2.2, 2.9); ax.axis('off')

def mark(x, y, band):
    ax.plot([x], [y], marker='o', ms=8.5, mfc=COL[band] if FILL[band] else 'none',
            mec=COL[band], mew=1.4, alpha=0.95, clip_on=False, zorder=5, ls='none')

for i, (name, band, ev) in enumerate(L):
    y = ys[i]
    mark(2.6, y, band)
    ax.text(5.6, y, name, ha='left', va='center', fontsize=8.5, color='k')
    ax.text(46, y, ev, ha='left', va='center', fontsize=7.0,
            color=C['neutral'], linespacing=1.35)

CLIFF = (ys[first_open-1] - heights[first_open-1]/2 + ys[first_open] + heights[first_open]/2) / 2.0
ax.plot([2.0, 99], [CLIFF, CLIFF], color=C['neutral'], lw=1.0, ls=(0, (6, 4)))
ax.text(2.0, CLIFF + 0.20, 'evidence available and reproduced',
        fontsize=8.0, color=C['fixed'], style='italic', va='bottom')
ax.text(2.0, CLIFF - 0.20, 'remaining work, with the reason it has not been done stated against each row',
        fontsize=8.0, color=C['neutral'], style='italic', va='top')

ax.text(2.0, TOP + 2.45,
        'Evidence status of each layer of the system',
        fontsize=10.2, fontweight='bold')
ax.text(2.0, TOP + 1.75,
        'Every layer carrying the platform’s motion is measured against an external reference or an independent implementation. '
        'The layers that remain\nare listed with the specific reason they are outstanding, which in three of five cases is the size of the available test space rather than the platform.',
        fontsize=7.8, color=C['neutral'], va='top', linespacing=1.45)

LEG = min(ys) - 1.5
for lbl, band, x in [('measured and reproduced', 'measured', 2.6),
                     ('works, below its requested update rate', 'rate', 30.0),
                     ('not yet established, reason stated', 'open', 66.0)]:
    mark(x, LEG, band)
    ax.text(x+2.0, LEG, lbl, fontsize=7.6, va='center')

plt.tight_layout()
plt.savefig(f'{FIGDIR}/fig22_layer_audit.png', bbox_inches='tight')
print('ok')
