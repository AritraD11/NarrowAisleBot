import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np, csv, math
import matplotlib.patches as mp

def load(path):
    with open(path) as f:
        r = csv.reader(f); next(r)
        return np.array([[float(x) for x in row] for row in r if len(row)==13])

A = load(f'{REPO}/data/bench_logs/run_20260804_193703.csv')   # v3.0
B = load(f'{REPO}/data/bench_logs/run_20260702_183233.csv')   # v2.0-era

# ============ FIG: open-loop characterisation, March 2026 ==================
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 3.3))
mean = [2.853, 2.983, 2.743, 2.507]           # FR FL RR RL  (journal §6.2)
sd   = [0.0195, 0.0075, 0.0437, 0.0510]
cv   = [1.33, 0.33, 2.25, 4.57]
x = np.arange(4)
a1.bar(x, mean, yerr=sd, capsize=4, color=MOTC, edgecolor='k', linewidth=0.5)
a1.axhline(max(mean), ls='--', lw=0.9, color=C['neutral'])
a1.text(3.42, max(mean)+0.03, 'fastest (FL)', fontsize=7.3, ha='right', color=C['neutral'])
for i, v in enumerate(mean):
    a1.text(i, v+0.10, f'{v:.3f}', ha='center', fontsize=8)
a1.annotate('', xy=(3, mean[3]), xytext=(3, mean[1]),
            arrowprops=dict(arrowstyle='<->', color=C['defect'], lw=1.3))
a1.text(2.86, (mean[3]+mean[1])/2, '16 %\ndeficit', ha='right', va='center',
        fontsize=8, color=C['defect'], fontweight='bold')
a1.set_xticks(x); a1.set_xticklabels(MOT); a1.set_ylim(0, 3.5)
a1.set_ylabel('shaft speed (rad/s)')
a1.set_title('(a) Open loop at fixed PWM = 120', loc='left')

a2.bar(x, cv, color=MOTC, edgecolor='k', linewidth=0.5)
for i, v in enumerate(cv):
    a2.text(i, v+0.11, f'{v:.2f} %', ha='center', fontsize=8)
a2.set_xticks(x); a2.set_xticklabels(MOT); a2.set_ylim(0, 5.4)
a2.set_ylabel('coefficient of variation (%)')
a2.set_title('(b) Run-to-run variability', loc='left')
a2.add_patch(mp.Rectangle((2.55, 0), 0.9, 5.4, fc=C['defect'], alpha=0.07, zorder=0))
a2.text(3.0, 5.05, 'RL: slowest\nand noisiest', ha='center', fontsize=7.6, color=C['defect'])
fig.suptitle('Open-loop motor characterisation, March 2026: the FR/RL diagonal pair '
             'differed by 11–13 %', fontsize=9.5, y=1.02, x=0.02, ha='left')
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig03_openloop_characterisation.png'); plt.close()

# ============ FIG: feedforward model ======================================
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 3.4))
w = np.linspace(0, 3.4, 200)
Kff, Kstat = 38.0, 8.0
a1.plot(w, Kff*w + Kstat, color=C['fixed'], lw=1.9,
        label=r'two-term  $K_{ff}\omega + K_{stat}$   (v3.0)')
a1.plot(w, 42.0*w, color=C['defect'], lw=1.6, ls='--',
        label=r'single slope  $K_{ff}\omega$   (v2.0)')
pts = [(1.50, 70.4, '14 May, back-calc', 'low'),
       (1.885, 80.0, '4 Aug, manual drive', 'high'),
       (2.621, 110.0, '4 Aug, AUTO TEST', 'high'),
       (2.77, 120.0, '14 May, back-calc', 'low')]
for wv, p, lab, conf in pts:
    a1.plot(wv, p, 'o', ms=8 if conf == 'high' else 6,
            mfc=C['telemetry'] if conf == 'high' else 'white',
            mec=C['telemetry'], mew=1.4, zorder=5)
a1.plot([], [], 'o', ms=8, color=C['telemetry'], label='measured, high confidence')
a1.plot([], [], 'o', ms=6, mfc='white', mec=C['telemetry'], mew=1.4,
        label='measured, low confidence')
a1.axvspan(3.0, 3.4, color=C['grey'], alpha=0.16)
a1.text(3.2, 22, 'extrapolated\n(no data)', ha='center', fontsize=7.2, color=C['neutral'])
a1.annotate(r'$K_{stat} = 8$ PWM' + '\nbreakaway offset',
            xy=(0.03, 9), xytext=(0.75, 30), fontsize=7.6, color=C['fixed'], ha='center',
            arrowprops=dict(arrowstyle='->', color=C['fixed'], lw=0.9,
                            connectionstyle='arc3,rad=0.2'))
a1.set_xlabel(r'commanded wheel speed  $\omega$  (rad/s)')
a1.set_ylabel('steady-state PWM (0–255)')
a1.set_xlim(0, 3.4); a1.set_ylim(0, 145)
a1.legend(loc='upper left', fontsize=7.3)
a1.set_title('(a) Feedforward fit across three campaigns', loc='left')

# residuals
wv = np.array([p[0] for p in pts]); pm = np.array([p[1] for p in pts])
res = 100*(Kff*wv + Kstat - pm)/pm
cols = [C['telemetry'] if p[3] == 'high' else C['light'] for p in pts]
a2.bar(range(4), res, color=cols, edgecolor='k', lw=0.5)
a2.axhline(0, color='k', lw=0.8)
for lim, ls in [(8, ':'), (-8, ':')]:
    a2.axhline(lim, color=C['neutral'], lw=0.8, ls=ls)
a2.text(3.45, 8.4, r'$\pm$8 %', fontsize=7.3, ha='right', color=C['neutral'])
for i, v in enumerate(res):
    a2.text(i, v + (0.6 if v > 0 else -1.5), f'{v:+.1f} %', ha='center', fontsize=7.8)
a2.set_xticks(range(4))
a2.set_xticklabels([f'{p[0]:.2f}\nrad/s' for p in pts], fontsize=7.5)
a2.set_ylim(-11, 11); a2.set_ylabel('model $-$ measured  (%)')
a2.set_title('(b) Residuals; solid bars are the high-confidence points', loc='left')
fig.suptitle('Two-term feedforward: a single slope cannot fit both ends of the range, '
             'because the\nPWM-per-rad/s ratio rises at low speed (the signature of static friction)',
             fontsize=9.5, y=1.06, x=0.02, ha='left')
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig05_feedforward_model.png'); plt.close()

# ============ FIG: Kff spread, artefact vs real ============================
fig, ax = plt.subplots(figsize=(6.4, 3.3))
old = [42.1, 40.2, 43.7, 47.9]; new = [37.3, 38.4, 38.3, 38.0]
xx = np.arange(4); wdt = 0.36
ax.bar(xx-wdt/2, old, wdt, color=C['defect'], alpha=0.85, edgecolor='k', lw=0.5,
       label='v2.0 — faulty-encoder era (19 % spread)')
ax.bar(xx+wdt/2, new, wdt, color=C['fixed'], alpha=0.9, edgecolor='k', lw=0.5,
       label='v3.0 — confirmed-good path (2.9 % spread)')
for i, (o, n) in enumerate(zip(old, new)):
    ax.text(i-wdt/2, o+0.5, f'{o:.1f}', ha='center', fontsize=7.6)
    ax.text(i+wdt/2, n+0.5, f'{n:.1f}', ha='center', fontsize=7.6)
ax.plot([-0.5, 3.5], [min(old)]*2, ls=':', lw=0.9, color=C['defect'])
ax.plot([-0.5, 3.5], [max(old)]*2, ls=':', lw=0.9, color=C['defect'])
ax.set_xticks(xx); ax.set_xticklabels(MOT); ax.set_ylim(0, 56)
ax.set_ylabel(r'$K_{ff}$  (PWM per rad/s)')
ax.legend(loc='upper left', fontsize=7.6)
ax.set_title('The per-motor spread was an instrumentation artefact, not real\n'
             'motor-to-motor variation', loc='left', fontsize=9.5)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig07_kff_artefact.png'); plt.close()
print('ok')
