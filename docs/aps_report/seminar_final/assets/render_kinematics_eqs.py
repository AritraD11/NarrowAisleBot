#!/usr/bin/env python3
"""Render the slide-7 kinematics equations as typeset PNGs (mathtext).

    python3 docs/aps_report/seminar_final/assets/render_kinematics_eqs.py

Not part of the main asset pipeline (extract_figs.py / crop_figs.py /
prep_photos.py) because it needs matplotlib, which the rest of the deck
build does not depend on. Outputs are committed directly to
assets/context/ rather than regenerated on every build, the same way the
externally-sourced context photos are.
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'context')
INK = '#1A2230'
ACCENT = '#1F4E79'

plt.rcParams['mathtext.fontset'] = 'cm'
plt.rcParams['font.size'] = 20


def render(tex_lines, name, color=INK, fontsize=20, line_gap=0.62):
    fig = plt.figure(figsize=(6, 0.62 * len(tex_lines) + 0.15))
    fig.patch.set_alpha(0)
    for i, tex in enumerate(tex_lines):
        y = 1 - (i + 0.55) / len(tex_lines)
        fig.text(0.0, y, tex, fontsize=fontsize, color=color, ha='left', va='center')
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=220, transparent=True, bbox_inches='tight', pad_inches=0.06)
    plt.close(fig)
    print(name)


render([
    r'$\omega_{FR} = \dfrac{1}{a}\left(u + v + r(l_1+d)\right)$',
    r'$\omega_{FL} = \dfrac{1}{a}\left(u - v - r(l_2+d)\right)$',
    r'$\omega_{RR} = \dfrac{1}{a}\left(u - v + r(l_2+d)\right)$',
    r'$\omega_{RL} = \dfrac{1}{a}\left(u + v - r(l_1+d)\right)$',
], 'eq_inverse_kinematics.png', color=ACCENT, fontsize=19)

render([
    r'$v_x = \dfrac{a}{4}(\omega_{FR}+\omega_{FL}+\omega_{RR}+\omega_{RL})$',
    r'$v_y = \dfrac{a}{4}(\omega_{FR}-\omega_{FL}-\omega_{RR}+\omega_{RL})$',
    r'$\omega_z = \dfrac{a}{2(l_1+l_2+2d)}(\omega_{FR}-\omega_{FL}+\omega_{RR}-\omega_{RL})$',
], 'eq_forward_kinematics.png', color=ACCENT, fontsize=19)

render([
    r'$l_1=0.403\,\mathrm{m}\quad l_2=0.333\,\mathrm{m}\quad d=0.1577\,\mathrm{m}$',
    r'$a=0.0762\,\mathrm{m\ (wheel\ radius)}$',
    r'$u=v_x\ \mathrm{(forward)}\quad v=v_y\ \mathrm{(lateral)}\quad r=\omega_z\ \mathrm{(yaw\ rate)}$',
], 'eq_kinematics_legend.png', color='#838E9F', fontsize=16)
