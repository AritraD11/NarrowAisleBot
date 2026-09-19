"""How the fatigue strand would be validated, objective by objective.

Drawn from the research proposal for that strand. The point of the figure is
the right-hand column: every modality is checked against a physical reference
before it is fused, and the fused score has to beat four single-modality
baselines before it counts as anything.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg2 import *

fig, ax = canvas(13.4, 7.4, 100, 58)

title(ax, 0.5, 57.6,
      'The three objectives, and what each one is measured against',
      'None of this is built. The figure is here because the strand is already specific enough to be tested, and\n'
      'because the reference measurements in the right-hand column are what would decide whether it works.')

# ── objective 1 ──────────────────────────────────────────────────────
band(ax, 0.5, 8.0, 31.0, 38.5, '', 'tel')
head(ax, 0.5, 40.5, 31.0, 6.0, 'OBJECTIVE 1', 'tel',
     sub='one contactless sensing node\nat a fixed capture point')

M, X = 27.5, 2.2
m1 = box(ax, X, 34.6, M, 4.6,
         'edge-AI camera, 1080p at 30 frames/s\n2D pose, stride, sway, cadence', 'tel',
         fs=7.5, hdr='Computer vision')
m2 = box(ax, X, 29.2, M, 4.6,
         'solid-state, >100k points/s\n3D gait, and no dependence on lighting', 'tel',
         fs=7.5, hdr='Lidar')
m3 = box(ax, X, 23.8, M, 4.6,
         '60 GHz FMCW, through clothing\nheart and respiration rate', 'tel',
         fs=7.5, hdr='Millimetre-wave radar')
m4 = box(ax, X, 18.4, M, 4.6,
         'long-wave infrared, 8 to 14 µm\nfacial skin temperature, heat strain', 'tel',
         fs=7.5, hdr='Thermal imaging')
box(ax, X, 12.6, M, 5.0,
    'all four on one bracket, ceiling or pillar,\n2.5 to 3.5 m up and angled down, working\nat 1 to 5 m',
    'grey', fs=7.5, hdr='Mounting and range')
caveat(ax, 16.0, 11.4,
       'Ambient above 40 °C throttles the edge processor. That is a\n'
       'design constraint on this node, not a detail.', fs=7.4, ha='center')

# ── objective 2 ──────────────────────────────────────────────────────
band(ax, 34.5, 8.0, 29.0, 38.5, '', 'note')
head(ax, 34.5, 40.5, 29.0, 6.0, 'OBJECTIVE 2', 'note',
     sub='one score per crossing,\nfused rather than read together')

f1 = box(ax, 36.0, 33.8, 26.0, 5.4,
         'one monitoring pass is one traversal of\nthe zone; features are cut from that window',
         'note', fc='note', fs=7.5, hdr='Feature extraction, per pass')
f2 = box(ax, 36.0, 26.6, 26.0, 6.0,
         'every feature referred to that worker’s own\nbaseline, recorded at the start of the shift,\n'
         'so between-person variation drops out', 'note', fc='note', fs=7.5,
         hdr='Within-subject normalisation')
f3 = box(ax, 36.0, 19.4, 26.0, 6.0,
         'a convolutional branch per stream, then a\nrecurrent stage over the sequence, with\n'
         'attention across the modalities', 'note', fc='note', fs=7.5,
         hdr='CNN-LSTM fusion')
f4 = box(ax, 36.0, 13.6, 26.0, 4.6,
         'a single number per crossing, on device;\nno raw video leaves the node', 'new',
         fc='new', fs=7.5, hdr='Fatigue Risk Score, 0 to 100')
ax.text(49.0, 11.4,
        'Processing on the node rather than in a server is what makes\n'
        'the privacy position defensible rather than promised.',
        ha='center', va='top', fontsize=7.4, color=P['note'], zorder=6,
        linespacing=1.45)

# ── objective 3 ──────────────────────────────────────────────────────
band(ax, 66.5, 8.0, 32.5, 38.5, '', 'new')
head(ax, 66.5, 40.5, 32.5, 6.0, 'OBJECTIVE 3', 'new',
     sub='validated against references,\nnot against itself')

box(ax, 68.0, 33.8, 29.5, 5.4,
    'gait from camera and lidar against\nmarker-based motion capture', 'new', fc='new',
    fs=7.5, hdr='Laboratory, per modality')
box(ax, 68.0, 26.6, 29.5, 6.0,
    'a subset of volunteers wearing surface EMG on\nthe calf muscles and inertial bands, recorded\n'
    'at the same time as the contactless capture', 'new', fc='new', fs=7.5,
    hdr='Against the contact method it replaces')
box(ax, 68.0, 19.4, 29.5, 6.0,
    'an operational, non-air-conditioned warehouse,\n30 to 50 workers across several shifts, scored\n'
    'against psychomotor vigilance and sleepiness', 'new', fc='new', fs=7.5,
    hdr='Field deployment')
box(ax, 68.0, 13.6, 29.5, 4.6,
    'camera alone, lidar alone, radar alone, thermal\nalone, and an ablation over the four',
    'bad', fc='bad', fs=7.5, hdr='The four baselines it has to beat', tc=P['bad'])
ax.text(82.75, 11.4,
        'A fused score that cannot beat the best single modality has\n'
        'bought nothing for four sensors and an edge processor.',
        ha='center', va='top', fontsize=7.4, color=P['bad'], zorder=6,
        linespacing=1.45)

for a, b in ((32.0, 35.5), (64.0, 67.5)):
    arr(ax, (a, 27.0), (b, 27.0), 'grey', lw=1.6)

summ(ax, 0.5, 0.8, 98.5, 5.4,
     'The order matters more than the schedule. The node comes first, because until one exists there is no data of any kind. '
     'Per-modality validation comes\nsecond and is the step most likely to end the strand, which is a reason to reach it early. '
     'Fusion and the baseline comparison come last, because they\nare the only steps that need every preceding one to have worked.',
     'grey', fs=8.0)

save(fig, 'fig36_fatigue_design.png')
