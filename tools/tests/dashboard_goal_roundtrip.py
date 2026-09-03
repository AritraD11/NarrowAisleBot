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

    # --- 2f. the DRIFT block, fed the real numbers that fooled us ---------
    # run_20260901_184810 finished with map (-0.0094, 0.0123) -- looks like a
    # perfect return to the mark -- while odom said (0.1041, 0.0161) and the
    # tape said 9 cm right. The card must make that visible.
    pg.evaluate("""() => {
        robotPose = { x:-0.0094, y:0.0123, yaw:-0.0026,
                      ox:0.1041, oy:0.0161, cx:-0.1142, cy:0.0011 };
        updateHud(); updateLivePoseCard();
    }""")
    hud = pg.evaluate("() => document.getElementById('mapHud').innerText")
    chk('0.114' in hud,        f'DRIFT shows the 11.4 cm the map hid')
    chk('0.104' in hud,        'ODOM row shows the independent witness')
    chk('-0.009' in hud,       'MAP row still shows the estimate verbatim')
    bad = pg.evaluate("() => !!document.querySelector('#mapHud .drift-bad')")
    chk(bad,                   'drift over 5 cm is flagged red, not printed quietly')
    dv = pg.evaluate("() => document.getElementById('liveDrift').innerText")
    chk('0.114' in dv,         f'DRIVE-view card agrees ("{dv}")')

    # a healthy pose must NOT cry wolf
    pg.evaluate("""() => {
        robotPose = { x:0.01, y:0.02, yaw:0, ox:0.012, oy:0.021, cx:-0.002, cy:0.001 };
        updateHud(); updateLivePoseCard();
    }""")
    ok_ = pg.evaluate("() => !!document.querySelector('#mapHud .drift-ok')")
    chk(ok_,                   'a 2 mm drift stays green')

    # and with no odom transform at all the block must hide, not render NaN
    pg.evaluate("() => { robotPose = { x:0, y:0, yaw:0 }; updateHud(); updateLivePoseCard(); }")
    hud2 = pg.evaluate("() => document.getElementById('mapHud').innerText")
    chk('NaN' not in hud2 and 'DRIFT' not in hud2,
        'no odom transform -> block hides instead of printing NaN')

    if errs:
        print(f'  JS ERRORS: {errs}'); p2 += 1
    pg.close(); b.close()

# ── PHASE 3 — the trail is a claim about where the robot WENT ────────────
# Added 2 Sep 2026. Two circle runs that morning drew a spiky starburst on a
# robot whose wheels held a 0.507 m circle to 5.2 mm RMS. Nothing was wrong
# with the pose: map_x is odom rotated and shifted by map->odom, and
# slam_toolbox rewrote that correction 17 times per run. The renderer joined
# the samples either side of each rewrite, drawing up to 0.198 m of straight
# line for a robot that had moved 0.005 m -- a frame change painted as
# motion, and the same class of fault as the 90 deg goal arrow above.
#
# PATH was worse: it accumulated MAP deltas, so it read 5.92 m for 3.23 m
# driven, an 83% overstatement with nothing on screen to flag it.
#
# Every check below is verified by reverting its own fix in-page and
# watching it fail, per the 1 Sep discipline.
print('\nPHASE 3 — trail breaks and PATH')
p3 = 0
def chk3(cond, msg):
    global p3
    print(('  PASS  ' if cond else '  FAIL  ') + msg)
    if not cond: p3 += 1

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
                           args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 1400, 'height': 900})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(page_file.as_uri()); pg.wait_for_timeout(400)
    pg.evaluate("setMapView(true)"); pg.wait_for_timeout(300)
    pg.evaluate("""() => { camX=0; camY=0; camScale=100; sizeCanvas(); }""")

    # A circle in ODOM with four map->odom rewrites injected, and map
    # computed from it exactly as the robot does: map = R(cyaw)*odom + ct.
    r = pg.evaluate("""() => {
        clearAllTrails();
        const N = 200, R = 0.5, STEP = 2*Math.PI/N;
        let corr = {x:0, y:0, yaw:0}, odomPath = 0, mapPath = 0;
        let pO = null, pM = null;
        for (let i = 0; i < N; i++) {
          const a = i*STEP, ox = R - R*Math.cos(a), oy = R*Math.sin(a);
          if (i > 0 && i % 40 === 0)
            corr = {x: corr.x - 0.18, y: corr.y + 0.12, yaw: corr.yaw - 0.09};
          const c = Math.cos(corr.yaw), s = Math.sin(corr.yaw);
          const mx = c*ox - s*oy + corr.x, my = s*ox + c*oy + corr.y;
          if (pO) odomPath += Math.hypot(ox-pO[0], oy-pO[1]);
          if (pM) mapPath  += Math.hypot(mx-pM[0], my-pM[1]);
          pO = [ox,oy]; pM = [mx,my];
          applyPose({type:'pose', x:mx, y:my, yaw:0, ox:ox, oy:oy,
                     cx:corr.x, cy:corr.y, cyaw:corr.yaw});
        }
        return {odomPath, mapPath, jumpCount, pathLength,
                brks: trajectory.filter(p => p.brk).length,
                pts: trajectory.length};
    }""")

    chk3(r['jumpCount'] == 4,  f"four rewrites counted four times (jumpCount={r['jumpCount']})")
    chk3(r['brks'] == 4,       f"four trail points carry brk (got {r['brks']})")

    # The pen must lift at each break: one moveTo to start, one per break.
    mv = pg.evaluate("""() => {
        const real = mctx.moveTo.bind(mctx); let n = 0;
        mctx.moveTo = function(){ n++; return real.apply(mctx, arguments); };
        drawTrajectory();
        mctx.moveTo = real; return n;
    }""")
    chk3(mv == 5, f'pen lifts at every break: {mv} moveTo for 1 start + 4 breaks')

    # REVERT THE FIX: clear the flags and the same trail draws unbroken.
    mv0 = pg.evaluate("""() => {
        const saved = trajectory.map(p => p.brk);
        trajectory.forEach(p => p.brk = false);
        const real = mctx.moveTo.bind(mctx); let n = 0;
        mctx.moveTo = function(){ n++; return real.apply(mctx, arguments); };
        drawTrajectory();
        mctx.moveTo = real;
        trajectory.forEach((p,i) => p.brk = saved[i]);
        return n;
    }""")
    chk3(mv0 == 1, f'and without brk it draws one unbroken line ({mv0} moveTo) — the guard has teeth')

    # PATH is the wheels, not the estimate.
    chk3(abs(r['pathLength'] - r['odomPath']) < 1e-9,
         f"PATH = odom path ({r['pathLength']:.4f} m, want {r['odomPath']:.4f} m)")
    chk3(abs(r['mapPath'] - r['odomPath']) > 0.2,
         f"the old map-delta sum would have read {r['mapPath']:.4f} m "
         f"({100*(r['mapPath']/r['odomPath']-1):+.0f}%) — what this replaces")
    card = pg.evaluate("() => document.getElementById('liveDist').innerText")
    chk3(card.startswith(f"{r['odomPath']:.2f}"), f'PATH card shows it ("{card}")')

    # No odom transform at all: say so, do not print a confident 0.00.
    dash = pg.evaluate("""() => {
        clearAllTrails();
        applyPose({type:'pose', x:0.4, y:0.2, yaw:0});
        applyPose({type:'pose', x:0.6, y:0.3, yaw:0});
        return document.getElementById('liveDist').innerText;
    }""")
    chk3('\u2014' in dash or '—' in dash, f'no odom -> PATH reads em dash, not 0.00 ("{dash}")')

    # Real corrections, lifted from run_20260902_114339 (t+142.0 -> t+145.7).
    real_jump = pg.evaluate("""() => {
        clearAllTrails();
        applyPose({type:'pose', x:0, y:0, yaw:0, ox:0, oy:0,
                   cx:-0.1212, cy:-0.1332, cyaw:-0.0494});
        const before = jumpCount;
        applyPose({type:'pose', x:0, y:0, yaw:0, ox:0.01, oy:0,
                   cx:-0.3104, cy:-0.1862, cyaw:-0.1267});
        return jumpCount - before;
    }""")
    chk3(real_jump == 1, 'a real recorded correction is detected as one jump')

    # Heading-only rewrite: translation-only detection would sail past this.
    yaw_only = pg.evaluate("""() => {
        clearAllTrails();
        applyPose({type:'pose', x:0, y:0, yaw:0, ox:0, oy:0, cx:0.5, cy:0.5, cyaw:0.00});
        const before = jumpCount;
        applyPose({type:'pose', x:0, y:0, yaw:0, ox:0, oy:0, cx:0.5, cy:0.5, cyaw:0.05});
        return jumpCount - before;
    }""")
    chk3(yaw_only == 1, 'a rewrite that turns the frame without shifting it still breaks the trail')

    # And the other way: float jitter must not invent rewrites.
    noise = pg.evaluate("""() => {
        clearAllTrails();
        let n = 0;
        for (let i = 0; i < 50; i++) {
          applyPose({type:'pose', x:i*0.01, y:0, yaw:0, ox:i*0.01, oy:0,
                     cx:0.2 + (i%2 ? 1e-9 : 0), cy:-0.1, cyaw:0.3 + (i%3 ? 1e-9 : 0)});
        }
        return jumpCount;
    }""")
    chk3(noise == 0, f'sub-micron float jitter invents no rewrites (jumpCount={noise})')

    # A rewrite while parked moves the frame < 5 mm: the break must survive
    # the distance gate that would otherwise drop the sample entirely.
    parked = pg.evaluate("""() => {
        clearAllTrails();
        applyPose({type:'pose', x:0, y:0, yaw:0, ox:0, oy:0, cx:0, cy:0, cyaw:0});
        const before = trajectory.filter(p => p.brk).length;
        applyPose({type:'pose', x:0.002, y:0, yaw:0, ox:0, oy:0, cx:0.002, cy:0, cyaw:0});
        return trajectory.filter(p => p.brk).length - before;
    }""")
    chk3(parked == 1, 'a 2 mm rewrite on a parked robot is still recorded, not swallowed by the 5 mm gate')

    hud = pg.evaluate("""() => { updateHud(); return document.getElementById('mapHud').innerText; }""")
    chk3('JUMPS' in hud, 'HUD surfaces the rewrite count')

    if errs:
        print(f'  JS ERRORS: {errs}'); p3 += 1
    pg.close(); b.close()

total = fail + p2 + p3
print('\n' + ('ALL PASS — position, heading, renderers, failure paths, trail truth'
               if not total else f'{total} FAILURE(S)'))
sys.exit(1 if total else 0)
