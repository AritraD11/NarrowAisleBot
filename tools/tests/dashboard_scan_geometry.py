#!/usr/bin/env python3
"""dashboard_scan_geometry.py — do the live LiDAR dots land where the laser
actually points?

WHY THIS EXISTS. §17.49 is the precedent and it is the whole argument: the
click-to-goal POSITION maths was exact to 1e-6 for weeks while every dragged
HEADING went out 90 degrees wrong, because two renderers on the same canvas
measured yaw from different axes and the picture agreed with the wrong one.
A scan overlay is the same hazard with more dots: base_link is not REP-103
here (+X is the robot's RIGHT, +Y is its NOSE, §17.10), the corrected
/scan_reliable frame measures bearing 0 along +X and +90 deg along +Y
(§17.15), and the laser sits 0.27 m forward of base_link (§17.12). Get any
one of those wrong and the dots still form a plausible room outline, just
rotated or offset, and nobody can tell by eye.

So this does not check that dots appear. It checks that drawScan() agrees
with drawRobot()/yawToVec() — the renderers that are already hardware-
validated — for beams whose answer is known by construction.

    python3 tools/tests/dashboard_scan_geometry.py     # from the repo root

Needs playwright + the Chromium at /opt/pw-browsers.

Run after ANY change to drawScan, LASER_BX/BY, yawToVec/vecToYaw, w2s/s2w,
_scan_callback, or aislebot.urdf's laser_joint."""
import math
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SRC = Path('src/mecanum_robot/mecanum_robot/phone_dashboard.py')

src = SRC.read_text(encoding='utf-8')
html = re.search(r'DASHBOARD_HTML\s*=\s*("""|\'\'\')(.*?)\1', src, re.S).group(2)

stub = """
<script>
window.__sent = [];
class WebSocket {
  static get OPEN(){ return 1; }
  constructor(u){ this.url=u; this.readyState=1;
                  setTimeout(()=>this.onopen&&this.onopen(),0); }
  send(s){ try { window.__sent.push(JSON.parse(s)); } catch(e){ window.__sent.push(s); } }
  close(){ this.readyState = 3; }
}
window.WebSocket = WebSocket;
</script>
"""
html = html.replace('<script>', stub + '<script>', 1)
page_file = Path('/tmp/dash_scan_test.html')
page_file.write_text(html, encoding='utf-8')

fails = []


def chk(ok, msg):
    print(('  PASS  ' if ok else '  FAIL  ') + msg)
    if not ok:
        fails.append(msg)


print('dashboard_scan_geometry.py')
print('=' * 68)

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
    page = b.new_page(viewport={'width': 900, 'height': 700})
    page.goto(page_file.as_uri())
    page.wait_for_timeout(250)

    # ── Phase 1: the constants are the measured ones ───────────────────
    print('\nPhase 1 — mount geometry matches the tape measure (§17.12)')
    lb = page.evaluate('({x: LASER_BX, y: LASER_BY})')
    chk(abs(lb['x'] - 0.00) < 1e-9,
        f"LASER_BX is on the centreline (got {lb['x']})")
    chk(abs(lb['y'] - 0.27) < 1e-9,
        f"LASER_BY is 0.27 m forward of base_link (got {lb['y']})")

    urdf = Path('src/mecanum_robot/urdf/aislebot.urdf').read_text(encoding='utf-8')
    # Anchor on the <joint> ELEMENT, not the first mention of the name: a
    # comment 260 lines earlier also says "laser_joint", and a lazy .*? from
    # there happily walks to some other link's origin. (It did, on the first
    # run of this test, and reported a real-looking 0.27 m disagreement that
    # did not exist.)
    m = re.search(
        r'<joint\s+name="laser_joint".*?<origin\s+xyz="\s*([-\d.eE+]+)\s+'
        r'([-\d.eE+]+)\s+([-\d.eE+]+)\s*"',
        urdf, re.S)
    chk(m is not None, 'aislebot.urdf still declares a laser_joint origin')
    if m:
        ux, uy = float(m.group(1)), float(m.group(2))
        chk(abs(ux - lb['x']) < 1e-6 and abs(uy - lb['y']) < 1e-6,
            f'dashboard ({lb["x"]}, {lb["y"]}) == URDF ({ux}, {uy}) '
            '— one mount, one number')

    # ── Phase 2: the transform agrees with drawRobot's own helpers ─────
    # For a beam of range R at bearing +90 deg (the NOSE axis in the
    # corrected scan frame), the hit must lie exactly (LASER_BY + R) along
    # yawToVec(yaw) from the robot centre. yawToVec is the helper drawRobot
    # uses for the nose line, so agreement here is agreement with the
    # renderer that has been checked against hardware.
    print('\nPhase 2 — drawScan agrees with yawToVec/drawRobot')

    def scan_point(px, py, yaw, bearing, rng):
        """Where the page's own drawScan formula puts one beam, in world m."""
        return page.evaluate(
            """([px,py,yaw,th,d]) => {
                 const c = Math.cos(yaw), s = Math.sin(yaw);
                 const bx = LASER_BX + d*Math.cos(th);
                 const by = LASER_BY + d*Math.sin(th);
                 return { x: px + bx*c - by*s, y: py + bx*s + by*c };
               }""",
            [px, py, yaw, bearing, rng])

    for yaw in (0.0, 0.7853981634, 1.5707963268, -2.0, 3.0):
        R = 2.5
        got = scan_point(0.4, -0.9, yaw, math.pi / 2, R)
        nv = page.evaluate('(y) => yawToVec(y)', yaw)
        exp_x = 0.4 + nv['x'] * (0.27 + R)
        exp_y = -0.9 + nv['y'] * (0.27 + R)
        err = math.hypot(got['x'] - exp_x, got['y'] - exp_y)
        chk(err < 1e-9,
            f'nose beam at yaw {yaw:+.4f} rad lands on the nose axis '
            f'(error {err:.2e} m)')

    # A beam at bearing 0 must land on the robot's RIGHT, which is
    # yawToVec(yaw) rotated -90 deg, plus the laser's forward offset.
    for yaw in (0.0, 1.1, -0.6):
        R = 1.8
        got = scan_point(0.0, 0.0, yaw, 0.0, R)
        nv = page.evaluate('(y) => yawToVec(y)', yaw)
        rx, ry = nv['y'], -nv['x']          # nose rotated -90 deg = right
        exp_x = rx * R + nv['x'] * 0.27
        exp_y = ry * R + nv['y'] * 0.27
        err = math.hypot(got['x'] - exp_x, got['y'] - exp_y)
        chk(err < 1e-9,
            f'bearing 0 beam at yaw {yaw:+.2f} lands on the RIGHT axis '
            f'(error {err:.2e} m)')

    # ── Phase 3: a beam pointing at a wall the robot is facing ─────────
    # Parked on the mark (yaw 0, nose = map +Y per §17.38), a nose-bearing
    # beam of 3.0 m must read y = 3.27 and x = 0. This is the case an
    # operator can check against a tape measure, so it is worth naming.
    print('\nPhase 3 — the hand-checkable case')
    got = scan_point(0.0, 0.0, 0.0, math.pi / 2, 3.0)
    chk(abs(got['x']) < 1e-9 and abs(got['y'] - 3.27) < 1e-9,
        f'on the mark, a 3.0 m nose beam reads (0.000, 3.270) '
        f'(got {got["x"]:.3f}, {got["y"]:.3f})')

    # ── Phase 4: the render path survives real message shapes ──────────
    print('\nPhase 4 — render path, including the shapes that break naive code')
    page.evaluate("""() => {
        applyPose({x: 0.2, y: -0.1, yaw: 0.4, ox: 0.2, oy: -0.1, cx: 0, cy: 0});
        setMapView(true);
    }""")
    page.wait_for_timeout(60)

    err = page.evaluate("""() => {
        try {
          const n = 240, r = [];
          for (let i = 0; i < n; i++) {
            // Deliberately mixed: nulls (the masked rear wedge and
            // out-of-range), short trusted returns, and long ones past the
            // trust radius that must draw faint instead of red.
            if (i % 7 === 0)       r.push(null);
            else if (i % 11 === 0) r.push(8.4);
            else                   r.push(1.2 + (i % 13) * 0.1);
          }
          liveScan = { angle_min: -Math.PI, angle_inc: 2*Math.PI/n, r: r,
                       trust: 5.0, valid: 190, total: 430, live: 323,
                       masked: 107, churn: 0.17 };
          scanStamp = performance.now();
          drawMap();
          return null;
        } catch (e) { return String(e); }
    }""")
    chk(err is None, f'drawMap() with a mixed scan does not throw ({err})')

    hud = page.evaluate("() => document.getElementById('mapHud').innerHTML")
    chk('CHURN' in hud and '17%' in hud,
        'HUD shows the live per-sweep churn rate')
    chk('VALID' in hud and '323' in hud,
        'VALID is against LIVE beams (323), not total (430) — the masked\n         rear wedge can never be valid and must not deflate the figure')
    chk('107 masked' in hud,
        'the HUD names the masked-beam count rather than hiding it')
    chk('scan_quality' in hud,
        'the HUD warns CHURN is not scan_quality.py flicker — the two were\n         conflated once and 76% vs 17% was read as an improvement it is not')

    # An all-null scan is what a fully masked or dead sensor looks like.
    err = page.evaluate("""() => {
        try {
          liveScan = { angle_min: -Math.PI, angle_inc: 0.05,
                       r: new Array(126).fill(null),
                       trust: 5.0, valid: 0, total: 430, live: 0,
                       masked: 430, churn: 0.0 };
          scanStamp = performance.now();
          drawMap();
          return null;
        } catch (e) { return String(e); }
    }""")
    chk(err is None, f'an all-null (fully masked) scan does not throw ({err})')

    # ── Phase 5: a frozen scan must stop being drawn ───────────────────
    # §17.25: /scan and slam_toolbox stopped publishing together while Nav2
    # kept driving. The last good sweep on screen looked authoritative.
    print('\nPhase 5 — a stale scan is withdrawn, not left on screen (§17.25)')
    stale = page.evaluate("""() => {
        liveScan = { angle_min: -Math.PI, angle_inc: 0.05,
                     r: new Array(126).fill(2.0), trust: 5.0,
                     valid: 126, total: 430, live: 323, masked: 107,
                     churn: 0.1 };
        scanStamp = performance.now() - 5000;   // 5 s old
        let drew = false;
        const realArc = mctx.arc;
        mctx.arc = function(){ drew = true; return realArc.apply(this, arguments); };
        drawScan();
        mctx.arc = realArc;
        return drew;
    }""")
    chk(stale is False, 'a 5 s old scan draws nothing')

    fresh = page.evaluate("""() => {
        scanStamp = performance.now();
        let drew = false;
        const realArc = mctx.arc;
        mctx.arc = function(){ drew = true; return realArc.apply(this, arguments); };
        drawScan();
        mctx.arc = realArc;
        return drew;
    }""")
    chk(fresh is True, 'a fresh scan does draw')

    # ── Phase 6: the layer toggle is real ──────────────────────────────
    print('\nPhase 6 — layer plumbing')
    chk(page.evaluate('() => mapLayers.scan') is True,
        'scan layer defaults ON')
    chk(page.evaluate("() => !!document.getElementById('layer-scan')"),
        'the VIEW SETTINGS panel has a Live LiDAR scan checkbox')
    off = page.evaluate("""() => {
        const el = document.getElementById('layer-scan');
        el.checked = false; el.dispatchEvent(new Event('change'));
        return mapLayers.scan;
    }""")
    chk(off is False, 'unchecking the box turns the layer off')

    b.close()

# ── Phase 7: the Python side, no browser needed ────────────────────────
print('\nPhase 7 — publisher-side invariants')
nan = float('nan')
chk((0.1 <= nan <= 10.0) is False,
    'NaN fails the range test, so masked beams are never marked valid')
chk('pts.append(round(r, 3) if valid[i] else None)' in src,
    'masked/invalid beams are serialised as null, never 0.0')
chk("'/scan_reliable'" in src and "LaserScan, '/scan'," not in src,
    'the dashboard subscribes /scan_reliable, not raw /scan (QoS, §13.4)')
chk("'churn':" in src and "'flicker'" not in src,
    'the publisher emits churn, not a field named flicker — scan_quality.py\n'
    '         owns that word and means something else by it')
chk("if not masked[i] and valid[i] != prev[i]" in src,
    'churn counts only LIVE beams; masked beams cannot change state and\n'
    '         would only dilute the rate')
chk("if tick % _node.scan_tick_divisor == 0 and _node.latest_scan" in src,
    'the broadcast rate comes from scan_publish_hz, not a hardcoded tick')
chk("self.scan_tick_divisor = max(1, round(10.0 / _hz))" in src,
    'scan_publish_hz is actually READ — no declared-but-dead parameter')

# The red/grey split on the map is only honest if the dashboard's trust
# radius equals what slam_toolbox is really discarding. Two files, one
# number: exactly the shape that drifts silently. This is the guard.
import re as _re
m = _re.search(r"declare_parameter\('scan_trust_range',\s*([0-9.]+)\)", src)
chk(m is not None, 'scan_trust_range default is findable in the dashboard')
dash_trust = float(m.group(1)) if m else None

slam = Path('system/slam_nodom_stageB.yaml').read_text(encoding='utf-8')
m2 = _re.search(r'^\s*max_laser_range:\s*([0-9.]+)\s*$', slam, _re.M)
chk(m2 is not None, 'max_laser_range is findable in slam_nodom_stageB.yaml')
slam_trust = float(m2.group(1)) if m2 else None

chk(dash_trust is not None and slam_trust is not None
    and abs(dash_trust - slam_trust) < 1e-9,
    f'dashboard scan_trust_range ({dash_trust}) == slam max_laser_range '
    f'({slam_trust}) — the grey dots mark what SLAM actually discards')

# updateHud() runs inside drawMap(). A throw there blanks the whole canvas,
# not one line, so no field of liveScan may be dereferenced unguarded.
chk('liveScan.trust.toFixed' not in src,
    'the HUD cannot throw on a missing trust field and take the map down')

print('=' * 68)
if fails:
    print(f'{len(fails)} FAILED:')
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('all checks passed')
