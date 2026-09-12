"""Figure 30 — the operator's own annotated dashboard screenshots, same three drives.

Figure 29 reconstructs the three commissioning maps from the saved PGM/YAML, which
is reproducible from source but is a re-rendering. These three are the actual
dashboard screenshots taken during the drives themselves and hand-annotated at the
time (`docs/evidence/monday_recon/`, `docs/evidence/tuesday_repeat/`), not
regenerated — they are embedded here exactly as captured, the same way Figure 24
embeds real photographs rather than redrawing them.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import matplotlib.image as mpimg
import matplotlib.patches as mp

EV = f'{REPO}/docs/evidence'
im1 = mpimg.imread(f'{EV}/monday_recon/front_leg_map_annotated.png')
im2 = mpimg.imread(f'{EV}/monday_recon/right_leg_map_annotated.png')
im3 = mpimg.imread(f'{EV}/tuesday_repeat/front_leg_repeat_annotated.png')

capt = [
    (im1, '(a) front leg, 31 Aug', '0.577 m return'),
    (im2, '(b) right leg, 31 Aug', '0.085 m return — the best on record'),
    (im3, '(c) front leg re-driven, 1 Sep', '0.209 m return, 0.857 m worst single correction'),
]
# Equal column widths would letterbox the wider two against the near-square
# middle shot. Sizing each column to its own image's aspect ratio instead fills
# every panel at the same height, so the row reads as one figure, not three.
aspects = [im.shape[1] / im.shape[0] for im, _, _ in capt]
row_h = 2.5
fig = plt.figure(figsize=(sum(aspects) * row_h + 1.0, row_h + 1.9))
gs = fig.add_gridspec(1, 3, width_ratios=aspects, wspace=0.08)

for k, (im, title, sub) in enumerate(capt):
    ax = fig.add_subplot(gs[k])
    ax.imshow(im); ax.axis('off')
    ax.set_title(f'{title}\n{sub}', loc='left', fontsize=8.4)

# The default axes margins are a fixed fraction of figure height, tuned for a
# much taller figure; on this one they left more blank space above and below
# the row than the row itself. Pinning them directly gives the images the room.
fig.subplots_adjust(top=0.80, bottom=0.06, left=0.01, right=0.99)

fig.text(0.01, -0.04,
         'green = SLAM-estimated path   ·   blue = wheel odometry   ·   yellow = correction event'
         '   ·   red = doubled wall',
         fontsize=7.6, color=C['neutral'])
fig.suptitle('The same three drives, from the operator\'s own dashboard screenshots rather than '
             'reconstructed from the saved map.\nWhere the SLAM and wheel traces run together the '
             'return was good (b); where they separate into a loop it was not (a, c).',
             fontsize=9.3, y=1.08, x=0.02, ha='left')
plt.savefig(f'{FIGDIR}/fig30_dashboard_screenshots.png', bbox_inches='tight')
print('ok')
