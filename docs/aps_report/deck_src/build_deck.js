// Builds the APS seminar deck as a real .pptx, with this project's own
// photographs and generated figures embedded. No stock imagery, no network.
//
//   node build_deck.js
//
// Output: ../NarrowAisleBot_APS_Seminar.pptx

const pptxgen = require('pptxgenjs');
const path = require('path');
const fs = require('fs');

const HERE = __dirname;
const REPORT = path.dirname(HERE);
const REPO = path.dirname(path.dirname(REPORT));
const FIG = (n) => path.join(REPORT, 'figures', n);
const PHOTO = (p) => path.join(REPO, 'docs', 'robot_photos', p);

// Plain palette. The accent is the same blue the report figures use for
// telemetry, so slides and figures read as one system.
const INK = '1A1A1A';
const ACCENT = '1F4E79';
const MUTED = '5A5A5A';
const PAPER = 'FFFFFF';

const TITLE_FONT = 'Cambria';
const BODY_FONT = 'Calibri';

// Slide geometry, inches, on a 13.333 x 7.5 canvas.
const W = 13.333, H = 7.5;
const M = 0.55;                 // outer margin
const TITLE_Y = 0.42;
const BAND_Y = 1.38;            // top of the content band
const BAND_H = 5.5;             // height of the content band
const FIG_X = M;
const FIG_W = 7.55;             // figure column
const COL_X = 8.5;              // text column
const COL_W = W - COL_X - M;    // 4.28

// Places an image inside the figure column, scaled to fit and centred
// vertically in the content band. Returns the caption's y position.
function placeFigure(slide, file, caption) {
  const dim = imageSize(file);
  const ar = dim.w / dim.h;
  let w = FIG_W;
  let h = w / ar;
  const maxH = BAND_H - (caption ? 0.42 : 0);
  if (h > maxH) { h = maxH; w = h * ar; }
  const x = FIG_X + (FIG_W - w) / 2;
  const y = BAND_Y;
  slide.addImage({ path: file, x, y, w, h });
  if (caption) {
    slide.addText(caption, {
      x: FIG_X, y: y + h + 0.1, w: FIG_W, h: 0.3,
      fontFace: BODY_FONT, fontSize: 10, color: MUTED,
      align: 'left', margin: 0, isTextBox: true,
    });
  }
}

// Minimal PNG/JPEG header reader, so the build needs nothing beyond node.
function imageSize(file) {
  const b = fs.readFileSync(file);
  if (b[0] === 0x89 && b[1] === 0x50) {           // PNG
    return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  }
  if (b[0] === 0xff && b[1] === 0xd8) {           // JPEG
    let i = 2;
    while (i < b.length) {
      if (b[i] !== 0xff) { i++; continue; }
      const marker = b[i + 1];
      if (marker >= 0xc0 && marker <= 0xcf &&
          marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc) {
        return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) };
      }
      i += 2 + b.readUInt16BE(i + 2);
    }
  }
  throw new Error('cannot read dimensions: ' + file);
}

function contentSlide(pres, s) {
  const slide = pres.addSlide();
  slide.background = { color: PAPER };

  slide.addText(s.title, {
    x: M, y: TITLE_Y, w: W - 2 * M, h: 0.8,
    fontFace: TITLE_FONT, fontSize: 32, bold: true, color: INK,
    align: 'left', valign: 'middle', margin: 0, isTextBox: true,
  });

  if (s.figure) placeFigure(slide, FIG(s.figure), s.caption);

  let y = BAND_Y + 0.05;
  for (const card of s.cards) {
    slide.addText(card.head, {
      x: COL_X, y, w: COL_W, h: 0.34,
      fontFace: BODY_FONT, fontSize: 15, bold: true, color: ACCENT,
      align: 'left', valign: 'top', margin: 0, isTextBox: true,
    });
    slide.addText(card.body, {
      x: COL_X, y: y + 0.38, w: COL_W, h: 1.9,
      fontFace: BODY_FONT, fontSize: 13.5, color: INK,
      align: 'left', valign: 'top', lineSpacingMultiple: 1.15,
      margin: 0, isTextBox: true,
    });
    y += 2.45;
  }

  slide.addText(String(s.n), {
    x: W - M - 0.6, y: H - 0.52, w: 0.6, h: 0.28,
    fontFace: BODY_FONT, fontSize: 10, color: MUTED,
    align: 'right', margin: 0, isTextBox: true,
  });

  slide.addNotes(s.notes);
  return slide;
}

const SLIDES = [
  {
    n: 2,
    title: 'The geometry, and why it is asymmetric',
    figure: 'fig01_asymmetric_geometry.png',
    caption: 'Plan view to scale, and the yaw coefficient each wheel earns from its own position.',
    cards: [
      { head: 'Wheels are not at the corners',
        body: 'A conventional mecanum base puts all four wheels the same distance from the centre. This one does not. The outer pair sits at 403 mm, the inner pair at 333 mm, with a half-track of 158 mm.' },
      { head: 'Each wheel earns its own term',
        body: 'That 70 mm offset gives the outer wheels a yaw coefficient of 0.561 m and the inner wheels 0.491 m, so the inverse kinematics cannot be the textbook one. Footprint 1.00 x 0.36 m, mass 45.5 kg, wheel radius 76.2 mm.' },
    ],
    notes: 'The aisle sets the width, so the wheels could not go where the textbook puts them. Front-right and rear-left ended up 403 mm from centre, front-left and rear-right 333 mm.\n\nThe consequence is that every wheel has a different lever arm on yaw, so the standard mecanum matrix does not apply and had to be re-derived for this chassis.',
  },
  {
    n: 3,
    title: 'What was built',
    figure: 'fig02_system_architecture.png',
    caption: 'Three layers, each link annotated with its rate and transport.',
    cards: [
      { head: 'Three processors, one rule',
        body: 'The split is by real-time capability, not by software preference. A Raspberry Pi 5 runs ROS 2 for planning and perception. An ESP32 runs the 100 Hz velocity loop with hardware quadrature decoding. An Arduino Mega drives the cargo arm and the staged UV-C tubes.' },
      { head: 'Sensing and command path',
        body: 'A YDLIDAR X4 Pro feeds SLAM. Nav2 plans, MPPI tracks, and a priority multiplexer keeps the manual joystick above the autonomous stream, so a person can always take the robot back.' },
    ],
    notes: 'Nothing here was chosen for novelty. The ESP32 exists because a 100 Hz deterministic loop cannot live on a Linux scheduler; the Arduino exists because the arm and the lamps need their own timing and must survive a Pi reboot.\n\nThe multiplexer is a safety decision: manual command always outranks autonomous command.',
  },
  {
    n: 4,
    title: 'Control, in air and on the floor',
    figure: 'fig08_v30_tracking.png',
    caption: 'Closed-loop velocity tracking, wheels free, 1816 samples.',
    cards: [
      { head: 'Open loop failed measurably',
        body: 'At equal duty cycle, one diagonal pair ran 11 to 13 percent faster than the other. That mismatch is what produced the strafing stutter. It was never a tuning problem; it was an unmeasured plant.' },
      { head: 'Closed loop, then measured',
        body: 'Tracking error is 1.2 to 1.4 percent of peak with the wheels free, and 3.4 to 4.0 percent under the real chassis weight. Not one run contained a saturated sample, so the loop still has headroom.' },
    ],
    notes: 'The stutter was visible long before it was explained. Characterising the four motors open-loop at a fixed PWM turned a driving complaint into a number: an 11 to 13 percent split inside one diagonal pair.\n\nThe loop is a 100 Hz PID with two feedforward terms, one proportional to commanded speed and one static term for stiction. Zero saturation matters because it means the errors quoted are the controller’s, not the motor’s ceiling.',
  },
  {
    n: 5,
    title: 'A prediction, then a test',
    figure: 'fig10_ground_load.png',
    caption: 'Steady-state PWM per rad/s, unloaded against loaded, computed from the raw logs.',
    cards: [
      { head: 'Written down beforehand',
        body: 'Before any floor test existed, the calibration notes recorded that ground contact should raise feedforward demand by 10 to 30 percent. The number was committed in advance, not fitted afterwards.' },
      { head: 'What the floor returned',
        body: 'Mean increase 24 percent. Front-right 22.5, front-left 23.6, rear-right 30.3, rear-left 21.0. All four sit inside the predicted band.' },
    ],
    notes: 'This is the one place in the year where a number was written down before the experiment that could refute it, so it is worth a slide of its own.\n\nThe quantity is steady-state PWM per rad/s: how much drive each motor needs to hold a given wheel speed. Unloaded against loaded, the same four motors, the same firmware.\n\nIf a reviewer asks why 30.3 percent on the rear right is not a concern: it is inside the band, and the rear right also carries the mast.',
  },
  {
    n: 6,
    title: 'The fault that defined the year',
    figure: 'fig06_encoder_cpr_fault.png',
    caption: 'The failure mechanism, and the bench cross-check that detected it.',
    cards: [
      { head: 'One constant, two encoders',
        body: 'A single counts-per-revolution constant was applied to two different encoder types. The front wheels reported twice their true speed, so the controller obediently ran them at half the commanded velocity.' },
      { head: 'Why it stayed hidden',
        body: 'There was no error and no warning. Every tracking plot looked clean, because the loop was closing correctly on the wrong number. It surfaced only when front and rear were compared on one command.' },
    ],
    notes: 'This is the fault class the year kept returning to: a silent unit or convention error that every self-check passes.\n\nThe controller was doing exactly what it was told. The instrumentation was lying, so the diagnostics were confirming the lie. That is why the audit rule became measure the input before tuning the estimator.\n\nSame family: the shared axis convention, the mirrored scan, the frame published in the wrong rotation.',
  },
  {
    n: 7,
    title: 'Perception: what the robot cannot see',
    figure: 'fig12_self_occlusion.png',
    caption: 'The rear cone, re-measured in the corrected frame at five headings.',
    cards: [
      { head: 'The mast is in the way',
        body: 'The rear mast blocks a 90 degree wedge of the scan. It was re-measured at five independent headings, and it does not move with the robot’s heading. It is structural, not incidental.' },
      { head: 'A phantom welded to the base',
        body: 'The blocked returns land beyond the sensor minimum range, so they read as a genuine hit on every sweep. 107 of 430 beams are now masked as invalid before the scan reaches SLAM.' },
    ],
    notes: 'The distinction that matters: a blind spot inside the minimum range is discarded automatically. This one is not. It is far enough out to look like a real wall that follows the robot everywhere.\n\nFive headings were used precisely to separate a chassis-fixed obstruction from something in the room. The wedge stayed put.\n\nMasking is a mitigation, not a fix; the honest version is that a quarter of the scan is gone.',
  },
  {
    n: 8,
    title: 'The symptom: maps that would not close',
    figure: 'fig16_correction_traces.png',
    caption: 'Three drives, same robot, same deployed configuration, same week.',
    cards: [
      { head: 'Every map folded',
        body: 'Return to the same physical mark came out at 0.577 m, 0.085 m and 0.209 m: a spread of 6.8 times on a task meant to repeat.' },
      { head: 'The base was not at fault',
        body: 'Wheel odometry closed under 3 cm on all three of those drives. Whatever folded the map was being added above the odometry, not inside it. That narrowed the search to one layer.' },
    ],
    notes: 'A 6.8 times spread is the point, not the worst value. An estimator that fails consistently can be corrected; one that fails differently every run cannot be trusted at all.\n\nThe odometry cross-check is what made this tractable. If the wheels close to 3 cm and the map does not, the fault is not mechanical and not in the drive layer.',
  },
  {
    n: 9,
    title: 'The result that decided the diagnosis',
    figure: 'fig18_invariance.png',
    caption: 'The same tight arc driven three times on three parameter sets.',
    cards: [
      { head: 'Three parameter sets',
        body: 'Cumulative pose correction: 2.80 m, 2.85 m, 2.86 m. Every scan-matching lever available was pulled between them. The total moved by 2 percent.' },
      { head: 'What invariance means',
        body: 'Tuning moved where the error appeared, never how much of it there was. A quantity that will not move when every lever is pulled is not set by those levers. So the search moved upstream, to the sensor.' },
    ],
    notes: 'This is the strongest single result of the year, and the one to slow down on.\n\nThe experiment was designed to be refutable: if the correction total had moved with tuning, the problem would have been tuning. It did not move. Two percent across three parameter sets is inside run-to-run noise.\n\nThat converts an open-ended tuning exercise into a closed argument about where the error enters, and it is what justified spending the following weeks measuring the LiDAR instead of the algorithm.',
  },
  {
    n: 10,
    title: 'Measuring the input, not the algorithm',
    figure: 'fig14_lidar_placement.png',
    caption: 'Placement trials: three mount positions on one standardised metric.',
    cards: [
      { head: 'First look at the scan',
        body: 'After a year of tuning the estimator, nobody had measured what it was being fed. With the robot stationary, 74.8 to 78 percent of rays flip between valid and invalid from one scan to the next.' },
      { head: 'A different cloud each sweep',
        body: 'Only 47.4 percent of beams are valid at any instant. The matcher is asked to align two clouds that do not share most of their points. The unit is a triangulation scanner meeting its own specification; the specification is not adequate here.' },
    ],
    notes: 'This is the measurement the invariance result pointed to, and it took one afternoon once the question was right.\n\nThe robot is not moving. Nothing in the room is moving. Three quarters of the beams still change state between consecutive sweeps.\n\nBe careful with the conclusion: the sensor is not broken. It is a low-cost triangulation unit performing within its datasheet. The mistake was expecting datasheet behaviour to be sufficient for pose-graph SLAM in a corridor.',
  },
  {
    n: 11,
    title: 'Choosing between two measured estimators',
    figure: 'fig19_stage_g.png',
    caption: 'The mechanism removed, and why disabling it is a selection rather than a workaround.',
    cards: [
      { head: 'Measured, then chosen',
        body: 'Over one 21.85 m drive, wheel odometry alone closed the loop to 0.229 m; odometry corrected by SLAM closed to 0.706 m. The correction was making the estimate worse, so it was removed.' },
      { head: 'What removal produced',
        body: 'Zero corrections across 698 seconds and 18.5 m, on two different routes. Photogrammetry against the floor grout shows the reported heading drift is largely estimator error rather than wheel slip.' },
    ],
    notes: 'Disabling the sequential scan matcher is not a workaround dressed up as a result. It is a selection between two estimators that were both measured on the same drive, and the worse one was dropped.\n\nThe photogrammetry cross-check matters because it rules out the obvious objection: that the wheels were slipping and odometry only looked better. Tile grout gives an independent ground truth.\n\nWhat this does not give is loop closure. Without a scan matcher there is no correction at all, which is fine for a straight run and not fine for a full map.',
  },
  {
    n: 12,
    title: 'Autonomous navigation: where it stands',
    figure: 'fig21_autonomy_gates.png',
    caption: 'Seven acceptance gates, written before the work and scored against it.',
    cards: [
      { head: 'What has run',
        body: 'The first autonomous forward-and-return round trip ran on 14 August. Operator-tapped goals inside a live mapping session were reached in 21 to 26 seconds, with the full Nav2 stack in the loop.' },
      { head: 'What is still blocked',
        body: 'DWB was replaced with MPPI on a source-level argument: its rotation-to-goal test compares translation against exact zero, so rotation-only goals fail by construction. Navigation on a saved map waits on a commissioning map that does not yet exist.' },
    ],
    notes: 'Be precise about the claim: goals were reached inside a live mapping session, not on a saved map. That is a real result and a limited one.\n\nThe DWB change is worth a sentence because it was decided by reading the controller’s source rather than by tuning against it. A bit-exact comparison against zero translation means a rotation-only goal can never satisfy the test.\n\nThe blocker is not code. It is that no map good enough to localise against has been produced yet, which is exactly what the previous four slides were about.',
  },
  {
    n: 13,
    title: 'An honest audit of the stack',
    figure: 'fig22_layer_audit.png',
    caption: 'The layer-by-layer audit. The break is at exactly one component.',
    cards: [
      { head: 'Where the line falls',
        body: 'Everything below the LiDAR is measured and reproducible. Everything from the LiDAR up is broken, starved of CPU, or has never been run. 82 defects were root-caused this year across eight categories.' },
      { head: 'Rules that came out of it',
        body: 'A value in the repository is not a value on the robot. Never fix an axis complaint in the display. Measure the input before tuning the estimator. Write the prediction down before running the test.' },
    ],
    notes: 'The point of grading the stack layer by layer is that the break is at exactly one component, not spread across the design. That is a good position to be in going into year two.\n\nEvery claim in the report carries an evidence grade: measured, single observation, hypothesis, retracted, or never run. Several earlier conclusions are marked retracted, and they are left in rather than quietly removed.\n\nThe four rules are not slogans; each one is the generalisation of a specific defect that cost weeks.',
  },
  {
    n: 14,
    title: 'Parallel project: UVGI instrumentation',
    figure: 'fig26_iot_architecture.png',
    caption: 'Five sensors, three concurrent wireless channels, two independent control paths.',
    cards: [
      { head: 'What it does',
        body: 'Instrumentation and control for a UV-C air-disinfection unit, under a departmental TIH-IoT activity. Five sensors, three concurrent wireless channels, two control paths, four zones, and no cloud dependency.' },
      { head: 'Reported with its limits',
        body: 'The UV channel is measured but sits in no control or alert path. The trigger signal has no causal relationship to pathogen load; the correction is a carbon-dioxide-derived occupancy proxy.' },
    ],
    notes: 'This is the second project, not a second thesis. Keep it to two minutes.\n\nThe engineering that is worth showing is the redundancy: three wireless channels running concurrently and two independent control paths, so a network failure does not leave the lamps in an unknown state.\n\nIt is presented with the same self-audit as the robot, which is why the limitations are on the slide rather than in the questions. The honest position is that the current trigger is an occupancy proxy, and dose-based control is year four.',
  },
  {
    n: 15,
    title: 'Research gaps, and the plan for years 2 to 4',
    figure: 'fig28_roadmap.png',
    caption: 'The five-phase roadmap and current standing.',
    cards: [
      { head: 'Two gaps worth the time',
        body: 'The asymmetry has never been compared against a matched symmetric baseline, so its cost and benefit are both unquantified. And what sensing corridor-width localisation actually requires is now a measured question rather than an assumption.' },
      { head: 'The sequence from here',
        body: 'Year 2: inertial sensing, a commissioning map, localisation on a saved map, a sensor comparison. Year 3: the geometry comparison, per-wheel slip, control under cargo load. Year 4: dose-based UV-C control, whole-system evaluation, writing up.' },
    ],
    notes: 'The first gap is the one that justifies the platform: nobody has shown what a non-collinear mecanum base costs or buys against a symmetric one on the same task, and this robot is the instrument for asking that.\n\nThe second gap only became a research question because of this year’s measurements. Before, sensor choice was an assumption; now it is a quantity with a number attached.\n\nYear two is deliberately unglamorous. An inertial sensor and one good commissioning map unblock everything above them.',
  },
];

function build() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE';            // must precede addSlide
  pres.author = 'Aritra Das';
  pres.company = 'Department of Biosciences and Bioengineering, IIT Bombay';
  pres.title = 'NarrowAisleBot — Annual Progress Seminar, Year 1';

  // --- 1. Title -----------------------------------------------------------
  const t = pres.addSlide();
  t.background = { color: PAPER };
  t.addText('Annual Progress Seminar · Year 1', {
    x: M, y: 1.15, w: 7.4, h: 0.4,
    fontFace: BODY_FONT, fontSize: 16, bold: true, color: ACCENT,
    charSpacing: 1, align: 'left', margin: 0, isTextBox: true,
  });
  t.addText('NarrowAisleBot', {
    x: M, y: 1.75, w: 7.4, h: 1.15,
    fontFace: TITLE_FONT, fontSize: 60, bold: true, color: INK,
    align: 'left', valign: 'middle', margin: 0, isTextBox: true,
  });
  t.addText('An asymmetric mecanum platform for autonomous operation in narrow aisles', {
    x: M, y: 3.0, w: 7.0, h: 0.9,
    fontFace: BODY_FONT, fontSize: 19, color: MUTED,
    align: 'left', valign: 'top', lineSpacingMultiple: 1.2,
    margin: 0, isTextBox: true,
  });
  t.addText([
    { text: 'Aritra Das', options: { bold: true, breakLine: true } },
    { text: 'Roll 25D0074', options: { breakLine: true } },
    { text: 'Department of Biosciences and Bioengineering, IIT Bombay', options: { breakLine: true } },
    { text: 'Supervisor: Prof. Ambarish Kunwar', options: { breakLine: true } },
    { text: 'September 2026', options: {} },
  ], {
    x: M, y: 4.75, w: 7.0, h: 1.7,
    fontFace: BODY_FONT, fontSize: 14, color: INK,
    align: 'left', valign: 'top', lineSpacingMultiple: 1.25,
    margin: 0, isTextBox: true,
  });

  const photo = PHOTO('2026-08-11_occlusion_trial_cw/cw_000.jpg');
  const pd = imageSize(photo);
  const ph = 6.4, pw = ph * (pd.w / pd.h);
  t.addImage({ path: photo, x: W - M - pw, y: (H - ph) / 2, w: pw, h: ph });
  t.addNotes('An omnidirectional cargo platform for narrow aisles, built and instrumented over the first year. This talk covers the electronics, firmware, software and mechanical work; the biological application sits outside it.\n\nThe photograph is the platform as it stood on 11 August: long chassis, four mecanum wheels at unequal radii, the mast, the LiDAR on the battery, the Pi and the motor driver.');

  // --- 2..15 Content ------------------------------------------------------
  for (const s of SLIDES) contentSlide(pres, s);

  // --- 16. Close ----------------------------------------------------------
  const c = pres.addSlide();
  c.background = { color: PAPER };
  c.addText('Thank you', {
    x: M, y: 0.7, w: 7.4, h: 1.2,
    fontFace: TITLE_FONT, fontSize: 54, bold: true, color: INK,
    align: 'left', valign: 'middle', margin: 0, isTextBox: true,
  });
  c.addText('Questions', {
    x: M, y: 1.95, w: 7.4, h: 0.5,
    fontFace: BODY_FONT, fontSize: 19, color: MUTED,
    align: 'left', margin: 0, isTextBox: true,
  });
  const facts = [
    ['Supervisor', 'Prof. Ambarish Kunwar'],
    ['Department', 'Biosciences and Bioengineering, IIT Bombay'],
    ['Roll number', '25D0074'],
  ];
  let fy = 3.35;
  for (const [k, v] of facts) {
    c.addText(k, {
      x: M, y: fy, w: 2.1, h: 0.32,
      fontFace: BODY_FONT, fontSize: 12, bold: true, color: ACCENT,
      align: 'left', margin: 0, isTextBox: true,
    });
    c.addText(v, {
      x: M + 2.2, y: fy, w: 4.6, h: 0.32,
      fontFace: BODY_FONT, fontSize: 14, color: INK,
      align: 'left', margin: 0, isTextBox: true,
    });
    fy += 0.62;
  }
  placeFigureOn(c, FIG('fig25_gantt.png'));
  c.addNotes('Questions.\n\nLikely ones and where the answer is:\n- Why not just buy a better LiDAR? Cost, and the sensor comparison is year two work item four.\n- Is disabling the scan matcher not giving up on SLAM? No: two estimators were measured on the same drive and the worse one was dropped. Slide 11.\n- Why an asymmetric base at all? The aisle width. And quantifying what it costs is research gap one.\n- How do you know odometry is not just hiding slip? Photogrammetry against the floor grout. Slide 11.\n\nThe timeline on the right is both projects reconstructed from 146 commits, if a date is queried.');

  const out = path.join(REPORT, 'NarrowAisleBot_APS_Seminar.pptx');
  return pres.writeFile({ fileName: out }).then(() => {
    console.log('wrote ' + out);
  });
}

// The closing slide carries the timeline in its right half rather than the
// standard figure column.
function placeFigureOn(slide, file) {
  const d = imageSize(file);
  const ar = d.w / d.h;
  const w = 5.1, h = w / ar;
  slide.addImage({ path: file, x: W - M - w, y: (H - h) / 2, w, h });
  slide.addText('Both projects on one timeline, reconstructed from 146 commits.', {
    x: W - M - w, y: (H - h) / 2 + h + 0.1, w, h: 0.3,
    fontFace: BODY_FONT, fontSize: 10, color: MUTED,
    align: 'left', margin: 0, isTextBox: true,
  });
}

build().catch((e) => { console.error(e); process.exit(1); });
