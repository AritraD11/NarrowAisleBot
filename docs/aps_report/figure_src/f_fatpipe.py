"""The proposed fatigue-assessment pipeline, sensor to score.

Replaces the second generative-tool image supplied with the research proposal.
The shape of this figure is the signal chain rather than the work plan, which
is what separates it from Figure 22: this is what a single crossing of the
monitored zone would produce, stage by stage, and where each stage would run.
Nothing to the right of the capture column has been built, and the figure says
so on its face rather than in the caption alone.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *

fig, ax = canvas(13.4, 7.4, 100, 62)

title(ax, 0.5, 61.4,
      'The proposed pipeline: four contactless streams, one score per crossing',
      'Read left to right. Nothing here has been built. The dashed rule separates what the proposal fixes, which is the\n'
      'sensor set and its mounting, from what it only designs. All four streams are reduced on the node itself, which is\n'
      'what makes the privacy claim a property of the architecture rather than an undertaking.')

ROW = [33.8, 27.2, 20.6, 14.0]
BH = 5.0

# ── capture ──────────────────────────────────────────────────────────
band(ax, 0.5, 12.3, 30.0, 34.0, '', 'tel')
head(ax, 0.5, 39.8, 30.0, 5.6, 'CAPTURE', 'tel',
     sub='one bracket, 2.5 to 3.5 m up,\nworking range 1 to 5 m')
SENS = [
    ('Camera', '1080p at 30 frames/s'),
    ('Lidar', 'solid state, >100k points/s'),
    ('Radar', '60 GHz FMCW, through clothing'),
    ('Thermal', 'long-wave infrared, 8 to 14 µm'),
]
cap = [box(ax, 2.0, y, 27.0, BH, s, 'tel', fs=7.4, hdr=h)
       for y, (h, s) in zip(ROW, SENS)]

# ── observables ──────────────────────────────────────────────────────
band(ax, 34.0, 12.3, 30.5, 34.0, '', 'cmd')
head(ax, 34.0, 39.8, 30.5, 5.6, 'OBSERVABLE, PER PASS', 'cmd',
     sub='one traversal of the zone is one\nwindow; features are cut from it')
OBS = [
    ('Gait regularity', 'stride time, cadence, lateral sway'),
    ('Gait geometry', 'three-dimensional, lighting-independent'),
    ('Cardiorespiratory', 'heart rate and respiration rate'),
    ('Thermal strain', 'facial skin temperature, against baseline'),
]
obs = [box(ax, 35.5, y, 27.5, BH, s, 'cmd', fc='cmd', fs=7.4, hdr=h)
       for y, (h, s) in zip(ROW, OBS)]

for a, b in zip(cap, obs):
    arr(ax, R(a), L(b), 'grey', lw=1.2)

# ── fusion and output ────────────────────────────────────────────────
band(ax, 68.0, 12.3, 31.5, 34.0, '', 'note')
head(ax, 68.0, 39.8, 31.5, 5.6, 'FUSION, ON THE NODE', 'note',
     sub='no raw video or point cloud\nleaves the bracket')

n1 = box(ax, 69.5, ROW[0], 28.5, BH,
         'every feature referred to that worker’s own\nbaseline, taken at the start of the shift',
         'note', fc='note', fs=7.4, hdr='Within-subject normalisation')
n2 = box(ax, 69.5, ROW[1], 28.5, BH,
         'one convolutional branch per stream, then a\nrecurrent stage across the sequence',
         'note', fc='note', fs=7.4, hdr='CNN-LSTM backbone')
n3 = box(ax, 69.5, ROW[2], 28.5, BH,
         'weights the four streams per pass, so an\noccluded or saturated one can be discounted',
         'note', fc='note', fs=7.4, hdr='Cross-modal attention')
n4 = box(ax, 69.5, ROW[3], 28.5, BH,
         'one number per crossing, computed and kept\non the node',
         'new', fc='new', fs=7.4, hdr='Fatigue Risk Score, 0 to 100')

for a, b in ((n1, n2), (n2, n3), (n3, n4)):
    arr(ax, (83.75, a[1]), (83.75, b[1] + BH), 'grey', lw=1.2)
route(ax, [(63.5, 23.1), (66.2, 23.1), (66.2, 36.3), (69.1, 36.3)],
      'grey', lw=1.6)

# ── the boundary of what exists ──────────────────────────────────────
ax.plot([32.25, 32.25], [10.6, 47.6], color=P['bad'], lw=1.5,
        ls=(0, (6, 4)), zorder=8)
ax.text(32.25, 48.3, 'specified  |  designed', ha='center', va='bottom',
        fontsize=8.2, color=P['bad'], fontweight='bold', zorder=9)

caveat(ax, 50.0, 9.8,
       'The edge processor is the constraint that decides whether any of this runs at all: it has to hold a four-stream\n'
       'inference budget in an unconditioned shed above 40 °C, which is a thermal-design problem before it is a modelling one.',
       fs=7.6, ha='center')

summ(ax, 0.5, 0.8, 99.0, 5.2,
     'Two design decisions carry most of the risk. Referring every feature to the worker’s own start-of-shift baseline is what allows a single threshold to mean\n'
     'the same thing for different people, and it costs a calibration pass at the start of every shift. Fusing on the node rather than at a server is what keeps the\n'
     'raw streams from leaving the bracket, and it is the reason the inference budget is fixed rather than elastic.',
     'grey', fs=8.0)

save(fig, 'fig44_fatigue_pipeline.png')
