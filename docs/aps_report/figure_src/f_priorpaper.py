"""The prior work's own chassis variants and kinematic schematic.

Panels (a) to (c) are reproduced from Arunkumar, Devkar, Vachhani and Kunwar,
'An omnidirectional asymmetric mobile robot for narrow aisle spaces', 2024
Tenth Indian Control Conference. They are the geometry this platform is built
on, in the notation that paper uses, so the symbols in Section 1.5 can be read
straight against them.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *
import matplotlib.image as mpimg

# the three crops beside this file were taken from page 2 of the paper's PDF
# in docs/, rendered at 4x and trimmed to their own bounding boxes
SRC = os.environ.get('NAB_PRIOR', os.path.dirname(os.path.abspath(__file__)))
fig, ax = canvas(13.0, 7.2, 100, 58)

title(ax, 0.5, 57.6,
      'The prior work: two chassis variants and the kinematic model',
      'Reproduced from the paper that established this geometry. Variant 1, in panel (a), is the arrangement\n'
      'the full-scale platform of this report is built on.')


def panel(path, x, y, w, h, tag, cap):
    """Place an image inside a data-coordinate box without distorting it.
    The axes are not square in data units, so the source aspect has to be
    converted into data units before it can be compared with the box."""
    img = mpimg.imread(os.path.join(SRC, path))
    ih, iw = img.shape[0], img.shape[1]
    x0_, x1_ = ax.get_xlim()
    y0_, y1_ = ax.get_ylim()
    upx = fig.get_figwidth() / (x1_ - x0_)     # inches per x unit
    upy = fig.get_figheight() / (y1_ - y0_)    # inches per y unit
    k = (iw / ih) * upy / upx                  # the box aspect the image needs
    if w / h > k:
        dh, dw = h, h * k
    else:
        dw, dh = w, w / k
    x0, y0 = x + (w - dw) / 2, y + (h - dh) / 2
    ax.imshow(img, extent=(x0, x0 + dw, y0, y0 + dh), aspect='auto', zorder=4)
    ax.text(x + w / 2, y - 1.0, tag, ha='center', va='top', fontsize=8.8,
            zorder=6, linespacing=1.4)
    return (x0, y0, dw, dh)


band(ax, 0.5, 4.0, 52.0, 44.0, '', 'tel')
panel('prior_v1.png', 2.0, 28.0, 49.0, 18.0,
      r'$\bf{(a)}$  Variant 1, the lateral wheels placed close together', '')
panel('prior_v2.png', 2.0, 8.5, 49.0, 15.0,
      r'$\bf{(b)}$  Variant 2, the lateral wheels distributed along the length', '')

band(ax, 55.5, 4.0, 43.5, 44.0, '', 'note')
panel('prior_kin.png', 57.0, 10.0, 40.5, 33.0,
      r'$\bf{(c)}$  The kinematic model, in the notation the paper uses', '')

save(fig, 'fig38_prior_chassis.png')
