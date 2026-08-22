import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import numpy as np
import matplotlib.patches as mp
import matplotlib.dates as mdates
from datetime import date

fig, ax = plt.subplots(figsize=(10.6, 5.4))

NAB, IOT, MILE = C['telemetry'], C['accent'], C['command']
tasks = [
  # (label, start, end, colour, track, hatch)
  ('Literature, coursework, problem formulation', '2025-08-01', '2026-01-15', C['grey'], 'A', ''),
  ('Open-loop v3 platform on Arduino Mega',       '2026-01-05', '2026-03-20', NAB, 'A', ''),
  ('Strafing-stutter diagnosis, motor characterisation', '2026-03-01', '2026-03-31', NAB, 'A', ''),
  ('Migration to ESP32, PCNT encoder subsystem',  '2026-03-15', '2026-05-05', NAB, 'A', ''),
  ('PID + feedforward design, air validation',    '2026-04-10', '2026-05-16', NAB, 'A', ''),
  ('Encoder / level-shifter fault campaign',      '2026-05-05', '2026-08-04', C['defect'], 'A', '///'),
  ('UV-C lighting subsystem on the arm (Mega v8)','2026-06-05', '2026-06-23', NAB, 'A', ''),
  ('LiDAR integration and first SLAM bringup',    '2026-06-20', '2026-07-08', NAB, 'A', ''),
  ('Repository consolidation, docs, self-hosted AP','2026-07-01','2026-07-20', NAB, 'A', ''),
  ('Encoder replacement, bench calibration harness','2026-07-18','2026-08-04', NAB, 'A', ''),
  ('Firmware v3.0: per-motor CPR, retuned PID',   '2026-08-03', '2026-08-05', NAB, 'A', ''),
  ('Bringup reliability, Map button, auto reports','2026-08-05','2026-08-08', NAB, 'A', ''),
  ('SLAM and Nav2 literature, theory documents',  '2026-08-07', '2026-08-11', NAB, 'A', ''),
  ('LiDAR placement trial, Foxglove, Nav2 audit', '2026-08-08', '2026-08-11', NAB, 'A', ''),
  ('Frame-convention faults found and fixed',     '2026-08-11', '2026-08-12', NAB, 'A', ''),
  ('UVGI instrumentation and control (TIH-IoT)',  '2026-02-01', '2026-07-31', IOT, 'B', 'xxx'),
]

y = 0
labels, ypos = [], []
for lab, s, e, col, trk, hat in tasks:
    d0 = mdates.date2num(date.fromisoformat(s))
    d1 = mdates.date2num(date.fromisoformat(e))
    ax.barh(y, d1-d0, left=d0, height=0.62, color=col, alpha=0.85,
            edgecolor='k', linewidth=0.5, hatch=hat, zorder=3)
    labels.append(lab); ypos.append(y); y += 1

ax.set_yticks(ypos); ax.set_yticklabels(labels, fontsize=7.8)
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
ax.set_xlim(mdates.date2num(date(2025,7,20)), mdates.date2num(date(2026,9,5)))
ax.tick_params(axis='x', labelsize=7.5)
ax.grid(axis='x', alpha=0.3); ax.grid(axis='y', alpha=0.12)

# milestones
miles = [('2026-05-14', 'PID validated\nin air'),
         ('2026-06-26', 'first live\nLiDAR scan'),
         ('2026-08-04', 'encoder fault\nroot-caused'),
         ('2026-08-06', 'first ground-truth\noccupancy map'),
         ('2026-08-11', 'map tracking\nconfirmed on hardware')]
LEVEL = [0, 0, 1, 2, 0]
for i, (d, txt) in enumerate(miles):
    dn = mdates.date2num(date.fromisoformat(d))
    ax.axvline(dn, color=MILE, lw=1.0, ls='--', alpha=0.8, zorder=2)
    ax.plot(dn, 15.85, marker='D', ms=5, color=MILE, zorder=6, clip_on=False)
    ax.annotate(txt, xy=(dn, 15.85), xytext=(dn, 17.15 + LEVEL[i]*1.55),
                ha='center', va='top', fontsize=6.6, color=MILE, clip_on=False,
                arrowprops=dict(arrowstyle='-', color=MILE, lw=0.6))

ax.axvline(mdates.date2num(date(2026,8,22)), color=C['defect'], lw=1.4)
ax.text(mdates.date2num(date(2026,8,23)), -0.7, 'this report', rotation=90,
        fontsize=7.2, color=C['defect'], va='top', ha='left')

# track separators
ax.axhline(14.55, color=C['neutral'], lw=0.9)
ax.text(mdates.date2num(date(2026,2,20)), 13.9,
        'Second project, run in parallel', fontsize=7.4, color=IOT,
        fontweight='bold', va='center')

ax.set_ylim(21.4, -1.2)
h = [mp.Patch(fc=NAB, ec='k', lw=0.5, label='NarrowAisleBot (primary)'),
     mp.Patch(fc=C['defect'], ec='k', lw=0.5, hatch='///', label='instrumentation fault campaign'),
     mp.Patch(fc=IOT, ec='k', lw=0.5, hatch='xxx', label='UVGI instrumentation (parallel)'),
     mp.Patch(fc=C['grey'], ec='k', lw=0.5, label='coursework and reading')]
ax.legend(handles=h, loc='upper left', bbox_to_anchor=(0.012, 0.685), ncol=1, fontsize=7.4,
          framealpha=0.95, frameon=True, edgecolor=C['grey'])
ax.set_title('Year-one activity, both projects on one timeline. Primary-project spans are '
             'reconstructed from the\nversion-control record; the parallel-project span is '
             'approximate and to be confirmed against the author\'s own log.',
             loc='left', fontsize=9.3, pad=10)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig18_gantt.png')
print('ok')
