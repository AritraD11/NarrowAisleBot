"""
f_status.py -- gate-by-gate status of Phases 2/3/4, as of 15 Sep 2026.

Source of every status here: Phase_234_Push.md's own §1 baseline (14 Sep),
updated against what was actually measured on 15 Sep in this session
(docs/Phase2_Without_IMU.md §5.2.1, docs/evidence/circular_loop_15sep/).
Nothing in this chart is invented; each row's status traces to a specific
doc or evidence folder, listed in the caption this script also prints.
"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from style import plt, C, FIGDIR

rows = [
    # (label, phase, status, note)
    ('Phase 1: motor control (PID)',            'P1', 'done',    '100% -- PID_Calibration.md'),
    ('Phase 2: odometry & state estimation',    'P2', 'ceiling', 'characterised @ ~75% ceiling (no IMU) -- Phase2_Without_IMU.md'),
    ('  → range envelope (§5.2)',      'P2', 'done',    'closed 15 Sep, 2 captures'),
    ('  → slip residual (Gap 3)',           'P2', 'todo',    'free from drives already happening, not yet run'),
    ('Phase 3: perception & mapping',           'P3', 'blocked', 'G4 not yet passed'),
    ('  → G4: return to mark < 0.15 m',     'P3', 'done',    '~6-30 mm measured, 3 runs -- circular_loop_15sep/'),
    ('  → G4: doubled walls < 1.0%',        'P3', 'partial', '0.7-0.8% recent runs, 1.03% on one -- borderline'),
    ('  → G4: unknown cells < 50%',         'P3', 'blocked', '77.6-84.6% measured, 3 runs -- the actual blocker'),
    ('  → G4: verdict not FOLDED',          'P3', 'partial', 'SUSPECT (not FOLDED) on every run so far'),
    ('Phase 4: autonomous navigation',          'P4', 'partial', 'rung C banked; G5/G6/G7 blocked on G4'),
    ('  → Rung C: live-map tap-to-goal',    'P4', 'done',    'banked 27 Aug, two goals 25.9s/21.0s'),
    ('  → G5: AMCL first bringup',          'P4', 'todo',    'code ready, never executed'),
    ('  → G6: five tapped goals',           'P4', 'todo',    'blocked on G4 + G5'),
    ('  → G7: named locations',             'P4', 'todo',    'code written+tested, not deployed'),
]

COLOR = {
    'done':    C['fixed'],
    'ceiling': C['fixed'],
    'partial': '#e8a33d',
    'blocked': C['defect'],
    'todo':    C['grey'],
}
WIDTH = {'done': 1.0, 'ceiling': 0.75, 'partial': 0.5, 'blocked': 0.15, 'todo': 0.0}
LABEL = {'done': 'done', 'ceiling': 'at ceiling', 'partial': 'partial',
         'blocked': 'blocked', 'todo': 'not started'}

fig, ax = plt.subplots(figsize=(9.5, 5.6))
y = list(range(len(rows)))[::-1]

for yi, (label, phase, status, note) in zip(y, rows):
    indented = label.startswith('  ')
    bary = yi
    barheight = 0.55
    ax.barh(bary, 1.0, height=barheight, color='#e9e9e9', zorder=1)
    w = WIDTH[status]
    if w > 0:
        ax.barh(bary, w, height=barheight, color=COLOR[status], zorder=2)
    ax.text(-0.02, bary, label, ha='right', va='center',
             fontsize=8.3 if indented else 9.3,
             fontweight='normal' if indented else 'bold',
             color='#333' if indented else '#111')
    ax.text(1.03, bary, LABEL[status], ha='left', va='center', fontsize=7.8,
             color=COLOR[status], fontweight='bold')
    ax.text(0.015, bary, note, ha='left', va='center', fontsize=6.6,
             color='white' if w > 0.25 else '#555', zorder=3)

ax.set_xlim(0, 1.55)
ax.set_ylim(-0.7, len(rows) - 0.3)
ax.set_yticks([])
ax.set_xticks([])
for spine in ax.spines.values():
    spine.set_visible(False)
ax.set_title('Phase / gate status -- 15 Sep 2026, 8 days to APS', loc='left', fontweight='bold')

legend_items = [
    plt.Rectangle((0, 0), 1, 1, color=C['fixed'], label='done / at its ceiling'),
    plt.Rectangle((0, 0), 1, 1, color='#e8a33d', label='partial / borderline'),
    plt.Rectangle((0, 0), 1, 1, color=C['defect'], label='blocked -- active gate'),
    plt.Rectangle((0, 0), 1, 1, color=C['grey'], label='not started'),
]
ax.legend(handles=legend_items, loc='lower right', ncol=2, fontsize=7.5,
          bbox_to_anchor=(1.0, -0.13))

fig.savefig(f'{FIGDIR}/status_15sep.png')
print(f'wrote {FIGDIR}/status_15sep.png')
print()
print('Sources, row by row:')
for label, phase, status, note in rows:
    print(f'  {label.strip():40s} {status:10s} {note}')
