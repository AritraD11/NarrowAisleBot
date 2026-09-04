import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp
import matplotlib.dates as mdates
from datetime import date

fig, ax = plt.subplots(figsize=(10.8, 5.9))

NAB, IOT, MILE = C['telemetry'], C['accent'], C['command']
tasks = [
  ('Literature, coursework, problem formulation', '2025-08-01', '2026-01-15', C['grey'], ''),
  ('Open-loop platform on Arduino Mega',          '2026-01-05', '2026-03-20', NAB, ''),
  ('Motor characterisation, migration to ESP32',  '2026-03-01', '2026-05-05', NAB, ''),
  ('PID + feedforward design, air validation',    '2026-04-10', '2026-05-16', NAB, ''),
  ('Encoder / level-shifter fault campaign',      '2026-05-05', '2026-08-04', C['defect'], '///'),
  ('UV-C lighting subsystem on the arm',          '2026-06-05', '2026-06-23', NAB, ''),
  ('LiDAR integration, first SLAM bringup',       '2026-06-20', '2026-07-08', NAB, ''),
  ('Repository consolidation, docs, self-hosted AP','2026-07-01','2026-07-20', NAB, ''),
  ('Bench calibration, firmware v3.0',            '2026-07-18', '2026-08-05', NAB, ''),
  ('Mapping reliability, automated run analysis', '2026-08-05', '2026-08-12', NAB, ''),
  ('Frame-convention faults found and fixed',     '2026-08-11', '2026-08-27', C['defect'], '///'),
  ('First Nav2 bringup and autonomous round trip','2026-08-13', '2026-08-19', NAB, ''),
  ('DWB replaced with MPPI, controller retuned',  '2026-08-18', '2026-08-20', NAB, ''),
  ('SLAM front-end investigation (Stages A–G)',   '2026-08-19', '2026-09-03', C['accent'], ''),
  ('Instrument build: 12 analysis tools',         '2026-08-20', '2026-09-03', NAB, ''),
  ('Obstacle-avoidance branch opened',            '2026-09-01', '2026-09-03', NAB, ''),
  ('UVGI instrumentation and control (TIH-IoT)',  '2026-02-01', '2026-07-31', IOT, 'xxx'),
]

y = 0
labels, ypos = [], []
for lab, s, e, col, hat in tasks:
    d0 = mdates.date2num(date.fromisoformat(s))
    d1 = mdates.date2num(date.fromisoformat(e))
    ax.barh(y, d1-d0, left=d0, height=0.62, color=col, alpha=0.85,
            edgecolor='k', linewidth=0.5, hatch=hat, zorder=3)
    labels.append(lab); ypos.append(y); y += 1

ax.set_yticks(ypos); ax.set_yticklabels(labels, fontsize=7.8)
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
ax.set_xlim(mdates.date2num(date(2025,7,20)), mdates.date2num(date(2026,10,20)))
ax.tick_params(axis='x', labelsize=7.5)
ax.grid(axis='x', alpha=0.3); ax.grid(axis='y', alpha=0.12)

# milestones
miles = [('2026-05-14', 'PID validated\nin air'),
         ('2026-06-26', 'first live\nLiDAR scan'),
         ('2026-08-04', 'encoder fault\nroot-caused'),
         ('2026-08-14', 'first autonomous\nround trip'),
         ('2026-08-29', 'angular gate\nclosed (G2)'),
         ('2026-09-03', 'SLAM front end\nroot-caused')]
LEVEL = [0, 1, 0, 2, 3, 1]
for i, (d, txt) in enumerate(miles):
    dn = mdates.date2num(date.fromisoformat(d))
    ax.axvline(dn, color=MILE, lw=1.0, ls='--', alpha=0.8, zorder=2)
    ax.plot(dn, 16.85, marker='D', ms=5, color=MILE, zorder=6, clip_on=False)
    ax.annotate(txt, xy=(dn, 16.85), xytext=(dn, 18.05 + LEVEL[i]*1.42),
                ha='center', va='top', fontsize=6.6, color=MILE, clip_on=False,
                arrowprops=dict(arrowstyle='-', color=MILE, lw=0.6))

ax.axvline(mdates.date2num(date(2026,9,3)), color=C['defect'], lw=1.4)
ax.text(mdates.date2num(date(2026,9,4)), -0.7, 'this report', rotation=90,
        fontsize=7.2, color=C['defect'], va='top', ha='left')

# track separators
ax.axhline(15.55, color=C['neutral'], lw=0.9)
ax.text(mdates.date2num(date(2026,2,20)), 14.85,
        'Second project, run in parallel', fontsize=7.4, color=IOT,
        fontweight='bold', va='center')

ax.set_ylim(24.4, -1.2)
h = [mp.Patch(fc=NAB, ec='k', lw=0.5, label='NarrowAisleBot (primary)'),
     mp.Patch(fc=C['accent'], ec='k', lw=0.5, label='SLAM front-end investigation'),
     mp.Patch(fc=C['defect'], ec='k', lw=0.5, hatch='///', label='fault campaigns'),
     mp.Patch(fc=IOT, ec='k', lw=0.5, hatch='xxx', label='UVGI instrumentation (parallel)'),
     mp.Patch(fc=C['grey'], ec='k', lw=0.5, label='coursework and reading')]
ax.legend(handles=h, loc='upper left', bbox_to_anchor=(0.012, 0.66), ncol=1, fontsize=7.4,
          framealpha=0.95, frameon=True, edgecolor=C['grey'])
ax.set_title('Year-one activity, both projects on one timeline. Primary-project spans are reconstructed '
             'from the version-control\nrecord across 146 commits; the parallel-project span is '
             'approximate and to be confirmed against the author\'s own log.',
             loc='left', fontsize=9.3, pad=10)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig25_gantt.png')
print('ok')
