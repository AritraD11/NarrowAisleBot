import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp

# ============ LiDAR placement trial =======================================
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.6),
                             gridspec_kw={'width_ratios':[1.1, 1]})
pos = ['P1  baseline\nfront of battery', 'P2  on top\nof the battery',
       'P3  elevated\non a box']
unk = [85.57, 85.01, 85.70]
fre = [12.61, 13.01, 12.36]
occ = [1.82, 1.98, 1.94]
dur = [275.7, 254.6, 266.8]
ext = [96.0, 82.9, 95.5]
vmax = [1.385, 2.207, 1.385]
x = np.arange(3)
a1.bar(x, unk, 0.55, color=C['grey'], edgecolor='k', lw=0.5, label='unknown')
a1.bar(x, fre, 0.55, bottom=unk, color='#e8eef4', edgecolor='k', lw=0.5, label='free')
a1.bar(x, occ, 0.55, bottom=np.array(unk)+np.array(fre), color=C['telemetry'],
       edgecolor='k', lw=0.5, label='occupied')
for i in range(3):
    a1.text(i, unk[i]/2, f'{unk[i]:.2f} %', ha='center', va='center',
            fontsize=8.5, color='white', fontweight='bold')
a1.set_xticks(x); a1.set_xticklabels(pos, fontsize=8)
a1.set_ylim(0, 108); a1.set_ylabel('occupancy-grid cells (%)')
a1.legend(fontsize=7.4, ncol=3, loc='upper center')
a1.set_title('(a) Map composition after one standardised drive', loc='left')

# secondary panel: the confound
a2.axis('off'); a2.set_xlim(0,1); a2.set_ylim(0,1)
a2.set_title('(b) Why the winner was not chosen on the number alone', loc='left')
rows = [('', 'P1', 'P2', 'P3'),
        ('unknown (%)', '85.57', '85.01', '85.70'),
        ('duration (s)', '275.7', '254.6', '266.8'),
        ('grid extent (m²)', '96.0', '82.9', '95.5'),
        (r'max |$\omega$| cmd (rad/s)', '1.385', '2.207', '1.385')]
for r, row in enumerate(rows):
    y = 0.90 - r*0.135
    for c, cell in enumerate(row):
        xx = [0.02, 0.50, 0.68, 0.86][c]
        ha = 'left' if c == 0 else 'center'
        bold = (r == 0) or (c == 2 and r == 1)
        col = C['fixed'] if (c == 2 and r == 1) else 'k'
        a2.text(xx, y, cell, ha=ha, va='center', fontsize=8.3,
                fontweight='bold' if bold else 'normal', color=col,
                transform=a2.transAxes)
    if r == 0:
        a2.plot([0.02, 0.96], [y-0.062]*2, color='k', lw=0.8, transform=a2.transAxes)
a2.add_patch(mp.Rectangle((0.62, 0.235), 0.12, 0.68, fc=C['fixed'], alpha=0.10,
                          ec=C['fixed'], lw=0.9, transform=a2.transAxes, zorder=0))
a2.text(0.02, 0.155, 'P2 posted the best coverage on a shorter, faster, smaller run,\n'
                     'all of which should have hurt it. P3 was the only controlled\n'
                     'pair against P1 and showed no improvement, so elevation as\n'
                     'implemented was insufficient rather than ineffective.',
        fontsize=7.7, va='top', transform=a2.transAxes)
fig.suptitle('LiDAR mount placement trial, 8 Aug 2026. Three positions, one standardised '
             'test motion,\nautomated map-quality report on every run.',
             fontsize=9.5, y=1.07, x=0.02, ha='left')
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig14_lidar_placement.png'); plt.close()

# ============ map coverage progression ====================================
fig, ax = plt.subplots(figsize=(7.6, 3.5))
runs = ['first map\n6 Aug', 'second map\n6 Aug', 'Map-button run\n7 Aug',
        'P1\n8 Aug', 'P2\n8 Aug', 'P3\n8 Aug']
unkp = [81.3, 79.6, 81.0, 85.57, 85.01, 85.70]
occp = [369/27522*100, 1179/36616*100, None, 1.82, 1.98, 1.94]
occ_cells = [369, 1179, None, None, None, None]
xx = np.arange(len(runs))
ax.plot(xx, unkp, 'o-', color=C['telemetry'], lw=1.6, ms=7, label='unknown cells (%)')
ax.axhspan(70, 90, color=C['command'], alpha=0.10)
ax.axhline(90, color=C['defect'], lw=1.0, ls='--')
ax.text(5.45, 90.6, 'automated report: "poor coverage" band',
        fontsize=7.2, ha='right', color=C['defect'])
ax.text(5.45, 71, 'automated report: "sparse coverage" warn band (70–90 %)',
        fontsize=7.2, ha='right', color='#7a3e00')
for i, v in enumerate(unkp):
    ax.text(i, v+1.1, f'{v:.1f}', ha='center', fontsize=7.6)
ax.set_xticks(xx); ax.set_xticklabels(runs, fontsize=7.8)
ax.set_ylim(60, 96); ax.set_ylabel('unknown cells (% of grid)')
ax.legend(fontsize=7.6, loc='lower left')
ax.set_title('Every map produced so far sits in the sparse band. §17.8 explains why:\n'
             'roughly a third of each scan is blocked by the robot\'s own structure.',
             loc='left', fontsize=9.5)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig15_map_coverage.png'); plt.close()
print('ok')
