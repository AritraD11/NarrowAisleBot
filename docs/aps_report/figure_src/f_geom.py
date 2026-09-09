import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.4, 4.3),
                              gridspec_kw={'width_ratios':[1.5,1]})

l1, l2, d, rw = 0.403, 0.333, 0.15769, 0.0762
L, W = 1.00, 0.36

ax.set_aspect('equal')
ax.add_patch(mp.Rectangle((-L/2, -W/2), L, W, fc='#eef2f6', ec=C['neutral'], lw=1.3, zorder=1))

wheels = [( l1,  d, 'FR', 'outer'), ( l2, -d, 'FL', 'inner'),
          (-l2,  d, 'RR', 'inner'), (-l1, -d, 'RL', 'outer')]
wl, wt = 0.15, 0.055
for x, y, lab, kind in wheels:
    col = C['telemetry'] if kind == 'outer' else C['command']
    ax.add_patch(mp.Rectangle((x-wl/2, y-wt/2), wl, wt, fc=col, ec='k', lw=0.7, zorder=3))
    sgn = 1 if kind == 'outer' else -1
    for k in np.linspace(-wl/2+0.012, wl/2-0.012, 5):
        ax.plot([x+k-0.014*sgn, x+k+0.014*sgn], [y-wt/2+0.006, y+wt/2-0.006],
                color='w', lw=0.9, zorder=4)
    ax.text(x, y + (0.055 if y > 0 else -0.055), lab, ha='center',
            va='bottom' if y > 0 else 'top', fontsize=9.5, fontweight='bold', color=col)

ax.plot(0, 0, marker='+', ms=11, mew=1.6, color='k', zorder=5)
ax.text(0.015, 0.015, 'body centre', fontsize=7.5)
ax.annotate('', xy=(0.16, 0), xytext=(0, 0),
            arrowprops=dict(arrowstyle='->', color='k', lw=1.0))
ax.text(0.17, 0.002, '+X  (drive fwd)', fontsize=7, va='center')

def dim(x0, x1, y, txt, col):
    ax.annotate('', xy=(x1, y), xytext=(x0, y),
                arrowprops=dict(arrowstyle='<->', color=col, lw=1.1))
    ax.text((x0+x1)/2, y+0.014, txt, ha='center', va='bottom', fontsize=8.2, color=col)

dim(0, l1, 0.315, r'$l_1 = 403$ mm   FR, RL  (outer)', C['telemetry'])
dim(0, l2, 0.245, r'$l_2 = 333$ mm   FL, RR  (inner)', C['command'])
ax.plot([l1, l1], [d, 0.315], color=C['telemetry'], lw=0.6, ls=':')
ax.plot([l2, l2], [-d, 0.245], color=C['command'], lw=0.6, ls=':')
ax.plot([0, 0], [0, 0.315], color='k', lw=0.6, ls=':')

ax.annotate('', xy=(-0.60, d), xytext=(-0.60, -d),
            arrowprops=dict(arrowstyle='<->', color=C['neutral'], lw=1.1))
ax.text(-0.615, 0, r'$2d = 315$ mm', rotation=90, ha='right', va='center',
        fontsize=8, color=C['neutral'])
ax.plot([-l1, -0.60], [-d, -d], color=C['neutral'], lw=0.6, ls=':')
ax.plot([-l2, -0.60], [ d,  d], color=C['neutral'], lw=0.6, ls=':')

# asymmetry offset: shade the 70 mm band rather than draw a 70 mm arrow
ax.add_patch(mp.Rectangle((l2, -0.30), l1-l2, 0.60, fc=C['defect'], alpha=0.13,
                          ec=C['defect'], lw=0.8, ls='--', zorder=2))
ax.annotate(r'$l_1 - l_2 = 70$ mm' + '\nthe asymmetry offset',
            xy=((l1+l2)/2, -0.30), xytext=(0.10, -0.415),
            fontsize=8.5, color=C['defect'], fontweight='bold', ha='center', va='center',
            arrowprops=dict(arrowstyle='->', color=C['defect'], lw=1.0,
                            connectionstyle='arc3,rad=-0.25'))

ax.set_xlim(-0.70, 0.72); ax.set_ylim(-0.48, 0.40)
ax.set_xlabel('longitudinal (m)'); ax.set_ylabel('lateral (m)')
ax.set_title('(a) Plan view, to scale.  Footprint tape-measured 1.00 × 0.36 m (§17.7)', loc='left')
ax.grid(alpha=0.12)

# ---- RIGHT: the IK coefficient matrix -------------------------------------
ax2.axis('off'); ax2.set_xlim(0,1); ax2.set_ylim(0,1)
T = ax2.transAxes
ax2.set_title('(b) Each wheel gets its own coefficient', loc='left')

def t2(x, y, s, **kw):
    kw.setdefault('transform', T); return ax2.text(x, y, s, **kw)

rows = [('FR', '+1', '+1', r'$+K_{o}$', 'outer'),
        ('FL', '+1', r'$-1$', r'$-K_{i}$', 'inner'),
        ('RR', '+1', r'$-1$', r'$+K_{i}$', 'inner'),
        ('RL', '+1', '+1', r'$-K_{o}$', 'outer')]
t2(0.5, 0.99, r'$\omega_i \;=\; (1/r_w)\;\times\;$[ row ]$\;\cdot\;(u,\,v,\,r)$',
   ha='center', va='top', fontsize=9.5)
cx = [0.13, 0.40, 0.585, 0.80]
for x, lab in zip(cx[1:], [r'$u$ fwd', r'$v$ strafe', r'$r$ yaw']):
    t2(x, 0.83, lab, ha='center', fontsize=8.5, color=C['neutral'])
for k, (m, a, b, c, kind) in enumerate(rows):
    y = 0.71 - k*0.115
    col = C['telemetry'] if kind == 'outer' else C['command']
    ax2.add_patch(mp.Rectangle((cx[3]-0.115, y-0.035), 0.23, 0.078,
                               fc=col, alpha=0.16, ec=col, lw=0.8, transform=T, zorder=0))
    t2(cx[0], y, m, ha='center', va='center', fontsize=9.5, fontweight='bold', color=col)
    t2(cx[1], y, a, ha='center', va='center', fontsize=9.5)
    t2(cx[2], y, b, ha='center', va='center', fontsize=9.5)
    t2(cx[3], y, c, ha='center', va='center', fontsize=10, color=col, fontweight='bold')
ax2.plot([0.255, 0.255], [0.225, 0.775], color='k', lw=0.9, transform=T, clip_on=False)
ax2.plot([0.945, 0.945], [0.225, 0.775], color='k', lw=0.9, transform=T, clip_on=False)

t2(0.5, 0.155, r'$K_{o}=l_1+d=0.5607$ m        $K_{i}=l_2+d=0.4907$ m',
   ha='center', va='center', fontsize=8.5)
ax2.add_patch(mp.Rectangle((0.01, 0.005), 0.98, 0.115, fc='#fdecea',
                           ec=C['defect'], lw=0.9, transform=T, zorder=0))
t2(0.5, 0.0625, 'One symmetric $K$ substituted anywhere in this column silently\n'
                'converts the robot to a conventional platform in that code path',
   ha='center', va='center', fontsize=7.8, color=C['defect'])

plt.subplots_adjust(wspace=0.22)
plt.savefig(f'{FIGDIR}/fig01_asymmetric_geometry.png')
print('ok')
