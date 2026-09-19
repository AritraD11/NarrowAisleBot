"""Per-wheel velocity loop as the deployed firmware actually runs it.

Every constant here is read off aislebot_esp32.ino rather than off an earlier
draft: the loop runs at 100 Hz, the gains are Kp 45 / Ki 250 / Kd 0.5, and the
feedforward is Kff*w + Kstat*sgn(w) — the viscous term on the velocity, the
static term on its sign. Two earlier diagrams had those two the other way round
and carried the bench-calibration sketch's gains instead of the deployed ones.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *

fig, ax = canvas(13.4, 7.5, 100, 56)

title(ax, 0.5, 55.6,
      'Per-wheel velocity loop, firmware v3.0',
      'One of these runs per wheel, at 100 Hz. The feedforward supplies most of the drive and the PID\n'
      'corrects only what the feedforward gets wrong. The three green blocks are what v3.0 added.')

# ── feedforward ──────────────────────────────────────────────────────
band(ax, 38.5, 36.0, 31.0, 7.6, 'Feedforward path (v3.0)', 'new')
ff = box(ax, 40.0, 37.3, 28.0, 5.2,
         'two-term feedforward\n'
         r'$K_{\mathrm{ff}}\,\omega_{\mathrm{cmd}} + K_{\mathrm{stat}}\cdot\mathrm{sgn}(\omega_{\mathrm{cmd}})$'
         '\n' r'$K_{\mathrm{ff}} \approx 38$ PWM per rad/s,  $K_{\mathrm{stat}} \approx 8$ PWM',
         'new', fc='new', fs=8.4)

band(ax, 73.0, 36.0, 26.0, 7.6, '', 'new')
ax.text(73.0 + 13.0, 36.0 + 3.8,
        'dynamic anti-windup:\nthe integral is clamped to the PWM\n'
        'headroom left after FF + P + D', ha='center', va='center',
        fontsize=8.4, zorder=5, linespacing=1.45)

# ── command path ─────────────────────────────────────────────────────
band(ax, 1.0, 18.4, 29.0, 9.2, 'Command / reference path', 'cmd')
sp = box(ax, 2.5, 20.1, 11.8, 5.8,
         'setpoint\n' r'$\omega_{\mathrm{cmd}}$  rad/s', 'cmd', fc='cmd', fs=8.8)
sl = box(ax, 17.0, 20.1, 11.8, 5.8,
         'slew limit\n' r'12 rad/s$^2$', 'cmd', fc='cmd', fs=8.8)

s1 = node(ax, 34.2, 23.0, 2.2)
ax.text(31.2, 25.6, '+', fontsize=13, ha='center', va='center')
ax.text(31.2, 20.4, r'$-$', fontsize=13, ha='center', va='center')

# ── PID ──────────────────────────────────────────────────────────────
band(ax, 39.0, 13.2, 23.5, 18.0, 'PID controller (v3.0)', 'note')
p_ = box(ax, 40.3, 26.2, 20.9, 4.0,
         r'P:  $K_p\,e$,     $K_p = 45$', 'note', fc='note', fs=8.8)
i_ = box(ax, 40.3, 21.0, 20.9, 4.0,
         r'I:  $K_i \int e\,dt$,   $K_i = 250$', 'note', fc='note', fs=8.8)
d_ = box(ax, 40.3, 15.8, 20.9, 4.0,
         r'D:  $-K_d\,\dot{y}$,   $K_d = 0.5$', 'note', fc='note', fs=8.8)
ax.text(50.75, 14.4, r'fixed gains, 100 Hz  ($\Delta t = 10$ ms)', ha='center',
        va='center', fontsize=8.2, color=P['note'], zorder=5)

s2 = node(ax, 67.0, 23.0, 2.2)

# ── actuation ────────────────────────────────────────────────────────
band(ax, 71.8, 18.4, 27.2, 9.2, 'Actuation path', 'cmd')
pw = box(ax, 73.2, 20.1, 11.6, 5.8,
         'PWM + DIR\n5 kHz, 8-bit\nmin output 5', 'cmd', fc='cmd', fs=8.4)
dr = box(ax, 86.0, 20.1, 11.6, 5.8,
         'MDD20A\n' r'$\rightarrow$ RMCS-2086' '\n' r'$\rightarrow$ mecanum wheel',
         'cmd', fc='cmd', fs=8.4)

# ── measurement ──────────────────────────────────────────────────────
band(ax, 24.0, 3.0, 74.0, 8.0, '', 'note')
ax.text(24.4, 1.9, 'Encoder feedback / measurement path', ha='left', va='top',
        fontsize=9.4, fontweight='bold', color=P['note'], zorder=9)
em = box(ax, 26.0, 4.2, 20.0, 5.6,
         'EMA velocity filter\n' r'$\alpha = 0.4$', 'note', fc='note', fs=8.8)
cp = box(ax, 49.5, 4.2, 22.0, 5.6,
         'per-motor CPR\n'
         r'$\omega_i = \dfrac{\Delta\,\mathrm{counts}}{\mathrm{CPR}(i)}\cdot\dfrac{2\pi}{\Delta t}$',
         'new', fc='new', fs=8.6)
pc = box(ax, 75.0, 4.2, 21.5, 5.6,
         'PCNT hardware\nquadrature counter', 'note', fc='note', fs=8.8)

# ── wiring ───────────────────────────────────────────────────────────
arr(ax, R(sp), L(sl), 'cmd')
arr(ax, R(sl), (s1[0] - s1[2], s1[1]), 'cmd')
ax.text(37.2, 24.4, r'$e$', fontsize=10.5, ha='center', va='center', zorder=8)
for b in (p_, i_, d_):
    arr(ax, (s1[0] + s1[2], s1[1]), L(b), 'cmd', lw=1.2)
    arr(ax, R(b), (s2[0] - s2[2], s2[1]), 'note', lw=1.2)
arr(ax, (67.0, 37.3), (67.0, 25.2), 'new', lw=1.8)
arr(ax, R(ff), (72.3, 39.8), 'new', ls='--', lw=1.3)
arr(ax, (s2[0] + s2[2], s2[1]), L(pw), 'cmd')
arr(ax, R(pw), L(dr), 'cmd')

route(ax, [(91.8, 20.1), (91.8, 13.2), (85.75, 13.2), (85.75, 9.8)], 'tel')
ax.text(90.6, 15.8, 'A/B through the\nlevel shifter', ha='right', va='center',
        fontsize=7.9, color=P['tel'], zorder=8, linespacing=1.35)
arr(ax, L(pc), R(cp), 'tel')
arr(ax, L(cp), R(em), 'tel')
route(ax, [(36.0, 9.8), (36.0, 12.4), (34.2, 12.4), (34.2, 20.8)], 'tel')
ax.text(33.0, 13.4, r'measured  $\omega_i$', ha='right', va='center',
        fontsize=8.3, color=P['tel'], zorder=8)

ax.text(1.0, 16.6,
        'D acts on the measurement, not on\nthe error, so a setpoint step produces\nno derivative kick.',
        ha='left', va='top', fontsize=8.2, color=P['note'], zorder=8,
        linespacing=1.45)
ax.text(1.0, 9.6,
        r'$K_{\mathrm{stat}}$ is faded in across 0.05 to 0.20 rad/s'
        '\nrather than stepped in at any non-zero\ncommand.',
        ha='left', va='top', fontsize=8.2, color=P['new'], zorder=8,
        linespacing=1.45)

save(fig, 'fig33_pid_loop.png')
