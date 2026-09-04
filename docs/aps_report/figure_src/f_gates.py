import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp

GATES = [
 ('G1', 'Deployment truth',   'passed',
  'every pending file hashed on arrival, every changed parameter confirmed on the live node'),
 ('G2', 'Angular gate closed','passed',
  'max correction 0.202 m against <0.30 m; largest heading step 4.57° against <10°'),
 ('G3', 'CPU headroom',       'open',
  'control loop 7.5–13.7 Hz against the 15 Hz the gate asks for'),
 ('G4', 'An accepted map',    'partial',
  'four sub-criteria: return-to-mark met once (0.085 m); the three map-quality ones never'),
 ('G5', 'AMCL alive',         'never',
  'never executed; a launch-topology fault made it structurally impossible until 1 Sep'),
 ('G6', 'Point and go',       'partial',
  'works during a live mapping session (two goals, 25.9 s and 21.0 s); untested on a saved map'),
 ('G7', 'Named locations',    'never', 'designed, no code written'),
]
COL = {'passed': C['fixed'], 'partial': C['command'], 'open': C['accent'], 'never': C['grey']}
FILL = {'passed': 1.0, 'partial': 0.45, 'open': 0.25, 'never': 0.0}

fig, ax = plt.subplots(figsize=(10.2, 4.2))
ax.set_xlim(0, 100); ax.set_ylim(-1.4, len(GATES)+1.6); ax.axis('off')

for i, (tag, name, st, ev) in enumerate(GATES):
    y = len(GATES) - i - 0.5
    col = COL[st]
    ax.text(1.0, y, tag, fontsize=9.5, fontweight='bold', va='center', color=col)
    ax.text(6.0, y, name, fontsize=8.8, va='center',
            fontweight='bold' if st == 'passed' else 'normal')
    # progress pill
    ax.add_patch(mp.FancyBboxPatch((27, y-0.20), 14, 0.40, boxstyle='round,pad=0.03',
                                   fc='#ececec', ec='none'))
    if FILL[st] > 0:
        ax.add_patch(mp.FancyBboxPatch((27, y-0.20), 14*FILL[st], 0.40,
                                       boxstyle='round,pad=0.03', fc=col, ec='none'))
    ax.text(43, y, ev, fontsize=7.4, va='center', color=C['neutral'])

# G4 is the gate — mark it
ax.annotate('', xy=(0.4, len(GATES)-3.05), xytext=(0.4, len(GATES)-3.95),
            arrowprops=dict(arrowstyle='-', color=C['defect'], lw=3.0))
ax.text(-1.0, len(GATES)-3.5, 'G4 is the gate:\neverything before it\nis preparation,\n'
        'everything after it\nis blocked on it',
        fontsize=7.6, color=C['defect'], ha='right', va='center', fontweight='bold')

ax.text(1.0, len(GATES)+1.15,
        'Seven acceptance gates, written before the work and scored against measurement',
        fontsize=9.6, fontweight='bold')
ax.text(1.0, len(GATES)+0.55,
        'Two passed on hardware. One is partially met and is the blocker. Two have never executed.',
        fontsize=8.0, color=C['neutral'])

for lbl, st, x in [('passed on hardware','passed',1), ('partially met','partial',24),
                   ('open, measured short','open',42), ('never executed','never',66)]:
    ax.add_patch(mp.Rectangle((x, -1.05), 2.0, 0.42, fc=COL[st],
                              ec='none' if FILL[st] else C['grey'],
                              alpha=1.0 if FILL[st] else 0.35, lw=0.8))
    ax.text(x+2.8, -0.84, lbl, fontsize=7.5, va='center')

plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig21_autonomy_gates.png', bbox_inches='tight')
print('ok')
