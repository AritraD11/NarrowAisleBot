"""Repair two defects in the supplied fatigue infographic before it is placed
in the report.

  1. "IR thremometer" is a misspelling of thermometer.
  2. "DPDP Act 2023 compliance (verified)" claims a verification for work that
     has not started. The chapter it sits in says in its first paragraph that
     no hardware has been built and nothing has been measured, so the figure
     contradicted its own text. The parenthetical is removed and the bullet
     reads as the design intent the other four bullets in that box are.

The replacement line is set in Carlito at a size and weight matched to the
neighbouring bullet by measuring the original's glyph band and ink coverage,
so the repair is not visible at the size the figure is placed.
"""
from PIL import Image, ImageDraw, ImageFont
import sys, os

SRC = sys.argv[1] if len(sys.argv) > 1 else 'new_5.png'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'infographic_fixed.png'
BG = (245, 249, 252)
INK = (26, 36, 58)
FONT = '/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf'

im = Image.open(SRC).convert('RGB')
d = ImageDraw.Draw(im)

d.rectangle((1136, 770, 1294, 793), fill=BG)
f = ImageFont.truetype(FONT, 12)
d.text((1141, 773), 'IR thermometer (for thermal)', font=f, fill=INK,
       stroke_width=0.35, stroke_fill=INK)

d.rectangle((1580, 779, 1639, 800), fill=BG)

im.save(OUT)
print('wrote', OUT, im.size)
