"""Read the real page of every heading out of a rendered PDF.

Headings are found by their face rather than by their words, because the
contents page repeats every heading verbatim and a text match picks that up
instead. The chapter and section faces are the only bold sans in the document.
"""
import json, sys
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextContainer, LTChar, LTTextLine

lap = LAParams(word_margin=0.18, char_margin=2.0, line_margin=0.30)
found = []
for pno, page in enumerate(extract_pages(sys.argv[1], laparams=lap), 1):
    for el in page:
        if not isinstance(el, LTTextContainer):
            continue
        for ln in el:
            if not isinstance(ln, LTTextLine):
                continue
            cs = [c for c in ln if isinstance(c, LTChar)]
            if not cs:
                continue
            f, s = cs[0].fontname, round(cs[0].size)
            sans_bold = ('Carlito-Bold' in f or 'Sans-Bold' in f
                         or ('Calibri' in f and 'Bold' in f))
            if sans_bold and s in (14, 16):
                found.append((' '.join(ln.get_text().split()), 1 if s == 16 else 2, pno))

HEAD = json.load(open(sys.argv[2]))
out, i = {}, 0
for text, level in HEAD:
    norm = ' '.join(text.split())
    while i < len(found):
        ft, fl, fp = found[i]
        i += 1
        if fl == level and (ft == norm or norm.startswith(ft) or ft.startswith(norm)):
            out[text] = fp
            break
    else:
        raise SystemExit('heading not located in the render: %r' % text)
json.dump(out, open(sys.argv[3], 'w'), indent=0)
print('located %d of %d headings across %d rendered heading lines'
      % (len(out), len(HEAD), len(found)))
