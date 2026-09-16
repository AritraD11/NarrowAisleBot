"""Figure 4 — the per-wheel velocity loop as compiled in firmware v3.0.

A schematic rather than a plot: every constant on it is the compiled value in
Appendix A, and the three green blocks are what v3.0 changed. It is generated
like every other figure so that a gain edited in firmware can be corrected here
in one place instead of in an image nobody can regenerate.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg import *
import matplotlib.patches as mp

fig, ax = canvas(12.6, 6.2, 100, 67)
cmd, tel, grn, pur = C['command'], C['telemetry'], C['fixed'], C['accent']

ORANGE = dict(fc='#fdf1e3', ec=cmd, tc='k')
PURPLE = dict(fc='#efe9f6', ec=pur, tc='k')
GREEN  = dict(fc='#eaf5ea', ec=grn, tc='k')


def junction(x, y, r=2.1):
    ax.add_patch(mp.Circle((x, y), r, fc='white', ec='k', lw=1.1, zorder=6))
    ax.text(x, y, r'$\Sigma$', ha='center', va='center', fontsize=10, zorder=7)
    return (x, y)


# ---- forward path --------------------------------------------------------
b_sp   = box(ax, 1.0, 38.0, 13.5, 8.0, 'setpoint\n' + r'$\omega^{*}_{i}$  rad/s',
             fs=7.6, **ORANGE)
b_slew = box(ax, 17.5, 38.0, 13.5, 8.0, 'slew limit\n12 rad/s$^2$', fs=7.6, **ORANGE)
s1 = junction(36.5, 42.0)
b_p = box(ax, 43.0, 47.5, 17.0, 6.6, r'P:  $K_p e$,    $K_p = 45$',   fs=7.4, **PURPLE)
b_i = box(ax, 43.0, 38.7, 17.0, 6.6, r'I:  $K_i\!\int\! e\,dt$,   $K_i = 250$', fs=7.4, **PURPLE)
b_d = box(ax, 43.0, 29.9, 17.0, 6.6, r'D:  $-K_d \dot{y}$,   $K_d = 0.5$', fs=7.4, **PURPLE)
s2 = junction(66.5, 42.0)
b_pwm = box(ax, 72.0, 38.0, 12.5, 8.0, 'PWM + DIR\n5 kHz, 8-bit\ndeadband 5', fs=7.4, **ORANGE)
b_out = box(ax, 87.0, 38.0, 12.0, 8.0, 'MDD20A →\nRMCS-2086 →\nmecanum wheel', fs=7.4, **ORANGE)

arr(ax, R(b_sp), L(b_slew), cmd, lw=1.3)
arr(ax, R(b_slew), (s1[0]-2.1, s1[1]), cmd, lw=1.3)
ax.text(s1[0]-2.6, s1[1]+3.0, '+', fontsize=11, ha='center', va='center')
ax.text(s1[0]-2.6, s1[1]-3.4, r'$-$', fontsize=11, ha='center', va='center')

# error fans out to the three terms
ax.plot([s1[0]+2.1, 40.5], [42.0, 42.0], color=cmd, lw=1.3, zorder=5)
ax.plot([40.5, 40.5], [50.8, 33.2], color=cmd, lw=1.3, zorder=5)
for b in (b_p, b_i, b_d):
    arr(ax, (40.5, b[1]+b[3]/2), L(b), cmd, lw=1.3)
ax.text(38.6, 44.6, '$e$', fontsize=9, color=cmd, ha='center')

# and recombines into the second junction
ax.plot([62.5, 62.5], [50.8, 33.2], color=pur, lw=1.3, zorder=5)
for b in (b_p, b_i, b_d):
    ax.plot([R(b)[0], 62.5], [R(b)[1], R(b)[1]], color=pur, lw=1.3, zorder=5)
arr(ax, (62.5, 42.0), (s2[0]-2.1, 42.0), pur, lw=1.3)

arr(ax, (s2[0]+2.1, 42.0), L(b_pwm), cmd, lw=1.3)
arr(ax, R(b_pwm), L(b_out), cmd, lw=1.3)

# ---- the two feedforward terms, added after the PID sum -------------------
b_ff = box(ax, 40.0, 57.5, 27.0, 6.2,
           'two-term feedforward\n' + r'$K_{ff}\,\omega^{*} + K_{stat}\,\mathrm{sgn}(\omega^{*})$',
           fs=7.4, **GREEN)
arr(ax, (s2[0], b_ff[1]), (s2[0], s2[1]+2.1), grn, lw=1.6)

b_aw = box(ax, 71.0, 56.0, 28.0, 7.7,
           'dynamic anti-windup:\nclamp I to the PWM headroom\nleft after FF + P + D',
           fs=7.2, ls='--', **GREEN)
ax.plot([b_aw[0], 61.0], [b_aw[1]+1.0, b_aw[1]+1.0], color=grn, lw=1.1, ls='--', zorder=4)
arr(ax, (61.0, b_aw[1]+1.0), (61.0, b_i[1]+b_i[3]), grn, lw=1.1, ls='--')

# ---- feedback path -------------------------------------------------------
b_cnt = box(ax, 74.0, 6.0, 18.0, 11.5, 'PCNT hardware\nquadrature counter', fs=7.4, **PURPLE)
b_cpr = box(ax, 47.0, 6.0, 22.0, 11.5,
            'per-motor CPR\n\n' + r'$\omega_i = \dfrac{\Delta\,\mathrm{counts}}{\mathrm{CPR}[i]}\cdot\dfrac{2\pi}{\Delta t}$',
            fs=7.4, **GREEN)
b_ema = box(ax, 27.5, 6.0, 18.0, 11.5, 'EMA velocity filter\n' + r'$\alpha = 0.4$',
            fs=7.4, **PURPLE)

ax.plot([C_(b_out)[0], C_(b_out)[0]], [b_out[1], 11.75], color=tel, lw=1.3, zorder=4)
arr(ax, (C_(b_out)[0], 11.75), R(b_cnt), tel, lw=1.3)
ax.text(C_(b_out)[0]+0.8, 24.0, 'A/B through the\nlevel shifter', fontsize=6.9,
        color=tel, ha='left', va='center')
arr(ax, L(b_cnt), R(b_cpr), tel, lw=1.3)
arr(ax, L(b_cpr), R(b_ema), tel, lw=1.3)

# measurement back to the summing junction
arr(ax, T(b_ema), (36.5, s1[1]-2.1), tel, lw=1.3)
ax.text(35.2, 24.5, r'measured  $\omega_i$', fontsize=7.4, color=tel,
        ha='right', va='center', bbox=MASK)

# derivative is taken on the measurement, not on the error
ax.plot([30.0, 30.0], [17.5, 31.5], color=pur, lw=1.0, ls=':', zorder=4)
arr(ax, (30.0, 31.5), (43.0, 31.5), pur, lw=1.0, ls=':')
ax.text(14.5, 26.0,
        'D acts on the measurement,\nnot on the error: no kick\nwhen the Pi steps a setpoint',
        fontsize=6.9, color=pur, ha='center', va='center', linespacing=1.35, bbox=MASK)

ax.set_title('Per-wheel velocity loop as compiled in firmware v3.0. The three green blocks are the '
             'v3.0 changes.\nThe feedforward supplies most of the drive; the PID corrects only the '
             'residual.', loc='left', fontsize=9.5, y=1.0)
plt.tight_layout()
plt.savefig(f'{FIGDIR}/fig04_control_loop.png')
print('ok')
