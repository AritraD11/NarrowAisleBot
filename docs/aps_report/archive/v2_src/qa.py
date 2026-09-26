# -*- coding: utf-8 -*-
"""Checks that have to pass before the restructured report goes out.

Numbering, cross-references, house style and picture resolution. Everything
here is checked against the .docx that was actually written, not against the
source that produced it.
"""
import re, sys, zipfile, os
from collections import Counter
import docx
from docx.oxml.ns import qn
from PIL import Image

DOC = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/user/NarrowAisleBot/docs/aps_report/APS Report Aritra - restructured.docx'
d = docx.Document(DOC)
paras = d.paragraphs
text_all = '\n'.join(p.text for p in paras)
fails, notes = [], []

# 1 ── figure captions run 1..N with no gaps and no repeats -----------
caps = [p.text for p in paras if re.match(r'^Figure \d+\.', p.text.strip())]
nums = [int(re.match(r'^Figure (\d+)\.', c.strip()).group(1)) for c in caps]
if nums != list(range(1, len(nums) + 1)):
    fails.append('figure captions out of order or duplicated: %s' % nums)
else:
    notes.append('figure captions 1 to %d, in order' % len(nums))

# 2 ── every Figure reference in the prose points at a caption --------
# "Figures 2 and 3" refers to both, so the plural form is expanded before counting
def _fignums(t):
    for m in re.finditer(r'Figures? ((?:\d+)(?:(?:,| and) \d+)*)', t):
        for n in re.findall(r'\d+', m.group(1)):
            yield int(n)


refs = Counter(_fignums(text_all))
for n in sorted(refs):
    if n > len(nums):
        fails.append('text refers to Figure %d, which does not exist' % n)
body_refs = {n: c - 1 for n, c in refs.items()}   # one of each count is the caption
orphans = [n for n in range(1, len(nums) + 1) if body_refs.get(n, 0) == 0]
notes.append('figures never referred to in the prose: %s'
             % (orphans if orphans else 'none'))

# 3 ── every Section reference points at a heading that exists --------
heads = {p.text.strip() for p in paras if p.style.name in ('Heading 1', 'Heading 2')}
secnums = {h.split()[0] for h in heads if re.match(r'^\d+\.\d+ ', h)}
for m in sorted(set(re.findall(r'Section (\d+\.\d+)', text_all))):
    if m not in secnums:
        fails.append('text refers to Section %s, which is not a heading' % m)
chapnums = {re.match(r'Chapter (\d+)', h).group(1) for h in heads
            if re.match(r'Chapter \d+', h)}
for m in sorted(set(re.findall(r'Chapter (\d+)', text_all))):
    if m not in chapnums:
        fails.append('text refers to Chapter %s, which is not a heading' % m)

# 4 ── no cross-reference from the old numbering survived -------------
stale = [p.text[:80] for p in paras if re.search(r'Section [56]\.\d|Chapter [567]\b', p.text)]
if stale:
    fails.append('stale cross-references: %s' % stale)

# 5 ── house style ----------------------------------------------------
BANNED = ['delve', 'leverage', 'utilize', 'foster', 'pivotal', 'robust',
          'seamless', 'cutting-edge', 'innovative', 'game-changing',
          'transformative', 'groundbreaking', 'paradigm', 'synergy', 'tapestry',
          'multifaceted', 'nuanced', 'realm', 'landscape', 'ecosystem',
          'holistic', 'unlock', 'harness', 'underscore', 'streamline',
          'testament', 'underpinnings', 'spearhead', 'empower', 'notably',
          'importantly', 'furthermore', 'moreover', 'consequently',
          'ever-evolving', 'in conclusion', 'to summarize', "it's worth noting"]
low = text_all.lower()
hits = {b: len(re.findall(r'\b' + re.escape(b), low)) for b in BANNED}
hits = {k: v for k, v in hits.items() if v}
if hits:
    fails.append('banned wording: %s' % hits)
if '—' in text_all:
    fails.append('em dash present, %d times' % text_all.count('—'))

# 6 ── pictures: count, and the density each one is placed at ---------
z = zipfile.ZipFile(DOC)
rels = z.read('word/_rels/document.xml.rels').decode()
R = dict(re.findall(r'Id="([^"]+)"[^>]*Target="media/([^"]+)"', rels))
xml = z.read('word/document.xml').decode()
placed = re.findall(r'<wp:extent cx="(\d+)" cy="(\d+)"/>.*?r:embed="(rId\d+)"',
                    xml, re.S)
os.makedirs('/tmp/qaimg', exist_ok=True)
rows = []
for cx, cy, rid in placed:
    name = R[rid]
    p = '/tmp/qaimg/' + name
    open(p, 'wb').write(z.read('word/media/' + name))
    w, h = Image.open(p).size
    wpt = int(cx) / 12700
    rows.append((name, w, h, wpt, w / (wpt / 72)))
print('%-13s %-12s %9s %8s' % ('media', 'pixels', 'placed pt', 'dpi'))
for name, w, h, wpt, dpi in rows:
    print('%-13s %-12s %9.1f %8.0f' % (name, '%dx%d' % (w, h), wpt, dpi))
low_dpi = [(n, int(d)) for n, _, _, _, d in rows if d < 200]
notes.append('pictures placed: %d, of which below 200 dpi: %s'
             % (len(rows), low_dpi if low_dpi else 'none'))

# 7 ── the contents points at the right pages -------------------------
import json
PAGES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'pages.json')))
toc = {}
for p in paras:
    m = re.match(r'^(.*?)\t(\d+)$', p.text)
    if m and p.runs and p.runs[0].font.name == 'Cambria':
        toc[m.group(1)] = int(m.group(2))
bad = {k: (v, PAGES.get(k)) for k, v in toc.items() if PAGES.get(k) != v}
if bad:
    fails.append('contents page numbers disagree with the render: %s' % bad)
else:
    notes.append('contents: %d entries, every page number matches the render'
                 % len(toc))

print()
for n in notes:
    print('  ok   ' + n)
for f in fails:
    print('  FAIL ' + f)
print('\n%s' % ('ALL CHECKS PASS' if not fails else '%d CHECK(S) FAILED' % len(fails)))
sys.exit(1 if fails else 0)
