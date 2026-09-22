"""Slide-ready copies of the project's own photographs.

Nothing here is generated or fetched. Every source is a photograph taken of
this robot, living in docs/robot_photos/ or docs/hardware/photos/. The only
operations are EXIF rotation (the phone writes the orientation as a tag rather
than rotating the pixels, and PowerPoint ignores the tag), an aspect crop, and
a downscale to something a 16:9 slide can actually use.
"""
import os
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
DST = os.path.join(HERE, 'photo')

# name -> (source relative to repo root, target aspect w/h or None, focus x/y in 0..1)
JOBS = {
    'title':          ('docs/robot_photos/2026-08-11_occlusion_trial_cw/cw_000.jpg',     0.667, (0.52, 0.50)),
    'platform_side':  ('docs/hardware/photos/nab_full_side_arm_lab_01.jpg',              0.72,  (0.45, 0.55)),
    'platform_front': ('docs/hardware/photos/nab_full_side_arm_lab_02.jpg',              1.40,  (0.45, 0.55)),
    'chassis_wheels': ('docs/hardware/photos/nab_chassis_drivers_wheels.jpg',            1.35,  (0.50, 0.50)),
    'chassis_top':    ('docs/hardware/photos/nab_chassis_battery_pi_top.jpg',            1.05,  (0.50, 0.62)),
    'floor_mark':     ('docs/robot_photos/2026-08-11_occlusion_trial_cw/base_position_marking.jpg', 1.15, (0.50, 0.58)),
    'three_quarter':  ('docs/robot_photos/2026-08-11_occlusion_trial_cw/cw_180.jpg',      1.30,  (0.50, 0.50)),
    'closing':        ('docs/robot_photos/2026-08-11_occlusion_trial_cw/cw_360.jpg',      1.55,  (0.52, 0.48)),
}

def crop_to(im, aspect, focus):
    w, h = im.size
    cur = w / h
    if abs(cur - aspect) < 1e-3:
        return im
    if cur > aspect:                       # too wide: trim the sides
        nw = int(round(h * aspect)); nh = h
    else:                                  # too tall: trim top and bottom
        nw = w; nh = int(round(w / aspect))
    cx, cy = focus
    x0 = int(round(cx * w - nw / 2)); y0 = int(round(cy * h - nh / 2))
    x0 = max(0, min(w - nw, x0));     y0 = max(0, min(h - nh, y0))
    return im.crop((x0, y0, x0 + nw, y0 + nh))

def main():
    os.makedirs(DST, exist_ok=True)
    for name, (rel, aspect, focus) in JOBS.items():
        im = ImageOps.exif_transpose(Image.open(os.path.join(REPO, rel)).convert('RGB'))
        if aspect:
            im = crop_to(im, aspect, focus)
        im.thumbnail((1800, 1800), Image.LANCZOS)
        out = os.path.join(DST, name + '.jpg')
        im.save(out, quality=88, optimize=True)
        print('%-16s %4d x %4d   <- %s' % (name, im.width, im.height, rel))

if __name__ == '__main__':
    main()
