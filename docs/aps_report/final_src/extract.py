"""Extract the APS PDF into structured blocks: style, runs (bold/italic), page."""
import json, re, collections
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextContainer, LTTextLine, LTChar, LTFigure, LTImage

PDF = '/root/.claude/uploads/3a59de25-0b2f-5e3a-89fe-898a68f9e73b/9229b4b4-APS_Report_Final.pdf'
OUT = '/tmp/claude-0/-home-user-NarrowAisleBot/3a59de25-0b2f-5e3a-89fe-898a68f9e73b/scratchpad/build/blocks.json'

def iter_lines(el):
    for x in el:
        if isinstance(x, LTTextLine): yield x
        elif isinstance(x, LTTextContainer): yield from iter_lines(x)

def style_of(fn, sz):
    f = fn.split('+')[-1]
    if f.startswith('Calibri-Bold') and sz >= 15.5: return 'h1'
    if f.startswith('Calibri-Bold') and sz >= 13.5: return 'h2'
    if f.startswith('Calibri'): return 'h2'
    if 'Italic' in f and sz <= 9.5: return 'caption'
    if sz >= 15.5: return 'title-big'
    if sz >= 13.5: return 'title-mid'
    if f.startswith('Cambria'): return 'toc'
    return 'body'

pages = []
la = LAParams(word_margin=0.18, char_margin=2.0, line_margin=0.30)
for pno, page in enumerate(extract_pages(PDF, laparams=la), 1):
    items = []
    for el in page:
        if isinstance(el, (LTFigure, LTImage)):
            items.append({'kind': 'image', 'y': el.y1, 'x': el.x0,
                          'h': el.height, 'w': el.width})
            continue
        if not isinstance(el, LTTextContainer): continue
        for line in iter_lines(el):
            chs = [c for c in line if isinstance(c, LTChar)]
            if not chs: continue
            runs = []
            for c in chs:
                f = c.fontname.split('+')[-1]
                bold = 'Bold' in f
                ital = 'Italic' in f
                sz = round(c.size, 1)
                key = (bold, ital, sz, f)
                if runs and runs[-1]['key'] == key:
                    runs[-1]['t'] += c.get_text()
                else:
                    runs.append({'key': key, 't': c.get_text()})
            fn = collections.Counter(c.fontname for c in chs).most_common(1)[0][0]
            sz = collections.Counter(round(c.size, 1) for c in chs).most_common(1)[0][0]
            items.append({'kind': 'line', 'y': round(line.y1, 1), 'x0': round(line.x0, 1),
                          'x1': round(line.x1, 1), 'style': style_of(fn, sz),
                          'size': sz, 'font': fn.split('+')[-1],
                          'runs': [{'b': r['key'][0], 'i': r['key'][1], 's': r['key'][2],
                                    'f': r['key'][3], 't': r['t']} for r in runs]})
    items.sort(key=lambda d: -d['y'])
    pages.append(items)

json.dump(pages, open(OUT, 'w'))
print('pages', len(pages), 'items', sum(len(p) for p in pages))
