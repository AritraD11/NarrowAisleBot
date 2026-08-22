import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg import *
import numpy as np

fig, ax = canvas(10.6, 5.2, 100, 49)
DONE, PART, TODO = C['fixed'], C['command'], C['grey']

phases = [
 (2.0,  'Phase 1\nClosed-loop\nvelocity control',
  'PCNT quadrature · 100 Hz PID\ntwo-term feedforward\nlatching E-STOP + trips',
  'validated in air\nground calibration open', DONE, 0.88),
 (21.0, 'Phase 2\nOdometry and\nstate estimation',
  'wheel odometry (running)\nIMU + EKF fusion (not started)\nIMU not yet procured',
  'the critical gap', PART, 0.35),
 (40.0, 'Phase 3\nPerception\nand mapping',
  'YDLIDAR X4 Pro + slam_toolbox\nautomated map reports\nlive Foxglove visualisation',
  'maps build repeatably\n~85 % unknown', PART, 0.65),
 (59.0, 'Phase 4\nAutonomous\nnavigation',
  'Nav2 configured and audited\nDWB first, MPPI measured\nnever yet executed',
  'blocked on Phase 2', TODO, 0.10),
 (78.0, 'Phase 5\nApplication\nintelligence',
  'fiducial docking\nbehaviour tree\nload-dependent gains',
  'years 2–4', TODO, 0.0),
]

for x, title, body, status, col, prog in phases:
    box(ax, x, 19.0, 18.0, 23.0, '', fc='white', ec=col, lw=1.4)
    ax.text(x+9, 40.8, title, ha='center', va='top', fontsize=8.6,
            fontweight='bold', color=col, linespacing=1.4)
    ax.text(x+9, 32.6, body, ha='center', va='top', fontsize=7.0, linespacing=1.6)
    ax.text(x+9, 26.4, status, ha='center', va='top', fontsize=7.0,
            color=col, style='italic', linespacing=1.4)
    ax.add_patch(mp.Rectangle((x+1.2, 20.4), 15.6, 1.9, fc='#ececec', ec='none', zorder=4))
    ax.add_patch(mp.Rectangle((x+1.2, 20.4), 15.6*prog, 1.9, fc=col, ec='none', zorder=5))
    ax.text(x+16.4, 22.7, f'{prog*100:.0f} %', ha='right', va='bottom', fontsize=6.6,
            color=C['neutral'])

for x in [20.0, 39.0, 58.0, 77.0]:
    ax.annotate('', xy=(x+1.0, 30.5), xytext=(x-1.0, 30.5),
                arrowprops=dict(arrowstyle='-|>', color=C['neutral'], lw=1.6))

# the blocking dependency
ax.annotate('', xy=(67.0, 18.6), xytext=(31.0, 18.6),
            arrowprops=dict(arrowstyle='-|>', color=C['defect'], lw=1.8,
                            connectionstyle='arc3,rad=0.55', ls='--'))
ax.text(49.0, 6.4, 'Nav2 is gated on fused localisation, not on the planner.\n'
        'Mecanum roller slip makes wheel odometry alone insufficient: '
        'Galati et al. report 4.56° of heading\ndrift over 10 m on industrial concrete, '
        'which is 0.79 m of lateral error in a corridor this robot barely fits.',
        ha='center', va='center', fontsize=7.6, color=C['defect'], linespacing=1.6,
        bbox=dict(fc='#fdecea', ec=C['defect'], lw=0.9, boxstyle='round,pad=0.6'))

ax.text(1.0, 46.6, 'Phase 3 was reached before Phase 2 deliberately: a scan-matched map builds '
        'without odometry, but navigating on one does not.',
        fontsize=7.8, color=C['neutral'], style='italic')

ax.set_title('Five-phase autonomy roadmap and where the work actually stands. Progress bars '
             'are the author\'s own\nassessment against each phase\'s stated deliverable, '
             'not a schedule metric.',
             loc='left', fontsize=9.5, y=0.99)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig21_roadmap.png'); plt.close()

# ============ defect taxonomy =============================================
from style import plt as _p
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.8, 4.0),
                             gridspec_kw={'width_ratios':[1, 1.25]})
layers = ['physical wiring,\nconnectors, power',
          'firmware constants\nand control logic',
          'ROS 2 node and\nlaunch configuration',
          'Nav2 configuration\n(audit, never yet run)',
          'frame and unit\nconventions',
          'deployment and\nversion drift']
counts = [6, 9, 8, 5, 4, 4]
cols = [C['command'], C['accent'], C['telemetry'], C['grey'], C['defect'], '#8c6d4f']
a1.barh(range(len(layers)), counts, color=cols, edgecolor='k', lw=0.5, height=0.62)
for i, v in enumerate(counts):
    a1.text(v+0.16, i, str(v), va='center', fontsize=8.5)
a1.set_yticks(range(len(layers))); a1.set_yticklabels(layers, fontsize=7.4)
a1.invert_yaxis(); a1.set_xlim(0, 10.4)
a1.set_xlabel('distinct root-caused defects on record')
a1.set_title('(a) Where 36 defects were found and fixed', loc='left')

a2.axis('off'); a2.set_xlim(0,1); a2.set_ylim(0,1)
a2.set_title('(b) The recurring signature', loc='left')
items = [
 ('Silent, not loud.', 'Every one of the four most costly faults produced clean-looking\n'
  'telemetry. The loop tracked; it tracked a corrupted signal.'),
 ('Found by cross-check, not by staring.',
  'The shared-CPR fault surfaced from a front-versus-rear count ratio;\n'
  'the mirrored scan from a block at three known bearings.'),
 ('Two faults at once, twice.',
  'A current-limited bench supply masked a broken encoder line; a stale\n'
  'systemd unit masked a missing TF frame.'),
 ('Isolate before tuning.',
  'Gains were touched only after the actuator, the sensor and the unit\n'
  'conversion had each been verified independently.'),
]
y = 0.955
for head, body in items:
    a2.text(0.02, y, head, fontsize=8.3, fontweight='bold', va='top',
            transform=a2.transAxes)
    a2.text(0.02, y-0.075, body, fontsize=7.5, va='top', transform=a2.transAxes,
            linespacing=1.5)
    y -= 0.255
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig17_defect_taxonomy.png'); plt.close()
print('ok')
