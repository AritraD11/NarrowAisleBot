#!/usr/bin/env python3
"""dashboard_wide_render.py -- does the map canvas stay clean on a WIDE screen?

WHY THIS EXISTS. 6 Oct 2026, the first browser look at the standard-frame
dashboard (DISPLAY_ROT = -PI/2) on a desktop showed solid dark stripes down
both sides of the map and a light box only in the middle. Two causes, both
invisible at phone size and in every earlier test (they measured clicks, not
pixels):

  - The background and the grid lines were drawn in the pre-rotation canvas
    rectangle. Rotated 90 degrees on a wide canvas, that rectangle covers
    only a central square of the screen.
  - Outside it the canvas was never painted at all, so it stayed transparent
    and the dark page behind it showed through as stripes.

So this renders the real page (the string Python actually serves, via
ast.literal_eval, per CLAUDE.md) at several viewport shapes, redraws the map
many times the way a live session does, and measures pixels:

  1. a side strip that the old code left unpainted must be fully painted and
     light, however many times the map is redrawn;
  2. grid lines must reach that strip at all (the grid covers the screen,
     not just the central square);
  3. the same at a tall phone shape and a square one.

    python3 tools/tests/dashboard_wide_render.py     # from the repo root

Needs playwright + the Chromium at /opt/pw-browsers."""
import ast
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SRC = Path('src/mecanum_robot/mecanum_robot/phone_dashboard.py')

tree = ast.parse(SRC.read_text(encoding='utf-8'))
html = None
for node in tree.body:
    if (isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'DASHBOARD_HTML'):
        html = ast.literal_eval(node.value)
if html is None:
    sys.exit('DASHBOARD_HTML not found')

stub = """<script>
class WebSocket{static get OPEN(){return 1}constructor(u){this.readyState=1;
setTimeout(()=>this.onopen&&this.onopen(),0)}send(){}close(){}}
window.WebSocket=WebSocket;
</script>"""
html = html.replace('<script>', stub + '<script>', 1)
page_file = Path('/tmp/dash_wide_render.html')
page_file.write_text(html, encoding='utf-8')

fails = []


def chk(ok, msg):
    print(('  PASS  ' if ok else '  FAIL  ') + msg)
    if not ok:
        fails.append(msg)


# Luminance helper runs in the page: reads the canvas back at device pixels.
MEASURE = """([x0, y0, x1, y1]) => {
  const c = document.getElementById('mapCanvas');
  const ctx = c.getContext('2d');
  const k = c.width / c.getBoundingClientRect().width;      // device px per css px
  const X0 = Math.round(x0 * k), Y0 = Math.round(y0 * k);
  const W = Math.max(1, Math.round((x1 - x0) * k)), H = Math.max(1, Math.round((y1 - y0) * k));
  const d = ctx.getImageData(X0, Y0, W, H).data;
  let minL = 255, nonBg = 0, n = 0, clear = 0;
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] < 250) { clear++; continue; }              // never painted
    const L = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
    n++; if (L < minL) minL = L;
    if (Math.abs(d[i] - 244) + Math.abs(d[i + 1] - 246) + Math.abs(d[i + 2] - 248) > 6) nonBg++;
  }
  return { minL: minL, nonBg: nonBg, n: n, clear: clear };
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
    for label, vw, vh in (('wide desktop', 1920, 950), ('laptop', 1400, 700),
                          ('phone portrait', 390, 844), ('square', 800, 800)):
        print(f'\n{label}  {vw}x{vh}')
        pg = b.new_page(viewport={'width': vw, 'height': vh})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(page_file.as_uri())
        pg.wait_for_timeout(300)
        pg.evaluate('setMapView(true)')
        pg.wait_for_timeout(250)
        pg.evaluate("""() => { robotPose = {x: 0, y: 0, yaw: 0}; camX = 0.5; camY = 0;
                               camScale = 100; sizeCanvas();
                               for (let i = 0; i < 40; i++) drawMap(); }""")
        pg.wait_for_timeout(150)
        box = pg.evaluate("""() => { const r = mapCanvas.getBoundingClientRect();
                                     return {w: r.width, h: r.height}; }""")
        # A strip near the left edge, clear of the pose box and the tool column,
        # taken from the part of the screen the old rotation never covered.
        W, H = box['w'], box['h']
        if W > H * 1.3:                       # wide: left margin outside the central square
            strip = [max(240, 0.02 * W), 0.30 * H, max(240, 0.02 * W) + 0.12 * W, 0.90 * H]
            where = 'left margin'
        else:                                 # tall or square: top/bottom margin
            # below the robot box, left of the X-axis labels on the right edge
            strip = [0.05 * W, 0.70 * H, 0.75 * W, 0.85 * H]
            where = 'lower band'
        m = pg.evaluate(MEASURE, strip)
        chk(m['clear'] == 0,
            f'{where} is fully painted, no transparent pixels ({m["clear"]} found)')
        chk(m['minL'] > 150,
            f'{where} stays light after 40 redraws (darkest pixel luminance {m["minL"]:.0f}, want > 150)')
        chk(m['nonBg'] > 0,
            f'{where} is not blank: gridlines reach it ({m["nonBg"]} non-background pixels)')
        chk(not errs, f'no page errors ({errs})')
        if vw == 1920:
            pg.screenshot(path='/tmp/dash_wide_render.png')
        pg.close()
    b.close()

print()
if fails:
    print(f'{len(fails)} FAILED:')
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('all checks passed')
