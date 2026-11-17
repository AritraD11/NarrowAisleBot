// Renders every svg/*.svg to png/*.png (light theme, white background) and runs the layout check.
//   node docs/flowcharts/render_png.js [scale] [mono]   scale defaults to 3; 'mono' renders the black-and-white set
// Needs Playwright with a Chromium. Set CHROMIUM=/path/to/chrome if the default is not found.
// Fonts: if ./fonts/ holds the IBM Plex woff files (see README) they are used, otherwise the
// SVG's own fallback stack (Segoe UI, Arial) is used.
const fs = require('fs');
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const here = __dirname;
const scale = Number(process.argv[2] || 3);
const sub = process.argv[3] || '';            // e.g. 'mono'
const svgDir = path.join(here, sub, 'svg');
const pngDir = path.join(here, sub, 'png');
fs.mkdirSync(pngDir, { recursive: true });

function fontCss() {
  const dir = path.join(here, 'fonts');
  const map = [['IBM Plex Mono', 500, 'mono500.woff'], ['IBM Plex Mono', 600, 'mono600.woff'],
               ['IBM Plex Sans', 400, 'sans400.woff'], ['IBM Plex Sans', 500, 'sans500.woff'],
               ['IBM Plex Sans', 600, 'sans600.woff']];
  let css = '';
  for (const [fam, w, file] of map) {
    const p = path.join(dir, file);
    if (fs.existsSync(p)) {
      css += `@font-face{font-family:'${fam}';font-weight:${w};src:url(data:font/woff;base64,${fs.readFileSync(p).toString('base64')}) format('woff');}`;
    }
  }
  return css;
}

(async () => {
  const exe = process.env.CHROMIUM;
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  const css = fontCss();
  let problems = 0;
  for (const file of fs.readdirSync(svgDir).filter(f => f.endsWith('.svg')).sort()) {
    const svg = fs.readFileSync(path.join(svgDir, file), 'utf8');
    const m = svg.match(/viewBox="0 0 (\d+) (\d+)"/);
    const W = +m[1], H = +m[2];
    const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: scale });
    const page = await ctx.newPage();
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${css}html,body{margin:0;background:#fff}svg{display:block}${sub === 'mono' ? 'svg{filter:grayscale(1)}' : ''}</style></head><body>${svg}</body></html>`);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(150);

    // ---- layout check, measured by the browser on the real fonts -------------------
    const issues = await page.evaluate(() => {
      const out = [];
      const svg = document.querySelector('svg');
      const vb = svg.viewBox.baseVal;
      const rects = [...svg.querySelectorAll('g.node')].map(g => {
        const r = g.querySelector('rect');
        return { g, x: +r.getAttribute('x'), y: +r.getAttribute('y'), w: +r.getAttribute('width'), h: +r.getAttribute('height'),
                 name: g.querySelector('.nt').textContent };
      });
      // 1. node text inside its own box
      for (const n of rects) {
        for (const t of n.g.querySelectorAll('text')) {
          if (!t.textContent.trim()) continue;
          const b = t.getBBox();
          if (b.x < n.x + 2 || b.x + b.width > n.x + n.w - 2 || b.y + b.height > n.y + n.h + 1)
            out.push(`text overflows node "${n.name}": "${t.textContent}" (needs ${Math.round(b.width)} px, box inner ${n.w - 4})`);
        }
      }
      // 1b. band titles inside their band
      for (const t of svg.querySelectorAll('text.bandlbl')) {
        const band = t.previousElementSibling; if (!band || !band.classList.contains('band')) continue;
        const bx = +band.getAttribute('x'), bw = +band.getAttribute('width');
        const b = t.getBBox();
        if (b.x + b.width > bx + bw - 6) out.push(`band title runs past its band: "${t.textContent}" (needs ${Math.round(b.width)} px of ${bw})`);
      }
      // 2. everything inside the canvas
      for (const t of svg.querySelectorAll('text')) {
        const b = t.getBBox();
        if (b.x < 0 || b.y < 0 || b.x + b.width > vb.width || b.y + b.height > vb.height)
          out.push(`text leaves the canvas: "${t.textContent}"`);
      }
      // 3. edge labels must not sit on a node, nor on each other
      const labels = [...svg.querySelectorAll('text.lb')].map(t => ({ t, b: t.getBBox(), s: t.textContent }));
      const hit = (a, b) => a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
      for (const L of labels) {
        for (const n of rects) {
          if (hit(L.b, { x: n.x, y: n.y, width: n.w, height: n.h })) out.push(`label "${L.s}" overlaps node "${n.name}"`);
        }
      }
      for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++)
        if (hit(labels[i].b, labels[j].b)) out.push(`labels overlap: "${labels[i].s}" and "${labels[j].s}"`);
      // 4. smallest rendered text, in px of the viewBox
      let min = 99;
      for (const t of svg.querySelectorAll('text')) { const fs = parseFloat(getComputedStyle(t).fontSize); if (fs < min) min = fs; }
      out.push(`INFO smallest text ${min} px`);
      return out;
    });
    const real = issues.filter(i => !i.startsWith('INFO'));
    const info = issues.find(i => i.startsWith('INFO'));
    const pt = (px) => (px * 13.333 * 72 / W).toFixed(1);
    const minpx = parseFloat(info.replace(/[^0-9.]/g, ''));
    console.log(`${file}  ${W}x${H}  ${info.slice(5)}  = ${pt(minpx)} pt on a 13.33 in slide  ${real.length ? real.length + ' ISSUES' : 'ok'}`);
    for (const r of real) console.log('   - ' + r);
    problems += real.length;
    await page.screenshot({ path: path.join(pngDir, file.replace('.svg', '.png')), clip: { x: 0, y: 0, width: W, height: H } });
    await ctx.close();
  }
  await browser.close();
  console.log(problems ? `\n${problems} layout issues` : '\nlayout check: clean');
  process.exit(problems ? 1 : 0);
})();
