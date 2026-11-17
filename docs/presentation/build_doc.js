// Builds docs/presentation/NarrowAisleBot_ROS2_Notes.docx: plain, black-and-white, editable notes,
// mostly flowcharts. Uses the mono figures from docs/flowcharts/mono/png and docs/hardware.
//
//   NODE_PATH=<dir with docx> node docs/presentation/build_doc.js

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, ImageRun, Table, TableRow, TableCell,
  WidthType, BorderStyle, AlignmentType, PageOrientation, LevelFormat, PageBreak, Footer, PageNumber,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..");
const MONO = (n) => path.join(ROOT, "docs", "flowcharts", "mono", "png", n);
const OUT = path.join(ROOT, "docs", "presentation", "NarrowAisleBot_ROS2_Notes.docx");

// A4 landscape, 0.7 in margins: 16838 - 2 x 1008 = 14822 DXA of text width
const MARGIN = 1008;
const TEXT_W = 16838 - 2 * MARGIN;
const PX_PER_IN = 96;

// ---------------------------------------------------------------- helpers
const p = (text, opts = {}) => new Paragraph({ children: runs(text), spacing: { after: 120 }, ...opts });
const h1 = (text, pageBreak = true) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: pageBreak, children: [new TextRun(text)] });
const h2 = (text, pageBreak = false) => new Paragraph({ heading: HeadingLevel.HEADING_2, pageBreakBefore: pageBreak, children: [new TextRun(text)] });
const bullet = (text) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), spacing: { after: 60 } });
const numbered = (text, ref = "steps") => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(text), spacing: { after: 60 } });

// text with **bold** spans and _{sub} subscripts
function runs(text) {
  if (Array.isArray(text)) return text;
  const out = [];
  const re = /\*\*(.+?)\*\*|_\{(.+?)\}/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun(text.slice(last, m.index)));
    if (m[1] !== undefined) out.push(new TextRun({ text: m[1], bold: true }));
    else out.push(new TextRun({ text: m[2], subScript: true }));
    last = re.lastIndex;
  }
  if (last < text.length) out.push(new TextRun(text.slice(last)));
  return out;
}

function figure(file, pw, ph, widthIn, alt) {
  const w = Math.round(widthIn * PX_PER_IN), h = Math.round(w * ph / pw);
  return new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 },
    children: [new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width: w, height: h },
      altText: { title: alt, description: alt, name: path.basename(file) } })],
  });
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(header, rows, fractions) {
  const cols = fractions.map((f) => Math.round(f * TEXT_W));
  cols[cols.length - 1] = TEXT_W - cols.slice(0, -1).reduce((a, b) => a + b, 0);
  const cell = (text, i, bold) => new TableCell({
    width: { size: cols[i], type: WidthType.DXA }, borders,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: bold ? [new TextRun({ text, bold: true })] : runs(text) })],
  });
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: cols,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true)) })]
      .concat(rows.map((r) => new TableRow({ children: r.map((t, i) => cell(t, i, i === 0 && r.length > 2)) }))),
  });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 60 } });

const SLIDE = [1760, 990];
const FIG_W = 9.6; // inches, leaves room for a heading and a line of text on the same page

// ---------------------------------------------------------------- content
const body = [];

// title block
body.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("NarrowAisleBot: how the ROS 2 software fits together")] }));
body.push(p("Working notes, October 2026. Diagrams are drawn from the code and launch files in the repo. Robot measurements are the latest recorded, up to 1 Oct 2026."));
body.push(p("The robot has three computers. A Raspberry Pi 5 runs ROS 2 Jazzy and makes every decision. An ESP32 runs the wheel-speed loop at 100 Hz. An Arduino Mega runs the arm and the UV tubes. Everything below is about how they talk to each other and what each ROS 2 node is for."));

// 1 big picture
body.push(h1("1. The whole system", false));
body.push(p("Solid box: starts at boot. Dashed box: started on demand, mapping from the phone's MAP button, Nav2 by hand. Grey boxes are hardware."));
body.push(figure(MONO("s1_system_overview_slide.png"), ...SLIDE, 7.6, "System overview"));

// 2 boot
body.push(h1("2. What starts, and when"));
body.push(p("systemd runs start_aislebot.sh, which sets ROS domain 42 with Cyclone DDS on loopback, waits for the ESP32 (gives up after 30 s) and the Mega (warns after 15 s), then launches 11 processes. Start mapping before Nav2, or the global costmap rejects the map until one arrives."));
body.push(figure(MONO("s6_boot_and_launch_slide.png"), ...SLIDE, FIG_W, "Boot chain and launch tree"));

// 3 nodes
body.push(h1("3. Every node: what it does, and why it's there"));
body.push(p("Nodes marked (ours) were written for this robot. The rest are standard ROS 2 or Nav2 packages."));
const NODE_HDR = ["Node", "What it does", "Why it's there"];
const FR = [0.2, 0.45, 0.35];
body.push(h2("Running at boot"));
body.push(table(NODE_HDR, [
  ["phone_dashboard (ours)", "Web page served to the phone over the robot's own Wi-Fi: joystick, E-STOP, arm and UV buttons, live map and scan, tap-to-goal, start and stop mapping, CSV logs.", "The phone is the operator console. No laptop or gamepad needed on the floor."],
  ["joy_node, joy_to_aislebot", "Read a USB gamepad and turn sticks and buttons into drive and arm commands.", "Backup control path. No gamepad is fitted at the moment."],
  ["twist_mux", "Picks between manual and Nav2 commands. Manual priority 100, Nav2 10; each source dropped after 0.5 s of silence.", "Manual always beats the planner, with no fighting over the wheels."],
  ["teleop_asym (ours)", "Inverse kinematics for the asymmetric base: body velocity (vx, vy, wz) to four wheel speeds.", "The wheelbase isn't a rectangle, so stock mecanum equations would be wrong."],
  ["esp32_bridge (ours)", "Serial link to the ESP32 at 921600 baud: wheel-speed setpoints out, 20 Hz telemetry in, E-STOP forwarded. Sends zero speeds after 0.5 s without input.", "Keeps the real-time loop on the microcontroller and everything else in ROS."],
  ["odometry_publisher (ours)", "Integrates measured wheel speeds into position and heading. Publishes /wheel_odom and the odom to base_link transform.", "The only pose source. No IMU, and SLAM scan matching is off."],
  ["arm_bridge (ours)", "Serial link to the Mega at 115200 baud: arm and lift velocity, homing, UV tube sequence. Own 300 ms watchdog.", "Stepper timing and relay switching stay off the Pi."],
  ["lcd_display (ours)", "Shows the Pi's IP address and network mode on the 16x2 LCD every 2 s.", "The robot runs headless; this is how you find it on the network."],
  ["robot_state_publisher", "Publishes the fixed transforms in the URDF, including where the LiDAR sits.", "SLAM and Nav2 need the sensor's position relative to the robot centre."],
  ["foxglove_bridge", "Streams every topic to Foxglove Studio on a laptop.", "Debug only: the one place to see costmaps, the plan and the collision monitor live."],
], FR));
body.push(h2("Started with mapping"));
body.push(table(NODE_HDR, [
  ["ydlidar driver", "Talks to the YDLIDAR X4 Pro over USB and publishes /scan, measured at about 11.4 Hz.", "Vendor driver, used as supplied."],
  ["scan_relay (ours)", "Undoes the sensor's mirrored bearing, blanks the 90 degree arc hidden by the rear mast (107 beams, set to NaN), republishes as RELIABLE.", "Without it the map is mirrored, the mast shows up as an obstacle, and SLAM and the costmaps (which subscribe RELIABLE) get nothing."],
  ["slam_toolbox", "Builds the occupancy-grid map; publishes /map and the map to odom correction.", "The robot works in unknown space and needs a map to plan on."],
  ["zero_point_tf", "Static marker at the map origin.", "A repeatable start position for tests."],
], FR));
body.push(h2("Started with Nav2", true));
body.push(table(NODE_HDR, [
  ["bt_navigator", "Runs Nav2's stock behaviour tree: plan, follow, and on failure clear costmaps, spin, back up, retry.", "Standard Nav2, unmodified."],
  ["planner_server", "NavFn with A* on the global costmap; may plan through unknown cells.", "The map grows while the robot drives."],
  ["controller_server", "MPPI on a 3 x 3 m rolling local costmap. Turns the path into velocity commands.", "Its Omni motion model samples sideways velocity directly, which a mecanum base needs."],
  ["behavior_server", "Recovery moves: Spin, BackUp, Wait.", "On this robot BackUp is a 0.30 m strafe to the left, because Nav2 assumes +X is forward and here +X is right."],
  ["velocity_smoother", "Caps speed at 0.12 m/s and 0.30 rad/s, limits acceleration (0.3 m/s² up, 0.5 down), stops after 1 s without input.", "Smooth, bounded commands whatever the controller asks for."],
  ["collision_monitor", "Projects the footprint 1.2 s ahead along the command; slows or stops if laser points fall inside.", "A last check before the wheels, using the live scan, not the map."],
  ["cmd_vel_axis_adapter (ours)", "Rotates the command from map axes (+X right, +Y forward) to wheel axes (+X forward, +Y left).", "Everything upstream uses one axis convention, the wheel kinematics another."],
  ["goal_pose_adapter (ours)", "Turns a tap on the dashboard map into a Nav2 goal.", "Lets the phone set goals."],
  ["smoother_server, waypoint_follower, lifecycle_manager", "Path smoothing, multi-goal runs, and bringing the Nav2 servers up in order.", "Part of the standard set; not used much yet."],
], FR));

// 4 drive path
body.push(h1("4. Drive commands: two sources, one path to the wheels"));
body.push(p("Manual wins while it's publishing and loses 0.5 s after the last message. Nothing from Nav2 reaches the wheels without passing velocity_smoother and collision_monitor. The dashboard E-STOP zeroes the drive, sends <S> to the ESP32 (latched in firmware), stops the arm, cancels any Nav2 goal and stops mapping."));
body.push(figure(MONO("s2_drive_command_path_slide.png"), ...SLIDE, FIG_W, "Drive command path"));

// 5 ESP32
body.push(h1("5. Inside the ESP32"));
body.push(p("Two FreeRTOS tasks. Comms on core 0 parses commands and sends telemetry. PID on core 1 runs every 10 ms: read encoders, filter, slew, feedforward plus PID, PWM out, safety checks. Any trip latches an E-STOP that only <E1> clears."));
body.push(figure(MONO("s5_esp32_firmware_slide.png"), ...SLIDE, FIG_W, "ESP32 firmware tasks"));
body.push(h2("Pin map (firmware v3.0)"));
body.push(table(["Motor", "PWM", "DIR", "Encoder A", "Encoder B", "PCNT unit", "Dir sign"], [
  ["FR", "GPIO 4", "GPIO 16", "GPIO 36 (SP)*", "GPIO 39 (SN)*", "0", "-1"],
  ["FL", "GPIO 17", "GPIO 18", "GPIO 34*", "GPIO 35*", "1", "+1"],
  ["RR", "GPIO 19", "GPIO 21", "GPIO 32", "GPIO 33", "2", "-1"],
  ["RL", "GPIO 22", "GPIO 23", "GPIO 25", "GPIO 26", "3", "+1"],
], [0.1, 0.13, 0.13, 0.17, 0.17, 0.15, 0.15]));
body.push(p("* Input-only pins with no internal pull-ups. PWM and DIR go straight to the two MDD20A drivers at 3.3 V. The encoders run at 5 V and go through an 8-channel BSS138 level shifter. Front encoders (GTK08) use Green for A and White for B; rear (RMCS-2086) use Yellow for A and Green for B.", { spacing: { before: 120, after: 120 } }));
body.push(figure(path.join(ROOT, "docs", "hardware", "esp32_pin_circuit_mono.png"), 1820, 1020, FIG_W, "ESP32 pin-level circuit"));

// 6 odometry
body.push(h1("6. Odometry, the only source of pose"));
body.push(p("Inverse kinematics, used by teleop_asym and by the ESP32. Axes: x forward, y left."));
[
  "ω_{FR} = (vx + vy + K_{out}·ωz) / r",
  "ω_{FL} = (vx − vy − K_{in}·ωz) / r",
  "ω_{RR} = (vx − vy + K_{in}·ωz) / r",
  "ω_{RL} = (vx + vy − K_{out}·ωz) / r",
].forEach((t) => body.push(p(t, { indent: { left: 720 }, spacing: { after: 40 } })));
body.push(p("Forward kinematics, used by odometry_publisher:", { spacing: { before: 160, after: 120 } }));
[
  "vx = (r/4)(ω_{FR} + ω_{FL} + ω_{RR} + ω_{RL})",
  "vy = (r/4)(ω_{FR} − ω_{FL} − ω_{RR} + ω_{RL}) × 0.92",
  "ωz = (r/4)(ω_{FR}/K_{out} − ω_{FL}/K_{in} + ω_{RR}/K_{in} − ω_{RL}/K_{out})",
].forEach((t) => body.push(p(t, { indent: { left: 720 }, spacing: { after: 40 } })));
body.push(p("K_{out} = l_{1} + d = 0.561 m, K_{in} = l_{2} + d = 0.491 m, r = 0.0762 m. The 0.92 is a lateral scale factor: the rollers scrub when strafing (it measured 0.80 on a different floor).", { spacing: { before: 160, after: 120 } }));
body.push(bullet("Wheel odometry alone ended 0.229 m off after a 21.85 m drive (3 Sep)."));
body.push(bullet("No IMU and no filter, so heading drift and strafe error aren't corrected by anything right now."));
body.push(bullet("dt comes from the Pi's arrival time at 20 Hz, using the ESP32's filtered wheel speeds."));

// 7 lidar + slam
body.push(h1("7. From LiDAR to map"));
body.push(p("The LiDAR driver publishes BEST_EFFORT, while slam_toolbox and the costmaps subscribe RELIABLE, so nothing gets through without scan_relay. In the TF tree, slam_toolbox owns map to odom, odometry_publisher owns odom to base_link, and the URDF owns base_link to laser_frame."));
body.push(figure(MONO("s4_perception_and_pose_slide.png"), ...SLIDE, FIG_W, "LiDAR to map and the TF tree"));
body.push(h2("SLAM settings as running"));
body.push(table(["Setting", "Value"], [
  ["Package", "slam_toolbox 2.8.5, online asynchronous mapping"],
  ["Solver", "Ceres, sparse normal Cholesky, Levenberg-Marquardt"],
  ["Scan matching", "Off"],
  ["Loop closing", "On, 2.0 m search distance"],
  ["New graph node", "Every 0.2 m or 0.2 rad of travel"],
  ["Laser range used", "Up to 5.0 m"],
  ["Map resolution", "0.05 m per cell"],
  ["Scan input", "/scan_reliable from scan_relay"],
], [0.3, 0.7]));
body.push(h2("Why scan matching is off"));
body.push(p("Over the same 21.85 m drive, wheel odometry alone ended 0.229 m off; odometry plus the scan matcher ended 0.706 m off. The scan matcher made pose three times worse, so it was switched off. The likely reason is on the input side: with the robot standing still, 75 to 78 % of rays flip between valid and invalid from one scan to the next."));
body.push(p("Side effect: map to odom only moves when slam_toolbox accepts a new scan, roughly every 0.18 m. Mapping comes back to the start mark within 6 to 30 mm, but 77 to 85 % of cells stay unknown against a 50 % target (15 Sep)."));

// 8 nav2 + mppi
body.push(h1("8. Nav2 and MPPI"));
body.push(p("A tap on the phone becomes a goal, bt_navigator asks the planner for a path and the MPPI controller for commands, and the commands pass the smoother, the collision monitor and the axis adapter before twist_mux."));
body.push(figure(MONO("s3_navigation_chain_slide.png"), ...SLIDE, FIG_W, "Nav2 chain"));
body.push(h2("How MPPI picks a command, each cycle"));
[
  "Start from last cycle's best control sequence: 40 steps of 0.05 s, so 2 s ahead.",
  "Add random noise to make 300 candidates: σ = 0.06 m/s in x and y, 0.15 rad/s in yaw.",
  "Roll each candidate forward with the Omni motion model, clipped to 0.12 m/s and 0.30 rad/s.",
  "Score each with seven critics (weights below). A candidate that hits the costmap scores 1,000,000.",
  "Average the candidates with weights exp(−(S − S_{min})/λ), λ = 0.3. Send the first command, shift, repeat. Asked for 20 Hz; measured 5 to 14 Hz on the Pi.",
].forEach((t) => body.push(numbered(t)));
body.push(gap());
body.push(table(["Critic", "Weight", "What it pushes for"], [
  ["PathAlign", "14", "Stay aligned with the planned path"],
  ["Goal", "5", "Get close to the goal position"],
  ["PathFollow", "5", "Make progress along the path"],
  ["Twirling", "5", "Don't spin needlessly"],
  ["Constraint", "4", "Stay inside the velocity limits"],
  ["Cost", "3.81", "Keep away from obstacles in the costmap"],
  ["GoalAngle", "3", "Arrive facing the right way"],
], [0.2, 0.1, 0.7]));
body.push(h2("Where the speed goes missing (1 Oct test)", true));
body.push(p("Goal 0.6 m straight ahead. Aborted after 194 s and 16 recoveries; the robot crept at about 1.5 mm/s, no contact. A bag of every stage of the command chain shows MPPI itself asking for about 4 mm/s against a 120 mm/s limit, and every stage after it passing that on unchanged."));
body.push(table(["Stage", "0 to 10 s", "10 to 20 s", "20 to 30 s", "30 to 40 s"], [
  ["/cmd_vel_nav (MPPI)", "4.4", "5.1", "3.8", "4.4"],
  ["/cmd_vel_smoothed", "4.4", "5.1", "3.8", "4.3"],
  ["/cmd_vel_baselink", "4.4", "5.0", "3.8", "4.3"],
  ["/cmd_vel (to the wheels)", "4.4", "5.0", "3.8", "4.3"],
], [0.32, 0.17, 0.17, 0.17, 0.17]));
body.push(p("Mean speed in mm/s per 10 s window.", { spacing: { before: 60, after: 120 } }));
body.push(bullet("Rules out: velocity_smoother, collision_monitor, the axis adapter, twist_mux and the ESP32."));
body.push(bullet("Points at: MPPI's own averaging. Noise alone gives 0.06 / √300 = 3.5 mm/s, close to the 4.4 measured, so the optimiser barely prefers any direction."));
body.push(bullet("Suspect, not proven: the 0.3 m/s² acceleration limit, which allows only 0.015 m/s per 0.05 s step."));
body.push(bullet("Next: the same goal with Nav2's stock limits (3.0 m/s²), already set on the live node but not yet in the repo file."));

// 9 status
body.push(h1("9. Where things stand"));
body.push(h2("Working, with measurements"));
[
  "Wheel-speed loop on the ESP32 at 100 Hz, with latching safety trips.",
  "Manual drive from the phone, with priority over Nav2 and four stacked watchdogs.",
  "Wheel odometry: 0.229 m error over a 21.85 m drive.",
  "Mapping comes back to the start mark within 6 to 30 mm.",
  "The global planner finds paths from the start mark (1 Oct).",
].forEach((t) => body.push(bullet(t)));
body.push(h2("Open"));
[
  "No autonomous goal reached yet: MPPI asks for about 4 mm/s.",
  "Map coverage: 77 to 85 % of cells unknown, against a 50 % target.",
  "No IMU, so heading drift isn't corrected.",
  "A 90 degree blind arc behind the mast.",
  "No hardware E-stop. The ESP32 is still powered from the Pi's USB.",
].forEach((t) => body.push(bullet(t)));
body.push(h2("Next"));
[
  "Re-run the 0.6 m goal with stock MPPI acceleration limits.",
  "If it drives, measure real acceleration on a straight run and set the limits from that.",
  "If it still creeps, look at temperature, sampling spread, critic weights and the real loop rate.",
  "Then a ladder of goals: 1 m forward, 1 m sideways, a 90 degree turn, a reverse.",
  "Rear sensing for the blind arc: a rear LiDAR or a ring of ToF sensors.",
].forEach((t) => body.push(numbered(t, "next")));

// appendix
body.push(h1("Appendix: every node and topic on one sheet"));
body.push(p("Dense on purpose. Zoom in."));
body.push(figure(MONO("h1_whole_system_handout.png"), 1560, 1160, 7.8, "Whole system, every node and topic"));

// ---------------------------------------------------------------- document
const doc = new Document({
  creator: "Aritra Das",
  title: "NarrowAisleBot ROS 2 notes",
  styles: {
    // Override docx-js's built-in styles in place (its defaults are blue), so every
    // heading level, the title and hyperlinks are black, and each style exists once.
    default: {
      document: { run: { font: "Calibri", size: 22, color: "000000" } },
      title: { run: { font: "Calibri", size: 40, bold: true, color: "000000" }, paragraph: { spacing: { after: 160 } } },
      heading1: { run: { font: "Calibri", size: 32, bold: true, color: "000000" }, paragraph: { spacing: { before: 120, after: 160 } } },
      heading2: { run: { font: "Calibri", size: 26, bold: true, color: "000000" }, paragraph: { spacing: { before: 240, after: 120 } } },
      heading3: { run: { font: "Calibri", size: 24, bold: true, color: "000000" } },
      heading4: { run: { font: "Calibri", size: 22, bold: true, italics: true, color: "000000" } },
      heading5: { run: { font: "Calibri", size: 22, color: "000000" } },
      heading6: { run: { font: "Calibri", size: 22, italics: true, color: "000000" } },
      hyperlink: { run: { color: "000000", underline: { type: "single", color: "000000" } } },
    },
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      ...["steps", "next"].map((reference) => ({ reference, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] })),
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE },
                           margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "NarrowAisleBot ROS 2 notes   ", size: 18 }), new TextRun({ children: [PageNumber.CURRENT], size: 18 })] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });
