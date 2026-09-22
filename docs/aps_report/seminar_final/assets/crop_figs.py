"""Trim the report figures down to the graphic itself for slide use.

Each figure in the report carries its own title, an explanatory paragraph and
often a dashed footnote box. All three are meant for a reader holding the
report; on a projected slide they are unreadable texture and they compete with
the slide heading. The row ranges below were read off assets/segment.py and
keep the panels, the panel labels and the in-figure annotation, and nothing
else. The originals stay in assets/fig/ untouched.
"""
import os
from PIL import Image
import numpy as np

SRC = os.path.join(os.path.dirname(__file__), 'fig')
DST = os.path.join(os.path.dirname(__file__), 'slide')

# figure number -> (first row kept, last row kept); None means keep the whole height
KEEP = {
    1:  (168, 1000), 2:  (190, 870),  3:  None,        4:  None,
    5:  None,        6:  None,        7:  (198, 1125), 8:  (158, 700),
    9:  (108, 1385), 10: (158, 705),  11: None,        12: None,
    13: (152, 812),  14: (142, 760),  15: None,        16: (108, 862),
    17: (212, 1184), 18: (128, 1072), 19: (163, 777),  20: (203, 872),
    21: (193, 1042),
}

def xtrim(arr, pad=12, thr=248):
    col = (arr < thr).any(axis=0)
    if not col.any():
        return 0, arr.shape[1]
    x0, x1 = int(col.argmax()), int(len(col) - col[::-1].argmax())
    return max(0, x0 - pad), min(arr.shape[1], x1 + pad)

# Figure 15 is the status board, and at full-slide size its rows are too small
# to read from the back of a room. It splits cleanly at its own dashed rule:
# established layers above, remaining work below. Two slides, each near full
# width, is legible where one is not.
SPLIT_15 = {'fig15a': (18, 848), 'fig15b': (856, 1523)}


def main():
    os.makedirs(DST, exist_ok=True)
    src15 = Image.open(os.path.join(SRC, 'fig15.png')).convert('RGB')
    for name, (r0, r1) in SPLIT_15.items():
        part = src15.crop((0, r0, src15.width, r1))
        g = np.asarray(part.convert('L'))
        x0, x1 = xtrim(g)
        part = part.crop((x0, 0, x1, part.height))
        part.save(os.path.join(DST, name + '.png'))
        print('%-7s %4d x %4d' % (name, part.width, part.height))
    for n in sorted(KEEP):
        src = os.path.join(SRC, 'fig%02d.png' % n)
        im = Image.open(src).convert('RGB')
        rows = KEEP[n]
        if rows:
            im = im.crop((0, rows[0], im.width, rows[1]))
        g = np.asarray(im.convert('L'))
        x0, x1 = xtrim(g)
        im = im.crop((x0, 0, x1, im.height))
        out = os.path.join(DST, 'fig%02d.png' % n)
        im.save(out)
        print('fig%02d  %4d x %4d' % (n, im.width, im.height))

if __name__ == '__main__':
    main()
