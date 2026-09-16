"""Figure 13 - the three commissioning maps of 15 September, from the saved PGM/YAML.

These are the runs whose acceptance-criteria figures Section 6.4 reports. The
earlier version of this figure plotted the 31 Aug / 1 Sep drives instead, so the
maps shown and the numbers quoted came from different experiments.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np, csv

EV = f'{REPO}/docs/evidence/circular_loop_15sep'
RUNS = [
    ('first attempt',            'run_20260915_131800', C['defect']),
    ('second attempt',           'run_20260915_140253', C['command']),
    ('third attempt, RAW gate',  'run_20260915_154615', C['fixed']),
]
UNKNOWN = 205


def read_pgm(path):
    with open(path, 'rb') as f:
        assert f.readline().strip() == b'P5'
        w, h = (int(v) for v in f.readline().split())
        maxval = int(f.readline())
        return np.frombuffer(f.read(w*h), dtype=np.uint8).reshape(h, w), maxval


def read_yaml(path):
    meta = {}
    for line in open(path):
        if ':' in line:
            k, v = line.split(':', 1); meta[k.strip()] = v.strip()
    res = float(meta['resolution'])
    ox, oy = (float(v) for v in meta['origin'].strip('[]').split(',')[:2])
    return res, ox, oy


def read_pose(path):
    xs, ys = [], []
    for r in csv.DictReader(open(path)):
        try:
            x, y = float(r['map_x']), float(r['map_y'])
        except (TypeError, ValueError, KeyError):
            continue
        if np.isfinite(x) and np.isfinite(y):
            xs.append(x); ys.append(y)
    return np.array(xs), np.array(ys)


fig, axes = plt.subplots(1, 3, figsize=(11.0, 4.2))
for ax, (name, stem, col) in zip(axes, RUNS):
    img, _ = read_pgm(f'{EV}/{stem}.pgm')
    res, ox, oy = read_yaml(f'{EV}/{stem}.yaml')
    h, w = img.shape
    extent = [ox, ox + w*res, oy, oy + h*res]
    unk = float((img == UNKNOWN).sum()) / img.size * 100.0
    occ = int((img <= 50).sum())

    shown = np.full(img.shape, 1.0)
    shown[img == UNKNOWN] = 0.80          # grey, never observed
    shown[img <= 50] = 0.0                # black, occupied
    ax.imshow(shown, cmap='gray', vmin=0, vmax=1, origin='lower',
              extent=extent, interpolation='nearest')

    xs, ys = read_pose(f'{EV}/{stem}_pose.csv')
    if len(xs):
        ax.plot(xs, ys, color=col, lw=1.1, alpha=0.9, zorder=3)
        ax.plot(xs[0], ys[0], 'o', mfc='none', mec=col, ms=7, mew=1.4, zorder=4)

    ax.set_title(f'{name}\n{unk:.1f} % unclassified  ·  {occ} occupied cells',
                 loc='left', fontsize=8.4)
    ax.set_xlabel('map x (m)')
    ax.set_aspect('equal')
axes[0].set_ylabel('map y (m)')

fig.legend(handles=[
    plt.Line2D([], [], color=C['neutral'], lw=1.4, label='path driven'),
    plt.Line2D([], [], marker='o', ls='none', mfc='none', mec=C['neutral'],
               ms=7, label='start and return mark'),
], loc='lower center', ncol=2, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.02))

fig.suptitle('The three commissioning maps of 15 September, rendered from the saved occupancy grids.\n'
             'Grey is never observed. Unclassified percentage is computed over the whole allocated '
             'grid, including cells the robot could not reach.',
             fontsize=9.3, y=1.06, x=0.02, ha='left')
plt.savefig(f'{FIGDIR}/fig29_field_maps.png', bbox_inches='tight')
print('ok')
