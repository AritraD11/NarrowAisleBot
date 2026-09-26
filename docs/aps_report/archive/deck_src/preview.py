#!/usr/bin/env python3
"""Render the deck's layout for visual QA, and report any text that overflows.

LibreOffice cannot run in this sandbox, so the .pptx cannot be rendered the
usual way. This reproduces the exact box geometry from build_deck.js and draws
it with PIL, which gives both something to look at and a hard overflow check.

Fonts: Liberation Sans stands in for Calibri and Liberation Serif for Cambria.
Liberation Sans carries Arial's metrics, which are wider than Calibri's, so a
body that fits here fits in PowerPoint with room to spare. Titles in Liberation
Serif run slightly narrower than Cambria, so they are checked against a 6 per
cent margin rather than the box edge.

    python3 preview.py            # writes preview/slide-NN.png, prints a report
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(REPORT))
OUT = os.path.join(HERE, 'preview')

DPI = 150
W_IN, H_IN = 13.333, 7.5
W, H = int(W_IN * DPI), int(H_IN * DPI)

SANS = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
SANS_B = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
SERIF_B = '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'

INK = (0x1A, 0x1A, 0x1A)
ACCENT = (0x1F, 0x4E, 0x79)
MUTED = (0x5A, 0x5A, 0x5A)
PAPER = (0xFF, 0xFF, 0xFF)

M = 0.55
TITLE_Y, TITLE_H = 0.42, 0.8
BAND_Y, BAND_H = 1.38, 5.5
FIG_X, FIG_W = M, 7.55
COL_X = 8.5
COL_W = W_IN - COL_X - M

problems = []


def px(inches):
    return int(round(inches * DPI))


def font(path, pt):
    # 1 pt = 1/72 in; at DPI px/in that is pt * DPI / 72 pixels.
    return ImageFont.truetype(path, int(round(pt * DPI / 72.0)))


def wrap(draw, text, fnt, width_in):
    """Greedy wrap to a pixel width, honouring explicit newlines."""
    limit = px(width_in)
    lines = []
    for para in text.split('\n'):
        words, cur = para.split(' '), ''
        for w in words:
            trial = w if not cur else cur + ' ' + w
            if draw.textlength(trial, font=fnt) <= limit:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def draw_text(draw, text, x_in, y_in, w_in, h_in, fnt, colour, pt,
              spacing=1.0, label='', slack=0.0, align='left'):
    """Draw wrapped text and record an overflow if it exceeds its box."""
    lines = wrap(draw, text, fnt, w_in)
    lh = pt * spacing * DPI / 72.0
    for i, line in enumerate(lines):
        lx = px(x_in)
        if align == 'right':
            lx = px(x_in + w_in) - int(draw.textlength(line, font=fnt))
        draw.text((lx, px(y_in) + int(i * lh)), line, font=fnt, fill=colour)
    used_h = len(lines) * lh / DPI
    widest = max((draw.textlength(l, font=fnt) for l in lines), default=0) / DPI
    if h_in and used_h > h_in * (1 + slack) + 1e-6:
        problems.append(f'{label}: text is {used_h:.2f}in tall in a {h_in:.2f}in box '
                        f'({len(lines)} lines)')
    if widest > w_in * (1 + slack) + 1e-6:
        problems.append(f'{label}: longest line {widest:.2f}in wide in a {w_in:.2f}in box')
    return used_h, len(lines)


def img_size(path):
    with Image.open(path) as im:
        return im.size


def paste(canvas, path, x_in, y_in, w_in, h_in):
    with Image.open(path) as im:
        im = im.convert('RGB').resize((px(w_in), px(h_in)), Image.LANCZOS)
        canvas.paste(im, (px(x_in), px(y_in)))


def place_figure(canvas, draw, path, caption, label):
    iw, ih = img_size(path)
    ar = iw / ih
    w = FIG_W
    h = w / ar
    max_h = BAND_H - (0.42 if caption else 0)
    if h > max_h:
        h = max_h
        w = h * ar
    x = FIG_X + (FIG_W - w) / 2
    y = BAND_Y
    paste(canvas, path, x, y, w, h)
    if y < TITLE_Y + TITLE_H:
        problems.append(f'{label}: figure top {y:.2f}in collides with the title band')
    if y + h > H_IN - 0.5:
        problems.append(f'{label}: figure bottom {y + h:.2f}in is inside the bottom margin')
    if caption:
        draw_text(draw, caption, FIG_X, y + h + 0.1, FIG_W, 0.3,
                  font(SANS, 10), MUTED, 10, 1.2, f'{label} caption')
    return y + h


def load_slides():
    """Pull the SLIDES array out of build_deck.js so there is one source."""
    src = open(os.path.join(HERE, 'build_deck.js'), encoding='utf-8').read()
    start = src.index('const SLIDES = [')
    end = src.index('\n];', start) + 3
    body = src[start + len('const SLIDES = '):end]
    node = subprocess.run(
        ['node', '-e', f'const S = {body}; console.log(JSON.stringify(S));'],
        capture_output=True, text=True, check=True)
    return json.loads(node.stdout)


def content_slide(s):
    canvas = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(canvas)
    label = f'slide {s["n"]}'

    # Cambria is wider than Liberation Serif, so allow 6% slack on titles.
    draw_text(d, s['title'], M, TITLE_Y + 0.12, W_IN - 2 * M, TITLE_H,
              font(SERIF_B, 32), INK, 32, 1.0, f'{label} title', slack=0.06)

    if s.get('figure'):
        place_figure(canvas, d, os.path.join(REPORT, 'figures', s['figure']),
                     s.get('caption'), label)

    y = BAND_Y + 0.05
    prev_bottom = 0.0
    for i, card in enumerate(s['cards'], 1):
        draw_text(d, card['head'], COL_X, y, COL_W, 0.34,
                  font(SANS_B, 15), ACCENT, 15, 1.0, f'{label} card{i} head')
        used, _ = draw_text(d, card['body'], COL_X, y + 0.38, COL_W, 1.9,
                            font(SANS, 13.5), INK, 13.5, 1.15,
                            f'{label} card{i} body')
        bottom = y + 0.38 + used
        if prev_bottom and y - prev_bottom < 0.18:
            problems.append(f'{label}: only {y - prev_bottom:.2f}in between cards')
        prev_bottom = bottom
        y += 2.45
    if prev_bottom > H_IN - 0.5:
        problems.append(f'{label}: last card ends at {prev_bottom:.2f}in, past the margin')

    draw_text(d, str(s['n']), W_IN - M - 0.6, H_IN - 0.52, 0.6, 0.28,
              font(SANS, 10), MUTED, 10, 1.0, f'{label} number', align='right')
    return canvas


def title_slide():
    canvas = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(canvas)
    draw_text(d, 'Annual Progress Seminar · Year 1', M, 1.15, 7.4, 0.4,
              font(SANS_B, 16), ACCENT, 16, 1.0, 'slide 1 eyebrow')
    draw_text(d, 'NarrowAisleBot', M, 1.85, 7.4, 1.15,
              font(SERIF_B, 60), INK, 60, 1.0, 'slide 1 title', slack=0.06)
    draw_text(d, 'An asymmetric mecanum platform for autonomous operation in narrow aisles',
              M, 3.0, 7.0, 0.9, font(SANS, 19), MUTED, 19, 1.2, 'slide 1 subtitle')
    byline = ('Aritra Das\nRoll 25D0074\n'
              'Department of Biosciences and Bioengineering, IIT Bombay\n'
              'Supervisor: Prof. Ambarish Kunwar\nSeptember 2026')
    draw_text(d, byline, M, 4.75, 7.0, 1.7, font(SANS, 14), INK, 14, 1.25,
              'slide 1 byline')
    photo = os.path.join(REPO, 'docs', 'robot_photos',
                         '2026-08-11_occlusion_trial_cw', 'cw_000.jpg')
    iw, ih = img_size(photo)
    ph = 6.4
    pw = ph * (iw / ih)
    paste(canvas, photo, W_IN - M - pw, (H_IN - ph) / 2, pw, ph)
    if W_IN - M - pw < 7.7:
        problems.append(f'slide 1: photo left edge {W_IN - M - pw:.2f}in overlaps the text column')
    return canvas


def closing_slide():
    canvas = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(canvas)
    draw_text(d, 'Thank you', M, 0.82, 7.4, 1.2, font(SERIF_B, 54), INK, 54,
              1.0, 'slide 16 title', slack=0.06)
    draw_text(d, 'Questions', M, 1.95, 7.4, 0.5, font(SANS, 19), MUTED, 19,
              1.0, 'slide 16 sub')
    facts = [('Supervisor', 'Prof. Ambarish Kunwar'),
             ('Department', 'Biosciences and Bioengineering, IIT Bombay'),
             ('Roll number', '25D0074')]
    fy = 3.35
    for k, v in facts:
        draw_text(d, k, M, fy, 2.1, 0.32, font(SANS_B, 12), ACCENT, 12, 1.0,
                  f'slide 16 {k} label')
        draw_text(d, v, M + 2.2, fy, 4.6, 0.32, font(SANS, 14), INK, 14, 1.0,
                  f'slide 16 {k} value')
        fy += 0.62
    gantt = os.path.join(REPORT, 'figures', 'fig25_gantt.png')
    iw, ih = img_size(gantt)
    gw = 5.1
    gh = gw / (iw / ih)
    paste(canvas, gantt, W_IN - M - gw, (H_IN - gh) / 2, gw, gh)
    if M + 2.2 + 4.6 > W_IN - M - gw:
        problems.append('slide 16: fact values run under the timeline')
    return canvas


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    pages = [title_slide()] + [content_slide(s) for s in load_slides()] + [closing_slide()]
    for i, p in enumerate(pages, 1):
        p.save(os.path.join(OUT, f'slide-{i:02d}.png'), quality=92)
    print(f'{len(pages)} slides -> {OUT}')
    if problems:
        print(f'\n{len(problems)} LAYOUT PROBLEM(S):')
        for p in problems:
            print('  - ' + p)
        return 1
    print('\nno overflow, no collisions')
    return 0


if __name__ == '__main__':
    sys.exit(main())
