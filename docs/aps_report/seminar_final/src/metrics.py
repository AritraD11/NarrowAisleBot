"""Measure text the way PowerPoint will lay it out, before it is written.

python-pptx cannot autofit and cannot wrap, so a paragraph one line too long
for its box does not error - it silently spills over whatever is beneath it.
The only way to catch that before opening the file is to measure.

Cambria and Calibri are not installed here, but Caladea and Carlito are, and
they are metric-compatible substitutes: same advance widths, same line
heights. Measuring against them gives the wrap points PowerPoint will pick on
a machine that has the real fonts. That is the same trick LibreOffice uses to
render the deck, and it is why the rendered PNGs are worth trusting.
"""
import os
from functools import lru_cache

from PIL import ImageFont

FONT_DIR = '/usr/share/fonts/truetype/crosextra'
SUBST = {'Cambria': 'Caladea', 'Calibri': 'Carlito'}
PX_PER_PT = 4.0          # measure at 4x and divide, so rounding does not bite


@lru_cache(maxsize=None)
def _font(name, size_pt, bold, italic):
    fam = SUBST.get(name, 'Carlito')
    style = ('Bold' if bold else '') + ('Italic' if italic else '')
    path = os.path.join(FONT_DIR, '%s-%s.ttf' % (fam, style or 'Regular'))
    if not os.path.exists(path):
        return None
    return ImageFont.truetype(path, int(round(size_pt * PX_PER_PT)))


def width_pt(text, name='Calibri', size=14, bold=False, italic=False):
    f = _font(name, size, bold, italic)
    if f is None:
        return len(text) * size * 0.5
    return f.getlength(text) / PX_PER_PT


def wrap(text, width_in, name='Calibri', size=14, bold=False, italic=False):
    """Greedy word wrap, as PowerPoint does it. Returns the lines."""
    limit = width_in * 72.0
    words, lines, cur = text.split(), [], ''
    for w in words:
        trial = (cur + ' ' + w).strip()
        if cur and width_pt(trial, name, size, bold, italic) > limit:
            lines.append(cur); cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or ['']


def line_height_in(size_pt, spacing=1.0):
    """PowerPoint's single line height is about 1.2 em for these faces."""
    return size_pt * 1.2 * spacing / 72.0


def block_height_in(text, width_in, size=14, name='Calibri', bold=False,
                    italic=False, spacing=1.0, space_after_pt=0.0):
    lines = wrap(text, width_in, name, size, bold, italic)
    return len(lines) * line_height_in(size, spacing) + space_after_pt / 72.0
