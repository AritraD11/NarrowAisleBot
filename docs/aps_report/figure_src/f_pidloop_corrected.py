"""Per-wheel velocity loop, CORRECTED wiring.

Same layout and numbers as f_pidloop.py, but fixes three wiring gaps found
by inspection:
  1. Feedforward never had a drawn input from the setpoint/slew-limit path,
     even though its own formula consumes omega_cmd.
  2. The anti-windup block had no drawn output anywhere, despite its stated
     job being to clamp the integral term.
  3. D was wired to the same error-junction output as P and I, contradicting
     the stated design ("D acts on the measurement, not the error") and
     showing no separate, heavier filter for the D path.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *

fig, ax = canvas(13.8, 8.2, 100, 62)

title(ax, 0.5, 61.0,
      'Per-wheel velocity loop, firmware v3.0 — corrected wiring',
      'Same numbers as before. Three connections added/rerouted so the arrows match what the\n'
      'boxes themselves claim: feedforward\'s input, anti-windup\'s output, and D\'s real source.',
      fs=13.0)

# ── feedforward ──────────────────────────────────────────────────────
band(ax, 38.5, 40.0, 31.0, 7.6, 'Feedforward path (v3.0)', 'new')
ff = box(ax, 40.0, 41.3, 28.0, 5.2,
         'two-term feedforward\n'
         r'$K_{\mathrm{ff}}\,\omega_{\mathrm{cmd}} + K_{\mathrm{stat}}\cdot\mathrm{sgn}(\omega_{\mathrm{cmd}})$'
         '\n' r'$K_{\mathrm{ff}} \approx 38$ PWM per rad/s,  $K_{\mathrm{stat}} \approx 8$ PWM',
         'new', fc='new', fs=8.4)

band(ax, 73.0, 40.0, 26.0, 7.6, '', 'new')
awbox = (73.0, 40.0, 26.0, 7.6)
ax.text(73.0 + 13.0, 40.0 + 3.8,
        'dynamic anti-windup:\nthe integral is clamped to the PWM\n'
        'headroom left after FF + P + D', ha='center', va='center',
        fontsize=8.4, zorder=5, linespacing=1.45)

# ── command path ─────────────────────────────────────────────────────
band(ax, 1.0, 22.4, 29.0, 9.2, 'Command / reference path', 'cmd')
sp = box(ax, 2.5, 24.1, 11.8, 5.8,
         'setpoint\n' r'$\omega_{\mathrm{cmd}}$  rad/s', 'cmd', fc='cmd', fs=8.8)
sl = box(ax, 17.0, 24.1, 11.8, 5.8,
         'slew limit\n' r'12 rad/s$^2$', 'cmd', fc='cmd', fs=8.8)

s1 = node(ax, 34.2, 27.0, 2.2)
ax.text(31.2, 29.6, '+', fontsize=13, ha='center', va='center')
ax.text(31.2, 24.4, r'$-$', fontsize=13, ha='center', va='center')

# ── PID ──────────────────────────────────────────────────────────────
band(ax, 39.0, 17.2, 23.5, 18.0, 'PID controller (v3.0)', 'note')
p_ = box(ax, 40.3, 30.2, 20.9, 4.0,
         r'P:  $K_p\,e$,     $K_p = 45$', 'note', fc='note', fs=8.8)
i_ = box(ax, 40.3, 25.0, 20.9, 4.0,
         r'I:  $K_i \int e\,dt$,   $K_i = 250$', 'note', fc='note', fs=8.8)
d_ = box(ax, 40.3, 19.8, 20.9, 4.0,
         r'D:  $-K_d\,\dot{y}$,   $K_d = 0.5$', 'note', fc='note', fs=8.8)
ax.text(50.75, 18.4, r'fixed gains, 100 Hz  ($\Delta t = 10$ ms)', ha='center',
        va='center', fontsize=8.2, color=P['note'], zorder=5)

s2 = node(ax, 67.0, 27.0, 2.2)

# ── actuation ────────────────────────────────────────────────────────
band(ax, 71.8, 22.4, 27.2, 9.2, 'Actuation path', 'cmd')
pw = box(ax, 73.2, 24.1, 11.6, 5.8,
         'PWM + DIR\n5 kHz, 8-bit\nmin output 5', 'cmd', fc='cmd', fs=8.4)
dr = box(ax, 86.0, 24.1, 11.6, 5.8,
         'MDD20A\n' r'$\rightarrow$ RMCS-2086' '\n' r'$\rightarrow$ mecanum wheel',
         'cmd', fc='cmd', fs=8.4)

# ── measurement ──────────────────────────────────────────────────────
band(ax, 24.0, 5.0, 74.0, 8.0, '', 'note')
ax.text(24.4, 3.9, 'Encoder feedback / measurement path', ha='left', va='top',
        fontsize=9.4, fontweight='bold', color=P['note'], zorder=9)
em = box(ax, 26.0, 6.2, 20.0, 5.6,
         'EMA velocity filter\n' r'$\alpha = 0.4$', 'note', fc='note', fs=8.8)
cp = box(ax, 49.5, 6.2, 22.0, 5.6,
         'per-motor CPR\n'
         r'$\omega_i = \dfrac{\Delta\,\mathrm{counts}}{\mathrm{CPR}(i)}\cdot\dfrac{2\pi}{\Delta t}$',
         'new', fc='new', fs=8.6)
pc = box(ax, 75.0, 6.2, 21.5, 5.6,
         'PCNT hardware\nquadrature counter', 'note', fc='note', fs=8.8)

# ── NEW: the second, heavier filter that only feeds D ──────────────────
df = box(ax, 2.0, 13.3, 20.0, 4.4,
         'extra filter, D path only\nheavier than the shared filter',
         'bad', fc='bad', fs=7.6, tc=P['bad'])

# ── wiring ───────────────────────────────────────────────────────────
arr(ax, R(sp), L(sl), 'cmd')
arr(ax, R(sl), (s1[0] - s1[2], s1[1]), 'cmd')
ax.text(37.2, 28.4, r'$e$', fontsize=10.5, ha='center', va='center', zorder=8)

# P and I still come from the error node e, unchanged.
for b in (p_, i_):
    arr(ax, (s1[0] + s1[2], s1[1]), L(b), 'cmd', lw=1.2)
    arr(ax, R(b), (s2[0] - s2[2], s2[1]), 'note', lw=1.2)

# FIX 3a: D no longer comes from s1. It comes from the new D-only filter box.
route(ax, [T(df), (12.0, 21.8), L(d_)], 'bad', lw=1.4)
arr(ax, R(d_), (s2[0] - s2[2], s2[1]), 'note', lw=1.2)

# FIX 3b: the D-filter branches off the same measured-omega line everything
# else uses, then filters it further before D ever sees it.
arr(ax, (34.2, 15.4), R(df), 'bad', lw=1.4)
ax.text(23.0, 12.6, 'branched off the same\nmeasured line, filtered again',
        ha='center', va='top', fontsize=7.3, color=P['bad'], zorder=8,
        linespacing=1.25)

# feedforward output down into s2 (unchanged)
arr(ax, (67.0, 41.3), (67.0, 29.2), 'new', lw=1.8)

# FIX 1: feedforward's INPUT, branched off the same slew-limited setpoint
# that feeds the error node, not invented from nowhere.
route(ax, [(28.8, 27.0), (28.8, 44.0), (40.0, 44.0)], 'cmd', lw=1.6)
ax.text(29.5, 35.0, r'$\omega_{\mathrm{cmd}}$' '\n(same signal,\nbranched)',
        ha='left', va='center', fontsize=7.6, color=P['cmd'], zorder=8,
        linespacing=1.3)

# FIX 2: anti-windup's OUTPUT, actually reaching the I term it claims to
# clamp. Stays high (y=36.5) until it is past the actuation column, so it
# never crosses the A/B-through-the-level-shifter run near the bottom.
route(ax, [(86.0, 40.0), (86.0, 36.5), (62.0, 36.5), (62.0, 27.0)], 'new', lw=1.6)
ax.text(75.0, 37.3, 'clamps the integral term', ha='center', va='bottom',
        fontsize=7.6, color=P['new'], zorder=8)

arr(ax, R(ff), (72.3, 43.8), 'new', ls='--', lw=1.3)
arr(ax, (s2[0] + s2[2], s2[1]), L(pw), 'cmd')
arr(ax, R(pw), L(dr), 'cmd')

route(ax, [(91.8, 24.1), (91.8, 17.2), (85.75, 17.2), (85.75, 11.8)], 'tel')
ax.text(90.6, 19.8, 'A/B through the\nlevel shifter', ha='right', va='center',
        fontsize=7.9, color=P['tel'], zorder=8, linespacing=1.35)
arr(ax, L(pc), R(cp), 'tel')
arr(ax, L(cp), R(em), 'tel')
route(ax, [(36.0, 11.8), (36.0, 15.4), (34.2, 15.4), (34.2, 24.8)], 'tel')
ax.text(31.6, 18.5, r'measured  $\omega_i$', ha='right', va='center',
        fontsize=8.3, color=P['tel'], zorder=8)

ax.text(1.0, 20.6,
        'D now visibly acts on a separately\nfiltered measurement, not on e.\n'
        'A setpoint step still produces no kick.',
        ha='left', va='top', fontsize=8.2, color=P['bad'], zorder=8,
        linespacing=1.45)
ax.text(1.0, 4.0,
        r'$K_{\mathrm{stat}}$ is faded in across 0.05 to 0.20 rad/s'
        '\nrather than stepped in at any non-zero\ncommand.',
        ha='left', va='top', fontsize=8.2, color=P['new'], zorder=8,
        linespacing=1.45)

save(fig, 'fig33_pid_loop_corrected.png')
