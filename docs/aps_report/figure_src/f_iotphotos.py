"""Two photographic plates for the monitoring chapter: the appliance and the
node as built, and the operator dashboard in service.

The source photographs are 450 x 600 and 800 x 600, which is all that exists,
so each is placed at a size that keeps it sharp rather than filling the page.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *
import matplotlib.image as mpimg

DOCX = os.environ.get(
    'NAB_IOTDOCX',
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 '..', '..', '..', 'IoT Box Project Report.docx'))


def _extract(dest):
    """Pull the photographs straight out of that project's own report, so the
    build has one source of truth for them rather than a second copy."""
    import zipfile
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(DOCX) as z:
        for n in z.namelist():
            if n.startswith('word/media/'):
                open(os.path.join(dest, os.path.basename(n)), 'wb').write(z.read(n))
    return dest


SRC = os.environ.get('NAB_IOTIMG') or _extract(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '_iot_media'))


def place(ax, fig, path, x, y, w, h):
    img = mpimg.imread(os.path.join(SRC, path))
    ih, iw = img.shape[0], img.shape[1]
    x0_, x1_ = ax.get_xlim()
    y0_, y1_ = ax.get_ylim()
    upx = fig.get_figwidth() / (x1_ - x0_)
    upy = fig.get_figheight() / (y1_ - y0_)
    k = (iw / ih) * upy / upx
    if w / h > k:
        dh, dw = h, h * k
    else:
        dw, dh = w, w / k
    x0, y0 = x + (w - dw) / 2, y + (h - dh) / 2
    ax.imshow(img, extent=(x0, x0 + dw, y0, y0 + dh), aspect='auto', zorder=4)
    ax.add_patch(__import__('matplotlib.patches', fromlist=['p']).Rectangle(
        (x0, y0), dw, dh, fc='none', ec='#8a97a4', lw=0.8, zorder=6))
    return (x0, y0, dw, dh)


def tag(ax, x, y, t):
    ax.text(x, y, t, ha='center', va='top', fontsize=8.8, zorder=7,
            linespacing=1.45)


# ── plate 1: the appliance and the node ──────────────────────────────
fig, ax = canvas(13.0, 6.0, 100, 46)
title(ax, 0.5, 45.6, 'The appliance and the sensing node as built', '')
place(ax, fig, 'image1.png', 2.0, 7.0, 40.0, 33.0)
tag(ax, 22.0, 5.6, r'$\bf{(a)}$  The integrated unit: aluminium duct on a stand, the lamp'
    '\ninside it, the control enclosure on top and the 120 mm fan\nset into the end face')
place(ax, fig, 'image2.png', 46.0, 7.0, 52.0, 33.0)
tag(ax, 72.0, 5.6, r'$\bf{(b)}$  Both control boxes powered and linked. Acrylic panels on '
    '3D-printed corner\nstandoffs, the helical long-range antenna through the top face, and the '
    'two displays\nreading live: irradiance and gas state on the left, uptime and firmware build on the right')
save(fig, 'fig40_iot_hardware.png')

# ── plate 2: the dashboard ───────────────────────────────────────────
fig, ax = canvas(13.0, 5.6, 100, 43)
title(ax, 0.5, 42.6, 'The operator dashboard in service', '')
place(ax, fig, 'image3.png', 1.0, 8.0, 48.0, 30.0)
tag(ax, 25.0, 6.6, r'$\bf{(a)}$  Status panels, zone 2 over MQTT. Gas index 143, below the 150'
    '\nthreshold, with the lamp correspondingly off; CO$_2$ at 1240 ppm, above its\n'
    '1200 ppm alert threshold; irradiance reading 3.64 with the lamp off')
place(ax, fig, 'image4.png', 51.0, 8.0, 48.0, 30.0)
tag(ax, 75.0, 6.6, r'$\bf{(b)}$  Trend panels. The legends expose the stored tag structure, which is how'
    '\nthe schema was confirmed. The left panel plots humidity and temperature against\n'
    'one axis labelled in degrees, which is a fault in the dashboard rather than in the data')
save(fig, 'fig41_iot_dashboard.png')
