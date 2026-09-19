"""The kinematic basis: the symmetric mecanum layout against the non-collinear
one established by the prior work, and what changes in the transformation.

Drawn from this project's own implementation of that geometry (the constants in
aislebot_esp32.ino and the derivation in docs/), at the dimensions of the built
machine. It is not a reproduction of the prior paper's own figure.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *
import matplotlib.patches as mp
import numpy as np

fig, ax = canvas(13.4, 8.0, 100, 62)

title(ax, 0.5, 61.6,
      'Wheel layout and the inverse kinematics that follow from it',
      'Both layouts give the same three planar degrees of freedom. Moving one diagonal pair inward decouples the\n'
      'vehicle width from the wheel rectangle, at the cost of a second yaw lever arm in the transformation.')

MM = 0.034
D = 157.69 * MM
L1, L2 = 403 * MM, 333 * MM
WL, WW = 152.4 * MM, 60 * MM
PL, PW = 1000 * MM, 250 * MM
CY = 40.0


def wheel(cx, cy, hand):
    """A mecanum wheel in plan. The rollers sit at 45 degrees, and the two
    diagonal pairs take opposite handedness — that is what makes the drive
    omnidirectional rather than merely four-wheel."""
    x0, y0 = cx - WL / 2, cy - WW / 2
    r = mp.Rectangle((x0, y0), WL, WW, fc='#dfe6ec', ec='#33475b', lw=1.1,
                     zorder=5)
    ax.add_patch(r)
    ya, yb = (0, WW) if hand > 0 else (WW, 0)
    for t in np.arange(-WW, WL + 0.01, 0.52):
        ln, = ax.plot([x0 + t, x0 + t + WW], [y0 + ya, y0 + yb],
                      color='#8496a8', lw=0.7, zorder=6)
        ln.set_clip_path(r)


def plan(cx, lf, lr, tag):
    ax.add_patch(mp.Rectangle((cx - PL / 2, CY - PW / 2), PL, PW, fc='#f1f4f7',
                              ec='#9aa8b5', lw=1.0, zorder=3))
    ax.plot([cx, cx], [CY - PW / 2 - 4.6, CY + PW / 2 + 4.6], color=P['grey'],
            lw=0.8, ls=(0, (6, 3, 1, 3)), zorder=4)
    for nm, wx, wy, hand in (('FR', cx + lf, CY - D, -1),
                             ('FL', cx + lr, CY + D, +1),
                             ('RR', cx - lr, CY - D, +1),
                             ('RL', cx - lf, CY + D, -1)):
        wheel(wx, wy, hand)
        ax.text(wx, wy + (2.7 if wy > CY else -2.7), nm, ha='center',
                va='center', fontsize=8.4, fontweight='bold', color='#33475b',
                zorder=8)
    arr(ax, (cx, CY), (cx + 5.8, CY), 'cmd', lw=1.3, zorder=9)
    arr(ax, (cx, CY), (cx, CY - 4.6), 'cmd', lw=1.3, zorder=9)
    ax.text(cx + 6.5, CY, r'$u$', fontsize=9.8, ha='left', va='center', zorder=9)
    ax.text(cx + 0.8, CY - 5.4, r'$v$', fontsize=9.8, ha='left', va='center', zorder=9)
    ax.text(cx, 50.2, tag, ha='center', va='bottom', fontsize=9.8,
            fontweight='bold', zorder=9)


plan(24.0, L1, L1, '(a)  Symmetric: all four wheels on one rectangle')
plan(74.0, L1, L2, '(b)  Non-collinear: one diagonal pair moved inward')


def dimx(x0, x1, y, lab, col='tel', above=True):
    ax.annotate('', xy=(x1, y), xytext=(x0, y),
                arrowprops=dict(arrowstyle='<|-|>', color=P[col], lw=1.1,
                                mutation_scale=10), zorder=9)
    ax.text((x0 + x1) / 2, y + (0.6 if above else -0.6), lab, ha='center',
            va='bottom' if above else 'top', fontsize=8.6, color=P[col],
            zorder=10, bbox=dict(fc='white', ec='none', pad=0.15))


dimx(24.0, 24.0 + L1, 42.5, r'$l = 403$ mm', 'tel')
dimx(74.0, 74.0 + L1, 42.5, r'$l_1 = 403$ mm  (outer)', 'tel')
dimx(74.0 - L2, 74.0, 42.5, r'$l_2 = 333$ mm  (inner)', 'new')
for cx in (24.0, 74.0):
    ax.annotate('', xy=(cx - 18.2, CY + D), xytext=(cx - 18.2, CY),
                arrowprops=dict(arrowstyle='<|-|>', color=P['note'], lw=1.1,
                                mutation_scale=10), zorder=9)
    ax.text(cx - 18.9, CY + D / 2, r'$d$', ha='right', va='center', fontsize=9.4,
            color=P['note'], zorder=10)
ax.text(24.0, 31.2, r'$d = 157.69$ mm, the same for all four wheels',
        ha='center', va='top', fontsize=8.6, color=P['note'], zorder=10)

# ── the transformation ───────────────────────────────────────────────
box(ax, 2.0, 15.5, 44.0, 12.8, '', 'tel', fc='tel')
ax.text(24.0, 26.4, 'One yaw lever arm, shared by all four wheels',
        ha='center', va='center', fontsize=8.9, fontweight='bold', zorder=6)
ax.text(24.0, 23.2, r'$K = l + d = 0.5607$ m', ha='center', va='center',
        fontsize=10.2, zorder=6)
ax.text(24.0, 19.0, r'$\omega_i = \frac{1}{r}\left(u \pm v \pm K\,\omega\right)$'
        '      for every wheel', ha='center', va='center', fontsize=10.6, zorder=6)

box(ax, 54.0, 15.5, 44.0, 12.8, '', 'new', fc='new')
ax.text(76.0, 26.7, 'Two lever arms, one for each diagonal pair',
        ha='center', va='center', fontsize=8.9, fontweight='bold', zorder=6)
ax.text(76.0, 23.9, r'$K_o = l_1 + d = 0.5607$ m,    $K_i = l_2 + d = 0.4907$ m',
        ha='center', va='center', fontsize=9.6, zorder=6)
ax.text(76.0, 20.2,
        r'$\omega_{\mathrm{FR}} = \frac{1}{r}(u + v + K_o\,\omega)$,     '
        r'$\omega_{\mathrm{FL}} = \frac{1}{r}(u - v - K_i\,\omega)$',
        ha='center', va='center', fontsize=10.2, zorder=6)
ax.text(76.0, 17.2,
        r'$\omega_{\mathrm{RR}} = \frac{1}{r}(u - v + K_i\,\omega)$,     '
        r'$\omega_{\mathrm{RL}} = \frac{1}{r}(u + v - K_o\,\omega)$',
        ha='center', va='center', fontsize=10.2, zorder=6)

summ(ax, 2.0, 2.0, 96.0, 9.2,
     'The translation terms are untouched. $u$ and $v$ enter every wheel with unit weight in both layouts, which is why '
     'straight-line and lateral motion\nbehave identically on the two. Only the yaw column changes. A symmetric platform '
     'has one coefficient to get right; this one has two, and they differ\nby 14 per cent, so a wheel driven with the '
     'wrong arm produces a yaw rate wrong by that much, and nothing else in the transformation reveals it.\n'
     '$r$ is the wheel radius, 76.2 mm. $u$ is forward, $v$ is lateral to the right, and $\\omega$ is yaw, positive anticlockwise.',
     'grey', fs=8.4)

save(fig, 'fig35_prior_kinematics.png')
