import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np

r_in   = 0.24
r_circ = 0.5*np.sqrt(1.12**2 + 0.48**2)
alpha  = 5.0
d = np.linspace(0, 0.75, 1200)

def cost(d, r_infl):
    c = np.where(d <= r_in, 253.0,
        np.where(d <= r_infl, np.ceil(252*np.exp(-alpha*(d - r_in))), 0.0))
    c[d <= 1e-9] = 254.0
    return c

fig, ax = plt.subplots(figsize=(7.8, 3.7))
ax.axvspan(0, r_in, color=C['defect'], alpha=0.12, lw=0)
ax.axvspan(r_in, r_circ, color=C['command'], alpha=0.10, lw=0)
ax.axvspan(r_circ, 0.75, color=C['fixed'], alpha=0.08, lw=0)

ax.plot(d, cost(d, 0.45), color=C['telemetry'], lw=2.1,
        label='global costmap,  inflation_radius = 0.45 m')
ax.plot(d, cost(d, 0.35), color=C['accent'], lw=1.6, ls='--',
        label='local costmap,  inflation_radius = 0.35 m')

ax.axvline(r_in,   color=C['defect'], ls=':', lw=1.1)
ax.axvline(r_circ, color=C['command'], ls=':', lw=1.1)
ax.text(r_in,   264, r'$r_{in}=0.24$ m'   + '\ninscribed', ha='center',
        va='bottom', fontsize=7.4, color=C['defect'])
ax.text(r_circ, 264, r'$r_{circ}=0.61$ m' + '\ncircumscribed', ha='center',
        va='bottom', fontsize=7.4, color=C['command'])

ax.text(r_in/2, 150, 'LETHAL / INSCRIBED\nin collision at\nevery heading',
        ha='center', fontsize=7.6, color=C['defect'])
ax.text((r_in+r_circ)/2, 168, 'collision depends on heading;\n'
        'the exact polygon check resolves it', ha='center', fontsize=7.6, color='#7a3e00')
ax.text(0.685, 150, 'path preference,\nnot a collision\nstatement',
        ha='center', fontsize=7.6, color=C['fixed'])

ax.annotate('both inflation radii stop short of $r_{circ}$:\n'
            'safety comes from the footprint check,\nnot from the inflation band',
            xy=(0.452, 12), xytext=(0.545, 92), fontsize=7.2, ha='center',
            arrowprops=dict(arrowstyle='->', lw=0.9, color=C['neutral'],
                            connectionstyle='arc3,rad=-0.3'))

ax.set_xlabel('distance to nearest obstacle,  $d$  (m)')
ax.set_ylabel('costmap cell cost  (0–254)')
ax.set_xlim(0, 0.75); ax.set_ylim(0, 292)
ax.set_yticks([0, 50, 100, 150, 200, 254])
ax.legend(loc='lower left', bbox_to_anchor=(0.005, 0.01), fontsize=7.4)
ax.set_title('Costmap inflation as configured, for the tape-measured 1.12 × 0.48 m footprint.\n'
             'An over-generous inflation radius would make an aisle the robot physically fits '
             'appear impassable.', loc='left', fontsize=9.5)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig16_costmap_inflation.png'); plt.close()
print('ok')
