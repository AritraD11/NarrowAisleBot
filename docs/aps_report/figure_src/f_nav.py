import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp

# ============ self-occlusion ==============================================
fig = plt.figure(figsize=(9.8, 4.7))
gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.35], wspace=0.28)

ax = fig.add_subplot(gs[0], projection='polar')
ax.set_theta_zero_location('E'); ax.set_theta_direction(1)
th = np.linspace(0, 2*np.pi, 720)
r = np.full_like(th, 1.0)
blind_lo, blind_hi = np.radians(150), np.radians(270)   # ~1/3 of sweep, rear
ax.fill_between(th, 0, 1.0, where=(th >= blind_lo) & (th <= blind_hi),
                color=C['defect'], alpha=0.28, zorder=1)
ax.plot(th, r, color=C['telemetry'], lw=1.6, zorder=3)
ax.add_patch(mp.Rectangle((0, 0), 2*np.pi, 0.12, color=C['grey'], alpha=0.5, zorder=4))
ax.text(np.radians(210), 0.55, 'blind sector\n~1/3 of sweep', ha='center', va='center',
        fontsize=8.2, color=C['defect'], fontweight='bold')
ax.text(np.radians(45), 0.55, 'usable\nreturns', ha='center', va='center',
        fontsize=8.2, color=C['telemetry'])
ax.set_ylim(0, 1.16); ax.set_yticklabels([])
ax.set_xticks(np.radians([0, 90, 180, 270]))
ax.set_xticklabels(['right', 'forward', 'left', 'rear'], fontsize=8)
ax.grid(alpha=0.3)
ax.set_title('(a) Measured blind sector\n(bearings pre-date the mirror fix)',
             loc='left', fontsize=9.3, pad=22)

ax2 = fig.add_subplot(gs[1]); ax2.axis('off'); ax2.set_xlim(0,1); ax2.set_ylim(0,1)
ax2.set_title('(b) Two distinct failure modes, needing different treatment',
              loc='left', fontsize=9.3, pad=22)
def blk(y, h, title, body, fc, ec, tc):
    ax2.add_patch(mp.FancyBboxPatch((0.01, y), 0.98, h, boxstyle='round,pad=0.015',
                                    fc=fc, ec=ec, lw=1.0, transform=ax2.transAxes))
    ax2.text(0.05, y+h-0.050, title, fontsize=8.6, fontweight='bold', color=tc,
             transform=ax2.transAxes, va='top')
    ax2.text(0.05, y+h-0.135, body, fontsize=7.3, transform=ax2.transAxes, va='top',
             linespacing=1.55)
blk(0.725, 0.275, 'Shadowing: tolerable',
    'Cells behind the structure are never observed and stay\n'
    'unknown. With allow_unknown: true, the planner simply\n'
    'has no information there.', '#eef2f6', C['telemetry'], C['telemetry'])
blk(0.365, 0.345, 'False permanent obstacles: damaging',
    'The rear mast sits beyond the 0.12 m minimum range, so it\n'
    'returns a valid hit every scan. The obstacle layer marks it\n'
    'occupied at a fixed bearing in the robot frame, giving an\n'
    'obstacle welded to the chassis that can never be cleared.',
    '#fdecea', C['defect'], C['defect'])
blk(0.005, 0.345, 'Correct fix: mask, do not reinterpret',
    'Affected sectors must be marked invalid in scan_relay.py\n'
    'before the scan reaches SLAM or the costmap, so the beams\n'
    'neither mark nor clear. Marking them free would erase real\n'
    'obstacles; marking them occupied is the present bug.',
    '#eaf5ea', C['fixed'], C['fixed'])
fig.suptitle('Self-occlusion is a navigation failure, not a mapping annoyance. The '
             'discriminator needs no props:\nreal features move in the laser frame under '
             'in-place rotation, self-occlusion does not.',
             fontsize=9.5, y=1.05, x=0.02, ha='left')
plt.savefig(f'{FIGDIR}/fig13_self_occlusion.png', bbox_inches='tight'); plt.close()

# ============ costmap inflation ===========================================
fig, ax = plt.subplots(figsize=(7.4, 3.6))
r_in, r_circ, r_infl, alpha = 0.24, 0.5*np.sqrt(1.12**2+0.48**2), 0.55, 3.0
d = np.linspace(0, 0.75, 900)
c = np.where(d <= r_in, 253,
    np.where(d <= r_infl, np.ceil(252*np.exp(-alpha*(d-r_in))), 0))
c[0] = 254
ax.plot(d, c, color=C['telemetry'], lw=2.0)
ax.axvspan(0, r_in, color=C['defect'], alpha=0.13)
ax.axvspan(r_in, r_circ, color=C['command'], alpha=0.12)
ax.axvspan(r_circ, r_infl, color=C['fixed'], alpha=0.10)
for xv, lab, col in [(r_in, r'$r_{in}=0.24$ m', C['defect']),
                     (r_circ, r'$r_{circ}=0.61$ m', C['command']),
                     (r_infl, r'$r_{infl}=0.55$ m', C['fixed'])]:
    ax.axvline(xv, color=col, ls='--', lw=1.0)
    ax.text(xv, 268, lab, rotation=0, ha='center', fontsize=7.4, color=col)
ax.text(r_in/2, 150, 'in collision at\nEVERY heading', ha='center', fontsize=7.6,
        color=C['defect'])
ax.text((r_in+r_circ)/2, 150, 'collision depends\non heading:\nthe polygon check\nresolves this',
        ha='center', fontsize=7.6, color='#7a3e00')
ax.text(0.66, 150, 'preference,\nnot collision', ha='center', fontsize=7.6, color=C['fixed'])
ax.set_xlabel('distance to nearest obstacle, $d$ (m)')
ax.set_ylabel('costmap cell cost (0–254)')
ax.set_ylim(0, 300); ax.set_xlim(0, 0.75)
ax.set_yticks([0, 100, 200, 253, 254])
ax.set_title('Costmap inflation for the measured 1.12 × 0.48 m footprint. Setting\n'
             'the inflation radius generously would make a passable aisle look blocked.',
             loc='left', fontsize=9.5)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig16_costmap_inflation.png'); plt.close()
print('ok')
