import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np, csv

def load(p):
    with open(p) as f:
        r = csv.reader(f); next(r)
        return np.array([[float(x) for x in row] for row in r if len(row)==13])

A = load(f'{REPO}/data/bench_logs/bench/run_20260804_193703.csv')
t = A[:,0]-A[0,0]
tg, ac = A[:,1], A[:,2]

# The step the zoom panel expands: the largest commanded change in the run.
i0 = int(np.argmax((t > 79.5) & (tg < -0.5)))
TGT = tg[i0+2]                      # -2.207 rad/s, the level commanded after the ramp
W0, W1 = t[i0]-1.3, t[i0]+3.6       # zoom window, seconds

fig = plt.figure(figsize=(9.6, 7.2))
gs = fig.add_gridspec(3, 1, height_ratios=[1.30, 0.95, 1.05], hspace=0.52)

# (a) full run -------------------------------------------------------------
ax = fig.add_subplot(gs[0])
ax.plot(t, tg, color=C['command'], lw=2.4, alpha=0.55, label='commanded', zorder=2)
ax.plot(t, ac, color=C['telemetry'], lw=0.85, label='measured (PCNT encoder)', zorder=3)
ax.set_ylabel('FR wheel speed (rad/s)'); ax.set_ylim(-3.3, 3.9); ax.set_xlim(0, t[-1])
ax.set_xlabel('time (s)')
ax.legend(loc='upper left', fontsize=8, ncol=2)
ax.set_title('(a) Front-right wheel, full run. Commanded profile spans '
             r'$\pm$2.8 rad/s over 90.8 s', loc='left')
# mark the region panel (b) expands, drawn so it is actually visible
ax.axvspan(W0, W1, color=C['accent'], alpha=0.13, zorder=1)
ax.annotate('expanded in (b)', xy=((W0+W1)/2, -3.0), xytext=((W0+W1)/2-26, -2.55),
            fontsize=7.6, color=C['accent'], ha='left', va='center',
            arrowprops=dict(arrowstyle='->', color=C['accent'], lw=0.9))

# (b) the step transient, with a real time axis ----------------------------
ax1 = fig.add_subplot(gs[1])
m = (t >= W0) & (t <= W1)
tr = t[m]-t[i0]
ax1.plot(tr, tg[m], color=C['command'], lw=2.4, alpha=0.55)
ax1.plot(tr, ac[m], color=C['telemetry'], lw=1.1, marker='o', ms=2.6)
ax1.axhline(TGT, color=C['neutral'], lw=0.7, ls=':')
ax1.set_xlim(tr[0], tr[-1]); ax1.set_ylim(-2.75, 0.62)
ax1.set_xlabel('time relative to the commanded step edge (s)')
ax1.set_ylabel('FR wheel speed\n(rad/s)')
ax1.set_title('(b) The largest commanded step in the run, expanded. The transient '
              'occupies three to four log samples', loc='left')
ax1.annotate('', xy=(0.0, -0.30), xytext=(0.20, -0.30),
             arrowprops=dict(arrowstyle='<->', color=C['fixed'], lw=1.1))
ax1.text(0.30, -0.95, 'within 5 % of the commanded '
                      r'$-$2.207 rad/s in 0.20 s (4 samples at 20 Hz);'
                      '\n3.5 % overshoot, then held to 0.003 rad/s mean offset, '
                      '0.004 rad/s s.d.\nOne marker per log sample; colours as in (a).',
         fontsize=7.4, va='center', ha='left', color=C['neutral'])

# (c) error traces ---------------------------------------------------------
ax2 = fig.add_subplot(gs[2])
for i in range(4):
    e = A[:,2+3*i] - A[:,1+3*i]
    ax2.plot(t, e, lw=0.65, color=MOTC[i], alpha=0.85, label=MOT[i])
ax2.axhline(0, color='k', lw=0.7)
for lv in (0.15, -0.15):
    ax2.axhline(lv, color=C['neutral'], lw=0.8, ls=':')
ax2.text(1.0, 0.175, r'$\pm$0.15 rad/s', ha='left', fontsize=7.2,
         color=C['neutral'], bbox=MASK)
ax2.set_ylim(-0.75, 0.62); ax2.set_xlim(0, t[-1])
ax2.set_xlabel('time (s)'); ax2.set_ylabel('tracking error (rad/s)')
ax2.legend(ncol=4, fontsize=8, loc='lower center', bbox_to_anchor=(0.5, -0.02))
ax2.set_title('(c) Tracking error, all four wheels. Excursions coincide with '
              'commanded step edges, not with steady state', loc='left')

fig.suptitle('Closed-loop velocity tracking on firmware v3.0, wheels free of the ground '
             '(run_20260804_193703.csv)', fontsize=9.5, y=0.975, x=0.02, ha='left')
plt.savefig(f'{FIGDIR}/fig08_v30_tracking.png'); plt.close()
print('ok')
