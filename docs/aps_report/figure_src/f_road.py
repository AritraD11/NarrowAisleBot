import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg import *
import numpy as np

fig, ax = canvas(10.6, 5.2, 100, 49)
DONE, PART, TODO = C['fixed'], C['command'], C['grey']

phases = [
 (2.0,  'Phase 1\nClosed-loop\nvelocity control',
  '100 Hz PID + 2-term feedforward\nhardware quadrature decode\nlatching E-STOP and trips',
  'validated in air and on\nthe floor; plant ID open', DONE, 0.90),
 (21.0, 'Phase 2\nOdometry and\nstate estimation',
  'wheel odometry: 0.07 % closure\nno IMU, no sensor fusion\nphantom yaw now measured',
  'the best instrument on the\nrobot, and still open-loop', PART, 0.55),
 (40.0, 'Phase 3\nPerception\nand mapping',
  'LiDAR, slam_toolbox, automated\nmap grading, live visualisation\nfront end root-caused',
  'maps build; none yet\naccepted for navigation', PART, 0.60),
 (59.0, 'Phase 4\nAutonomous\nnavigation',
  'MPPI on the omni model\nautonomous round trips done\nAMCL has never run',
  'works on a live map,\nnot yet on a saved one', PART, 0.45),
 (78.0, 'Phase 5\nApplication\nintelligence',
  'named locations\ndose-based UV-C control\ncargo handling under load',
  'years 2 to 4', TODO, 0.0),
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
ax.annotate('', xy=(67.0, 18.6), xytext=(50.0, 18.6),
            arrowprops=dict(arrowstyle='-|>', color=C['defect'], lw=1.8,
                            connectionstyle='arc3,rad=0.55', ls='--'))
ax.text(58.0, 6.4, 'Navigation on a saved map is gated on one artefact that does not exist: an accepted\n'
        'commissioning map. Point-and-go already works inside a live mapping session, which is\n'
        'why the roadmap now runs on two tracks rather than waiting.',
        ha='center', va='center', fontsize=7.6, color=C['defect'], linespacing=1.7,
        bbox=dict(fc='#fdecea', ec=C['defect'], lw=0.9, boxstyle='round,pad=0.6'))

ax.text(1.0, 46.6, 'The phases were not completed in order, and the reason is recorded rather than tidied away: '
        'Phase 4 was reached before Phase 2.',
        fontsize=7.8, color=C['neutral'], style='italic')

ax.set_title('The five-phase roadmap and where the work actually stands, September 2026. Progress figures\n'
             'are assessed against each phase\'s own stated deliverable, not against a schedule.',
             loc='left', fontsize=9.5, y=0.99)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig28_roadmap.png'); plt.close()

# ============ defect taxonomy =============================================
from style import plt as _p
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.2, 4.3),
                             gridspec_kw={'width_ratios':[1, 1.25]})
layers = ['ROS 2 node and\nlaunch topology',
          'navigation config\nand tuning',
          'firmware constants\nand control logic',
          'frame and unit\nconventions',
          'deployment and\nversion drift',
          'operator dashboard',
          'analysis instruments',
          'wiring, connectors,\npower']
counts = [19, 13, 9, 9, 9, 8, 8, 7]
cols = [C['telemetry'], C['grey'], C['accent'], C['defect'], '#8c6d4f',
        '#2e75b6', '#7a9a5b', C['command']]
a1.barh(range(len(layers)), counts, color=cols, edgecolor='k', lw=0.5, height=0.62)
for i, v in enumerate(counts):
    a1.text(v+0.35, i, str(v), va='center', fontsize=8.5)
a1.set_yticks(range(len(layers))); a1.set_yticklabels(layers, fontsize=7.2)
a1.invert_yaxis(); a1.set_xlim(0, 23)
a1.set_xlabel('distinct root-caused defects on record')
a1.set_title('(a) Where 82 defects were found and fixed', loc='left')

a2.axis('off'); a2.set_xlim(0,1); a2.set_ylim(0,1)
a2.set_title('(b) The rules that came out of them', loc='left')
items = [
 ('Silent, not loud.', 'The most costly faults each produced clean-looking telemetry.\n'
  'The loop tracked. It tracked a corrupted signal.'),
 ('A value in the repository is not a value on the robot.',
  'Loop-closure tuning sat in git for three days while three journal\n'
  'entries reasoned about parameters that were never active.'),
 ('Never fix a frame complaint in the display.',
  'Four separate display-side compensations grew over one real frame\n'
  'fault and hid it for two weeks.'),
 ('An instrument that cannot fail its own check is not an instrument.',
  'Two photogrammetry measurements returned confident wrong answers\n'
  'and were caught only by a validation frame with a known result.'),
]
y = 0.955
for head, body in items:
    a2.text(0.02, y, head, fontsize=8.3, fontweight='bold', va='top',
            transform=a2.transAxes)
    a2.text(0.02, y-0.075, body, fontsize=7.5, va='top', transform=a2.transAxes,
            linespacing=1.5)
    y -= 0.245
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig23_defect_taxonomy.png'); plt.close()
print('ok')
