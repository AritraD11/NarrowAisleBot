import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np, csv, math
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

def load(p):
    with open(p) as f:
        r = csv.reader(f); next(r)
        return np.array([[float(x) for x in row] for row in r if len(row)==13])

A = load(f'{REPO}/data/bench_logs/run_20260804_193703.csv')
t = A[:,0]-A[0,0]

fig = plt.figure(figsize=(9.6, 5.6))
gs = fig.add_gridspec(2, 1, height_ratios=[1.35, 1], hspace=0.34)

# (a) FR full trace + inset
ax = fig.add_subplot(gs[0])
tg, ac, pw = A[:,1], A[:,2], A[:,3]
ax.plot(t, tg, color=C['command'], lw=2.4, alpha=0.55, label='commanded', zorder=2)
ax.plot(t, ac, color=C['telemetry'], lw=0.85, label='measured (PCNT encoder)', zorder=3)
ax.set_ylabel('FR wheel speed (rad/s)'); ax.set_ylim(-3.3, 3.9); ax.set_xlim(0, t[-1])
ax.legend(loc='upper left', fontsize=8, ncol=2)
ax.set_title('(a) Front-right wheel, full run. Commanded profile spans '
             r'$\pm$2.8 rad/s over 90.8 s', loc='left')

# inset on the largest transient
i0 = int(np.argmax(np.abs(np.diff(tg))))
lo, hi = max(0, i0-25), min(len(t)-1, i0+70)
axi = inset_axes(ax, width='23%', height='34%', loc='lower left',
                 bbox_to_anchor=(0.035, 0.045, 1, 1), bbox_transform=ax.transAxes)
axi.plot(t[lo:hi], tg[lo:hi], color=C['command'], lw=2.2, alpha=0.55)
axi.plot(t[lo:hi], ac[lo:hi], color=C['telemetry'], lw=1.1, marker='o', ms=2.2)
axi.set_xticks([]); axi.tick_params(labelsize=6.5); axi.grid(alpha=0.2)
axi.set_title('step transient, 20 Hz log', fontsize=6.8, pad=2)
for s in axi.spines.values(): s.set_edgecolor(C['neutral'])
mark_inset(ax, axi, loc1=2, loc2=4, fc='none', ec=C['grey'], lw=0.7, ls=':')

# (b) error traces
ax2 = fig.add_subplot(gs[1])
for i in range(4):
    e = A[:,2+3*i] - A[:,1+3*i]
    ax2.plot(t, e, lw=0.65, color=MOTC[i], alpha=0.85, label=MOT[i])
ax2.axhline(0, color='k', lw=0.7)
for lv in (0.15, -0.15):
    ax2.axhline(lv, color=C['neutral'], lw=0.8, ls=':')
ax2.text(1.0, 0.175, r'$\pm$0.15 rad/s', ha='left', fontsize=7.2, color=C['neutral'])
ax2.set_ylim(-0.75, 0.62); ax2.set_xlim(0, t[-1])
ax2.set_xlabel('time (s)'); ax2.set_ylabel('tracking error (rad/s)')
ax2.legend(ncol=4, fontsize=8, loc='lower center', bbox_to_anchor=(0.5, -0.02))
ax2.set_title('(b) Tracking error, all four wheels. Excursions coincide with '
              'commanded step edges, not with steady state', loc='left')

fig.suptitle('Closed-loop velocity tracking on firmware v3.0, wheels free of the ground '
             '(run_20260804_193703.csv)', fontsize=9.5, y=0.985, x=0.02, ha='left')
plt.savefig(f'{FIGDIR}/fig08_v30_tracking.png'); plt.close()
print('ok')
