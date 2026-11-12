// Dashboard in a real browser:  node tests/test_dashboard_browser.js [screenshot_dir]
//
// Starts the dashboard server in --mock mode (no ROS), opens it in headless
// Chromium at phone size and checks, through the page itself:
//   no JavaScript errors in the console, ever (the 15 Sep 2026 lesson)
//   WebSocket connects; hello config is applied
//   joystick drag moves the robot; release stops it
//   MAP start builds a map image; NAV start; a tapped goal is sent and driven to
//   E-STOP latches (joystick ignored), CLEAR releases it
//   RE-ZERO is refused while mapping
//   REC writes rows; the MCU console round-trips
//   MAP stop saves a .pgm/.yaml pair
// Needs: python3 with fastapi + uvicorn, and Node's playwright.
"use strict";
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const KIT = path.resolve(__dirname, "..");
const SHOTS = process.argv[2] || null;
const PORT = 18000 + Math.floor(Math.random() * 1000);
const LOGDIR = fs.mkdtempSync(path.join(os.tmpdir(), "dash-"));
let fails = 0;
function check(ok, msg) { console.log((ok ? "  ok   " : "  FAIL ") + msg); if (!ok) fails++; }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const srv = spawn("python3", ["-m", "robot_base.dashboard.server", "--mock", "--port", String(PORT),
                                "--name", "testbot", "--log-dir", LOGDIR],
                    { cwd: path.join(KIT, "ros2", "robot_base"), stdio: ["ignore", "pipe", "pipe"] });
  let srvOut = "";
  srv.stdout.on("data", (d) => { srvOut += d; });
  srv.stderr.on("data", (d) => { srvOut += d; });
  for (let i = 0; i < 50; i++) {
    try { const r = await fetch("http://127.0.0.1:" + PORT + "/health"); if (r.ok) break; } catch (e) { /* not up yet */ }
    await sleep(200);
  }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
                                       hasTouch: false });
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("dialog", (d) => d.accept());
  try {
    await page.goto("http://127.0.0.1:" + PORT + "/");
    await page.waitForFunction(() => document.getElementById("conn").classList.contains("on"), null, { timeout: 5000 });
    check(true, "WebSocket connected (green dot)");
    check((await page.textContent("#name")) === "testbot", "hello config applied: robot name shown");
    check(await page.isVisible("#mock"), "MOCK chip visible in mock mode");
    check(!(await page.isVisible("#turn-wrap")), "turn slider hidden on a non-holonomic base");
    check((await page.$$("#wheel-rows tr")).length === 2, "one wheel row per wheel");

    const poseX = async () => page.evaluate(() => (st.pose ? st.pose[0] : null));
    await page.waitForFunction(() => st.pose !== null);
    const x0 = await poseX();
    const box = await page.locator("#stick").boundingBox();
    const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(cx, cy - 70, { steps: 5 });
    await sleep(1500);
    await page.mouse.up();
    await sleep(600);
    const x1 = await poseX();
    check(x1 - x0 > 0.1, "joystick forward moved the robot +x by " + (x1 - x0).toFixed(3) + " m");
    await sleep(800);
    const x2 = await poseX();
    check(Math.abs(x2 - x1) < 0.01, "release stops it (moved " + (x2 - x1).toFixed(4) + " m after release)");

    await page.click("#map-toggle");
    await page.waitForFunction(() => st.mapping === true, null, { timeout: 3000 });
    check(true, "MAP start: mapping chip on");
    await page.waitForFunction(() => mapInfo !== null, null, { timeout: 5000 });
    check(await page.evaluate(() => mapInfo.width > 0 && mapImg !== null), "map image built from the grid");
    check(await page.evaluate(() => scanPts.length > 50), "scan points arriving");

    await page.click("#rezero");
    await sleep(400);
    check((await page.textContent("#log")).includes("re-zero refused"), "RE-ZERO refused while mapping");

    await page.click("#nav-toggle");
    await page.waitForFunction(() => st.nav === true, null, { timeout: 3000 });
    check(true, "NAV start");
    await page.click("#goal-mode");
    const mb = await page.locator("#map").boundingBox();
    await page.mouse.move(mb.x + mb.width / 2 + 60, mb.y + mb.height / 2 - 20);
    await page.mouse.down();
    await page.mouse.move(mb.x + mb.width / 2 + 60, mb.y + mb.height / 2 - 80, { steps: 4 });
    await page.mouse.up();
    await page.waitForFunction(() => st.goal !== null, null, { timeout: 3000 });
    const goal = await page.evaluate(() => st.goal);
    check(Math.abs(goal[2] - Math.PI / 2) < 0.2, "dragging up on the map sets heading +90 deg (map +y): " +
          (goal[2] * 180 / Math.PI).toFixed(0) + " deg");
    await page.waitForFunction(() => st.nav_status === "SUCCEEDED", null, { timeout: 20000 });
    check(true, "mock robot drove to the goal: SUCCEEDED");
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "dashboard_phone.png"), fullPage: false });

    await page.click("#estop");
    await page.waitForFunction(() => st.estop === true, null, { timeout: 2000 });
    check((await page.textContent("#estop")) === "CLEAR", "E-STOP latched, button reads CLEAR");
    const e0 = await poseX();
    await page.mouse.move(cx, cy); await page.mouse.down();
    await page.mouse.move(cx, cy - 70, { steps: 3 }); await sleep(800); await page.mouse.up();
    check(Math.abs((await poseX()) - e0) < 0.005, "joystick ignored while latched");
    await page.click("#estop");
    await page.waitForFunction(() => st.estop === false, null, { timeout: 2000 });
    check(true, "CLEAR releases it");

    await page.click("#rec-toggle");
    await page.waitForFunction(() => st.rec !== null && st.rec > 5, null, { timeout: 5000 });
    await page.click("#rec-toggle");
    await sleep(400);
    check(/recorded \d+ rows/.test(await page.textContent("#log")), "REC wrote rows");

    await page.fill("#mcu-cmd", "<?>");
    await page.press("#mcu-cmd", "Enter");
    await sleep(500);
    const lg = await page.textContent("#log");
    check(lg.includes("> <?>") && lg.includes("[OK,MOCK]"), "MCU console round trip");

    await page.click("#map-toggle");      // confirm dialog auto-accepted
    await page.waitForFunction(() => st.mapping === false, null, { timeout: 5000 });
    const saved = fs.readdirSync(LOGDIR).filter((f) => f.startsWith("map_"));
    check(saved.some((f) => f.endsWith(".pgm")) && saved.some((f) => f.endsWith(".yaml")),
          "MAP stop saved " + saved.join(", "));

    if (SHOTS) {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.click("#map-toggle");
      await page.waitForFunction(() => mapInfo !== null && st.mapping, null, { timeout: 5000 });
      await sleep(1500);
      await page.screenshot({ path: path.join(SHOTS, "dashboard_desktop.png") });
    }
    check(errors.length === 0, "no JavaScript errors in the console" + (errors.length ? ": " + errors.join(" | ") : ""));
  } catch (e) {
    check(false, "exception: " + e.message);
    console.log(srvOut.slice(-2000));
  } finally {
    await browser.close();
    srv.kill("SIGINT");
  }
  console.log(fails ? "\n" + fails + " FAILED" : "\nall dashboard browser checks passed");
  process.exit(fails ? 1 : 0);
})();
