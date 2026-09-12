"""Draw dimension callouts onto the SolidWorks top-view render.

Pixel anchors were measured from the render itself by luminance thresholding,
not placed by eye. The four wheel centres recovered that way agree with the
CAD positions (l1 = 403, l2 = 333) to under half a pixel, which is what
establishes that the render is to scale and that these anchors are correct.

The render pixels are untouched. The source is cropped to the model plus a
margin of its own background, then placed on white so the callouts have room.
"""
import math
from PIL import Image, ImageDraw, ImageFont

SRC = "cad/AislebotBasePlatform_SteelChasis.JPG"
OUT = "cad/renders/chassis_top_dimensioned.png"

# Anchors measured on the source image.
PL, PR, PT, PB = 180, 1333, 340, 631   # plate edges
WTOP, WBOT = 269, 701                  # wheel outer extremes
WCX = {"ul": 292.0, "ur": 1140.0, "ll": 373.0, "lr": 1221.0}
WUR_RIGHT = 1227                       # right edge of the upper-right wheel
WLR_RIGHT = 1308                       # right edge of the lower-right wheel

CROP = (150, 240, 1370, 730)           # keeps some original background
OFF = (80, 230)                        # where the crop lands on the canvas
CANVAS = (1700, 920)

RED = (200, 30, 40)
BLUE = (30, 90, 190)
INK = (25, 25, 25)

dx = OFF[0] - CROP[0]
dy = OFF[1] - CROP[1]
X = lambda v: v + dx
Y = lambda v: v + dy

im = Image.open(SRC).convert("RGB").crop(CROP)

# Flatten SolidWorks' gradient backdrop to white so the crop leaves no seam.
# Measured on this render, background sits above luminance 210 and the model
# below 195, with nothing in between, so this cannot touch model pixels.
import numpy as np
arr = np.asarray(im).astype(np.uint8).copy()
arr[arr.astype(int).mean(axis=2) > 195] = 255
im = Image.fromarray(arr)

canvas = Image.new("RGB", CANVAS, (255, 255, 255))
canvas.paste(im, OFF)
d = ImageDraw.Draw(canvas)

FB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 27)
FS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)


def arrow(p, q, colour, head=14):
    d.line([p, q], fill=colour, width=3)
    ang = math.atan2(q[1] - p[1], q[0] - p[0])
    for s in (0.40, -0.40):
        d.line([q, (q[0] - head * math.cos(ang - s),
                    q[1] - head * math.sin(ang - s))], fill=colour, width=3)


def dim(p, q, colour):
    """Double-headed dimension line between two points."""
    mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    arrow(mid, p, colour)
    arrow(mid, q, colour)


def ext(p, q, colour):
    d.line([p, q], fill=colour, width=1)


def label(text, xy, colour, font=FB, anchor="mm"):
    x, y = xy
    l, t, r, b = d.textbbox((x, y), text, font=font, anchor=anchor)
    d.rectangle([l - 9, t - 6, r + 9, b + 6], fill=(255, 255, 255))
    d.text((x, y), text, font=font, fill=colour, anchor=anchor)


# ------------------------------------------------------------ centreline
cx = (X(PL) + X(PR)) / 2
d.line([(cx, Y(WTOP) - 175), (cx, Y(WBOT) + 150)], fill=INK, width=1)
label("centre", (cx, Y(WTOP) - 192), INK, font=FS)

# ---------------------------------------------------------------- length
y = Y(WBOT) + 108
ext((X(PL), Y(PB)), (X(PL), y + 18), RED)
ext((X(PR), Y(PB)), (X(PR), y + 18), RED)
dim((X(PL), y), (X(PR), y), RED)
label("LENGTH   1000 mm", (cx, y), RED)

# --------------------------------------------------- plate width, 250 mm
x = X(PR) + 78
ext((X(PR), Y(PT)), (x + 18, Y(PT)), RED)
ext((X(PR), Y(PB)), (x + 18, Y(PB)), RED)
dim((x, Y(PT)), (x, Y(PB)), RED)
label("250 mm", (x + 26, (Y(PT) + Y(PB)) / 2 - 15), RED, anchor="lm")
label("chassis plate", (x + 26, (Y(PT) + Y(PB)) / 2 + 15), RED, font=FS, anchor="lm")

# --------------------------------------------- width over wheels, 375.4
x = X(PR) + 260
ext((X(WUR_RIGHT), Y(WTOP)), (x + 18, Y(WTOP)), BLUE)
ext((X(WLR_RIGHT), Y(WBOT)), (x + 18, Y(WBOT)), BLUE)
dim((x, Y(WTOP)), (x, Y(WBOT)), BLUE)
label("375.4 mm", (x + 26, (Y(WTOP) + Y(WBOT)) / 2 - 15), BLUE, anchor="lm")
label("over wheels", (x + 26, (Y(WTOP) + Y(WBOT)) / 2 + 15), BLUE, font=FS, anchor="lm")

# ------------------------------------------- centre-to-wheel, l1 and l2
y1 = Y(WTOP) - 155
xw = X(WCX["ul"])
ext((xw, Y(WTOP)), (xw, y1 - 16), RED)
dim((cx, y1), (xw, y1), RED)
label("l₁ = 403 mm  (outer)", ((cx + xw) / 2, y1), RED)

y2 = Y(WTOP) - 85
xw = X(WCX["ur"])
ext((xw, Y(WTOP)), (xw, y2 - 16), BLUE)
dim((cx, y2), (xw, y2), BLUE)
label("l₂ = 333 mm  (inner)", ((cx + xw) / 2, y2), BLUE)

canvas.save(OUT)
print("wrote", OUT, canvas.size)
