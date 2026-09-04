import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import matplotlib.image as mpimg
import matplotlib.patches as mp
import numpy as np

P = f'{REPO}/docs/robot_photos'
im1 = mpimg.imread(f'{P}/2026-08-11_orientation_fix/block_at_front.jpg')
im2 = mpimg.imread(f'{P}/2026-08-11_recalibration_cw/map_cw_000_marked.png')
im3 = mpimg.imread(f'{P}/2026-08-11_orientation_fix/forward_drive_frame_start.jpg')
im4 = mpimg.imread(f'{P}/2026-08-11_orientation_fix/forward_drive_frame_end.jpg')

# crop the Foxglove 3D panel out of the full window screenshot
h, w = im2.shape[:2]
im2c = im2[int(0.08*h):int(0.965*h), int(0.268*w):int(0.998*w)]

fig = plt.figure(figsize=(10.2, 6.6))
gs = fig.add_gridspec(2, 3, height_ratios=[1.45, 1], hspace=0.13, wspace=0.14)

ax1 = fig.add_subplot(gs[0, 0:2])
ax1.imshow(im1); ax1.axis('off')
ax1.set_title('(a) Top-down, axis convention marked by hand. Reference block at the\n'
              'robot\'s front; LiDAR on top of the battery (mount position 2).',
              loc='left', fontsize=8.2)

ax2 = fig.add_subplot(gs[0, 2])
ax2.imshow(im2c); ax2.axis('off')
ax2.set_title('(b) The same instant in Foxglove:\n'
              'scan points, TF axes, 0.5 m grid.', loc='left', fontsize=8.2)

for k, (im, cap) in enumerate([(im3, '(c) forward-drive test, start frame'),
                               (im4, '(d) same test, end frame')]):
    axk = fig.add_subplot(gs[1, k])
    axk.imshow(im[:int(0.945*im.shape[0]), :]); axk.axis('off')
    axk.set_title(cap, loc='left', fontsize=8.2)

ax5 = fig.add_subplot(gs[1, 2]); ax5.axis('off')
ax5.set_xlim(0,1); ax5.set_ylim(0,1)
ax5.add_patch(mp.FancyBboxPatch((0.02, 0.06), 0.96, 0.88, boxstyle='round,pad=0.02',
                                fc='#eef2f6', ec=C['telemetry'], lw=1.0,
                                transform=ax5.transAxes))
ax5.text(0.5, 0.86,
         'Why these frames matter',
         ha='center', va='top', fontsize=8.4, fontweight='bold',
         color=C['telemetry'], transform=ax5.transAxes)
ax5.text(0.5, 0.71,
         'Driving toward a placed block while\n'
         'watching its position close in the map\n'
         'is what established the LiDAR angle\n'
         'convention. That recording predates the\n'
         'later drift symptom, which is why the\n'
         'correction was applied to odometry and\n'
         'not to the LiDAR.',
         ha='center', va='top', fontsize=7.2, transform=ax5.transAxes, linespacing=1.75)

fig.suptitle('The physical platform and the measurements taken on it, 11 August 2026',
             fontsize=9.6, y=0.965, x=0.02, ha='left')
plt.savefig(f'{FIGDIR}/fig24_platform_photos.png', bbox_inches='tight')
print('ok')
