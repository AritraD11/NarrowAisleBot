import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp

fig = plt.figure(figsize=(10.4, 4.6))
gs  = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.15, 1.0], wspace=0.40)

# ---- (a) correction events, before and after -------------------------------
ax = fig.add_subplot(gs[0])
labels = ['perimeter\n28 Aug', 'Nav2 goal\n1 Sep', 'two circles\n3 Sep', 'perimeter\n3 Sep']
events = [48, 9, 0, 0]
cols   = [C['defect'], C['defect'], C['fixed'], C['fixed']]
b = ax.bar(range(4), events, 0.6, color=cols, edgecolor='k', lw=0.5)
for i, v in enumerate(events):
    ax.text(i, v + 1.4, str(v), ha='center', fontsize=10, fontweight='bold',
            color=cols[i])
ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=7.6)
ax.set_ylim(0, 58); ax.set_ylabel('map→odom correction events')
ax.axvline(1.5, color=C['neutral'], lw=1.0, ls='--')
ax.text(1.58, 52, 'use_scan_matching\nset to false', fontsize=7.8, color=C['fixed'],
        fontweight='bold', va='top')
ax.text(0.02, 0.985, 'sequential scan matcher ON', transform=ax.transAxes,
        fontsize=7.6, color=C['defect'], va='top')
ax.set_title('(a) The mechanism, removed', loc='left')

# ---- (b) what replaced it --------------------------------------------------
a2 = fig.add_subplot(gs[1]); a2.axis('off'); a2.set_xlim(0,1); a2.set_ylim(0,1)
a2.set_title('(b) Why it is a selection, not a retreat', loc='left')
a2.text(0.0, 0.90,
        'Over the same 21.85 m drive:',
        fontsize=8.4, va='top')
rows = [('wheel odometry alone', '0.229 m', '1.27 %', C['fixed']),
        ('odometry + SLAM front end', '0.706 m', '3.9 %', C['defect'])]
y = 0.74
for name, val, pct, col in rows:
    a2.add_patch(mp.Rectangle((0.0, y-0.155), 0.98, 0.185, fc=col, alpha=0.13, ec=col, lw=0.9))
    a2.text(0.05, y+0.005, name, fontsize=8.0, va='center', color=col, fontweight='bold')
    a2.text(0.05, y-0.095, f'closed {val}  —  {pct} of path', fontsize=8.0, va='center', color=col)
    y -= 0.225
a2.text(0.0, 0.30,
        'The expensive estimator was three times worse\n'
        'than the cheap one. Turning the sequential\n'
        'matcher off means the pose comes from the\n'
        'wheels and the scan is stamped down there.\n\n'
        'Projected on a 10 m perimeter, odometry alone\n'
        'gives about 0.13 m — inside the 0.15 m return\n'
        'gate that five sessions of matcher tuning\n'
        'never reached.',
        fontsize=7.7, va='top', linespacing=1.6)

# ---- (c) the phantom yaw ---------------------------------------------------
a3 = fig.add_subplot(gs[2])
runs = ['two circles\n723.8° turned', '12 m out-and-back\n364.5° turned']
odo  = [3.85, 4.49]
phys = [0.03, 0.00]
x = np.arange(2); w = 0.34
a3.bar(x-w/2, odo, w, color=C['command'], edgecolor='k', lw=0.5,
       label='odometry says')
a3.bar(x+w/2, phys, w, color=C['telemetry'], edgecolor='k', lw=0.5,
       label='the floor says')
for i, (o, p) in enumerate(zip(odo, phys)):
    a3.text(i-w/2, o+0.13, f'{o:.2f}°', ha='center', fontsize=8.4, fontweight='bold')
    a3.text(i+w/2, p+0.13, f'{p:.2f}°', ha='center', fontsize=8.4)
a3.set_xticks(x); a3.set_xticklabels(runs, fontsize=7.6)
a3.set_ylim(0, 6.9); a3.set_ylabel('heading error at the mark (°)')
a3.legend(fontsize=7.6, loc='upper right', ncol=1)
a3.text(0.5, 0.30, 'Measured off the floor tile grout in\n'
        'the run video, the method validated\n'
        'each time against a frame of known\n'
        'rotation: −28.0° read as −27.07°.',
        transform=a3.transAxes, ha='center', va='top', fontsize=6.9, style='italic',
        bbox=dict(fc='white', ec=C['grey'], lw=0.6, alpha=0.94, pad=2.5))
a3.set_title('(c) The drift is in the estimate', loc='left')

fig.suptitle('The campaign resolves: the sequential scan matcher was the fault, and part of what '
             'this project\ncalled physical wheel slip turns out to be estimator error.',
             fontsize=9.5, y=1.045, x=0.02, ha='left')
plt.savefig(f'{FIGDIR}/fig19_stage_g.png', bbox_inches='tight')
print('ok')
