import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp

# ============ (1) the invariance result ====================================
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.8, 3.8),
                             gridspec_kw={'width_ratios':[1.15, 1]})
sets = ['arc 1\nmin_travel_heading 0.2\nangle_penalty 1.2',
        'arc 2\n0.1\n1.2',
        'arc 3\n0.1\n0.6']
cum   = [2.80, 2.85, 2.86]
maxc  = [0.367, 0.229, 0.366]
step  = [10.42, 5.71, 10.23]
x = np.arange(3)

a1.bar(x, cum, 0.55, color=C['telemetry'], edgecolor='k', lw=0.5, zorder=3)
lo, hi = min(cum), max(cum)
a1.axhspan(lo, hi, color=C['defect'], alpha=0.30, zorder=4)
for i, v in enumerate(cum):
    a1.text(i, v+0.09, f'{v:.2f} m', ha='center', fontsize=9.5, fontweight='bold', zorder=5)
a1.set_xticks(x); a1.set_xticklabels(sets, fontsize=7.2)
a1.set_ylim(0, 3.9); a1.set_ylabel('cumulative map→odom correction (m)')
a1.annotate(f'the whole spread is {hi-lo:.2f} m — 2 % of the total',
            xy=(2.28, (lo+hi)/2), xytext=(1.35, 3.45), fontsize=8.2,
            color=C['defect'], fontweight='bold', ha='center',
            arrowprops=dict(arrowstyle='->', color=C['defect'], lw=1.1,
                            connectionstyle='arc3,rad=-0.2'))
a1.set_title('(a) The total does not move', loc='left')

w = 0.38
a2.bar(x-w/2, maxc, w, color=C['command'], edgecolor='k', lw=0.5, label='largest correction (m)')
a2b = a2.twinx()
a2b.bar(x+w/2, step, w, color=C['light'], edgecolor='k', lw=0.5, label='largest heading step (°)')
a2.set_ylabel('largest correction (m)', color=C['command'])
a2b.set_ylabel('largest heading step (°)', color=C['neutral'])
a2.set_xticks(x); a2.set_xticklabels(['arc 1', 'arc 2', 'arc 3'], fontsize=8)
a2.set_ylim(0, 0.62); a2b.set_ylim(0, 17.4); a2b.grid(False)
h1, l1 = a2.get_legend_handles_labels(); h2, l2 = a2b.get_legend_handles_labels()
a2.legend(h1+h2, l1+l2, loc='upper center', bbox_to_anchor=(0.5, 0.99), fontsize=7.4, ncol=2)
a2.set_title('(b) but the distribution does', loc='left')
a2.text(0.5, 0.885, 'Halving the heading threshold halved the largest step and pulled\n'
        'the peak correction under the gate. It changed the total by 2 %.',
        transform=a2.transAxes, ha='center', va='top', fontsize=7.6)

fig.suptitle('Tuning the scan matcher redistributes the error without reducing it. '
             'A quantity invariant\nacross every lever available is not being set by those levers.',
             fontsize=9.5, y=1.03, x=0.02, ha='left')
plt.subplots_adjust(wspace=0.30)
plt.savefig(f'{FIGDIR}/fig18_invariance.png', bbox_inches='tight'); plt.close()

# ============ (2) rotation maps nothing ====================================
fig, (b1, b2) = plt.subplots(1, 2, figsize=(9.6, 3.6),
                             gridspec_kw={'width_ratios':[1, 1.05]})
runs  = ['pure rotation\n714°, 642 s', 'turn while rolling\n111 s', 'perimeter drive\n621 s']
wall  = [2.1, 77.2, 88.1]
nodes = [1, 18, 48]
cols  = [C['defect'], C['fixed'], C['telemetry']]
b1.bar(range(3), wall, 0.58, color=cols, edgecolor='k', lw=0.5)
for i, (v, n) in enumerate(zip(wall, nodes)):
    b1.text(i, v+2.2, f'{v:.1f} m', ha='center', fontsize=9, fontweight='bold')
    b1.text(i, v/2, f'{n}\npose-graph\nnodes', ha='center', va='center', fontsize=7.4,
            color='white' if i else C['defect'])
b1.set_xticks(range(3)); b1.set_xticklabels(runs, fontsize=7.6)
b1.set_ylim(0, 105); b1.set_ylabel('wall observed (m)')
b1.set_title('(a) Ten and a half minutes of sweeping a room, for two metres of wall',
             loc='left', fontsize=8.8)

b2.axis('off'); b2.set_xlim(0,1); b2.set_ylim(0,1)
b2.text(0.02, 0.97, 'What was actually happening', fontsize=9, fontweight='bold', va='top')
b2.text(0.02, 0.86,
        'The commissioning procedure adopted in §17.39 was\n'
        '"perimeter, nose leading, rotating at every corner so\n'
        'the LiDAR sweeps every wall". Those corner rotations\n'
        'contribute nothing: no scan accepted, no graph node,\n'
        'no occupied cell.\n\n'
        'Set the heading threshold to 0.05 rad and a full 360°\n'
        'in place still produced one node in 166 seconds — the\n'
        'session\'s first scan, and not one more. The threshold\n'
        'is not the gate.\n\n'
        'Holding forward and yaw together instead reached 88 %\n'
        'of the perimeter drive\'s wall coverage in 18 % of its\n'
        'time and 18 % of its distance.',
        fontsize=7.8, va='top', linespacing=1.55)
b2.add_patch(mp.Rectangle((0.01, 0.015), 0.97, 0.115, fc='#fdecea', ec=C['defect'], lw=0.9))
b2.text(0.5, 0.072, 'Three sessions of tuning had been spent against a test\n'
        'geometry that records nothing.',
        ha='center', va='center', fontsize=7.8, color=C['defect'], fontweight='bold')
fig.suptitle('Rotation in place adds no pose-graph node and no map cell, '
             'which invalidated the drive procedure\nitself rather than its parameters.',
             fontsize=9.5, y=1.05, x=0.02, ha='left')
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig17_rotation_deadzone.png'); plt.close()
print('ok')
