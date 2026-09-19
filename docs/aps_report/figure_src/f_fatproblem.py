"""Why contact-based fatigue assessment fails on a warehouse floor.

Replaces the graphical abstract supplied with the research proposal. That
image was produced with a generative tool, which is a liability in a document
submitted for examination however it is captioned, and it set its own type and
its own palette besides. This redraws the same argument in the report's own
hand: the operating conditions on the left, the three classes of established
method and the specific reason each one fails on the right, and the
requirement that follows from all three underneath.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *

fig, ax = canvas(13.4, 7.4, 100, 62)

title(ax, 0.5, 61.4,
      'The operating condition, and why the established methods do not survive it',
      'Each entry in the right-hand column is a limitation of the instrument rather than of the physiology. The methods\n'
      'measure fatigue correctly in a laboratory; what they cannot do is keep measuring it through a full shift on a floor.')

ROW = [38.0, 31.4, 24.8, 18.2]
BH = 5.0

# ── left: the conditions ─────────────────────────────────────────────
band(ax, 0.5, 17.2, 38.5, 34.3, '', 'bad')
head(ax, 0.5, 44.8, 38.5, 5.8, 'THE FLOOR', 'bad',
     sub='Indian logistics and warehousing,\nwhere this strand is aimed')

box(ax, 2.2, ROW[0], 35.1, BH,
    '22 million employed, and about 70 per cent of them\nin the unorganised sector',
    'bad', fc='bad', fs=7.5, hdr='Scale of exposure')
box(ax, 2.2, ROW[1], 35.1, BH,
    'ten to twelve hours of sustained walking and lifting,\noften with no scheduled recovery period',
    'bad', fc='bad', fs=7.5, hdr='Shift length')
box(ax, 2.2, ROW[2], 35.1, BH,
    'ambient routinely above 40 °C in unconditioned sheds,\nwith measured exceedances of heat-stress limits',
    'bad', fc='bad', fs=7.5, hdr='Thermal environment')
box(ax, 2.2, ROW[3], 35.1, BH,
    'more than 26,800 recorded workplace incidents a year,\nagainst minimal occupational health monitoring',
    'bad', fc='bad', fs=7.5, hdr='Recorded outcome')

# ── right: the method classes, and where each one stops ──────────────
band(ax, 43.5, 17.2, 56.0, 34.3, '', 'tel')
head(ax, 43.5, 44.8, 56.0, 5.8, 'WHAT IS AVAILABLE TODAY, AND WHERE IT STOPS', 'tel',
     sub='the three classes of method the literature offers, and the failure mode\n'
         'each one shows once it is taken out of the laboratory')

PAIRS = [
    ('Subjective report', 'questionnaires and supervisor\nassessment',
     'retrospective, and answered by\nthe person being assessed'),
    ('Contact physiological', 'surface electromyography, ECG\nand inertial bands',
     'gelled electrodes on skin that is\nwet with perspiration for hours'),
    ('Worn sensors', 'wrist and chest units read\ncontinuously over the shift',
     'heat and sweat degrade contact,\nand wearing it at all is a choice'),
]
for y, (hd, lt, rt) in zip(ROW[:3], PAIRS):
    a = box(ax, 45.2, y, 25.0, BH, lt, 'tel', fs=7.5, hdr=hd)
    b = box(ax, 73.5, y, 24.8, BH, rt, 'bad', fc='bad', fs=7.5,
            hdr='Fails because', tc=P['bad'])
    arr(ax, (70.7, y + BH / 2), (73.0, y + BH / 2), 'grey', lw=1.3)

box(ax, 45.2, ROW[3], 53.1, BH,
    'an instrument that observes the worker at a distance, over a full shift, and asks nothing of them',
    'new', fc='new', fs=7.8, hdr='What the three failures jointly specify')

arr(ax, (38.7, ROW[1] + BH / 2), (43.1, ROW[1] + BH / 2), 'grey', lw=1.7)

summ(ax, 0.5, 9.4, 99.0, 5.2,
     'The three failure modes are not the same failure. Subjective report is unreliable at the source, and no instrument removes that. The contact methods are\n'
     'reliable and cannot be kept in contact for eight hours in that heat, which is an instrumentation problem and therefore a tractable one. It is the second\n'
     'kind of failure, and only the second, that this strand proposes to address.',
     'grey', fs=8.0)

save(fig, 'fig43_fatigue_problem.png')
