"""Figure 9 — the v3.0 controller against the previous firmware generation.

Both runs are recomputed from the bench logs rather than transcribed, so the
numbers here and the table in §6.4 come from the same arithmetic: relative error
is the RMS of (measured - commanded) over the whole run, expressed as a
percentage of that motor's peak commanded speed, and actuator use is the peak
magnitude of the commanded PWM against full scale.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np, csv

FULL_SCALE = 255.0


def load(path):
    with open(path) as f:
        r = csv.reader(f); next(r)
        return np.array([[float(x) for x in row] for row in r if len(row) == 13])


def metrics(d):
    peak, err, pwm = [], [], []
    for i in range(4):
        tg, ac, pw = d[:, 1+3*i], d[:, 2+3*i], d[:, 3+3*i]
        p = np.max(np.abs(tg))
        peak.append(p)
        err.append(100*np.sqrt(np.mean((ac - tg)**2))/p)
        pwm.append(100*np.max(np.abs(pw))/FULL_SCALE)
    return peak, err, pwm


OLD = load(f'{REPO}/data/bench_logs/bench/run_20260702_183233.csv')   # 2 Jul
NEW = load(f'{REPO}/data/bench_logs/bench/run_20260804_193703.csv')   # 4 Aug
o_peak, o_err, o_pwm = metrics(OLD)
n_peak, n_err, n_pwm = metrics(NEW)

fig, (a, b, c) = plt.subplots(1, 3, figsize=(10.2, 3.7))
x, w = np.arange(4), 0.36
OLDC, NEWC = C['light'], C['telemetry']

def pair(ax, lo, hi, fmt, yl):
    ax.bar(x - w/2, lo, w, color=OLDC, edgecolor='k', lw=0.5, label='v2.0-era, 2 Jul')
    ax.bar(x + w/2, hi, w, color=NEWC, edgecolor='k', lw=0.5, label='v3.0, 4 Aug')
    ax.set_xticks(x); ax.set_xticklabels(MOT)
    ax.set_ylim(0, yl)
    for i in range(4):
        ax.text(i - w/2, lo[i] + yl*0.022, fmt.format(lo[i]), ha='center', fontsize=7.4)
        ax.text(i + w/2, hi[i] + yl*0.022, fmt.format(hi[i]), ha='center', fontsize=7.4)

# (a) how much of the speed range each run actually exercised
pair(a, o_peak, n_peak, '{:.2f}', 3.85)
a.set_ylabel('peak commanded (rad/s)')
a.set_title('(a) Operating envelope exercised', loc='left', fontsize=9)
# Sat across the FL bar in the previous version of this figure; the headroom in
# the y limit is there so it has somewhere of its own to go.
a.text(1.5, 3.62, f'{np.mean(n_peak)/np.mean(o_peak):.1f}× wider speed range',
       ha='center', fontsize=8.2, fontweight='bold', color=C['fixed'], bbox=MASK)

# (b) error relative to the range being asked for
pair(b, o_err, n_err, '{:.1f}', 5.8)
b.set_ylabel('RMS tracking error (% of peak)')
b.set_title('(b) Relative tracking error', loc='left', fontsize=9)

# (c) how much actuator authority was left unused
pair(c, o_pwm, n_pwm, '{:.0f} %', 122)
c.axhline(100, color=C['defect'], lw=1.2, ls='--')
c.text(3.45, 103, 'saturation', ha='right', fontsize=7.4, color=C['defect'], bbox=MASK)
c.set_ylabel('peak PWM used (% of full scale)')
c.set_title('(c) Control authority in reserve', loc='left', fontsize=9)

h, l = a.get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.035))
fig.suptitle('Two bench runs compared. The v3.0 controller holds a lower relative error over a '
             'three-times\nwider speed range, with roughly half the PWM range still unused.',
             fontsize=9.5, y=1.06, x=0.02, ha='left')
plt.tight_layout()
plt.savefig(f'{FIGDIR}/fig09_tracking_comparison.png', bbox_inches='tight')
plt.close()
print('ok')
