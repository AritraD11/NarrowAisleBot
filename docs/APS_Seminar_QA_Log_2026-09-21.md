# Seminar prep — Q&A log, 21 Sep 2026

A conversational walkthrough of the APS report and the seminar deck, done the
day before the 23 Sep seminar to pressure-test understanding of the PID story
and the SLAM story before the review. Nothing in this file is a new
experimental result except where explicitly marked in §3 — it's a digest of
questions asked and answered against `APS_Report_Draft_v2.md`,
`PID_Calibration.md`, and two short phone-camera clips of the robot supplied
in the conversation. Treat it as a study aid, not a source of record; where it
disagrees with the report or the journal, they win.

---

## 1. PID and feedforward — how the numbers were actually chosen

Four gains ship in `aislebot_esp32.ino`: `Kff`, `Kstat`, `Kp`, `Ki`, `Kd`, and
they weren't picked independently — three of the five chain off one another.

- **Feedforward** (`Kff`, `Kstat`) comes first, fit from three separate in-air
  bench campaigns to `pwm = Kff·ω + Kstat·sgn(ω)`. `Kff = 38` is the
  viscous (speed-proportional) term; `Kstat = 8` is the constant breakaway
  push needed to beat static friction from a standstill, independent of
  target speed. Per-wheel `Kff` (37.3/38.4/38.3/38.0) comes from scaling the
  shared value by each motor's measured speed relative to the four-motor mean
  in one test — not four separate fits. The old 19% per-motor spread that
  used to justify per-motor compensation was a measurement artefact (the
  front/rear encoder-CPR bug), not a real mechanical difference; on the
  corrected signal path all four motors sit inside a ~3% band.
- **`K` (plant DC gain)** falls straight out of the fit: `K = 1/Kff = 0.0263
  rad/s per PWM`.
- **`Ki = 1/(K·λ)`**, direct-synthesis tuning, `λ = 0.15 s` chosen
  conservatively. `= 253`, rounded to 250. The old value of 30 meant a 0.1
  rad/s error only moved output 3 PWM/s, closing a realistic gap in >3.7 s;
  at 250 the same gap closes in 0.4 s.
- **`Kp = τ·Ki`** theoretically, needing the plant's mechanical time constant
  `τ`, which stayed unmeasured for a long time (assumed 0.18 s). A dedicated
  bench test on 14 Sep (`nab_pid_logger.py --test plant`, wheels in the air,
  open-loop PWM steps, PID bypassed) measured `τ ≈ 0.09 s`, half the assumed
  value. Plugged into the formula that gives `Kp = 22` or `26` depending on
  which measurement of τ is used. A closed-loop sweep of both candidates
  against the shipped `Kp = 45`, across four setpoints and all four motors
  (16 rows), found the shipped value won on overshoot in all 16, by 43–54%.
  Reasoned explanation: the two-term feedforward already supplies most of the
  step command, so `Kp`'s real job here is damping that transient, not
  cancelling an uncompensated plant pole the way the formula assumes. `Kp`
  stayed at 45, confirmed rather than changed.
- **`Kd = 0.5`**, small by design — with a well-matched PI on a near-first-order
  plant, derivative action theoretically contributes little beyond damping
  unmodelled lag (driver delay, gearbox compliance). It also acts on
  measurement, not error, to avoid derivative kick from the Pi's stepped
  setpoints.

**Same PID for all four wheels, different asymmetric geometry — not a
contradiction.** The asymmetry lives entirely in the inverse kinematics
upstream, which hands each wheel a different target speed. Once that target
exists, each wheel's loop has one job — track its own number — and that job
is identical across wheels because the four motors are, once measured
correctly, nearly identical. If they weren't, one shared gain set wouldn't be
enough.

**Load caveat, explicitly open.** Ground-load correction to feedforward is
not settled: predicted 10–30%, the first floor run gave a mean of 24% (inside
the band), but two later runs on the same day gave 14% and 3%. No adaptive
control exists yet (Gap 6). It's literature-reviewed as Year 3 work
(Lin & Shih 2013; Cao et al. 2022), gated on an explicit decision rule:
advance to something adaptive only if the fixed-gain controller visibly
underperforms under real cargo load, not pre-emptively.

---

## 2. Which formulas are original versus standard

Two pieces of this project's own math, not borrowed:

1. **The slip/yaw residual (§4.1)**, falling out of an audit of the
   asymmetric IK matrix: rows 1&4 share `(u+v)`, rows 2&3 share `(u−v)`, so
   each diagonal wheel pair independently measures yaw on its own lever arm.
   `s = ω_FR + 1.142656·ω_FL − 1.142656·ω_RR − ω_RL` (1.142656 = K_o/K_i for
   this robot's own geometry). Doesn't exist in the cited kinematics paper,
   and can't exist on a symmetric platform (K_o = K_i collapses it to
   nothing). Still an instrument, not yet a result — Gap 3/Year 3 is the
   experiment that would use it on real slip data.
2. **The four-model phantom-yaw diagnostic (§4.6.4)** — testing whether
   estimator error scales with distance, time, rotation, or a flat constant,
   scored by worst/best fit ratio across three runs. An investigative method
   built for this specific question, not lifted from a paper.

Everything else — the asymmetric IK itself [1], the two-term feedforward
model, direct-synthesis PI tuning, point-to-line ICP [6], graph-based SLAM
[7], Bayesian log-odds occupancy [8] — is standard, cited or textbook
methodology, correctly chosen and then calibrated on this hardware, not
reinvented.

---

## 3. Pose estimation on vs off — including a first-hand video check

Two phone-camera clips of the same circular test route were reviewed frame by
frame in this conversation, one with SLAM scan-matching off, one with it on.
**This is informal confirmation, not a logged/analysed run** — no CSV, no
`run_analyzer.py` pass — but the dashboard's own on-screen numbers matched
the report's mechanism closely enough to be worth recording.

- **Matching off**: the dashboard's `DRIFT` field (its label for the
  map↔odom gap) read `0.000 m` in every frame checked, the whole way through.
  Ended the drive back at (−0.006, 0.003) m, essentially the start mark.
- **Matching on**: `DRIFT` swung between roughly 0.5 and 1.0 m over the same
  drive, never converging, shown in red on the dashboard's own display. The
  built map showed a dense streaked "starburst" pattern, the same walls
  redrawn repeatedly in different places — a visual match for the doubled-wall
  defect (§4.6.5) rather than a formally re-measured instance of it.

**On why point-and-go still worked with matching on despite the bad map**:
the robot's live pose and a freshly tapped goal both live inside the same
moving, corrected map frame, so a correction event drags both together and
the *relative* vector between them survives even while the *absolute* map
underneath is being smeared. This is the report's own distinction, stated
directly in §4.7: "commissioning quality is a mapping problem, operating
quality is a localisation problem, and the project had been trying to solve
the second by tuning the first."

**Clarified in the conversation**: "pose estimation" in the broad sense
(some running x/y/heading belief) was never disabled — it runs continuously
off wheel odometry regardless of the matching setting. What got disabled is
one specific correction layer on top of it (the SLAM front end), because it
was measured to make that base estimate worse, not better, on this hardware.

---

## 4. Why no map has ever been accepted — the full chain (§4.5–§4.6.6)

Answering "why couldn't we build a map" honestly needs the whole stack, not
one cause:

1. **The sensor itself is noisy scan-to-scan.** The X4 Pro, a triangulation
   scanner, flips 74.8–78% of rays between valid/invalid between consecutive
   scans even with the robot stationary; only 47.4% valid at any instant.
   It's performing to its own published spec (2 cm absolute <1 m, 3.5% of
   range 1–6 m, **no spec at all above 6 m**) — the spec just isn't tight
   enough for the task, and that specification was mis-quoted for months
   before being corrected in this report.
2. **The front end reacts to that noise on a fixed schedule, not on real
   disagreement.** Cumulative correction measured 2.80/2.85/2.86 m across
   three different parameter sets — invariant to within 2%, which is what
   proved this isn't a tuning problem. The 17 corrections in the Stage G A/B
   test fired at a mean interval of 0.183 m of travel, ±1 cm — a metronome,
   not a response — which is also why no loop closure has ever been observed
   to fire on this robot: a real closure would show up off-cadence, and none
   of the 17 did.
3. **Self-occlusion removes a real quarter of every scan.** A 90° wedge
   behind the robot, 107 of 430 beams, permanently masked because an
   unmasked mast reads as a phantom obstacle welded to the chassis in every
   frame.
4. **The commissioning procedure adopted to dodge #3 became the dominant
   cause of poor coverage.** "Rotate at every corner" was chosen specifically
   to sweep the blind wedge, but rotation in place adds no pose-graph node
   and no map cell: two full turns, 714° over 642 s, produced 43 occupied
   cells. Turning while translating instead reached 88% of a perimeter
   drive's coverage in 18% of its time. This is the direct explanation for
   why the "unknown cells" acceptance criterion has never once passed —
   72.6–84.6% unknown across seven drives, three LiDAR quality gates, and the
   matching on/off A/B, unmoved by any of them.
5. **Early tuning sessions were spent on a geometrically degenerate test
   route.** A tight circle at 5 m range makes 1° of heading error
   indistinguishable from 8.7 cm of translation, so the matcher resolves the
   ambiguity onto heading every time — predicted and then confirmed exactly.
6. **A separate, still-open odometry bug sits underneath all of it.**
   "Phantom yaw" — heading drift the odometry fabricates that the floor
   (photogrammetry ground truth) says never physically happened, measured at
   3.85°/4.49° against 0.03°/0.00° on two runs. Even the clean, matching-off
   baseline isn't drift-proof over a long run; it's just not being actively
   corrupted on top of that residual drift.

**Bottom line, stated plainly because it matters for tomorrow's questions:**
matching-off is a real fix for causes #2, and by extension #5, but causes #3,
#4 and #6 are independent of the matching setting entirely. No map — off or
on — has ever cleared all four acceptance criteria (not folded, doubled walls
<1.0%, unknown <50%, return to mark <0.15 m) at once. The cleanest result to
date, 6.4 mm closure with matching off, was on a short tight circle, flagged
in the report itself as an easier case; the bigger out-and-back route that
would actually test this under the corrected (turn-while-translating)
procedure is logged as not yet run.

---

## 5. Why localisation (AMCL) has never run — two separate blockers

1. **No accepted map exists to localise against** (§4 above) — still open,
   and the practical blocker today.
2. **A launch-topology bug, already fixed.** The file that starts the LiDAR
   also started SLAM, and the localisation launch file refused to run
   alongside SLAM while starting no sensor source of its own — so even with a
   perfect map, localisation would have activated and waited for a scan
   forever. Sensor bringup is now split into its own file, shared by both
   launch paths, fixed in September.

Because of (2), localisation has never executed even once, good map or bad,
which means there's genuine uncertainty about what else might surface the
first time it actually runs — one specific example already flagged and
untested: whether `amcl.robot_model_type` in `nav2_params.yaml` needs the
Jazzy pluginlib class name rather than the pre-Galactic bare string it
currently holds.

---

*Digest only — full technical detail, numbers and citations live in
`APS_Report_Draft_v2.md`, `PID_Calibration.md`, and `Research_Journal.md`.*
