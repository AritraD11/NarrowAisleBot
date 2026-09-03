import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dg import *

fig, ax = canvas(10.6, 5.8, 100, 57)
tel, red, grn = C['telemetry'], C['defect'], C['fixed']

# main chain
xs = [2, 20.5, 39, 57.5, 76]
labels = [
 ('ydlidar driver', '/scan\nbest-effort QoS'),
 ('scan_relay', '/scan_reliable\nmirror + yaw remap'),
 ('slam_toolbox', 'scan match →\npose graph'),
 ('/map + map→odom', '1.0 Hz occupancy\ngrid'),
 ('map_saver_cli\n+ run_report.py', 'PGM/YAML + JSON\nquality report'),
]
bx = []
for x, (t, sub) in zip(xs, labels):
    b = box(ax, x, 35.0, 17.0, 11.5, f'{t}\n\n{sub}', fs=7.2, fc='#e6eef6', ec=tel, tc=tel)
    bx.append(b)
for i in range(4):
    arr(ax, R(bx[i]), L(bx[i+1]), tel, lw=1.5)

# odometry input
b_odo = box(ax, 39, 24.5, 17.0, 7.5, 'odometry_publisher\nTF odom→base_link\n(motion prior)',
            fs=7.2, fc='#e6eef6', ec=tel, tc=tel)
arr(ax, T(b_odo), B(bx[2]), tel, lw=1.5)

# gates
gates = [
 (20.5, 'GATE 1 — QoS incompatibility',
  'A best-effort publisher and a reliable subscriber never\n'
  'form a DDS connection. topic echo and topic hz both\n'
  'work, because the CLI negotiates QoS on the fly; the\n'
  'SLAM node does not. Symptom: "Waiting for laser_scans"\n'
  'forever, on a topic that is demonstrably publishing.'),
 (39, 'GATE 2 — the missing TF frame',
  'odometry_publisher only sent a transform inside its\n'
  'telemetry callback, and the bridge parameter that\n'
  'enables telemetry defaulted off. odom therefore never\n'
  'existed in TF at all. Symptom: slam_toolbox reaches\n'
  'Activating and then prints nothing further.'),
 (57.5, 'GATE 3 — duplicate and hidden publishers',
  'An undocumented systemd unit was already running the\n'
  'driver and the relay. Every manual bringup stacked a\n'
  'second instance, doubling the relay rate to 22.6 Hz and\n'
  'reproducing the exact checksum-error signature the\n'
  'documentation attributes to a cable fault.'),
]
boxx = [1.0, 34.0, 67.0]
for (px, head, body), gx in zip(gates, boxx):
    p = px + 8.5
    cx = gx + 16.0
    ax.plot([p, p], [35.0, 26.0], color=red, lw=1.0, ls=':', zorder=2)
    ax.plot([p, cx], [26.0, 26.0], color=red, lw=1.0, ls=':', zorder=2)
    ax.plot([cx, cx], [26.0, 21.4], color=red, lw=1.0, ls=':', zorder=2)
    ax.plot(cx, 21.0, marker='v', ms=7, color=red, zorder=5)
    box(ax, gx, 2.0, 32.0, 18.0, '', fc='#fdecea', ec=red, lw=1.0)
    ax.text(cx, 18.4, head, ha='center', va='top', fontsize=7.8,
            fontweight='bold', color=red)
    ax.text(cx, 15.2, body, ha='center', va='top', fontsize=6.8, linespacing=1.6)

ax.text(1.0, 54.6,
        'Three faults, each of which produced a healthy-looking system and no error message. '
        'All three were found by\ncross-checking one subsystem against another, never by '
        'reading a log line that said what was wrong.',
        fontsize=8.0, color=C['neutral'], va='top', linespacing=1.6)
ax.set_title('The mapping pipeline and the three silent gates that blocked it, 6–7 August 2026',
             loc='left', fontsize=9.5, y=1.0)
plt.tight_layout(); plt.savefig(f'{FIGDIR}/fig11_mapping_pipeline.png')
print('ok')
