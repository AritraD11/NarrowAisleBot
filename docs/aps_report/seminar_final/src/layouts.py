"""The five slide layouts the deck uses, and nothing else.

Every slide is assembled from primitives rather than from a PowerPoint master,
because the master would have to be edited in PowerPoint and this deck is
rebuilt from source. The layout functions are deliberately dumb: they take a
dict, they place shapes, they do no fitting. Overflow is caught by src/qa.py
instead, which is the only thing that can actually measure it.
"""
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from theme import *
import metrics

TITLE_PT = 27
TITLE_W = COL * 0.775


# ---------------------------------------------------------------- chrome ----
def _blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def title_lines(text, size=TITLE_PT):
    return metrics.wrap(text, TITLE_W, HEAD, size, bold=True)


def _heading(slide, text, kicker=None, sub=None):
    """Place the heading, then return the y the content region starts at.

    A two-line heading pushes the accent rule and everything under it down,
    rather than running into the rule. Which titles wrap is measured, not
    guessed: see src/metrics.py.
    """
    n = len(title_lines(text))
    tf = textbox(slide, MARGIN, TITLE_Y, TITLE_W, 0.46 * n + 0.24)
    p = para(tf, first=True, line=0.95)
    run(p, text, size=TITLE_PT, font=HEAD, color=INK, bold=True)
    if kicker:
        tf2 = textbox(slide, MARGIN + TITLE_W + 0.10, TITLE_Y + 0.10, COL - TITLE_W - 0.10, 0.32)
        p2 = para(tf2, first=True, align=PP_ALIGN.RIGHT)
        run(p2, kicker.upper(), size=10, color=MUTED, spacing=1.2)
    rule_y = RULE_Y + (n - 1) * 0.46
    box(slide, MARGIN, rule_y, 0.86, 0.055, fill=ACCENT)
    if sub:
        tf3 = textbox(slide, MARGIN + 1.05, rule_y - 0.10, COL - 1.05, 0.32)
        p3 = para(tf3, first=True)
        run(p3, sub, size=12.5, color=MUTED, italic=True)
    return rule_y + 0.30


def _footer(slide, n):
    tf = textbox(slide, MARGIN, FOOT_Y, COL * 0.7, 0.28)
    p = para(tf, first=True)
    run(p, 'Annual Progress Seminar  ·  Aritra Das  ·  25D0074  ·  IIT Bombay',
        size=9, color=RGBColor(0xA8, 0xB1, 0xBE))
    tf2 = textbox(slide, MARGIN + COL * 0.7, FOOT_Y, COL * 0.3, 0.28)
    p2 = para(tf2, first=True, align=PP_ALIGN.RIGHT)
    run(p2, str(n), size=9.5, font=HEAD, color=MUTED)


def _bullets(slide, items, x, y, w, h, size=14.5, gap=9):
    tf = textbox(slide, x, y, w, h)
    for i, it in enumerate(items):
        if isinstance(it, str):
            text, color, lead = it, BODY, None
        else:
            text, color, lead = (list(it) + [None, None])[:3]
            color = color or BODY
        sub = text.startswith('~')
        # a sub-point belongs to the bullet above it, so the air goes after the
        # pair rather than between the two halves of it
        p = para(tf, first=(i == 0), space_after=gap + (10 if sub else 0), line=1.05)
        if sub:
            p.space_before = 0
            pPr = p._p.get_or_add_pPr(); pPr.set('marL', str(Inches(0.20)))
            run(p, text[1:], size=size - 1.5, color=MUTED, italic=True)
            continue
        bullet(p, color=ACCENT_2)
        if lead:
            run(p, lead, size=size, color=color, bold=True)
            run(p, text, size=size, color=BODY)
        else:
            run(p, text, size=size, color=color)
    return tf


def _takeaway(slide, text, y=None, w=None):
    y = 6.00 if y is None else y
    w = COL if w is None else w
    box(slide, MARGIN, y, w, 0.60, fill=TINT)
    box(slide, MARGIN, y, 0.045, 0.60, fill=ACCENT)
    tf = textbox(slide, MARGIN + 0.28, y + 0.055, w - 0.50, 0.50, anchor=MSO_ANCHOR.MIDDLE)
    p = para(tf, first=True, line=1.0)
    run(p, text, size=13, font=HEAD, color=ACCENT, italic=True)


def _tiles(slide, tiles, x, y, w, h=0.92, gap=0.16):
    n = len(tiles)
    tw = (w - gap * (n - 1)) / n
    for i, t in enumerate(tiles):
        value, label = t[0], t[1]
        color = (t[2] if len(t) > 2 else None) or ACCENT
        tx = x + i * (tw + gap)
        box(slide, tx, y, tw, h, fill=TINT)
        box(slide, tx, y, tw, 0.045, fill=color)
        tf = textbox(slide, tx + 0.14, y + 0.15, tw - 0.28, h - 0.24)
        p = para(tf, first=True, line=0.95)
        run(p, value, size=19, font=HEAD, color=color, bold=True)
        p2 = para(tf, space_before=2, line=0.98)
        run(p2, label, size=10, color=MUTED)


def _video_placeholder(slide, x, y, w, h, filename, caption=None):
    """A box to paste a video into, labelled with the exact source filename.

    Not a still frame: python-pptx cannot embed a linked video the way
    PowerPoint's own Insert > Video does, so this is deliberately a marked
    box rather than a fake thumbnail. The filename is what the presenter
    matches against the Drive folder when dropping the real clip in.
    """
    from pptx.enum.shapes import MSO_SHAPE
    box(slide, x, y, w, h, fill=TINT, line=ACCENT_2, lw=1.25)
    box(slide, x, y, w, 0.05, fill=ACCENT_2)
    box(slide, x, y + h - 0.05, w, 0.05, fill=ACCENT_2)
    cx, cy = x + w / 2, y + h / 2 - 0.22
    tri = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, Inches(cx - 0.20), Inches(cy - 0.20), Inches(0.40), Inches(0.40))
    tri.rotation = 90
    tri.shadow.inherit = False
    tri.fill.solid(); tri.fill.fore_color.rgb = ACCENT
    tri.line.fill.background()
    tf = textbox(slide, x + 0.20, cy + 0.28, w - 0.40, 0.26, anchor=MSO_ANCHOR.TOP)
    p = para(tf, first=True, align=PP_ALIGN.CENTER)
    run(p, 'VIDEO  ·  INSERT HERE', size=9.5, color=MUTED, bold=True, spacing=1.3)
    tf2 = textbox(slide, x + 0.20, cy + 0.54, w - 0.40, 0.36, anchor=MSO_ANCHOR.TOP)
    p2 = para(tf2, first=True, align=PP_ALIGN.CENTER, line=1.0)
    run(p2, filename, size=12.5, font=TEXT, color=INK, bold=True)
    if caption:
        tf3 = textbox(slide, x + 0.18, y + h - 0.40, w - 0.36, 0.36)
        p3 = para(tf3, first=True, align=PP_ALIGN.CENTER, line=0.95)
        run(p3, caption, size=9.5, color=MUTED, italic=True)


def _table(slide, headers, rows, x, y, w, h, size=11.5, col_w=None, right=()):
    nrows, ncols = len(rows) + 1, len(headers)
    col_w = col_w or [1.0 / ncols] * ncols
    rh = min(0.42, h / nrows)
    yy = y
    # header
    for c, head in enumerate(headers):
        cx = x + sum(col_w[:c]) * w
        tf = textbox(slide, cx + 0.06, yy + 0.05, col_w[c] * w - 0.12, rh)
        p = para(tf, first=True, align=PP_ALIGN.RIGHT if c in right else PP_ALIGN.LEFT)
        run(p, head, size=size - 0.5, color=ACCENT, bold=True)
    yy += rh * 0.86
    box(slide, x, yy, w, 0.018, fill=ACCENT)
    yy += 0.10
    for r, rowvals in enumerate(rows):
        for c, cell in enumerate(rowvals):
            cx = x + sum(col_w[:c]) * w
            tf = textbox(slide, cx + 0.06, yy + 0.045, col_w[c] * w - 0.12, rh)
            p = para(tf, first=True, align=PP_ALIGN.RIGHT if c in right else PP_ALIGN.LEFT, line=0.98)
            bold = isinstance(cell, tuple)
            txt = cell[0] if bold else cell
            col = cell[1] if bold and len(cell) > 1 else BODY
            run(p, txt, size=size, color=col, bold=bold, font=HEAD if bold else TEXT)
        yy += rh
        if r < len(rows) - 1:
            box(slide, x, yy - 0.02, w, 0.008, fill=RULE)
    return yy


# ---------------------------------------------------------------- layouts ---
def title_slide(prs, s):
    slide = _blank(prs)
    pw = 5.05
    cover_image(slide, s['image'], SW - pw, 0, pw, SH)
    box(slide, SW - pw, 0, 0.05, SH, fill=ACCENT)

    tf = textbox(slide, MARGIN, 0.90, SW - pw - MARGIN - 0.70, 0.40)
    p = para(tf, first=True)
    run(p, s['kicker'].upper(), size=11, color=ACCENT, bold=True, spacing=1.6)

    tf = textbox(slide, MARGIN, 1.42, SW - pw - MARGIN - 0.62, 2.70)
    p = para(tf, first=True, line=1.04)
    run(p, s['title'], size=31, font=HEAD, color=INK, bold=True)

    box(slide, MARGIN, 4.06, 1.10, 0.055, fill=ACCENT)

    tf = textbox(slide, MARGIN, 4.42, SW - pw - MARGIN - 0.70, 2.10)
    for i, (label, value) in enumerate(s['meta']):
        p = para(tf, first=(i == 0), space_after=6, line=1.0)
        run(p, label + '   ', size=10.5, color=MUTED)
        run(p, value, size=13, color=INK if i == 0 else BODY, font=HEAD if i == 0 else TEXT,
            bold=(i == 0))

    tf = textbox(slide, MARGIN, 6.72, SW - pw - MARGIN - 0.70, 0.40)
    p = para(tf, first=True)
    run(p, s['date'], size=10.5, color=MUTED)
    notes(slide, s.get('notes', ''))
    return slide


def divider(prs, s, n, slide=None):
    if slide is None:
        slide = _blank(prs)
    box(slide, 0, 0, SW, SH, fill=TINT)
    box(slide, 0, 0, 0.16, SH, fill=ACCENT)

    tf = textbox(slide, 1.55, 1.52, 3.0, 0.95)
    p = para(tf, first=True, line=0.9)
    run(p, s['numeral'], size=62, font=HEAD, color=RGBColor(0xBF, 0xCF, 0xE0), bold=True)

    tf = textbox(slide, 1.55, 2.44, 9.6, 0.42)
    p = para(tf, first=True)
    run(p, s['kicker'].upper(), size=11.5, color=ACCENT, bold=True, spacing=1.8)

    tf = textbox(slide, 1.55, 2.90, 9.8, 1.00)
    p = para(tf, first=True, line=1.0)
    run(p, s['title'], size=35, font=HEAD, color=INK, bold=True)

    box(slide, 1.55, 4.14, 1.10, 0.055, fill=ACCENT)

    tf = textbox(slide, 1.55, 4.48, 9.1, 1.10)
    p = para(tf, first=True, line=1.15)
    run(p, s['line'], size=15, font=HEAD, color=BODY, italic=True)

    if s.get('status'):
        tf = textbox(slide, 1.55, 5.62, 9.1, 0.40)
        p = para(tf, first=True)
        run(p, s['status'], size=11.5, color=s.get('status_color', GREEN), bold=True, spacing=0.6)
    _footer(slide, n)
    notes(slide, s.get('notes', ''))
    return slide


def content(prs, s, n, slide=None):
    if slide is None:
        slide = _blank(prs)
    y = _heading(slide, s['title'], s.get('kicker'), s.get('sub'))

    take = s.get('takeaway')
    bottom = 5.86 if take else BODY_B

    if s.get('tiles'):
        _tiles(slide, s['tiles'], MARGIN, y, COL)
        y += 1.16

    img = s.get('image')
    vid = s.get('video')
    side = s.get('side', 'right')
    img_w = s.get('image_w', 0.50)

    if s.get('videos'):
        # a pair of video placeholders, side by side, spanning the full width
        gap = 0.30
        n_v = len(s['videos'])
        vw = (COL - gap * (n_v - 1)) / n_v
        vh = min(2.55, bottom - y - 1.6)
        for i, (fname, cap) in enumerate(s['videos']):
            _video_placeholder(slide, MARGIN + i * (vw + gap), y, vw, vh, fname, caption=cap)
        y += vh + 0.24
        if s.get('bullets'):
            _bullets(slide, s['bullets'], MARGIN, y, COL * s.get('text_w', 0.88),
                     bottom - y, size=s.get('size', 13.5), gap=s.get('gap', 9))
    elif s.get('images'):
        # two figures side by side, each with its own caption, spanning the full width
        gap = 0.30
        n_i = len(s['images'])
        iw2 = (COL - gap * (n_i - 1)) / n_i
        ih2 = min(3.1, bottom - y - 1.9)
        for i, (path, cap) in enumerate(s['images']):
            ix2 = MARGIN + i * (iw2 + gap)
            fit_image(slide, path, ix2, y, iw2, ih2, frame=s.get('frame', False))
            if cap:
                tf = textbox(slide, ix2, y + ih2 + 0.06, iw2, 0.28)
                p = para(tf, first=True, align=PP_ALIGN.CENTER)
                run(p, cap, size=10, color=MUTED, italic=True)
        y += ih2 + 0.36
        if s.get('bullets'):
            _bullets(slide, s['bullets'], MARGIN, y, COL * s.get('text_w', 0.88),
                     bottom - y, size=s.get('size', 13.5), gap=s.get('gap', 9))
    elif (img or vid) and side in ('right', 'left'):
        gap = 0.42
        bw = COL * (1 - img_w) - gap
        iw = COL * img_w
        bx = MARGIN if side == 'right' else MARGIN + iw + gap
        ix = MARGIN + bw + gap if side == 'right' else MARGIN
        if s.get('bullets'):
            _bullets(slide, s['bullets'], bx, y, bw, bottom - y, size=s.get('size', 14.5))
        if s.get('table'):
            _table(slide, s['table'][0], s['table'][1], bx, y, bw, bottom - y,
                   size=s.get('table_size', 11.5), col_w=s.get('col_w'), right=s.get('right', ()))
        if vid:
            _video_placeholder(slide, ix, y, iw, bottom - y, vid, caption=s.get('video_caption'))
        else:
            fit_image(slide, img, ix, y, iw, bottom - y, frame=s.get('frame', False))
    elif (img or vid) and side == 'bottom':
        if vid:
            _video_placeholder(slide, MARGIN, y, COL, bottom - y, vid, caption=s.get('video_caption'))
        else:
            fit_image(slide, img, MARGIN, y, COL, bottom - y, frame=s.get('frame', False))
    elif (img or vid) and side == 'full':
        cap = s.get('caption')
        ih = bottom - y - (0.30 if cap else 0)
        if vid:
            _video_placeholder(slide, MARGIN, y, COL, ih, vid, caption=s.get('video_caption'))
        else:
            fit_image(slide, img, MARGIN, y, COL, ih, frame=s.get('frame', False))
        if cap:
            tf = textbox(slide, MARGIN, y + ih + 0.08, COL, 0.28)
            p = para(tf, first=True, align=PP_ALIGN.CENTER)
            run(p, cap, size=10.5, color=MUTED, italic=True)
    else:
        if s.get('two_col'):
            gap = 0.55
            cw = (COL - gap) / 2
            left, right_ = s['two_col']
            for k, (head, items) in enumerate([left, right_]):
                cx = MARGIN + k * (cw + gap)
                if head:
                    tf = textbox(slide, cx, y, cw, 0.32)
                    p = para(tf, first=True)
                    run(p, head.upper(), size=10.5, color=ACCENT, bold=True, spacing=1.1)
                _bullets(slide, items, cx, y + (0.44 if head else 0), cw,
                         bottom - y - 0.44, size=s.get('size', 13.5))
        else:
            if s.get('table'):
                end = _table(slide, s['table'][0], s['table'][1], MARGIN, y, COL,
                             s.get('table_h', bottom - y),
                             size=s.get('table_size', 12.5), col_w=s.get('col_w'),
                             right=s.get('right', ()))
                y = end + 0.26          # bullets, if any, stack under the table
            if s.get('bullets'):
                _bullets(slide, s['bullets'], MARGIN, y, COL * s.get('text_w', 0.88),
                         bottom - y, size=s.get('size', 15.5), gap=s.get('gap', 12))

    if take:
        _takeaway(slide, take)
    _footer(slide, n)
    notes(slide, s.get('notes', ''))
    return slide


def closing(prs, s, n):
    slide = _blank(prs)
    ih = 2.30
    cover_image(slide, s['image'], 0, SH - ih, SW, ih)
    box(slide, 0, SH - ih, SW, 0.045, fill=ACCENT)

    tf = textbox(slide, MARGIN, 0.62, COL, 0.42)
    p = para(tf, first=True)
    run(p, s['kicker'].upper(), size=11, color=ACCENT, bold=True, spacing=1.6)

    tf = textbox(slide, MARGIN, 1.10, COL * 0.86, 0.80)
    p = para(tf, first=True, line=1.0)
    run(p, s['title'], size=32, font=HEAD, color=INK, bold=True)

    top, avail, w = 2.12, SH - ih - 2.30, COL * 0.90
    size, gap = 14.0, 8.0
    while size > 10.5:                      # shrink until the three lines fit
        need = sum(metrics.block_height_in(t, w, size=size, name=HEAD, italic=True,
                                           spacing=1.08, space_after_pt=gap)
                   for t in s['lines'])
        if need <= avail:
            break
        size -= 0.5
    tf = textbox(slide, MARGIN, top, w, avail)
    for i, line in enumerate(s['lines']):
        p = para(tf, first=(i == 0), space_after=gap, line=1.08)
        run(p, line, size=size, font=HEAD, color=BODY, italic=True)
    notes(slide, s.get('notes', ''))
    return slide
