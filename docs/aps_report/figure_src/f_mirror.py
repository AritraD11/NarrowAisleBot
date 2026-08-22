import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp

fig = plt.figure(figsize=(10.4, 4.1))
gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.2], wspace=0.42)

meas = [(0, 270, 'right'), (90, 180, 'front'), (180, 90, 'left')]

# ---- (a) polar: where the block was vs where it appeared -----------------
ax = fig.add_subplot(gs[0], projection='polar')
ax.set_theta_zero_location('E'); ax.set_theta_direction(1)
for true, rep, lab in meas:
    ax.plot([np.radians(true)]*2, [0, 1.0], color=C['fixed'], lw=2.0)
    ax.plot(np.radians(true), 1.0, 'o', ms=8, color=C['fixed'], zorder=5)
    ax.plot([np.radians(rep)]*2, [0, 0.75], color=C['defect'], lw=1.6, ls='--')
    ax.plot(np.radians(rep), 0.75, 's', ms=7, color=C['defect'], zorder=5)
ax.plot([], [], color=C['fixed'], lw=2, marker='o', label='block, true bearing')
ax.plot([], [], color=C['defect'], lw=1.6, ls='--', marker='s', label='block, as reported')
ax.set_ylim(0, 1.15); ax.set_yticklabels([])
ax.set_xticks(np.radians([0, 90, 180, 270]))
ax.set_xticklabels(['0°  right', '90°  fwd', '180°  left', '270°  rear'], fontsize=7.2)
ax.grid(alpha=0.3)
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.40), fontsize=7.2)
ax.set_title('(a) Three block placements', loc='left', fontsize=9.3, pad=12)

# ---- (b) the discriminator ----------------------------------------------
ax2 = fig.add_subplot(gs[1])
tr = np.array([m[0] for m in meas]); rp = np.array([m[1] for m in meas])
diff = (rp - tr) % 360
summ = (rp + tr) % 360
xx = np.arange(3)
ax2.plot(xx, diff, 'o--', color=C['defect'], lw=1.6, ms=8,
         label='reported $-$ true')
ax2.plot(xx, summ, 's-', color=C['fixed'], lw=2.0, ms=8,
         label='reported $+$ true')
for i in range(3):
    ax2.text(i, summ[i]+16, f'{summ[i]:.0f}°', ha='center', fontsize=8.2,
             color=C['fixed'], fontweight='bold')
    ax2.text(i, diff[i]-32, f'{diff[i]:.0f}°', ha='center', fontsize=8.2, color=C['defect'])
ax2.set_xticks(xx); ax2.set_xticklabels(['right', 'front', 'left'])
ax2.set_xlim(-0.4, 2.4); ax2.set_ylim(0, 380); ax2.set_yticks([0, 90, 180, 270, 360])
ax2.set_ylabel('angle (deg, mod 360)')
ax2.legend(loc='lower left', fontsize=7.4)
ax2.text(0.50, 0.36, 'a rotation would leave the red\nline flat. It does not.',
         transform=ax2.transAxes, ha='center', fontsize=7.4, color=C['neutral'])
ax2.set_title('(b) Reflection, not rotation', loc='left', fontsize=9.3, pad=10)

# ---- (c) why it mattered ------------------------------------------------
ax3 = fig.add_subplot(gs[2]); ax3.axis('off'); ax3.set_xlim(0,1); ax3.set_ylim(0,1)
ax3.set_title('(c) Why no transform could fix it', loc='left', fontsize=9.3, pad=12)
ax3.add_patch(mp.FancyBboxPatch((0.02, 0.60), 0.96, 0.32,
                                boxstyle='round,pad=0.02', fc='#eaf5ea',
                                ec=C['fixed'], lw=1.0, transform=ax3.transAxes))
ax3.text(0.5, 0.76,
         'All three placements solve one relation:\n'
         r'$\mathrm{reported} \;=\; 270° - \mathrm{true}$   (mod 360°)',
         ha='center', va='center', fontsize=9, transform=ax3.transAxes)
ax3.add_patch(mp.FancyBboxPatch((0.02, 0.30), 0.96, 0.24,
                                boxstyle='round,pad=0.02', fc='#fdecea',
                                ec=C['defect'], lw=1.0, transform=ax3.transAxes))
ax3.text(0.5, 0.42,
         'tf2 composes rigid motions only. A reflection\n'
         'inverts handedness, so no static transform at\n'
         'any angle is equivalent to it.',
         ha='center', va='center', fontsize=8, color=C['defect'], transform=ax3.transAxes)
ax3.add_patch(mp.FancyBboxPatch((0.02, 0.02), 0.96, 0.21,
                                boxstyle='round,pad=0.02', fc='#eef2f6',
                                ec=C['telemetry'], lw=1.0, transform=ax3.transAxes))
ax3.text(0.5, 0.125,
         'Fix: re-index the scan itself in scan_relay.py\n'
         r'(mirror = True, yaw offset = 270°), via a cached'
         '\nindex map built once per scan geometry.',
         ha='center', va='center', fontsize=8, color=C['telemetry'],
         transform=ax3.transAxes)

fig.suptitle('The mirrored-scan fault, 11 Aug 2026. Bearings were defined empirically from '
             'how the robot\nactually drives, not assumed from the REP-103 convention; '
             'an earlier derivation that did assume it was 90° wrong.',
             fontsize=9.5, y=1.07, x=0.02, ha='left')
plt.savefig(f'{FIGDIR}/fig14_lidar_mirror.png', bbox_inches='tight'); plt.close()
print('ok')
