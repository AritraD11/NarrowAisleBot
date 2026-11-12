// print_pdf.js <html> <pdf> - render the manual with Chromium (Playwright).
"use strict";
const { chromium } = require("playwright");
const path = require("path");
(async () => {
  const [html, pdf] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + path.resolve(html), { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({
    path: pdf, format: "A4", printBackground: true, outline: true, tagged: false,
    displayHeaderFooter: true,
    headerTemplate: "<div></div>",
    footerTemplate: "<div style='width:100%;font:8px Inter,sans-serif;color:#7a8294;padding:0 15mm;display:flex;justify-content:space-between'>" +
      "<span>Mobile Robot Setup Manual · v1.0</span><span><span class='pageNumber'></span> / <span class='totalPages'></span></span></div>",
    margin: { top: "16mm", bottom: "18mm", left: "15mm", right: "15mm" },
  });
  await browser.close();
})();
