#!/usr/bin/env python3
"""dashboard_goal_roundtrip.py — does a tap on the map become the goal you meant?

Answers, exactly rather than by eye, a question raised on 28 Aug: the goal
appeared to land somewhere other than where the cursor was. Measuring that
off a screen recording gave pixel-per-metre estimates disagreeing by 3x, so
this drives the real page in headless Chromium instead: it stubs the
WebSocket, synthesises a click at a known canvas offset, and compares the
world coordinate the dashboard actually SENDS against the analytic inverse
of its own camera.

    python3 tools/tests/dashboard_goal_roundtrip.py        # from the repo root

Needs playwright + the Chromium at /opt/pw-browsers. Run it after ANY change
to w2s/s2w/unrotatePtr/sizeCanvas or the pointer handlers.

Result 28 Aug 2026: exact to 1e-6 at device pixel ratios 1, 2 and 3. The
click -> world transform is NOT the source of any observed goal offset; a
goal is stored in the MAP frame, and the map frame moves (§17.42).

EXTENDED 1 Sep 2026 (§17.49), because passing this test was not enough.
Position was exact all along while every dragged HEADING went out 90 deg
wrong -- the drag handler wrote a bare atan2 (measured from +X) into the
same field robotPose.yaw initialises (measured from +Y), and
drawGoalMarker() drew the arrow from +X while drawRobot() drew the nose
from +Y, so the picture agreed with the wrong number. A test that measures
only position cannot see any of that. Phase 2 below covers heading,
renderer agreement, the stale-cssW click offset, and the two failure paths
where the UI used to claim success it had not achieved.

Run after ANY change to the pointer handlers, w2s/s2w/unrotatePtr/
sizeCanvas, vecToYaw/yawToVec, send(), or the E-STOP path."""
import re, json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

src = Path('src/mecanum_robot/mecanum_robot/phone_dashboard.py').read_text(encoding='utf-8')
html = re.search(r'DASHBOARD_HTML\s*=\s*("""|\'\'\')(.*?)\1', src, re.S).group(2)

# Stub the WebSocket so the page runs headless, and CAPTURE what it sends.
stub = """
<script>
window.__sent = [];
class WebSocket {
  static get OPEN(){ return 1; }
  constructor(u){ this.url=u; this.readyState=1;
                  setTimeout(()=>this.onopen&&this.onopen(),0); }
  send(s){ if (this.readyState !== 1) throw new Error('not open');
           try { window.__sent.push(JSON.parse(s)); } catch(e){ window.__sent.push(s); } }
  close(){ this.readyState = 3; }
}
window.WebSocket = WebSocket;
</script>
"""
html = html.replace('<script>', stub + '<script>', 1)
page_file = Path('/tmp/dash_test.html'); page_file.write_text(html, encoding='utf-8')

results, fail = [], 0
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
                           args=['--no-sandbox'])
    for label, vw, vh, dsf in [('desktop',1900,950,1.0), ('phone',390,844,3.0), ('hidpi',1440,900,2.0)]:
        pg = b.new_page(viewport={'width':vw,'height':vh}, device_scale_factor=dsf)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(page_file.as_uri())
        pg.wait_for_timeout(400)
        pg.evaluate("setMapView(true)")           # open the map view
        pg.wait_for_timeout(300)
        # give it a map + pose so the canvas has a camera
        pg.evaluate("""() => {
            robotPose = {x:0, y:0, yaw:0};
            camX = 0; camY = 0; camScale = 100;   // 100 px per metre
            sizeCanvas(); drawMap();
        }""")
        pg.wait_for_timeout(200)
        box = pg.evaluate("() => { const r = mapCanvas.getBoundingClientRect();"
                          "  return {l:r.left, t:r.top, w:r.width, h:r.height, cssW, cssH, dpr, rot: DISPLAY_ROT}; }")
        # arm the goal, click at a known offset from the canvas centre
        pg.evaluate("goalArmed = true")
        for fx, fy in [(0.0,0.0), (-0.30,0.28), (-0.15,0.34)]:
            offx = fx * box['w']; offy = fy * box['h']
            cx = box['l'] + box['w']/2 + offx
            cy = box['t'] + box['h']/2 + offy
            pg.mouse.move(cx, cy); pg.mouse.down(); pg.mouse.up()
            pg.wait_for_timeout(60)
            sent = pg.evaluate("() => window.__sent.filter(m => m && m.type === 'goal').slice(-1)[0]")
            # analytic expectation from the same camera
            exp_x =  offx / 100.0
            exp_y = -offy / 100.0
            got_x, got_y = (sent['x'], sent['y']) if sent else (None, None)
            ok = sent is not None and abs(got_x-exp_x) < 1e-6 and abs(got_y-exp_y) < 1e-6
            if not ok: fail += 1
            results.append((label, offx, offy, exp_x, exp_y, got_x, got_y, ok))
            pg.evaluate("goalArmed = true")
        results.append((label+' :: cssW/rect', box['cssW'], box['w'], box['cssH'], box['h'],
                        box['dpr'], box['rot'], abs(box['cssW']-box['w'])<0.5 and abs(box['cssH']-box['h'])<0.5))
        if errs: print(f'  JS ERRORS on {label}: {errs}'); fail += 1
        pg.close()
    b.close()

print(f"{'view':<10}{'click dx':>9}{'dy':>6}{'expect x':>10}{'y':>8}{'sent x':>10}{'y':>8}   ok")
for r in results:
    if 'cssW' in str(r[0]):
        print(f"  {r[0]}: cssW={r[1]:.1f} rect.w={r[2]:.1f}  cssH={r[3]:.1f} rect.h={r[4]:.1f}  dpr={r[5]}  DISPLAY_ROT={r[6]}  {'OK' if r[7] else 'MISMATCH'}")
        continue
    l,ox,oy,ex,ey,gx,gy,ok = r
    gxs = f'{gx:.4f}' if gx is not None else '  none'
    gys = f'{gy:.4f}' if gy is not None else '  none'
    print(f"{l:<10}{ox:>9.0f}{oy:>6.0f}{ex:>10.4f}{ey:>8.4f}{gxs:>10}{gys:>8}   {'ok' if ok else 'FAIL'}")
print('\n' + ('PHASE 1 PASS — click maps to world exactly'
               if not fail else f'PHASE 1: {fail} FAILURE(S)'))

# ── PHASE 2 — heading, renderer agreement, and the failure paths ─────────
# Everything below was uncovered on 1 Sep and is the reason a 90 deg heading
# error survived a test suite that reported "exact to 1e-6".
print('\nPHASE 2 — heading, renderers, failure paths')
p2 = 0
def chk(cond, msg):
    global p2
    print(('  PASS  ' if cond else '  FAIL  ') + msg)
    if not cond: p2 += 1

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
                           args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1400, 'height': 900})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(page_file.as_uri()); pg.wait_for_timeout(400)
    pg.evaluate("setMapView(true)"); pg.wait_for_timeout(300)
    pg.evaluate("""() => { robotPose={x:0,y:0,yaw:0}; camX=0; camY=0; camScale=100;
                           sizeCanvas(); drawMap(); }""")
    pg.wait_for_timeout(150)
    box = pg.evaluate("() => { const r=mapCanvas.getBoundingClientRect();"
                      " return {l:r.left,t:r.top,w:r.width,h:r.height}; }")
    ccx = box['l'] + box['w']/2
    ccy = box['t'] + box['h']/2

    # --- 2a. drag direction -> commanded yaw, in the ROBOT's convention ---
    # Screen-up is map +Y is the nose, so dragging up must command yaw 0.
    for dx_px, dy_px, want, name in [(0, -120, 0.0,   'drag UP    -> nose forward, yaw 0'),
                                     (120, 0,  -90.0, 'drag RIGHT -> yaw -90'),
                                     (-120, 0,  90.0, 'drag LEFT  -> yaw +90')]:
        pg.evaluate("() => { window.__sent.length = 0; goalArmed = true; }")
        pg.mouse.move(ccx, ccy); pg.mouse.down()
        pg.mouse.move(ccx + dx_px, ccy + dy_px, steps=4); pg.mouse.up()
        pg.wait_for_timeout(60)
        g = pg.evaluate("() => window.__sent.filter(m=>m&&m.type==='goal').slice(-1)[0]")
        got = (g['yaw'] * 180 / 3.141592653589793) if g else None
        chk(g is not None and abs(((got - want + 540) % 360) - 180) < 1e-6,
            f'{name}  (sent {got:.1f} deg)' if g else f'{name}  (NOTHING SENT)')

    # --- 2b. the two renderers must agree, by construction ---
    same = pg.evaluate("""() => {
        for (const d of [-170,-90,-45,0,45,90,170]) {
            const y = d*Math.PI/180, v = yawToVec(y);
            // drawRobot's nose vector, recomputed from the same helper
            if (Math.abs(v.x - (-Math.sin(y))) > 1e-12) return false;
            if (Math.abs(v.y - ( Math.cos(y))) > 1e-12) return false;
            // exact inverse
            const back = vecToYaw(v.x, v.y);
            if (Math.abs(((back-y+3*Math.PI)%(2*Math.PI))-Math.PI) > 1e-12) return false;
        }
        return true; }""")
    chk(same, 'yawToVec/vecToYaw exact inverses, and match drawRobot nose geometry')

    # --- 2c. stale cssW must not move the commanded point ---
    # Reproduces the reported "marker lands right of the pointer": corrupt the
    # cache the way a missed resize would, then click and require exactness.
    pg.evaluate("() => { window.__sent.length = 0; cssW = cssW * 0.75; goalArmed = true; }")
    offx = 200
    pg.mouse.move(ccx + offx, ccy); pg.mouse.down(); pg.mouse.up()
    pg.wait_for_timeout(60)
    g = pg.evaluate("() => window.__sent.filter(m=>m&&m.type==='goal').slice(-1)[0]")
    chk(g is not None and abs(g['x'] - offx/100.0) < 1e-6,
        f'stale cssW self-repairs: sent x={g["x"]:.4f}, want {offx/100.0:.4f}' if g
        else 'stale cssW self-repairs (NOTHING SENT)')

    # --- 2d. a command that cannot be delivered must not report success ---
    # activeGoal must be cleared first: 2c legitimately set it, and the check
    # below is "a FAILED send adds no marker", not "no marker exists".
    pg.evaluate("() => { window.__sent.length = 0; ws.readyState = 3;"
                "        activeGoal = null; goalArmed = true; }")
    pg.mouse.move(ccx + 50, ccy + 50); pg.mouse.down(); pg.mouse.up()
    pg.wait_for_timeout(60)
    st = pg.evaluate("""() => ({ sent: window.__sent.length,
                                 hint: document.getElementById('mapHint').textContent,
                                 active: activeGoal, armed: goalArmed })""")
    chk(st['sent'] == 0,            'socket down: nothing reaches the wire')
    chk('NOT CONNECTED' in st['hint'], f'socket down: operator is told ("{st["hint"]}")')
    chk(st['active'] is None,       'socket down: no goal marker added as if commanded')
    chk(st['armed'] is True,        'socket down: stays ARMED so a retry is one tap')

    # --- 2e. a latched E-STOP must survive a reconnect ---
    # This used to send arm/ENABLE unconditionally on every onopen, so a
    # Wi-Fi blip re-armed an E-STOPped robot with nobody touching anything.
    pg.evaluate("() => { window.__sent.length = 0; ws.readyState = 1; estopped = true; ws.onopen(); }")
    pg.wait_for_timeout(60)
    msgs = pg.evaluate("() => window.__sent.slice()")
    chk(not any(m.get('type') == 'arm' and m.get('cmd') == 'ENABLE' for m in msgs),
        'reconnect while E-STOPped does NOT re-arm')
    chk(any(m.get('type') == 'estop' for m in msgs),
        're-asserts the stop on reconnect (robot may have restarted)')
    pg.evaluate("() => { window.__sent.length = 0; estopped = false; ws.onopen(); }")
    pg.wait_for_timeout(60)
    msgs = pg.evaluate("() => window.__sent.slice()")
    chk(any(m.get('type') == 'arm' and m.get('cmd') == 'ENABLE' for m in msgs),
        'normal reconnect still auto-enables the arm')

    if errs:
        print(f'  JS ERRORS: {errs}'); p2 += 1
    pg.close(); b.close()

total = fail + p2
print('\n' + ('ALL PASS — position, heading, renderers and failure paths'
               if not total else f'{total} FAILURE(S)'))
sys.exit(1 if total else 0)
