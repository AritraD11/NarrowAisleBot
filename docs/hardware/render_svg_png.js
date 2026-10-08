// Renders one SVG to PNG with the IBM Plex fonts from docs/flowcharts/fonts.
//   node docs/hardware/render_svg_png.js docs/hardware/esp32_pin_circuit.svg [scale]
// Set CHROMIUM=/path/to/chrome if Playwright cannot find its own browser.
const fs = require('fs');
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const file = process.argv[2];
const scale = Number(process.argv[3] || 2);
const fonts = path.join(__dirname, '..', 'flowcharts', 'fonts');
const map = [['IBM Plex Mono', 500, 'mono500.woff'], ['IBM Plex Mono', 600, 'mono600.woff'],
             ['IBM Plex Sans', 400, 'sans400.woff'], ['IBM Plex Sans', 500, 'sans500.woff'], ['IBM Plex Sans', 600, 'sans600.woff']];
let css = '';
for (const [fam, w, f] of map) {
  const p = path.join(fonts, f);
  if (fs.existsSync(p)) css += `@font-face{font-family:'${fam}';font-weight:${w};src:url(data:font/woff;base64,${fs.readFileSync(p).toString('base64')}) format('woff');}`;
}
(async () => {
  const svg = fs.readFileSync(file, 'utf8');
  const m = svg.match(/viewBox="0 0 (\d+) (\d+)"/);
  const W = +m[1], H = +m[2];
  const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: scale });
  const page = await ctx.newPage();
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${css}html,body{margin:0;background:#fff}svg{display:block}${/_mono\.svg$/.test(file) ? 'svg{filter:grayscale(1)}' : ''}</style></head><body>${svg}</body></html>`);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(150);
  // overflow check: every in-box label must stay inside the canvas, and text must not collide
  const issues = await page.evaluate(({ W, H }) => {
    const out = [], t = [...document.querySelectorAll('text')].map(e => ({ b: e.getBBox(), s: e.textContent }));
    for (const x of t) if (x.b.x < 0 || x.b.y < 0 || x.b.x + x.b.width > W || x.b.y + x.b.height > H) out.push('off canvas: ' + x.s);
    const hit = (a, b) => a.x < b.x + b.width - 1 && a.x + a.width > b.x + 1 && a.y < b.y + b.height - 1 && a.y + a.height > b.y + 1;
    for (let i = 0; i < t.length; i++) for (let j = i + 1; j < t.length; j++) if (hit(t[i].b, t[j].b)) out.push('text overlap: "' + t[i].s + '" and "' + t[j].s + '"');
    return out;
  }, { W, H });
  const png = file.replace(/\.svg$/, '.png');
  await page.screenshot({ path: png, clip: { x: 0, y: 0, width: W, height: H } });
  await browser.close();
  console.log('wrote', png, `${W * scale}x${H * scale}`);
  if (issues.length) { console.log(issues.map(i => '  - ' + i).join('\n')); process.exit(1); }
  console.log('text check: clean');
})();
