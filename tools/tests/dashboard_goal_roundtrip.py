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

Round-trip test: does a click at a known canvas pixel produce the world
coordinate the dashboard then SENDS?  Exact, not eyeballed."""
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
  constructor(u){ this.url=u; setTimeout(()=>this.onopen&&this.onopen(),0); }
  send(s){ try { window.__sent.push(JSON.parse(s)); } catch(e){ window.__sent.push(s); } }
  close(){}
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
print('\n' + ('ALL PASS — click maps to world exactly' if not fail else f'{fail} FAILURE(S)'))
sys.exit(1 if fail else 0)
