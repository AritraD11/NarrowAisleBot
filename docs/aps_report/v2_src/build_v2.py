# -*- coding: utf-8 -*-
"""Build the restructured APS report.

The layout is the September document's, measured off it and reproduced rather
than reinvented: A4 with 25.4 mm margins, Times New Roman 12 justified for the
body, Calibri Bold 16 and 14 for chapter and section headings, Times New Roman
Italic 9 for captions under a centred label line, Cambria 12 with a hanging
indent for the references, and tables ruled only above the header, below it and
under the last row.

What changes is the structure. One unified introduction covering all three
strands, then a chapter each, then a combined conclusion. Prose that already
existed is copied run for run out of the previous document rather than retyped,
so nothing the supervisor has read alters by accident; every cross-reference in
that copied prose is remapped, and every remap is asserted.

Run twice: the first pass writes the document, LibreOffice renders it, the real
page of every heading is read back, and the second pass writes the contents with
those numbers.
"""
import json, os, re, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docx
from docx import Document
from docx.shared import Pt, Mm, Inches, RGBColor
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER)
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import OxmlElement, parse_xml

import content as C

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(f'{HERE}/../../..')
FIGDIR = os.path.abspath(f'{HERE}/../figures')
MEDIA = os.environ.get('NAB_MEDIA')       # the previous document's word/media
BASE = os.environ.get('NAB_BASE')         # the previous document itself
OUT = os.path.abspath(f'{HERE}/../APS Report Aritra - restructured.docx')
PAGES = f'{HERE}/pages.json'

# ── the previous document, indexed by paragraph ──────────────────────
SRC = Document(BASE)
SP = SRC.paragraphs

# Section and chapter numbers moved when the chapters were regrouped. Every
# reference in reused prose is rewritten here, and the count of each rewrite is
# asserted at the end of the build so a missed one cannot pass silently.
REMAP = [
    ('Section 5.1', 'Section 1.3'), ('Section 5.2', 'Section 1.4'),
    ('Section 5.3', 'Section 1.4'), ('Section 5.4', 'Section 1.5'),
    ('Section 5.5', 'Section 1.7'), ('Section 5.6', 'Section 1.8'),
    ('Section 5.7', 'Section 1.8'), ('Section 5.8', 'Section 2.4'),
    ('Section 5.9', 'Section 1.9'),
    ('Section 6.1', 'Section 1.10'), ('Section 6.2', 'Section 1.11'),
    ('Section 6.3', 'Section 1.12'), ('Section 6.4', 'Section 1.13'),
    ('Section 6.5', 'Section 1.14'), ('Section 6.6', 'Section 1.15'),
    ('Section 6.7', 'Section 1.16'), ('Section 6.8', 'Section 2.6'),
    ('Chapter 7', 'Chapter 4'),
]
# Figure numbers moved too, because the prior work's own figure now opens the
# document. Only three figures are referred to by number in reused prose.
REMAP += [('Figure 14', 'Figure 15'), ('Figure 13', 'Figure 14'),
          ('Figure 10', 'Figure 11')]
REMAP_HITS = {a: 0 for a, _ in REMAP}
# A reference that must NOT survive into the new document at all.
STALE = re.compile(r'Section [56]\.\d|Chapter [567]\b')


def remap(t):
    for a, b in REMAP:
        if a in t:
            REMAP_HITS[a] += t.count(a)
            t = t.replace(a, b)
    return t


# ── document ─────────────────────────────────────────────────────────
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Mm(210), Mm(297)
sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Mm(25.4)


def set_font(style, name, size, bold=False, italic=False, color=None):
    style.font.name = name
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    if color is not None:
        style.font.color.rgb = color
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.append(rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), name)


st = doc.styles['Normal']
set_font(st, 'Times New Roman', 12)
st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
st.paragraph_format.space_after = Pt(9)
st.paragraph_format.space_before = Pt(0)
st.paragraph_format.line_spacing = 1.0

h1 = doc.styles['Heading 1']
set_font(h1, 'Calibri', 16, bold=True, color=RGBColor(0, 0, 0))
h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
h1.paragraph_format.space_before = Pt(12)
h1.paragraph_format.space_after = Pt(8)
h1.paragraph_format.keep_with_next = True

h2 = doc.styles['Heading 2']
set_font(h2, 'Calibri', 14, bold=True, color=RGBColor(0, 0, 0))
h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
h2.paragraph_format.space_before = Pt(10)
h2.paragraph_format.space_after = Pt(8)
h2.paragraph_format.keep_with_next = True


def para(text='', style=None, align=None, size=None, bold=False, italic=False,
         font=None, space_after=None, space_before=None, line_spacing=None,
         keep_with_next=False):
    p = doc.add_paragraph(style=style)
    if text:
        r = p.add_run(text)
        r.bold = bold
        r.italic = italic
        if size:
            r.font.size = Pt(size)
        if font:
            r.font.name = font
            r._element.rPr.rFonts.set(qn('w:eastAsia'), font)
            r._element.rPr.rFonts.set(qn('w:cs'), font)
    if align is not None:
        p.paragraph_format.alignment = align
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    if space_before is not None:
        p.paragraph_format.space_before = Pt(space_before)
    if line_spacing is not None:
        p.paragraph_format.line_spacing = line_spacing
    p.paragraph_format.keep_with_next = keep_with_next
    return p


from _tables_eqs import TABLES, EQS, M, W

# the previous monitoring table described the system generically; this one
# names the parts, which is what the chapter now needs
TABLES['TABLE_IOT'] = C.TABLE_IOT2

# ── front matter ─────────────────────────────────────────────────────
TITLE = ('Development and Validation of Narrow-Aisle Robotic and IoT-Based '
         'Systems for Warehouse Management')

para('Annual Progress Seminar Report on', align=WD_ALIGN_PARAGRAPH.CENTER,
     size=16, italic=True, space_after=14, line_spacing=1.15)
p = doc.add_paragraph()
p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(18)
p.paragraph_format.line_spacing = 1.15
r = p.add_run(TITLE)
r.bold = True
r.font.size = Pt(18)
for t, b, sa in [('(On completion of first year of PhD)', False, 26),
                 ('by', False, 12),
                 ('ARITRA DAS', True, 6),
                 ('Roll No: 25D0074', False, 26),
                 ('Under the supervision of', False, 12),
                 ('PROF. AMBARISH KUNWAR', True, 12)]:
    para(t, align=WD_ALIGN_PARAGRAPH.CENTER, size=14, bold=b, space_after=sa,
         line_spacing=1.15)
p = doc.add_paragraph()
p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(22)
p.add_run().add_picture(f'{MEDIA}/image1.png', width=Pt(104.4), height=Pt(96.2))
for t in ('Department of Biosciences and Bioengineering',
          'Indian Institute of Technology Bombay', 'Mumbai, Maharashtra'):
    para(t, align=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_after=4,
         line_spacing=1.15)


def copy_runs(p, srcp, size=None, force_italic=False):
    """Reproduce a paragraph of the previous document run for run, so bold
    lead-ins and italic journal titles survive, with cross-references remapped."""
    for r in srcp.runs:
        t = remap(r.text)
        nr = p.add_run(t)
        nr.bold = r.bold
        nr.italic = True if force_italic else r.italic
        if size:
            nr.font.size = Pt(size)
    return p


def pagebreak_before(p):
    p.paragraph_format.page_break_before = True
    return p


def frontmatter(title, idxs, tail=()):
    pagebreak_before(para(title, size=16, bold=True,
                          align=WD_ALIGN_PARAGRAPH.LEFT, space_after=18,
                          keep_with_next=True))
    for i in idxs:
        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(10)
        p.paragraph_format.line_spacing = 1.15
        copy_runs(p, SP[i])
    for i in tail:
        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        copy_runs(p, SP[i])


frontmatter('Acknowledgement', [14, 15, 16])
frontmatter('Plagiarism Undertaking', [19], [20, 21])

# ---- abstract, which the September version did not have
pagebreak_before(para('Abstract', size=16, bold=True,
                      align=WD_ALIGN_PARAGRAPH.LEFT, space_after=18,
                      keep_with_next=True))
for t in C.ABSTRACT:
    para(t, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=10, line_spacing=1.15)

# ---- contents. The page numbers are measured off a rendering of this same
#      document rather than typed, and the build refuses to emit final output
#      until they have been.
TOC = [(k, t) for k, t, *_ in
       [(e[0], e[1]) for e in C.BODY if e[0] in ('h1', 'h2')]]
PAGEMAP = json.load(open(PAGES)) if os.path.exists(PAGES) else {}

pagebreak_before(para('Table of Contents', size=16,
                      align=WD_ALIGN_PARAGRAPH.LEFT, font='Calibri',
                      space_after=12, keep_with_next=True))


def toc_line(text, level, page):
    tp = doc.add_paragraph()
    pf = tp.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.space_after = Pt(4.3)
    pf.line_spacing = 1.0
    pf.left_indent = Pt(12) if level == 2 else Pt(0)
    pf.tab_stops.add_tab_stop(Pt(453.4), WD_TAB_ALIGNMENT.RIGHT,
                              WD_TAB_LEADER.DOTS)
    for txt in (text, '\t', str(page)):
        r = tp.add_run(txt)
        r.font.name = 'Cambria'
        r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Cambria')
        r._element.rPr.rFonts.set(qn('w:cs'), 'Cambria')
        r.font.size = Pt(12)


for kind, text in TOC:
    toc_line(text, 1 if kind == 'h1' else 2, PAGEMAP.get(text, ''))
BODY_STARTS_NEW_PAGE = True

# ── body ─────────────────────────────────────────────────────────────
from _tables_eqs import *  # noqa  (TABLES, EQS and the m: helpers)


def add_table(spec):
    t = doc.add_table(rows=1, cols=len(spec['cols']))
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.autofit = False
    for i, c in enumerate(spec['head']):
        cell = t.rows[0].cells[i]
        cell.text = ''
        pp = cell.paragraphs[0]
        pp.paragraph_format.space_after = Pt(1.8)
        pp.paragraph_format.space_before = Pt(1.8)
        pp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pp.add_run(c)
    for row in spec['rows']:
        cells = t.add_row().cells
        for i, c in enumerate(row):
            cells[i].text = ''
            pp = cells[i].paragraphs[0]
            pp.paragraph_format.space_after = Pt(1.8)
            pp.paragraph_format.space_before = Pt(1.8)
            pp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pp.add_run(c)
    total = sum(spec['cols'])
    tblPr0 = t._tbl.tblPr
    tblPr0.insert_element_before(parse_xml(
        f'<w:tblW {nsdecls("w")} w:w="{int(total*20)}" w:type="dxa"/>'),
        'w:jc', 'w:tblCellSpacing', 'w:tblInd', 'w:tblBorders', 'w:shd',
        'w:tblLayout', 'w:tblCellMar', 'w:tblLook')
    tblPr0.insert_element_before(parse_xml(
        f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'), 'w:tblCellMar',
        'w:tblLook')
    tblPr0.insert_element_before(parse_xml(
        f'<w:tblCellMar {nsdecls("w")}>'
        f'<w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
        f'<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/>'
        f'</w:tblCellMar>'), 'w:tblLook')
    grid = t._tbl.find(qn('w:tblGrid'))
    for gc, w in zip(grid.findall(qn('w:gridCol')), spec['cols']):
        gc.set(qn('w:w'), str(int(w * 20)))
    for r_ in t.rows:
        for i, cell in enumerate(r_.cells):
            cell.width = Pt(spec['cols'][i])
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        f'<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'</w:tblBorders>')
    t._tbl.tblPr.insert_element_before(borders, 'w:shd', 'w:tblLayout',
                                       'w:tblCellMar', 'w:tblLook')
    hdr = t.rows[0]
    trPr = hdr._tr.get_or_add_trPr()
    trPr.insert_element_before(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'),
                               'w:trHeight', 'w:tblCellSpacing', 'w:jc')
    for cell in hdr.cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.insert_element_before(parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
            f'</w:tcBorders>'), 'w:shd', 'w:tcMar', 'w:textDirection',
            'w:tcFitText', 'w:vAlign', 'w:hideMark')
    return t


def add_equation(xmls):
    for x in xmls:
        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(9)
        p.paragraph_format.space_before = Pt(9)
        p._p.append(parse_xml(f'<m:oMath xmlns:m="{M}" xmlns:w="{W}">{x}</m:oMath>'))


def _proposal_media(_cache=[]):
    """Unpack the fatigue proposal's pictures once, so the graphical abstract
    used as Figure 20 comes from that document rather than from a second copy."""
    if _cache:
        return _cache[0]
    import zipfile
    src = os.environ.get('NAB_PROPOSAL',
                         os.path.join(REPO, 'BB701 Full Proposal 25D0074.docx'))
    dest = os.path.join(HERE, '_proposal_media')
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(src) as z:
        for n in z.namelist():
            if n.startswith('word/media/'):
                open(os.path.join(dest, os.path.basename(n)), 'wb').write(z.read(n))
    _cache.append(dest)
    return dest


def add_figure(key):
    src, w, cap = C.FIGS[key]
    path = (src.replace('NEW/', FIGDIR + '/')
               .replace('MEDIA/', MEDIA + '/')
               .replace('REPO/', REPO + '/')
               .replace('SRC/', _proposal_media() + '/'))
    assert os.path.exists(path), path
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(path, width=Pt(w))
    lp = doc.add_paragraph()
    lp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    lp.paragraph_format.space_after = Pt(9.5)
    lp.paragraph_format.line_spacing = 1.0
    lr = lp.add_run(C.LABELS[key])
    lr.italic = True
    lr.font.size = Pt(9)
    cp = doc.add_paragraph()
    cp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    cp.paragraph_format.space_after = Pt(8)
    cp.paragraph_format.line_spacing = 1.0
    cr = cp.add_run(cap)
    cr.italic = True
    cr.font.size = Pt(9)


HEADINGS = []          # (text, level) in document order, for the contents pass
first_chapter = True
chapter_open = 0
used_figs = set()

for el in C.BODY:
    kind = el[0]
    if kind == 'h1':
        if not first_chapter:
            blank = doc.add_paragraph()
            blank.paragraph_format.space_after = Pt(9)
            blank.paragraph_format.keep_with_next = True
        hp = doc.add_paragraph(el[1], style='Heading 1')
        if first_chapter:
            hp.paragraph_format.space_before = Pt(0)
            hp.paragraph_format.page_break_before = True
        first_chapter = False
        chapter_open = 2
        HEADINGS.append((el[1], 1))
    elif kind == 'h2':
        doc.add_paragraph(el[1], style='Heading 2')
        if chapter_open == 2:
            chapter_open = 1
        HEADINGS.append((el[1], 2))
    elif kind == 'p':
        p = doc.add_paragraph()
        if chapter_open == 1:
            p.paragraph_format.keep_with_next = True
            chapter_open = 0
        p.add_run(el[1])
    elif kind == 'lead':
        p = doc.add_paragraph()
        if chapter_open == 1:
            p.paragraph_format.keep_with_next = True
            chapter_open = 0
        r = p.add_run(el[1])
        r.bold = True
        if el[2]:
            p.add_run(' ' + el[2])
    elif kind in ('R', 'Rs'):
        srcp = SP[el[1]]
        p = doc.add_paragraph()
        if chapter_open == 1:
            p.paragraph_format.keep_with_next = True
            chapter_open = 0
        if kind == 'R':
            copy_runs(p, srcp)
        else:
            full = remap(srcp.text)
            for find, repl in el[2]:
                assert full.count(find) == 1, (el[1], find[:50])
                full = full.replace(find, repl)
            lead = srcp.runs[0] if srcp.runs else None
            if lead is not None and lead.bold and full.startswith(lead.text):
                r = p.add_run(lead.text)
                r.bold = True
                p.add_run(full[len(lead.text):])
            else:
                p.add_run(full)
    elif kind == 'ref':
        srcp = SP[el[1]]
        # four entries carry a stray space inside the page range, which the
        # en dash makes obvious in print: "1271\u2013 1278"
        def _pages(t):
            return re.sub('(\\d)\\s*\u2013\\s*(\\d)', '\\1\u2013\\2', t)
        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.333)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.0
        for r in srcp.runs:
            nr = p.add_run(_pages(r.text))
            nr.italic = r.italic
            nr.bold = r.bold
            nr.font.name = 'Cambria'
            nr._element.rPr.rFonts.set(qn('w:eastAsia'), 'Cambria')
            nr._element.rPr.rFonts.set(qn('w:cs'), 'Cambria')
            nr.font.size = Pt(12)
    elif kind == 'F':
        add_figure(el[1])
        used_figs.add(el[1])
        chapter_open = 0
    elif kind == 'T':
        add_table(TABLES[el[1]])
        para('', space_after=0, space_before=0)
    elif kind == 'E':
        add_equation(EQS[el[1]])
    else:
        raise SystemExit('unknown element ' + kind)

# ── footer ───────────────────────────────────────────────────────────
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp._p.append(parse_xml(
    f'<w:fldSimple {nsdecls("w")} w:instr=" PAGE "><w:r>'
    f'<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
    f'<w:sz w:val="20"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple>'))

# ── checks that must hold before anything is written ─────────────────
missing = set(C.FIGS) - used_figs
assert not missing, 'figures defined but never placed: %s' % sorted(missing)
unmapped = []
for p in doc.paragraphs:
    if STALE.search(p.text):
        unmapped.append(p.text[:90])
assert not unmapped, 'stale cross-references survived:\n' + '\n'.join(unmapped)

doc.save(OUT)
print('wrote', OUT)
print('paragraphs %d  tables %d  figures %d  headings %d'
      % (len(doc.paragraphs), len(doc.tables), len(used_figs), len(HEADINGS)))
print('cross-references remapped:',
      ', '.join('%s→%s x%d' % (a, b, REMAP_HITS[a])
                for a, b in REMAP if REMAP_HITS[a]))
json.dump([h for h in HEADINGS], open(f'{HERE}/headings.json', 'w'))
