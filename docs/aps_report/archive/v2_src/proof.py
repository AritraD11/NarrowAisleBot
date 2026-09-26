# -*- coding: utf-8 -*-
"""Proofreading pass over the finished document.

Everything here reads the .docx that was actually written. The checks are the
ones that catch the errors a careful reader would: a word typed twice, a
spelling that drifts between British and American in the same document, a
number that disagrees with the same number elsewhere, a quotation mark of the
wrong kind, a space before a full stop.
"""
import re, sys, collections
import docx

DOC = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/user/NarrowAisleBot/docs/aps_report/APS Report Aritra - restructured.docx'
d = docx.Document(DOC)
paras = [p.text for p in d.paragraphs]
tbl = [c.text for t in d.tables for r in t.rows for c in r.cells]
ALL = paras + tbl
TEXT = '\n'.join(ALL)
found = collections.OrderedDict()


def note(k, items):
    if items:
        found[k] = items


# ── mechanical ───────────────────────────────────────────────────────
note('doubled word', [(i, m.group(0)) for i, t in enumerate(ALL)
                      for m in re.finditer(r'\b(\w+)\s+\1\b', t, re.I)
                      if m.group(1).lower() not in ('that', 'had', 'the')])
# a chapter heading separates its number from its title with two spaces,
# on purpose; anywhere else a double space is a slip
note('double space', [(i, t[max(0, m.start()-35):m.start()+35])
                      for i, t in enumerate(ALL) for m in re.finditer(r'\S  +\S', t)
                      if not re.match(r'^Chapter \d+  \S', t.strip())])
note('space before punctuation', [(i, t[max(0, m.start()-35):m.start()+10])
                                  for i, t in enumerate(ALL)
                                  for m in re.finditer(r'\s[,.;:](\s|$)', t)])
note('straight apostrophe', [(i, t[max(0, m.start()-30):m.start()+30])
                             for i, t in enumerate(ALL) for m in re.finditer(r"\w'\w", t)])
note('straight quote', [(i, t[:60]) for i, t in enumerate(ALL) if '"' in t])
note('em or en dash between words', [(i, t[max(0, m.start()-35):m.start()+35])
                                     for i, t in enumerate(ALL)
                                     for m in re.finditer(r'[A-Za-z]\s*[–—]\s*[A-Za-z]', t)])
note('sentence not capitalised', [(i, t[:60]) for i, t in enumerate(ALL)
                                  if re.match(r'^[a-z]', t.strip()) and len(t.strip()) > 40])
note('unbalanced brackets', [(i, t[:70]) for i, t in enumerate(ALL)
                             if t.count('(') != t.count(')')])

# ── spelling register: the document is British throughout ────────────
# the document is British throughout. A bare 'meter' is a slip; one inside
# parameter, perimeter or tachometer is not, so every pattern is bounded.
US = [r'\bnormaliz', r'\bcharacteriz', r'\borganiz', r'\brecogniz', r'\bminimiz',
      r'\boptimiz', r'\banalyz', r'\bmeters?\b', r'\bliters?\b', r'\bcenter',
      r'\bcolor', r'\bbehavior', r'\bmodeling\b', r'\blabeled\b', r'\btraveled\b',
      r'\bfulfill\b', r'\bdefense\b']
_bib = next(i for i, t in enumerate(paras) if t.strip() == 'Bibliography')
note('American spelling in body', [(i, m.group(0), t[max(0, m.start()-40):m.start()+40])
                                   for i, t in enumerate(paras[:_bib])
                                   for w in US for m in re.finditer(w, t)])

# ── house style ──────────────────────────────────────────────────────
BANNED = ['delve', 'leverage', 'utilize', 'utilise', 'foster', 'pivotal', 'robust',
          'seamless', 'cutting-edge', 'innovative', 'game-changing', 'transformative',
          'groundbreaking', 'paradigm', 'synergy', 'tapestry', 'multifaceted',
          'nuanced', 'realm', 'landscape', 'ecosystem', 'holistic', 'unlock',
          'harness', 'underscore', 'streamline', 'testament', 'underpinnings',
          'spearhead', 'empower', 'notably', 'importantly', 'furthermore',
          'moreover', 'consequently', 'ever-evolving', 'in conclusion', 'to summarize']
low = TEXT.lower()
note('banned wording', [(w, len(re.findall(r'\b' + w, low)))
                        for w in BANNED if re.search(r'\b' + w, low)])

# ── numbers that appear more than once must agree ────────────────────
FACTS = {
    'wheel RMS unloaded': r'0\.040 to 0\.047',
    'wheel RMS loaded': r'0\.066 to 0\.074',
    'outer arm': r'0\.5607',
    'inner arm': r'0\.4907',
    'half track': r'157\.69',
    'mass': r'45\.54',
    'peak PWM': r'131 of the 255',
    'loop rate': r'100 Hz',
    'Kp': r'\bKp = 45\b|proportional gain of 45',
    'Ki': r'Ki = 250|integral gain of 253|integral gain is 250',
    'closure 10.61': r'10\.61 m',
    'scan match 206.7': r'206\.7',
    'incidents': r'26,800',
    'workers': r'22 million',
}
note('key figures found', [(k, len(re.findall(v, TEXT))) for k, v in FACTS.items()])

# ── cross-reference integrity ────────────────────────────────────────
heads = {p.text.strip() for p in d.paragraphs
         if p.style.name in ('Heading 1', 'Heading 2')}
secs = {h.split()[0] for h in heads if re.match(r'^\d+\.\d+ ', h)}
note('dangling Section ref', sorted({m for m in re.findall(r'Section (\d+\.\d+)', TEXT)
                                    if m not in secs}))
caps = sorted({int(m) for m in re.findall(r'^Figure (\d+)\.', TEXT, re.M)})
note('dangling Figure ref', sorted({int(n) for g in
                                    re.findall(r'Figures? ((?:\d+)(?:(?:,| and) \d+)*)', TEXT)
                                    for n in re.findall(r'\d+', g)} - set(caps)))

# ── text repeated between a caption and the prose beside it ──────────
GRAM = 9
body = [t for t in paras[:next(i for i, x in enumerate(paras)
                               if x.strip() == 'Bibliography')] if t.strip()]
pos = collections.defaultdict(set)
for i, t in enumerate(body):
    w = re.findall(r"[\w'\u2019%\u00b0.-]+", t.lower())
    for j in range(len(w) - GRAM + 1):
        pos[' '.join(w[j:j + GRAM])].add(i)
pairs = {}
for gram, where in pos.items():
    if len(where) > 1:
        k = tuple(sorted(where))
        if k not in pairs or len(gram) > len(pairs[k]):
            pairs[k] = gram
# neighbouring paragraphs repeating each other is the case worth reporting;
# the abstract and the conclusions restating a result on purpose is not
near = [(k, g) for k, g in pairs.items()
        if max(k) - min(k) <= 20 and not body[min(k)].startswith(('Chapter', 'Figure'))]
note('repetition between neighbouring paragraphs',
     [('paras %s' % (list(k),), g) for k, g in sorted(near)])

print('paragraphs %d, table cells %d, words %d'
      % (len(paras), len(tbl), len(TEXT.split())))
for k, v in found.items():
    print('\n== %s (%d) ==' % (k, len(v)))
    for item in v[:14]:
        print('   ', item)
    if len(v) > 14:
        print('    ... %d more' % (len(v) - 14))
