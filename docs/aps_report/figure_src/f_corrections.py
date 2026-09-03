import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np, csv, math

RUNS = [
 ('front leg, 31 Aug',   f'{REPO}/data/field_runs/run_20260831/run_20260831_155316_pose_trimmed.csv', C['defect']),
 ('right leg, 31 Aug',   f'{REPO}/data/field_runs/run_20260831/run_20260831_191509_pose.csv',        C['fixed']),
 ('front leg re-driven, 1 Sep', f'{REPO}/data/field_runs/run_20260901/run_20260901_112335_pose.csv', C['accent']),
]

def load(p):
    rows = list(csv.DictReader(open(p)))
    def g(r, k):
        try: return float(r[k])
        except (TypeError, ValueError): return None
    out = []
    for r in rows:
        t, cx, cy, cw = g(r,'epoch_s'), g(r,'corr_x'), g(r,'corr_y'), g(r,'corr_yaw_deg')
        ox, oy        = g(r,'odom_x'), g(r,'odom_y')
        if None in (t, cx, cy, cw): continue
        out.append((t, cx, cy, cw, ox, oy))
    t0 = out[0][0]
    return np.array([(t-t0, cx, cy, cw, ox or 0, oy or 0) for t, cx, cy, cw, ox, oy in out])

fig = plt.figure(figsize=(10.4, 5.6))
gs  = fig.add_gridspec(2, 3, height_ratios=[1.25, 1], width_ratios=[1,1,1],
                       hspace=0.42, wspace=0.30)

# --- top: correction magnitude against time, all three runs -----------------
ax = fig.add_subplot(gs[0, :])
for name, path, col in RUNS:
    d = load(path)
    mag = np.hypot(d[:,1], d[:,2])
    ax.plot(d[:,0], mag, color=col, lw=1.4, label=name)
ax.set_xlabel('time into drive (s)'); ax.set_ylabel(r'$|$map$\rightarrow$odom correction$|$  (m)')
ax.set_ylim(0, 1.02); ax.set_xlim(0, 245)
ax.axhline(0.30, color=C['neutral'], lw=1.0, ls='--')
ax.text(3, 0.325, 'G2 gate, 0.30 m', ha='left', fontsize=7.4, color=C['neutral'])
ax.legend(loc='lower left', fontsize=8, bbox_to_anchor=(0.005, 0.02))
ax.annotate('0.857 m, the largest correction on record,\non the route that gave 0.678 m nine days before',
            xy=(139, 0.90), xytext=(243, 0.95), fontsize=7.6, color=C['accent'],
            ha='right', va='top',
            arrowprops=dict(arrowstyle='->', color=C['accent'], lw=1.0,
                            connectionstyle='arc3,rad=0.22'))
ax.set_title('Three drives. Same robot, same configuration, same operator, same week.', loc='left')

# --- bottom left: the three summary numbers --------------------------------
a1 = fig.add_subplot(gs[1, 0])
labels = ['front\n31 Aug', 'right\n31 Aug', 'front\nrepeat']
ret    = [0.577, 0.085, 0.209]
cols   = [C['defect'], C['fixed'], C['accent']]
a1.bar(range(3), ret, 0.6, color=cols, edgecolor='k', lw=0.5)
a1.axhline(0.15, color='k', lw=1.1, ls='--')
a1.text(-0.42, 0.163, 'G4 gate, 0.15 m', ha='left', fontsize=7.2)
for i, v in enumerate(ret):
    a1.text(i, v+0.018, f'{v:.3f}', ha='center', fontsize=8)
a1.set_xticks(range(3)); a1.set_xticklabels(labels, fontsize=7.6)
a1.set_ylim(0, 0.74); a1.set_ylabel('return to mark (m)')
a1.set_title('(a) 6.8× spread', loc='left', fontsize=9)

# --- bottom middle: cumulative correction per metre ------------------------
a2 = fig.add_subplot(gs[1, 1])
cum = [0.562, 0.305, 0.484]
a2.bar(range(3), cum, 0.6, color=cols, edgecolor='k', lw=0.5)
a2.axhline(0.507, color=C['neutral'], lw=1.1, ls=':')
a2.text(2.42, 0.525, 'pre-fix baseline', ha='right', fontsize=7.0, color=C['neutral'])
for i, v in enumerate(cum):
    a2.text(i, v+0.014, f'{v:.3f}', ha='center', fontsize=8)
a2.set_xticks(range(3)); a2.set_xticklabels(labels, fontsize=7.6)
a2.set_ylim(0, 0.68); a2.set_ylabel('cumulative correction ÷ path (m/m)')
a2.set_title('(b) two of three worse than baseline', loc='left', fontsize=9)

# --- bottom right: the wheels, for contrast --------------------------------
a3 = fig.add_subplot(gs[1, 2])
wheel = [0.028, 0.019, 0.031]
a3.bar(range(3), wheel, 0.6, color=C['telemetry'], edgecolor='k', lw=0.5)
for i, v in enumerate(wheel):
    a3.text(i, v+0.0012, f'{v:.3f}', ha='center', fontsize=8)
a3.set_xticks(range(3)); a3.set_xticklabels(labels, fontsize=7.6)
a3.set_ylim(0, 0.062); a3.set_ylabel('wheel-odometry closure (m)')
a3.set_title('(c) the cheap sensor, same drives', loc='left', fontsize=9)
a3.text(0.5, 0.72, 'under 3 cm\nevery time', transform=a3.transAxes, ha='center',
        fontsize=8, color=C['telemetry'], style='italic')

plt.savefig(f'{FIGDIR}/fig16_correction_traces.png', bbox_inches='tight')
print('ok')
