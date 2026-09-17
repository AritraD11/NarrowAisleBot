"""Rebuild the APS report as a .docx, matching the submitted PDF's formatting,
with the audited corrections applied.

Source of truth for layout, measured off the PDF:
  A4, 25.4 mm margins all round
  body      Times New Roman 12, justified, single spacing, 9 pt after
  headings  Calibri Bold 16 (chapter) / 14 (section)
  captions  Times New Roman Italic 9, justified; centred label line above
  tables    top rule, header rule, bottom rule; no vertical or interior rules
  refs      Cambria 12, hanging indent at 0.5 in
"""
import json, os, re, copy
from docx import Document
from docx.shared import Pt, Mm, Inches, RGBColor, Emu
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT,
                            WD_TAB_LEADER)
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import OxmlElement, parse_xml

SCRATCH = os.path.dirname(os.path.abspath(__file__))
BLOCKS = json.load(open(f'{SCRATCH}/blocks.json'))
IMGDIR = os.path.abspath(f'{SCRATCH}/../pdfimg')
OUT = '/home/user/NarrowAisleBot/docs/aps_report/APS report Aritra.docx'

PT = 1.0  # pdf points

# ---------------------------------------------------------------- regions ---
# (page, y_high, y_low) inclusive windows whose lines are dropped from the
# paragraph flow because they are rebuilt as tables or equations.
DROP = [
    (12, 300.5, 0.0), (13, 800.0, 657.1),      # hardware specification table
    (20, 633.1, 452.5),                        # monitoring specification table
    (22, 634.5, 564.8),                        # per-wheel tracking table
    (28, 729.7, 649.9),                        # scan-matching comparison table
    (15, 334.8, 334.8), (15, 275.4, 252.4), (15, 101.6, 84.0),
    (16, 571.7, 554.6),
]
# marker insertion points: (page, y_of_first_dropped_line, marker)
MARK = {
    (12, 300.5): 'TABLE_SPEC', (20, 633.1): 'TABLE_IOT',
    (22, 634.5): 'TABLE_WHEEL', (28, 729.7): 'TABLE_SCAN',
    (15, 334.8): 'EQ1', (15, 275.4): 'EQ2', (15, 101.6): 'EQ3',
    (16, 571.7): 'EQ4',
}

def dropped(page, y):
    for p, hi, lo in DROP:
        if p == page and lo - 0.05 <= y <= hi + 0.05:
            return True
    return False

# ------------------------------------------------------------ paragraphs ---
def runs_text(line):
    return ''.join(r['t'] for r in line['runs'])

def assemble(page_from=5, page_to=37):
    """Merge lines into paragraph dicts: style, runs [(bold, italic, text)]."""
    flow = []
    prev = None
    seen_marks = set()
    for pno in range(page_from, page_to + 1):
        for it in BLOCKS[pno - 1]:
            if it['kind'] == 'image':
                flow.append({'style': 'image', 'page': pno,
                             'w': it['w'], 'h': it['h']})
                prev = None
                continue
            y = it['y']
            key = (pno, round(y, 1))
            if key in MARK and key not in seen_marks:
                seen_marks.add(key)
                flow.append({'style': 'marker', 'name': MARK[key]})
            if dropped(pno, y):
                prev = None
                continue
            style = it['style']
            newpara = True
            if style == 'toc':
                # reference list: a new entry begins at the number, continuation
                # lines sit at the hanging indent
                if prev is not None and prev['style'] == 'toc' and it['x0'] > 100:
                    newpara = False
            elif prev is not None and prev['style'] == style:
                same_x = abs(prev['_x0'] - it['x0']) < 3.0
                if prev['_page'] == pno:
                    if prev['_y'] - y < 17.5 and same_x:
                        newpara = False
                elif prev['_page'] == pno - 1:
                    # a paragraph running across a page boundary: the last line
                    # on the previous page is justified to the full measure
                    if prev['_x1'] > 515.0 and same_x:
                        newpara = False
            if newpara:
                para = {'style': style, 'runs': [], '_y': y, '_x1': it['x1'],
                        '_x0': it['x0'], '_page': pno, 'size': it['size']}
                flow.append(para)
                prev = para
            else:
                joiner = '' if prev['runs'] and prev['runs'][-1]['t'].rstrip().endswith('-') else ' '
                if joiner and prev['runs']:
                    prev['runs'][-1]['t'] = prev['runs'][-1]['t'].rstrip() + ' '
                elif prev['runs']:
                    prev['runs'][-1]['t'] = prev['runs'][-1]['t'].rstrip()
                prev['_y'] = y
            prev['_x1'] = it['x1']
            prev['_page'] = pno
            for r in it['runs']:
                t = re.sub(r'\s+', ' ', r['t'])
                if prev['runs'] and prev['runs'][-1]['b'] == r['b'] and prev['runs'][-1]['i'] == r['i']:
                    prev['runs'][-1]['t'] += t
                else:
                    prev['runs'].append({'b': r['b'], 'i': r['i'], 't': t})
            prev['_y'] = y
    for p in flow:
        if p['style'] in ('image', 'marker'):
            continue
        for r in p['runs']:
            r['t'] = re.sub(r'\s+', ' ', r['t'])
        while p['runs'] and not p['runs'][-1]['t'].strip():
            p['runs'].pop()
        if p['runs']:
            p['runs'][-1]['t'] = p['runs'][-1]['t'].rstrip()
            p['runs'][0]['t'] = p['runs'][0]['t'].lstrip()
    return [p for p in flow if p['style'] in ('image', 'marker') or p['runs']]

FLOW = assemble()

# ------------------------------------------------------------------ edits ---
# Every edit is (must_match_count, find, replace). The count is asserted, so a
# silent miss is impossible.
EDITS = [
    # 1. Section 5.2, the encoder count and everything derived from it.
    (1,
     'Each drive motor produces 93,132 encoder counts per revolution at the wheel, '
     'after the optical encoder is read in full quadrature and the gear reduction is '
     'applied. At the rated speed the output shaft turns once per second, so one motor '
     'emits 93,132 counted edges per second and four motors emit 372,528.',
     'The two front motors carry GTK08 encoders producing 186,264 counts per '
     'revolution at the wheel, and the two rear motors optical encoders producing '
     '93,132, in both cases after full quadrature decoding and the gear reduction. At '
     'the rated speed the output shaft turns once per second, so the four motors '
     'together emit 558,792 counted edges per second.'),
    (1, 'leaves approximately 43 cycles per edge',
        'leaves approximately 29 cycles per edge'),
    # 2. Section 6.1, the drive behind the tracking table is teleoperated.
    (1,
     'Tracking holds under autonomous operation as well as on the bench. The table '
     'below comes from the motor telemetry of the autonomous drive shown as Drive C in '
     'Figure 10, logged at 20 Hz over 4 713 samples per wheel.',
     'Tracking holds on the floor under operator control as well as on the bench. The '
     'table below comes from the motor telemetry of the drive shown as Drive C in '
     'Figure 10, logged at 20 Hz over 4,713 telemetry rows.'),
    # 3. Figure 9 caption, matching the figure's own arithmetic.
    (1, 'The measured increases are 22.4, 23.6, 30.3 and 21.2 per cent',
        'The measured increases are 22.5, 23.6, 30.3 and 21.0 per cent'),
    # 4. Section 6.1 body, the provenance of the run the 24 % comes from.
    (1,
     'The prediction is a good one on the evidence, and the one motor sitting at the '
     'edge of it is the sort of detail worth keeping in view when the loaded '
     'feedforward is re-measured.',
     'These figures come from the first of three floor runs recorded on 6 August. The '
     'two later runs of that afternoon, at the same commanded levels but driven over '
     'different patches of floor, give means of 14 and 3 per cent, so the increase is '
     'real while its size is not established to better than the width of the band it '
     'was predicted against. The likeliest reason is the surface rather than the load: '
     'casual driving covers different floor patches and headings, where a staircase '
     'test holds position and sweeps demand instead. That test has not been run on the '
     'floor, and it is what would settle the figure. The one motor sitting at the edge '
     'of the band is worth keeping in view when it is.'),
    # 5. The peak drive demand, which the logs put at 131 of 255.
    (1, 'the largest drive demand observed at the operating velocity limit was 134 of '
        'the 255 available, leaving about 47 per cent of the commanded range unused',
        'the largest drive demand observed at the operating velocity limit was 131 of '
        'the 255 available, leaving about 49 per cent of the commanded range unused'),
    # 6. Figure 10 caption: the three drives were teleoperated, and the closure is
    #    the odometry's residual rather than a measurement of the physical return.
    (1, 'Wheel-odometry trajectories for three logged autonomous drives, plotted from '
        'the recorded pose. Each drive returns to its starting mark: 19 mm over 8.00 m',
        'Wheel-odometry trajectories for three logged drives, each driven manually '
        'under operator control, plotted from the recorded pose. In each case the robot '
        'was driven back to its starting mark and the wheel-odometry estimate closed to '
        '19 mm over 8.00 m'),
    (1, 'and each returns to its starting mark within 1 per cent of the distance travelled.',
        'and each closed to within 1 per cent of the distance travelled.'),
    # 7. Section 6.4, the photogrammetry result stated in the direction it was measured.
    (1,
     'On two structurally different routes the robot finished 3.85° and 4.49° away '
     'from its commanded heading, while wheel odometry, the published estimate and the '
     'SLAM pose all agreed with one another to within a few hundredths of a degree. '
     'Three estimates agreeing while all three disagree with the floor is the signature '
     'of an error they share, not one that separates them.',
     'On two structurally different routes, wheel odometry, the published estimate and '
     'the SLAM pose all reported 3.85° and 4.49° of heading change by the end of the '
     'drive, while the floor, read photogrammetrically against the tile grout, put the '
     'robot within 0.03° of the heading it started from. The robot came back to its '
     'heading. The estimators did not. Three estimates agreeing with one another while '
     'all three disagree with the floor is the signature of an error they share, not '
     'one that separates them.'),
]

def apply_edits(flow):
    for n, find, repl in EDITS:
        hits = 0
        for p in flow:
            if p['style'] in ('image', 'marker'):
                continue
            full = ''.join(r['t'] for r in p['runs'])
            if find not in full:
                continue
            hits += full.count(find)
            new = full.replace(find, repl)
            # Rebuild runs, preserving a leading bold lead-in if there was one.
            lead = p['runs'][0]
            if lead['b'] and not new.startswith(lead['t']):
                pass
            if lead['b'] and new.startswith(lead['t']):
                p['runs'] = [{'b': 1, 'i': lead['i'], 't': lead['t']},
                             {'b': 0, 'i': 0, 't': new[len(lead['t']):]}]
            else:
                p['runs'] = [{'b': 0, 'i': 0, 't': new}]
        assert hits == n, f'edit matched {hits} times, expected {n}: {find[:60]!r}'
    return flow

FLOW = apply_edits(FLOW)

# ------------------------------------------------------------------ tables ---
TABLE_SPEC = {
    'cols': [126.2, 327.8],
    'head': ['Item', 'Value'],
    'rows': [
        ['Footprint, tape-measured', '1.00 × 0.36 m'],
        ['Mass', '45.54 kg'],
        ['Outer and inner wheel longitudinal distance', '0.403 m and 0.333 m'],
        ['Half track width', '0.15769 m, identical for all four wheels'],
        ['Wheel radius', '0.0762 m'],
        ['Drive motors', '4 × geared DC, 24 V, 1:47 reduction, 60 rpm rated'],
        ['Encoders', 'Front pair GTK08, 186,264 counts per revolution at the wheel; '
                     'rear pair optical, 93,132'],
        ['Motor drivers', '2 × dual-channel, 20 A continuous, 1.5 V logic threshold'],
        ['Real-time controller', 'ESP32, 100 Hz control loop, hardware quadrature decoding'],
        ['Host computer', 'Raspberry Pi 5, Ubuntu 24.04, ROS 2'],
        ['Lidar', 'YDLIDAR X4 Pro, single-plane triangulation, 360°, 0.12–10 m rated '
                  'range, manufacturer-stated 2 cm absolute below 1 m and 3.5 % of '
                  'range from 1 to 6 m'],
        ['Power', 'LiFePO₄ 12.8 V, 30 Ah, with boost to 24 V drive and buck to 5 V logic'],
        ['Cargo arm and lighting', 'Two lateral and one vertical stepper axis, '
                                   'three-tube staged ultraviolet lighting'],
        ['Operating velocity limit', '0.12 m/s linear, 0.30 rad/s yaw'],
    ],
}
TABLE_IOT = {
    'cols': [87.9, 366.1],
    'head': ['Item', 'Specification'],
    'rows': [
        ['Sensing node', 'Single-board microcontroller with integrated Wi-Fi'],
        ['Gateway', 'Second microcontroller with a long-range LoRa module, level-translated'],
        ['Server', 'Raspberry Pi 5, containerised data platform'],
        ['Measured quantities', 'Carbon dioxide, temperature, relative humidity, '
                                'particulate mass at two size fractions, and a '
                                'non-selective gas index'],
        ['Actuators', 'Opto-isolated relay for the lamp supply and a variable-speed fan '
                      'with tachometer feedback'],
        ['Channels', 'Local Wi-Fi at 5 s, long-range LoRa at 30 s, cellular messaging on alert'],
        ['Control law', 'Hysteresis with a dead band, with fan speed scaled across the '
                        'upper part of the index range'],
        ['Zones', 'Four, across two radio-isolated deployments against a shared database'],
    ],
}
TABLE_WHEEL = {
    'cols': [72.4, 112.2, 164.3, 105.1],
    'head': ['Wheel', 'RMS error (rad/s)', 'Mean absolute error (rad/s)', 'Saturated samples'],
    'rows': [
        ['Front right', '0.077', '0.039', '0.0 %'],
        ['Front left', '0.066', '0.034', '0.0 %'],
        ['Rear right', '0.068', '0.032', '0.0 %'],
        ['Rear left', '0.075', '0.039', '0.0 %'],
    ],
}
TABLE_SCAN = {
    'cols': [153.1, 56.7, 106.1, 138.1],
    'head': ['Route', 'Range cap', 'Wheel odometry alone', 'With the scan-matching front end'],
    'rows': [
        ['38 s square, 1.42 m of path', '10 m', '2.58 cm', '6.2 cm'],
        ['1047 s drive, 21.85 m of wheel path', '10 m', '0.229 m, 10.53°', '0.477 m, 16.18°'],
        ['82.5 s circle, 3.193 m of path', '5 m', '16.2 mm, 0.51 %', '206.7 mm, 6.47 %'],
    ],
}
TABLES = {'TABLE_SPEC': TABLE_SPEC, 'TABLE_IOT': TABLE_IOT,
          'TABLE_WHEEL': TABLE_WHEEL, 'TABLE_SCAN': TABLE_SCAN}

# --------------------------------------------------------------- equations ---
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def mr(t, nor=False):
    pr = '<m:rPr><m:nor/></m:rPr>' if nor else ''
    t = (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
    return (f'<m:r xmlns:m="{M}" xmlns:w="{W}">{pr}'
            f'<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
            f'<m:t xml:space="preserve">{t}</m:t></m:r>')

def msub(base, sub):
    return f'<m:sSub xmlns:m="{M}"><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>'

def mfrac(num, den, kind='bar'):
    pr = f'<m:fPr><m:type m:val="{kind}"/></m:fPr>' if kind != 'bar' else ''
    return f'<m:f xmlns:m="{M}">{pr}<m:num>{num}</m:num><m:den>{den}</m:den></m:f>'

def macc(inner, chr_='̂'):
    return (f'<m:acc xmlns:m="{M}"><m:accPr><m:chr m:val="{chr_}"/></m:accPr>'
            f'<m:e>{inner}</m:e></m:acc>')

def mdelim(inner):
    return (f'<m:d xmlns:m="{M}"><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/>'
            f'</m:dPr><m:e>{inner}</m:e></m:d>')

K = lambda s: msub(mr('K'), mr(s, nor=True))
W_ = lambda s: msub(mr('ω'), mr(s, nor=True))
D_ = lambda s: msub(mr('δ'), mr(s, nor=True))
L_ = lambda s: msub(mr('l'), mr(s, nor=True))
INV_R = mfrac(mr('1'), mr('r'), 'lin')

EQ1 = (K('o') + mr('=') + L_('1') + mr('+') + mr('d') + mr('=') + mr('0.5607')
       + mr(' m, ', nor=True)
       + K('i') + mr('=') + L_('2') + mr('+') + mr('d') + mr('=') + mr('0.4907')
       + mr(' m', nor=True))

def _wheel(name, a, b, c, kk):
    return (W_(name) + mr('=') + INV_R
            + mdelim(mr('u') + mr(a) + mr('v') + mr(b) + mr('ω') + K(kk)))

EQ2A = (_wheel('FR', '+', '+', None, 'o') + mr(', ', nor=True)
        + _wheel('FL', '−', '−', None, 'i') + mr(',', nor=True))
EQ2B = (_wheel('RR', '−', '+', None, 'i') + mr(', ', nor=True)
        + _wheel('RL', '+', '−', None, 'o') + mr('.', nor=True))

EQ3 = (macc(mr('ω')) + msub(mr(''), mr('outer', nor=True)).replace('<m:e></m:e>', '<m:e></m:e>')
       if False else
       (msub(macc(mr('ω')), mr('outer', nor=True)) + mr('=')
        + mfrac(mr('r') + mdelim(W_('FR') + mr('−') + W_('RL')), mr('2') + K('o'))
        + mr(', ', nor=True)
        + msub(macc(mr('ω')), mr('inner', nor=True)) + mr('=')
        + mfrac(mr('r') + mdelim(W_('RR') + mr('−') + W_('FL')), mr('2') + K('i'))))

EQ4 = (msub(mr('e'), mr('ω')) + mr('=') + mfrac(mr('r'), mr('2'))
       + mdelim(mfrac(D_('outer'), K('o')) + mr('−') + mfrac(D_('inner'), K('i'))))

EQS = {'EQ1': [EQ1], 'EQ2': [EQ2A, EQ2B], 'EQ3': [EQ3], 'EQ4': [EQ4]}

# ----------------------------------------------------------------- document ---
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
        rf = OxmlElement('w:rFonts'); rpr.append(rf)
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
        r.bold = bold; r.italic = italic
        if size: r.font.size = Pt(size)
        if font:
            r.font.name = font
            r._element.rPr.rFonts.set(qn('w:eastAsia'), font)
            r._element.rPr.rFonts.set(qn('w:cs'), font)
    if align is not None: p.paragraph_format.alignment = align
    if space_after is not None: p.paragraph_format.space_after = Pt(space_after)
    if space_before is not None: p.paragraph_format.space_before = Pt(space_before)
    if line_spacing is not None: p.paragraph_format.line_spacing = line_spacing
    p.paragraph_format.keep_with_next = keep_with_next
    return p

# ---- title page
para('Annual Progress Seminar Report on', align=WD_ALIGN_PARAGRAPH.CENTER,
     size=16, italic=True, space_after=14, line_spacing=1.15)
p = doc.add_paragraph()
p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(18)
p.paragraph_format.line_spacing = 1.15
r = p.add_run('Development and Validation of Narrow-Aisle Robotic and IoT-Based '
              'Systems for Warehouse Applications, with a Proposed Framework for '
              'Contactless Worker-Fatigue Assessment')
r.bold = True; r.font.size = Pt(18)
for t, b, sa in [('(On completion of first year of PhD)', False, 26),
                 ('by', False, 12),
                 ('ARITRA DAS', True, 6),
                 ('Roll No: 25D0074', False, 26),
                 ('Under the supervision of', False, 12),
                 ('PROF. AMBARISH KUNWAR', True, 12)]:
    para(t, align=WD_ALIGN_PARAGRAPH.CENTER, size=14, bold=b, space_after=sa,
         line_spacing=1.15)
p = doc.add_paragraph(); p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(22)
p.add_run().add_picture(f'{IMGDIR}/p01_Image15.png', width=Pt(104.4), height=Pt(96.2))
for t in ('Department of Biosciences and Bioengineering',
          'Indian Institute of Technology Bombay', 'Mumbai, Maharashtra'):
    para(t, align=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_after=4, line_spacing=1.15)
doc.add_page_break()

# ---- acknowledgement and undertaking, from the PDF's own text
def frontmatter(title, paragraphs, tail=()):
    para(title, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT,
         space_after=18, keep_with_next=True)
    for t in paragraphs:
        para(t, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=10, line_spacing=1.15)
    for t in tail:
        para(t, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2, line_spacing=1.15)
    doc.add_page_break()

FRONT = json.load(open(f'{SCRATCH}/frontmatter.json'))
frontmatter('Acknowledgement', FRONT['ack'])
frontmatter('Plagiarism Undertaking', FRONT['plag'], FRONT['plag_tail'])

# ---- table of contents (a real field, so page numbers are always right)
para('Table of Contents', size=16, align=WD_ALIGN_PARAGRAPH.LEFT,
     font='Calibri', space_after=12, keep_with_next=True)
TOC = json.load(open(f'{SCRATCH}/toc.json'))
for e in TOC:
    tp = doc.add_paragraph()
    pf = tp.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.space_after = Pt(4.3)
    pf.line_spacing = 1.0
    pf.left_indent = Pt(12) if e['level'] == 2 else Pt(0)
    pf.tab_stops.add_tab_stop(Pt(453.4),
                              WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    for txt in (e['text'], '\t', str(e['page'])):
        r = tp.add_run(txt)
        r.font.name = 'Cambria'
        r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Cambria')
        r._element.rPr.rFonts.set(qn('w:cs'), 'Cambria')
        r.font.size = Pt(12)

doc.add_page_break()

# ---- body
PLACED = 0
IMAGES = {}
for fn in sorted(os.listdir(IMGDIR)):
    m = re.match(r'p(\d+)_', fn)
    if m and int(m.group(1)) > 1:
        IMAGES.setdefault(int(m.group(1)), []).append(fn)

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
        f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'),
        'w:tblCellMar', 'w:tblLook')
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
    # borders: rule above the header, below the header, and below the last row
    tblPr = t._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        f'<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'</w:tblBorders>')
    tblPr.insert_element_before(
        borders, 'w:shd', 'w:tblLayout', 'w:tblCellMar', 'w:tblLook')
    hdr = t.rows[0]
    trPr = hdr._tr.get_or_add_trPr()
    trPr.insert_element_before(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'),
                               'w:trHeight', 'w:tblCellSpacing', 'w:jc')
    for cell in hdr.cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.insert_element_before(parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
            f'</w:tcBorders>'), 'w:shd', 'w:tcMar', 'w:textDirection', 'w:tcFitText',
            'w:vAlign', 'w:hideMark')
    return t

def add_equation(xmls):
    for x in xmls:
        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(9)
        p.paragraph_format.space_before = Pt(9)
        p._p.append(parse_xml(f'<m:oMath xmlns:m="{M}" xmlns:w="{W}">{x}</m:oMath>'))

CHAPTER_RE = re.compile(r'^Chapter \d+$')
first_chapter = True
chapter_open = 0   # binds a chapter's opening block so it cannot be left stranded
for el in FLOW:
    if el['style'] == 'marker':
        name = el['name']
        if name in TABLES:
            add_table(TABLES[name])
            para('', space_after=0, space_before=0)
        else:
            add_equation(EQS[name])
        continue
    if el['style'] == 'image':
        fns = IMAGES.get(el['page'], [])
        if not fns:
            continue
        fn = fns.pop(0)
        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = False
        p.add_run().add_picture(f'{IMGDIR}/{fn}', width=Pt(el['w']))
        if chapter_open == 1:
            p.paragraph_format.keep_with_next = True
            chapter_open = 0
        PLACED += 1
        continue
    text = ''.join(r['t'] for r in el['runs'])
    if el['style'] == 'h1':
        is_chapter = bool(CHAPTER_RE.match(text.strip()))
        blank = None
        if is_chapter and not first_chapter:
            # the original separates chapters with a blank line, not a page break
            blank = doc.add_paragraph()
            blank.paragraph_format.space_after = Pt(9)
            blank.paragraph_format.keep_with_next = True
        hp = doc.add_paragraph(text.strip(), style='Heading 1')
        if first_chapter and is_chapter:
            hp.paragraph_format.space_before = Pt(0)
        if is_chapter:
            chapter_open = 2
        first_chapter = False
        continue
    if el['style'] == 'h2':
        doc.add_paragraph(text.strip(), style='Heading 2')
        if chapter_open == 2:
            chapter_open = 1
        continue
    if el['style'] == 'caption':
        centred = el['_x0'] > 120
        p = doc.add_paragraph()
        p.paragraph_format.alignment = (WD_ALIGN_PARAGRAPH.CENTER if centred
                                        else WD_ALIGN_PARAGRAPH.JUSTIFY)
        p.paragraph_format.space_after = Pt(9.5 if centred else 8)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.keep_with_next = False
        r = p.add_run(text)
        r.italic = True
        r.font.size = Pt(9)
        continue
    if el['style'] == 'toc':
        # the reference list: Cambria, numbered, hanging indent
        p = doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.333)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.0
        for run in el['runs']:
            r = p.add_run(run['t'])
            r.italic = bool(run['i'])
            r.bold = bool(run['b'])
            r.font.name = 'Cambria'
            r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Cambria')
            r._element.rPr.rFonts.set(qn('w:cs'), 'Cambria')
            r.font.size = Pt(12)
        continue
    p = doc.add_paragraph()
    if chapter_open == 1:
        p.paragraph_format.keep_with_next = True
        chapter_open = 0
    for run in el['runs']:
        r = p.add_run(run['t'])
        r.bold = bool(run['b'])
        r.italic = bool(run['i'])

# ---- page numbers, so the table of contents points at something
footer = sec.footer
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp._p.append(parse_xml(
    f'<w:fldSimple {nsdecls("w")} w:instr=" PAGE "><w:r>'
    f'<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
    f'<w:sz w:val="20"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple>'))

doc.save(OUT)
print('wrote', OUT)
print('paragraphs', len(doc.paragraphs), 'tables', len(doc.tables), 'images placed', PLACED)
