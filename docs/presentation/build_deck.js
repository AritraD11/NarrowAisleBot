// Builds docs/presentation/NarrowAisleBot_ROS2_Architecture.pptx
//
//   NODE_PATH=<dir with pptxgenjs> node docs/presentation/build_deck.js
//
// Figures come from docs/flowcharts/png and docs/hardware, so rebuild those first if the
// system changed. Every number on a slide is taken from the repo; the source is named in the
// speaker notes of the slide that uses it.

const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const P = (...a) => path.join(ROOT, ...a);
const FIG = (n) => P("docs", "flowcharts", "png", n);
const OUT = P("docs", "presentation", "NarrowAisleBot_ROS2_Architecture.pptx");

const THEME = {
  name: "NarrowAisleBot",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "172126", lt1: "FFFFFF", dk2: "52606A", lt2: "F1F4F3",
    accent1: "C2410C", accent2: "0072B2", accent3: "00896A",
    accent4: "7C4DA8", accent5: "66737C", accent6: "C62828",
    hlink: "0072B2", folHlink: "7C4DA8",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Aritra Das";
pres.title = "NarrowAisleBot ROS 2 architecture";
const C = pres.SchemeColor;

const W = 13.333, M = 0.6, CW = W - 2 * M;

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE",
  background: { color: HEX.dk1 },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.lt1 },
  margin: [0.4, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.32, w: CW, h: 0.78,
        fontSize: 30, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "NarrowAisleBot  |  ROS 2 architecture  |  October 2026",
        options: { x: M, y: 7.04, w: 8, h: 0.3, fontSize: 10, color: C.text2, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 7.04, w: 0.6, h: 0.3, fontSize: 10, color: C.text2, align: "right" },
});

const addContent = (title, section) => {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
};

// image that keeps its aspect ratio, centred in a box
const fitImage = (s, file, pw, ph, box) => {
  const r = Math.min(box.w / pw, box.h / ph);
  const w = pw * r, h = ph * r;
  s.addImage({ path: file, x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h });
};
const FIGBOX = { x: M, y: 1.2, w: CW, h: 5.65 };
const SLIDE_FIG = [1760, 990];

const body = (s, text, opt) => s.addText(text, Object.assign({ isTextBox: true, fontSize: 15, color: C.text1, valign: "top", margin: 0, paraSpaceAfter: 6 }, opt));
const card = (s, x, y, w, h, fill) => s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: fill || C.background2 }, line: { color: C.background2, width: 0 } });

// ---------------------------------------------------------------- 1 title
pres.addSection({ title: "Introduction" });
{
  const s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Introduction" });
  s.addImage({ path: P("docs", "presentation", "img", "title_robot.jpg"), x: W - 3.3, y: 0, w: 3.3, h: 7.5,
               sizing: { type: "cover", w: 3.3, h: 7.5 } });
  s.addText("NarrowAisleBot", { isTextBox: true, x: M + 0.1, y: 1.6, w: 8.8, h: 0.95, fontSize: 46, bold: true, color: C.background1, margin: 0 });
  s.addText("The ROS 2 software on the robot: every node, what it does, and why it is there",
    { isTextBox: true, x: M + 0.1, y: 2.65, w: 8.6, h: 1.1, fontSize: 24, color: C.background1, margin: 0, valign: "top" });
  s.addText("With the current mapping (slam_toolbox), Nav2 and MPPI controller status",
    { isTextBox: true, x: M + 0.1, y: 3.85, w: 8.6, h: 0.5, fontSize: 17, color: "C9D3D6", margin: 0 });
  s.addText([
    { text: "Aritra Das", options: { bold: true, breakLine: true } },
    { text: "IIT Bombay  |  October 2026", options: { breakLine: true } },
    { text: "Robot measurements as of 1 Oct 2026", options: { color: "9FAEB4" } },
  ], { isTextBox: true, x: M + 0.1, y: 5.35, w: 8.0, h: 1.2, fontSize: 15, color: C.background1, margin: 0, valign: "top", paraSpaceAfter: 4 });
  s.addNotes("Title. The photo is the robot in the lab, Aug 2026, UV lamp arm raised. Everything in this deck is read from the repository: code, launch files, parameter files, and the session handoffs that record what was measured on the robot.");
}

// ---------------------------------------------------------------- 2 the robot
{
  const s = addContent("What the robot is, and what the software has to do", "Introduction");
  s.addImage({ path: P("docs", "presentation", "img", "dims_schematic.png"), x: M, y: 1.45, w: 6.6, h: 6.6 * 372 / 780 });
  s.addText("Wheel layout from the CAD model. Outer wheels (FR, RL) sit 403 mm from the centre, inner wheels (FL, RR) 333 mm. The chassis is 252 mm wide without wheels, about 360 mm across them.",
    { isTextBox: true, x: M, y: 4.85, w: 6.6, h: 0.9, fontSize: 13, color: C.text2, margin: 0, valign: "top" });
  const x = 7.65, w = W - M - x;
  body(s, [
    { text: "Why the wheelbase is asymmetric", options: { bold: true, breakLine: true } },
    { text: "Staggering the wheel pairs lets the chassis be narrow enough for aisles a conventional mecanum platform cannot enter.", options: { breakLine: true } },
    { text: " ", options: { fontSize: 6, breakLine: true } },
    { text: "What the software must do", options: { bold: true, breakLine: true } },
    { text: "Drive in any direction, sideways and in reverse included, from a phone and on its own in unknown space, while carrying a UV lamp arm.", options: { breakLine: true } },
    { text: " ", options: { fontSize: 6, breakLine: true } },
    { text: "How the work is split", options: { bold: true, breakLine: true } },
    { text: "A 100 Hz wheel-speed loop on an ESP32, the arm on an Arduino Mega, and everything else as ROS 2 nodes on a Raspberry Pi 5." },
  ], { x, y: 1.5, w, h: 5.2 });
  s.addNotes("Geometry: l1 0.403 m, l2 0.333 m, half-track d 0.15769 m, wheel radius 0.0762 m (firmware constants, aislebot_esp32.ino). The asymmetric layout is why the kinematics on slide 15 are not the textbook mecanum equations.");
}

// ---------------------------------------------------------------- 3 system at a glance
{
  const s = addContent("The whole system on one page", "Introduction");
  fitImage(s, FIG("s1_system_overview_slide.png"), ...SLIDE_FIG, FIGBOX);
  s.addNotes("Solid band: starts at boot from systemd. Dashed band: started on demand, mapping from the dashboard MAP button, Nav2 by hand. Line colours: blue manual drive, orange autonomous drive, black the merged command to the wheels, green feedback and odometry, purple LiDAR and map, grey operator and control, dashed grey TF.");
}

// ---------------------------------------------------------------- 4 three computers
pres.addSection({ title: "Hardware" });
{
  const s = addContent("Three computers, each with one job", "Hardware");
  const cards = [
    { name: "Raspberry Pi 5", role: "Ubuntu 24.04, ROS 2 Jazzy", stat: "11", statLbl: "processes at boot, more on demand",
      lines: ["Operator interface, kinematics, odometry, mapping and planning", "Runs its own Wi-Fi access point for the phone", "Talks to both microcontrollers over USB serial"],
      why: "Gives the libraries (Nav2, slam_toolbox) but cannot promise a 10 ms loop." },
    { name: "ESP32-WROOM-32", role: "Drive controller, firmware v3.0", stat: "100 Hz", statLbl: "wheel-speed PID on four motors",
      lines: ["Counts encoders in hardware (PCNT), 186,264 counts per front wheel turn", "Latching E-STOP; overspeed, runaway and stall trips", "921,600 baud link to the Pi"],
      why: "Timing and safety that do not depend on Linux being responsive." },
    { name: "Arduino Mega 2560", role: "Arm and UV controller, firmware v8", stat: "3", statLbl: "stepper axes: two arms and a lift",
      lines: ["Three UV tubes on relays, switched on in stages", "500 ms watchdog on arm motion", "115,200 baud link to the Pi"],
      why: "Step pulses and relay switching stay off the Pi." },
  ];
  const cw = (CW - 2 * 0.3) / 3;
  cards.forEach((c, i) => {
    const x = M + i * (cw + 0.3), y = 1.35, h = 5.45;
    card(s, x, y, cw, h);
    const ix = x + 0.3, iw = cw - 0.6;
    s.addText(c.name, { isTextBox: true, x: ix, y: y + 0.28, w: iw, h: 0.45, fontSize: 20, bold: true, color: C.text1, margin: 0 });
    s.addText(c.role, { isTextBox: true, x: ix, y: y + 0.72, w: iw, h: 0.35, fontSize: 13, color: C.text2, margin: 0 });
    s.addText(c.stat, { isTextBox: true, x: ix, y: y + 1.2, w: iw, h: 0.85, fontSize: 44, bold: true, color: C.accent1, margin: 0 });
    s.addText(c.statLbl, { isTextBox: true, x: ix, y: y + 2.02, w: iw, h: 0.35, fontSize: 13, color: C.text2, margin: 0 });
    s.addText(c.lines.map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < c.lines.length - 1 } })),
      { isTextBox: true, x: ix, y: y + 2.55, w: iw, h: 1.75, fontSize: 13, color: C.text1, margin: 0, valign: "top", paraSpaceAfter: 5 });
    s.addText([{ text: "Why: ", options: { bold: true } }, { text: c.why }],
      { isTextBox: true, x: ix, y: y + 4.35, w: iw, h: 0.85, fontSize: 13, color: C.text1, margin: 0, valign: "top" });
  });
  s.addNotes("Counts per wheel turn: front GTK08 encoders 1000 PPR x 4 x 46.566 gear ratio = 186,264; rear RMCS-2086 encoders 500 lines, so 93,132. The Pi starts 11 processes at boot (aislebot_full.launch.py); mapping and Nav2 add about 15 more when started.");
}

// ---------------------------------------------------------------- 5 ESP32 wiring
{
  const s = addContent("How the ESP32 is wired", "Hardware");
  fitImage(s, P("docs", "hardware", "esp32_pin_circuit.png"), 1820, 1020, FIGBOX);
  s.addNotes("Generated from the firmware: the script reads the GPIO numbers and direction signs out of aislebot_esp32.ino, and the shifter channels out of Bench_Test_Map.md, and refuses to draw if they disagree. Encoders run at 5 V; the 8-channel BSS138 shifter brings them to 3.3 V. Driver inputs take 3.3 V logic directly. Front and rear encoders use different wire colours for A and B.");
}

// ---------------------------------------------------------------- 6 power
{
  const s = addContent("Power rails and grounding", "Hardware");
  const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 } } });
  const rows = [
    [hdr("Rail"), hdr("Source"), hdr("Feeds")],
    ["12.8 V", "LiFePO4 battery, 30 Ah, through an SSR-50DD solid-state relay", "Boost and buck converters"],
    ["24 V", "1200 W boost converter", "Both Cytron MDD20A motor drivers"],
    ["5 V", "DFRobot 60 W buck converter", "Four encoders, level shifter high side"],
    ["3.3 V", "ESP32 on-board regulator", "Level shifter low side"],
    ["USB 5 V", "Raspberry Pi 5", "ESP32, power and data together"],
  ];
  s.addTable(rows, { x: M, y: 1.4, w: 7.3, colW: [1.1, 3.6, 2.6], fontSize: 13, color: C.text1,
    border: { type: "solid", pt: 0.75, color: "D5DBDB" }, valign: "middle", rowH: 0.62, margin: [4, 8, 4, 8] });
  const x = 8.3, w = W - M - x;
  card(s, x, 1.4, w, 1.85);
  s.addText([
    { text: "One ground bus", options: { bold: true, breakLine: true } },
    { text: "ESP32, buck, boost, both driver logic grounds, the shifter and all four encoder black wires. The Pi's ground arrives through the USB cable." },
  ], { isTextBox: true, x: x + 0.3, y: 1.6, w: w - 0.6, h: 1.55, fontSize: 14, color: C.text1, margin: 0, valign: "top", paraSpaceAfter: 4 });
  card(s, x, 3.5, w, 2.75, "FBEDEA");
  s.addText([
    { text: "Not done yet", options: { bold: true, color: C.accent6, breakLine: true } },
    { text: "No hardware E-stop. Every stop path is software today. A latching normally-closed button in series with the SSR trigger is planned.", options: { breakLine: true } },
    { text: " ", options: { fontSize: 6, breakLine: true } },
    { text: "The ESP32 is still powered from the Pi's USB. Feeding its VIN from the 5 V buck and cutting VBUS is planned, to keep motor ground noise out of the encoder counts." },
  ], { isTextBox: true, x: x + 0.3, y: 3.7, w: w - 0.6, h: 2.4, fontSize: 14, color: C.text1, margin: 0, valign: "top", paraSpaceAfter: 4 });
  s.addNotes("Sources: Master_Reference.md sections 2.5, 3.1 and 3.2 for the rails and ground bus; Hardware_Roadmap.md for the E-stop and the VIN fix, both listed there as not done.");
}

// ---------------------------------------------------------------- 7 boot
pres.addSection({ title: "Nodes" });
{
  const s = addContent("What starts, and when", "Nodes");
  fitImage(s, FIG("s6_boot_and_launch_slide.png"), ...SLIDE_FIG, FIGBOX);
  s.addNotes("systemd runs start_aislebot.sh, which sets ROS domain 42 and Cyclone DDS on loopback, waits for the USB devices, then launches aislebot_full.launch.py. Mapping starts from the dashboard MAP button. Nav2 is started by hand after the map is running; the other order makes the global costmap reject the map until one arrives.");
}

// ---------------------------------------------------------------- node tables
const nodeTable = (title, section, rows, notes) => {
  const s = addContent(title, section);
  const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 } } });
  const data = [[hdr("Node"), hdr("What it does"), hdr("Why it is there")]].concat(
    rows.map(([n, what, why, own]) => [
      { text: own ? [{ text: n, options: { bold: true, breakLine: true } }, { text: "written for this robot", options: { fontSize: 12, color: C.accent1 } }] : n,
        options: { bold: true } },
      what, why]));
  s.addTable(data, { x: M, y: 1.35, w: CW, colW: [2.85, 5.35, 3.9], fontSize: 15, color: C.text1,
    border: { type: "solid", pt: 0.75, color: "D5DBDB" }, valign: "top", margin: [9, 10, 9, 10], autoPage: false });
  s.addNotes(notes);
  return s;
};

nodeTable("Running at boot: operator side and drive chain", "Nodes", [
  ["phone_dashboard", "Web page served to the phone over the robot's own Wi-Fi: joystick, E-STOP, arm and UV buttons, live map and scan, tap-to-goal, start and stop mapping, CSV logs.", "The phone is the operator console. No laptop or gamepad is needed on the floor.", true],
  ["joy_node, joy_to_aislebot", "Read a USB gamepad and turn sticks and buttons into drive and arm commands.", "Backup control path. No gamepad is fitted at present.", false],
  ["twist_mux", "Chooses between manual and Nav2 commands. Manual has priority 100, Nav2 10; each source is dropped after 0.5 s of silence.", "Manual control must always beat the planner, with no fighting over the wheels.", false],
  ["teleop_asym", "Inverse kinematics for the asymmetric base: body velocity (vx, vy, wz) to four wheel speeds.", "The wheelbase is not a rectangle, so the stock mecanum equations would be wrong.", true],
  ["esp32_bridge", "Serial link to the ESP32: sends wheel-speed setpoints, reads 20 Hz telemetry, forwards E-STOP. Sends zero speeds after 0.5 s without input.", "Keeps the real-time loop on the microcontroller and everything else in ROS.", true],
], "All of these start at boot. twist_mux settings: config/twist_mux.yaml. Speed limits passed at launch: 0.15 m/s and 0.30 rad/s. The dashboard is one Python file: a FastAPI web server and a ROS node on its own thread.");

nodeTable("Running at boot: pose, arm and support", "Nodes", [
  ["odometry_publisher", "Integrates measured wheel speeds into position and heading. Publishes /wheel_odom and the odom to base_link transform.", "The only pose source on the robot. There is no IMU, and SLAM scan matching is off.", true],
  ["arm_bridge", "Serial link to the Mega: arm and lift velocity, homing, the UV tube sequence. Its own 300 ms watchdog.", "Stepper timing and relay switching stay off the Pi.", true],
  ["lcd_display", "Shows the Pi's IP address and network mode on the 16x2 LCD every 2 s.", "The robot runs headless; this is how you find it on the network.", true],
  ["robot_state_publisher", "Publishes the fixed transforms in the URDF, including where the LiDAR sits on the body.", "SLAM and Nav2 need the sensor's position relative to the robot centre.", false],
  ["foxglove_bridge", "Streams every topic to Foxglove Studio on a laptop over a WebSocket.", "Debug only: the one place to see costmaps, the plan and the collision monitor live.", false],
], "odometry_publisher: lateral scale 0.92 corrects roller scrub when strafing (measured on the floor at the zero mark; 0.80 on another floor). The LiDAR sits at (0, 0.27, 0.275) m from base_link in the URDF.");

nodeTable("Started with mapping: LiDAR and slam_toolbox", "Nodes", [
  ["ydlidar driver", "Talks to the YDLIDAR X4 Pro over USB and publishes /scan, measured at about 11.4 Hz.", "Vendor driver, used as supplied.", false],
  ["scan_relay", "Undoes the sensor's mirrored bearing, blanks the 90 degree arc hidden by the rear mast, and republishes the scan as RELIABLE.", "Without it the map comes out mirrored, the mast appears as an obstacle, and SLAM and the costmaps (which subscribe RELIABLE) receive nothing.", true],
  ["slam_toolbox", "Builds the occupancy-grid map from scans and odometry; publishes /map and the map to odom correction.", "The robot works in unknown space and needs a map to plan on.", false],
  ["zero_point_tf", "Static marker at the map origin.", "A repeatable start position for every test.", false],
], "scan_relay: the sensor reports bearing as 270 degrees minus the true bearing; the masked arc is -135 to -45 degrees, 107 beams, set to NaN so it neither marks nor clears. All ten of its parameters can be changed live from the dashboard.");

nodeTable("Started with Nav2: planning and control", "Nodes", [
  ["bt_navigator", "Runs Nav2's stock behaviour tree: plan, follow, and on failure clear the costmaps, spin, back up, retry.", "Standard Nav2, unmodified.", false],
  ["planner_server", "NavFn with A* on the global costmap. Plans the whole route and may cross unknown cells.", "The map grows while the robot drives, so the planner has to accept unknown space.", false],
  ["controller_server", "MPPI on a 3 x 3 m rolling local costmap. Turns the path into velocity commands.", "Its Omni motion model samples sideways velocity directly, which a mecanum base needs.", false],
  ["behavior_server", "Recovery moves: Spin, BackUp, Wait.", "On this robot BackUp is a 0.30 m strafe to the left, because Nav2 assumes +X is forward and here +X is right.", false],
  ["smoother_server, waypoint_follower, lifecycle_manager", "Path smoothing, multi-goal runs, and bringing the Nav2 servers up in order.", "Part of the standard set; not used much yet.", false],
], "Nav2 1.3.12. Parameters: src/mecanum_navigation/config/nav2_params.yaml. BackUp as a left strafe was read from the Nav2 source on 30 Sep and seen in the 1 Oct log (0.31 m to the left).");

nodeTable("Started with Nav2: the safety chain and two adapters", "Nodes", [
  ["velocity_smoother", "Caps speed at 0.12 m/s and 0.30 rad/s, limits acceleration to 0.3 m/s² up and 0.5 m/s² down, stops after 1 s without input.", "Smooth, bounded commands whatever the controller asks for.", false],
  ["collision_monitor", "Projects the robot's footprint 1.2 s ahead along the command and slows or stops if laser points fall inside.", "A last check before the wheels that uses the live scan, not the map.", false],
  ["cmd_vel_axis_adapter", "Rotates the command from the map's axes (+X right, +Y forward) to the wheels' axes (+X forward, +Y left).", "Everything upstream uses one axis convention and the wheel kinematics another.", true],
  ["goal_pose_adapter", "Turns a tap on the dashboard map into a Nav2 goal.", "Lets the phone set goals.", true],
], "Order on the way to the wheels: controller or behavior server, velocity_smoother, collision_monitor, cmd_vel_axis_adapter, twist_mux. The adapter is last so that everything before it, the collision polygon included, works in the same axes as the footprint.");

// ---------------------------------------------------------------- 13 drive path
{
  const s = addContent("Drive commands: two sources, one path to the wheels", "Nodes");
  fitImage(s, FIG("s2_drive_command_path_slide.png"), ...SLIDE_FIG, FIGBOX);
  s.addNotes("Manual wins while it publishes and loses 0.5 s after the last message. Four watchdogs stack. The dashboard E-STOP zeroes the drive command, sends <S> to the ESP32 (latched in firmware), stops the arm, cancels any Nav2 goal and stops mapping.");
}

// ---------------------------------------------------------------- 14 ESP32 firmware
{
  const s = addContent("Inside the ESP32 drive firmware", "Nodes");
  fitImage(s, FIG("s5_esp32_firmware_slide.png"), ...SLIDE_FIG, FIGBOX);
  s.addNotes("Two FreeRTOS tasks: comms on core 0, PID on core 1 at 100 Hz with vTaskDelayUntil. Velocity is an EMA of encoder deltas, alpha 0.4. Feedforward was fitted in air, not under load. Trips: watchdog 750 ms, overspeed 1.3 x the 5.2 rad/s limit for 300 ms, runaway 500 ms, stall at PWM 250 or more with under 0.15 rad/s for 2 s. All gains can be changed over serial without reflashing.");
}

// ---------------------------------------------------------------- 15 odometry
{
  const s = addContent("Odometry: the only source of pose", "Nodes");
  // "ω_FR" becomes ω with FR set as a real subscript
  const eq = (lines) => {
    const runs = [];
    lines.forEach((t, k) => {
      const parts = t.split(/_([A-Za-z0-9]+)/);
      parts.forEach((p, j) => { if (p) runs.push({ text: p, options: j % 2 ? { subscript: true } : {} }); });
      if (k < lines.length - 1) runs[runs.length - 1].options = Object.assign({}, runs[runs.length - 1].options, { breakLine: true });
    });
    return runs;
  };
  card(s, M, 1.35, 7.0, 2.45);
  s.addText("Inverse kinematics (teleop_asym and the ESP32)", { isTextBox: true, x: M + 0.3, y: 1.5, w: 6.4, h: 0.35, fontSize: 14, bold: true, color: C.text1, margin: 0 });
  s.addText(eq(["ω_FR = (vx + vy + K_out·ωz) / r", "ω_FL = (vx − vy − K_in·ωz) / r", "ω_RR = (vx − vy + K_in·ωz) / r", "ω_RL = (vx + vy − K_out·ωz) / r"]),
    { isTextBox: true, x: M + 0.3, y: 1.92, w: 6.4, h: 1.75, fontSize: 16, fontFace: "Cambria", color: C.text1, margin: 0, valign: "top", paraSpaceAfter: 3 });
  card(s, M, 3.95, 7.0, 2.1);
  s.addText("Forward kinematics (odometry_publisher)", { isTextBox: true, x: M + 0.3, y: 4.1, w: 6.4, h: 0.35, fontSize: 14, bold: true, color: C.text1, margin: 0 });
  s.addText(eq(["vx = (r/4)(ω_FR + ω_FL + ω_RR + ω_RL)", "vy = (r/4)(ω_FR − ω_FL − ω_RR + ω_RL) × 0.92", "ωz = (r/4)(ω_FR/K_out − ω_FL/K_in + ω_RR/K_in − ω_RL/K_out)"]),
    { isTextBox: true, x: M + 0.3, y: 4.52, w: 6.6, h: 1.4, fontSize: 16, fontFace: "Cambria", color: C.text1, margin: 0, valign: "top", paraSpaceAfter: 3 });
  s.addText(eq(["K_out = l_1 + d = 0.561 m,  K_in = l_2 + d = 0.491 m,  r = 0.0762 m.  Axes: x forward, y left."]),
    { isTextBox: true, x: M, y: 6.2, w: 7.0, h: 0.5, fontSize: 12, color: C.text2, margin: 0 });
  const x = 8.2, w = W - M - x;
  s.addText("0.229 m", { isTextBox: true, x, y: 1.35, w, h: 0.85, fontSize: 44, bold: true, color: C.accent3, margin: 0 });
  s.addText("closure error after a 21.85 m drive, wheel odometry alone (3 Sep)", { isTextBox: true, x, y: 2.2, w, h: 0.65, fontSize: 13, color: C.text2, margin: 0, valign: "top" });
  s.addText("0.92", { isTextBox: true, x, y: 3.05, w, h: 0.85, fontSize: 44, bold: true, color: C.accent3, margin: 0 });
  s.addText("lateral scale factor: the rollers scrub when strafing. It was 0.80 on a different floor.", { isTextBox: true, x, y: 3.9, w, h: 0.65, fontSize: 13, color: C.text2, margin: 0, valign: "top" });
  body(s, "No IMU and no filter. Heading drift and strafe error are not corrected by anything at present, and the forward equations are the exact inverse of the ones the ESP32 drives with.",
    { x, y: 4.85, w, h: 1.6, fontSize: 14 });
  s.addNotes("Integration uses the Pi's arrival time for dt, at 20 Hz, from EMA-filtered wheel speeds. The published frame is rotated 90 degrees so +Y reads forward, to match the map's convention. The 0.229 m figure is from StageG_Deploy.md; on the same drive, odometry plus the scan matcher closed 0.706 m (next section).");
}

// ---------------------------------------------------------------- 16 perception
pres.addSection({ title: "Mapping and navigation" });
{
  const s = addContent("From LiDAR to map", "Mapping and navigation");
  fitImage(s, FIG("s4_perception_and_pose_slide.png"), ...SLIDE_FIG, FIGBOX);
  s.addNotes("The LiDAR driver publishes BEST_EFFORT; slam_toolbox and the costmaps subscribe RELIABLE, so without scan_relay nothing arrives. TF: slam_toolbox owns map to odom, odometry_publisher owns odom to base_link, robot_state_publisher owns base_link to laser_frame.");
}

// ---------------------------------------------------------------- 17 SLAM today
{
  const s = addContent("SLAM as it runs today, and why scan matching is off", "Mapping and navigation");
  const rows = [
    [{ text: "Setting", options: { bold: true, color: C.background1, fill: { color: C.text1 } } }, { text: "Value", options: { bold: true, color: C.background1, fill: { color: C.text1 } } }],
    ["Package", "slam_toolbox 2.8.5, online asynchronous mapping"],
    ["Solver", "Ceres, sparse normal Cholesky, Levenberg-Marquardt"],
    ["Scan matching", "Off"],
    ["Loop closing", "On, 2.0 m search distance"],
    ["New graph node", "Every 0.2 m or 0.2 rad of travel"],
    ["Laser range used", "Up to 5.0 m"],
    ["Map resolution", "0.05 m per cell"],
    ["Scan input", "/scan_reliable from scan_relay"],
  ];
  s.addTable(rows, { x: M, y: 1.35, w: 6.4, colW: [2.1, 4.3], fontSize: 13, color: C.text1,
    border: { type: "solid", pt: 0.75, color: "D5DBDB" }, valign: "middle", rowH: 0.5, margin: [4, 8, 4, 8] });
  const x = 7.5, w = W - M - x;
  s.addText("Same 21.85 m drive, error at the end", { isTextBox: true, x, y: 1.35, w, h: 0.4, fontSize: 15, bold: true, color: C.text1, margin: 0 });
  s.addText([{ text: "0.229 m", options: { bold: true, color: C.accent3, fontSize: 36 } }, { text: "   wheel odometry alone", options: { fontSize: 14, color: C.text2 } }],
    { isTextBox: true, x, y: 1.85, w, h: 0.7, margin: 0, valign: "middle" });
  s.addText([{ text: "0.706 m", options: { bold: true, color: C.accent6, fontSize: 36 } }, { text: "   odometry plus scan matcher", options: { fontSize: 14, color: C.text2 } }],
    { isTextBox: true, x, y: 2.55, w, h: 0.7, margin: 0, valign: "middle" });
  body(s, [
    { text: "The scan matcher made pose three times worse, so it was switched off. That picks the better of two measured estimators.", options: { breakLine: true } },
    { text: "The likely reason is on the input side: with the robot standing still, 75 to 78 % of rays flip between valid and invalid from one scan to the next.", options: { breakLine: true } },
    { text: "Consequence: map to odom only moves when slam_toolbox accepts a new scan, about every 0.18 m. Mapping returns to the start mark within 6 to 30 mm, but 77 to 85 % of cells stay unknown, against a 50 % target (15 Sep)." },
  ], { x, y: 3.45, w, h: 3.35, fontSize: 14, paraSpaceAfter: 8 });
  s.addNotes("Sources: system/slam_nodom_stageB.yaml (the file running on the robot, matched by hash), StageG_Deploy.md for the 0.229 m and 0.706 m closure and the ray-flip measurement, Project_Status.md for the mapping gate figures. Unknown-cell coverage is the open mapping problem.");
}

// ---------------------------------------------------------------- 18 Nav2 chain
{
  const s = addContent("Nav2 as configured: from a tap to the wheels", "Mapping and navigation");
  fitImage(s, FIG("s3_navigation_chain_slide.png"), ...SLIDE_FIG, FIGBOX);
  s.addNotes("Nothing autonomous reaches the wheels without passing velocity_smoother and collision_monitor. Not started on purpose: route_server and opennav_docking (no route graph, no dock) and robot_localization (no IMU).");
}

// ---------------------------------------------------------------- 19 MPPI how
{
  const s = addContent("MPPI: how the controller picks a command", "Mapping and navigation");
  const steps = [
    "Start from last cycle's best control sequence: 40 steps of 0.05 s, so 2 s ahead.",
    "Add random noise to make 300 candidates: σ = 0.06 m/s in x and y, 0.15 rad/s in yaw.",
    "Roll each candidate forward with the Omni motion model, clipped to 0.12 m/s and 0.30 rad/s.",
    "Score each with seven critics. A candidate that hits the costmap scores 1,000,000.",
    [{ text: "Average the candidates with weights exp(−(S − S" }, { text: "min", options: { subscript: true } }, { text: ")/λ), λ\u00a0=\u00a00.3. Send the first command, shift the sequence, repeat." }],
  ];
  steps.forEach((t, i) => {
    const y = 1.4 + i * 0.98;
    s.addShape(pres.ShapeType.ellipse, { x: M, y: y + 0.04, w: 0.5, h: 0.5, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 } });
    s.addText(String(i + 1), { isTextBox: true, x: M, y: y + 0.04, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0 });
    s.addText(t, { isTextBox: true, x: M + 0.75, y, w: 6.15, h: 0.85, fontSize: 14, color: C.text1, margin: 0, valign: "top" });
  });
  s.addText("Requested at 20 Hz; measured 5 to 14 Hz on the Pi.", { isTextBox: true, x: M + 0.75, y: 6.35, w: 6.15, h: 0.4, fontSize: 12, color: C.text2, margin: 0 });
  s.addChart(pres.ChartType.bar, [{ name: "Weight", labels: ["PathAlign", "Goal", "PathFollow", "Twirling", "Constraint", "Cost", "GoalAngle"], values: [14, 5, 5, 5, 4, 3.81, 3] }], {
    x: 7.75, y: 1.3, w: W - M - 7.75, h: 5.45, barDir: "bar", catAxisOrientation: "maxMin",
    showTitle: true, title: "Critic weights (nav2_params.yaml)", titleFontSize: 14, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
    chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 12, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "General",
    catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 13, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, barGapWidthPct: 60,
  });
  s.addNotes("MPPI is a sampling-based model predictive controller. The weights favour following the path's direction (PathAlign 14) over everything else. gamma is 0.015. Acceleration limits in the committed file: 0.3 m/s² up, 0.5 down (x and y), 0.6 rad/s² in yaw. PathAngle and PreferForward critics were dropped because they assume +X is forward.");
}

// ---------------------------------------------------------------- 20 MPPI result
{
  const s = addContent("MPPI: where the speed goes missing (1 Oct test)", "Mapping and navigation");
  s.addChart(pres.ChartType.bar, [{ name: "Mean speed", labels: ["MPPI output", "after velocity_smoother", "after collision_monitor", "into the wheels (/cmd_vel)"], values: [4.4, 4.4, 4.4, 4.4] }], {
    x: M, y: 1.3, w: 7.1, h: 4.9, barDir: "bar", catAxisOrientation: "maxMin",
    showTitle: true, title: "Speed requested at each stage, mm/s (axis ends at the 120 mm/s limit)", titleFontSize: 13, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
    chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 12, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "0.0",
    catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt",
    valAxisMinVal: 0, valAxisMaxVal: 120, valAxisMajorUnit: 20, valAxisLabelColor: HEX.dk2, valAxisLabelFontSize: 11, valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: "E3E7E8", size: 0.75 }, catGridLine: { style: "none" }, showLegend: false, barGapWidthPct: 70,
  });
  s.addText("Mean over the first 40 s of the goal, from a bag of every stage of the chain.", { isTextBox: true, x: M, y: 6.3, w: 7.1, h: 0.4, fontSize: 12, color: C.text2, margin: 0 });
  const x = 8.1, w = W - M - x;
  body(s, [
    { text: "The test", options: { bold: true, breakLine: true } },
    { text: "Goal 0.6 m straight ahead. Aborted after 194 s and 16 recoveries; the robot crept at about 1.5 mm/s. No contact.", options: { breakLine: true } },
    { text: "What it rules out", options: { bold: true, breakLine: true } },
    { text: "Every stage after MPPI passes the same 4 mm/s on, so the smoother, collision monitor, axis adapter, mux and ESP32 are cleared.", options: { breakLine: true } },
    { text: "What it points at", options: { bold: true, breakLine: true } },
    { text: "Averaging noise alone gives 0.06 / √300 = 3.5 mm/s, close to the 4.4 measured: the optimiser barely prefers any direction. The 0.3 m/s² acceleration limit is a suspect, not a proven cause.", options: { breakLine: true } },
    { text: "Next", options: { bold: true, breakLine: true } },
    { text: "Same goal with Nav2's stock limits (3.0 m/s²), already set on the live node." },
  ], { x, y: 1.35, w, h: 5.45, fontSize: 14, paraSpaceAfter: 5 });
  s.addNotes("Per 10 s window, MPPI's mean output was 4.4, 5.1, 3.8 and 4.4 mm/s, and the same at every later stage. Peak motor PWM during the stall was about 29 of 255. The collision monitor changed state only during recoveries. Source: Session_Handoff_2026-10-01.md, Part 2. The live limit change is lost when Nav2 restarts; the repo file still says 0.3.");
}

// ---------------------------------------------------------------- 21 status
pres.addSection({ title: "Status" });
{
  const s = addContent("Where things stand", "Status");
  const colW = (CW - 0.3) / 2;
  const col = (x, head, color, fill, items) => {
    card(s, x, 1.35, colW, 5.0, fill);
    s.addText(head, { isTextBox: true, x: x + 0.4, y: 1.6, w: colW - 0.8, h: 0.5, fontSize: 21, bold: true, color, margin: 0 });
    s.addText(items.map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < items.length - 1 } })),
      { isTextBox: true, x: x + 0.4, y: 2.3, w: colW - 0.8, h: 3.9, fontSize: 18, color: C.text1, margin: 0, valign: "top", paraSpaceAfter: 12 });
  };
  col(M, "Working, with measurements", C.accent3, "EAF4F0", [
    "Wheel-speed loop on the ESP32 at 100 Hz, with latching safety trips",
    "Manual drive from the phone, with priority over Nav2 and four stacked watchdogs",
    "Wheel odometry: 0.229 m error over a 21.85 m drive",
    "Mapping: returns to the start mark within 6 to 30 mm",
    "Global planner: finds paths from the start mark (1 Oct)",
  ]);
  col(M + colW + 0.3, "Open", C.accent6, "FBEDEA", [
    "No autonomous goal reached yet: MPPI asks for about 4 mm/s",
    "Map coverage: 77 to 85 % of cells unknown, against a 50 % target",
    "No IMU, so heading drift is not corrected",
    "A 90 degree blind arc behind the mast",
    "No hardware E-stop",
  ]);
  s.addNotes("Mapping figures are from 15 Sep (Project_Status.md); odometry from the 3 Sep Stage G drive; MPPI and planner from 1 Oct (Session_Handoff_2026-10-01.md).");
}

// ---------------------------------------------------------------- 22 next steps
{
  const s = addContent("Next steps, and where I would value your view", "Status");
  const x2 = 7.25, w1 = x2 - M - 0.4, w2 = W - M - x2;
  s.addText("Next steps", { isTextBox: true, x: M, y: 1.35, w: w1, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0 });
  const steps = [
    "Re-run the 0.6 m goal with stock MPPI acceleration limits.",
    "If it drives, measure real acceleration on a straight run and set the limits from that.",
    "If it still creeps, check temperature, sampling spread, critic weights and the real loop rate.",
    "Then a ladder of goals: 1 m forward, 1 m sideways, a 90 degree turn, a reverse.",
    "Rear sensing for the blind arc, a rear LiDAR or a ring of ToF sensors.",
  ];
  s.addText(steps.map((t, k) => ({ text: t, options: { bullet: { type: "number" }, breakLine: k < steps.length - 1 } })),
    { isTextBox: true, x: M, y: 1.95, w: w1, h: 4.8, fontSize: 17, color: C.text1, margin: 0, valign: "top", paraSpaceAfter: 12 });
  card(s, x2, 1.35, w2, 5.0);
  s.addText("For an electrical review", { isTextBox: true, x: x2 + 0.35, y: 1.55, w: w2 - 0.7, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0 });
  const qs = [
    [{ text: "E-stop. ", options: { bold: true } }, { text: "A latching normally-closed button in series with the SSR-50DD trigger. Is that the right place to break the circuit?" }],
    [{ text: "ESP32 supply. ", options: { bold: true } }, { text: "Pi USB today. Is VIN from the 5 V buck enough, or should the logic side be isolated?" }],
    [{ text: "Encoder edges. ", options: { bold: true } }, { text: "About 38.5 kHz per channel on the front encoders at the 5.2 rad/s limit, through a BSS138 shifter. Is the rise time comfortable?" }],
    [{ text: "Grounding. ", options: { bold: true } }, { text: "One bus shared by the 24 V drivers and the 3.3 V logic." }],
  ];
  const runs = [];
  qs.forEach((q, k) => { q.forEach((r, j) => runs.push({ text: r.text, options: Object.assign({}, r.options, j === q.length - 1 && k < qs.length - 1 ? { breakLine: true } : {}) })); });
  s.addText(runs, { isTextBox: true, x: x2 + 0.35, y: 2.15, w: w2 - 0.7, h: 4.05, fontSize: 15, color: C.text1, margin: 0, valign: "top", paraSpaceAfter: 12 });
  s.addNotes("Encoder frequency: 5.2 rad/s is 0.83 wheel turns per second; times the 46.566 gear ratio is 38.5 motor turns per second; times 1000 pulses per turn is 38.5 kHz on each of the A and B channels. The rear encoders, at 500 lines, see half that.");
}

// ---------------------------------------------------------------- 23 appendix
pres.addSection({ title: "Appendix" });
{
  const s = addContent("Appendix: every node and topic on one sheet", "Appendix");
  fitImage(s, FIG("h1_whole_system_handout.png"), 1560, 1160, FIGBOX);
  s.addNotes("Dense on purpose: zoom in on the iPad. Every edge here was checked against the source; see docs/flowcharts/QA_2026-10-02.md. The red dashed line is a latent fault: teleop_asym also listens to /joy and could drive the wheels without going through twist_mux if a gamepad were plugged in.");
}

// ---------------------------------------------------------------- write + theme
(async () => {
  await pres.writeFile({ fileName: OUT });
  let applyTheme = null;
  try { ({ applyTheme } = require(process.env.APPLY_THEME || "./apply_theme.js")); } catch (e) { /* optional */ }
  if (applyTheme) { await applyTheme(OUT, THEME); console.log("theme applied"); }
  else console.log("apply_theme.js not found: scheme colours fall back to the Office palette. Set APPLY_THEME.");
  console.log("wrote", OUT);
})();
