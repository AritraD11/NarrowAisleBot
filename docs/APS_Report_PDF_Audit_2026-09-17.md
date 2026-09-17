# Audit of `APS_Report_Final.pdf`, 17 Sep 2026

Six days before the seminar (23 Sep 2026, 14:30). The file audited is the
37-page PDF supplied by the operator, produced by Microsoft Word LTSC on
17 Sep 2026 at 18:41 IST, author `aritradas`. Every quantitative claim in it
was traced back to a file in this repository, and where a raw log existed the
number was recomputed rather than read off a document that quotes it.

Checked against all five branches: `main`, `claude/amr-and-slam` (contained in
`main`), `claude/aps-report-draft-2nywbq` (contained in `main`), this branch,
and `claude/determined-feynman-rw4tfh` (9 commits ahead of `main`, unmerged).

---

## 0. What the PDF is, relative to what is in the repository

The PDF is not a conversion of either Markdown draft. It is a restructured
document written to the institute's APS format: seven chapters, an
introduction and literature review per strand, five objectives, 14 figures and
37 numbered references. `APS_Report_Draft_v2.md` has ten sections, three
objectives, 22 figures and 26 references. No branch carries the PDF's text, so
the repository cannot be used to diff it. It can only be used to check it.

**The figures in the PDF come from `claude/determined-feynman-rw4tfh`, which is
not merged.** This was established from the artefacts themselves, not inferred:

| Figure in the PDF | State it is in | What `main` still produces |
|---|---|---|
| Fig 5, monitoring architecture | reads "Four sensor packages" | reads "five sensors" |
| Fig 8, closed-loop tracking | three panels, with the step expanded | two panels, no step panel |
| Fig 9, ground load | "Three of the four motors fall inside that band" | "all four motors land inside that band" |
| Fig 13, commissioning maps | the three 15 Sep maps | the 31 Aug / 1 Sep drives |
| Fig 14, layer audit | rebuilt against current data | the older layout |
| Fig 3, electronics | portrait relayout, `Kff` unit label fixed | landscape, stale label |

Two figures in the PDF (Figure 10, endpoint closure, and the three-drive
trajectory panel) exist in no branch at all. They were made outside the repo.

Consequence: regenerating figures from `main` produces a different report.
Merge `claude/determined-feynman-rw4tfh` before anyone runs
`for f in figure_src/f_*.py; do python3 "$f"; done` again.

---

## 1. Errors to fix before submission

Ordered by how much damage each does if a committee member finds it first.

### 1.1 Section 6.4 states the photogrammetry result backwards

The report says:

> On two structurally different routes the robot finished 3.85° and 4.49° away
> from its commanded heading, while wheel odometry, the published estimate and
> the SLAM pose all agreed with one another to within a few hundredths of a
> degree.

That is the opposite of what was measured. `APS_Report_Draft_v2.md` §4.6.4 is
explicit: "The robot physically returned to its starting heading every time.
The estimator did not." The floor read −0.03° and +0.00°. The 3.85° and 4.49°
are what the estimators reported and the robot never did. The whole value of
that measurement is that it moves several degrees of heading error out of the
physics and into the estimator, where calibration can reach it.

The "few hundredths of a degree" is also carrying the wrong job. It is the
photogrammetric residual against the floor. The three-way agreement between
wheels, odometry and SLAM (0.002 m, within 0.01°) is a separate result, from
run `_154615` on 15 Sep, recorded in `docs/evidence/gap3_slip_residual/`.

Section 6.6 and Chapter 7 both state it the right way round ("Heading errors of
3.85° and 4.49° were invisible to every instrument on the robot, because all of
them derive from the same wheel measurements"). So §6.4 contradicts the rest of
the report as well as the evidence.

Suggested replacement for the first sentence: *On two structurally different
routes the odometry, the published estimate and the SLAM pose all reported
3.85° and 4.49° of heading change that the floor says did not happen, agreeing
with one another while all three disagreed with the tile grout.*

### 1.2 The encoder count in §5.2 is wrong, and Figure 3 says so on the same page

> Each drive motor produces 93,132 encoder counts per revolution at the wheel

The front pair does not. `aislebot_esp32.ino` lines 139 to 148:

```
Front  GTK08      : 1000 PPR x 4 (full quad) x 46.566 = 186 264
Rear   RMCS-2086  :  500 lines x 4             x 46.566 =  93 132
```

Verified on the bench at a 2.0 to 2.1x front/rear raw-count ratio, and the
whole point of §4.3.1 of the v2 draft, which the PDF does not carry.

Everything downstream shifts. At rated speed the four motors emit 558,792
counted edges per second, not 372,528, which leaves about 28.6 ATmega2560
cycles per edge rather than 43. The argument for the ESP32 gets stronger, not
weaker. Figure 3's own caption already says "The front and rear motors carry
encoders of different resolution and different wiring convention", so as it
stands the page contradicts itself.

The specification table in §5.1 should carry the split too. It currently lists
the motors and no encoders.

### 1.3 The ground-load percentages in §6.1 disagree with Figure 9

Text: 22.4, 23.6, 30.3 and 21.2. Figure 9, on the facing page: +22.5, +23.6,
+30.3, +21.0. Recomputed here from `run_20260805_140048.csv` (air) against
`run_20260806_152810.csv` (floor), by the generator's own median-of-steady-state
method: **22.5, 23.6, 30.3, 21.0, mean 24.4**. `SEMINAR_DECK.md` line 96 has the
right four. Two digits in the report text do not.

### 1.4 The 24 % ground-load figure is one run of three, and the repo says the spread is wide

This is the more serious half of the same paragraph. Recomputing all three
ground runs against the same air baseline:

| Ground run | FR | FL | RR | RL | mean |
|---|---|---|---|---|---|
| `run_20260806_152810` (the one reported) | +22.5 | +23.6 | +30.3 | +21.0 | 24.4 % |
| `run_20260806_183540` | +12.4 | +14.5 | +18.0 | +12.6 | 14.4 % |
| `run_20260806_184938` | +4.6 | +3.1 | +2.3 | +2.2 | 3.1 % |

`data/bench_logs/README.md` records this already, in its own words: the first
run's plateaus gave a clean +12 to 15 %, the later two range from +1 % to +24 %,
"not a tight band", with floor-texture variation named as a live suspect
alongside weight. One of the three runs falls outside the predicted 10 to 30 %
band entirely.

The report presents 24 % as the measured increase and calls the prediction "a
good one on the evidence". A reader with the CSVs will find two other answers.
The honest version costs two sentences: name the run, give the other two means,
and say that the structured staircase test on the floor is what would settle
the size. That is what `PID_Calibration.md` §7 already calls for.

### 1.5 The three drives in Figure 10 were driven by hand

Figure 10's title is "Endpoint closure from wheel odometry, three autonomous
drives", and §6.1 refers to "the autonomous drive shown as Drive C".

Drive A and Drive B are the 31 Aug reconnaissance legs
(`docs/evidence/monday_recon/`): "continuous mixed motion, straight,
wall-hugging, `W`+`Q`/`W`+`E` turns taken while rolling, some strafing". Those
are teleop keys. Drive C is `run_20260901_112335`, the 1 Sep repeat test
(`docs/evidence/tuesday_repeat/`), re-driven "same route, same style, same
deployed config" by the operator. The autonomous runs of that day were in the
evening, at 18:48 and 19:38.

The numbers are right. I recomputed Drive C from
`run_20260901_112335_pose.csv`: odometry path 10.61 m, closure 96.5 mm, 0.91 %
of path. Drives A and B match `monday_recon/README.md` exactly (8.00 m / 19 mm,
9.61 m / 28 mm). Only the word "autonomous" is wrong, in two places.

Worth a second sentence in §6.2 as well. "Each drive returns to its starting
mark: 19 mm over 8.00 m" reads as a physical return measurement. It is the
odometry's residual on the assumption that the robot was driven back to its
mark. On Drive C the map-frame estimate was 0.209 m out at the same instant.

### 1.6 "134 of the 255 available" is not in any log

Maximum absolute PWM across every bench and ground CSV in the repository:

| Run | max abs PWM | % of 255 |
|---|---|---|
| `run_20260702_183233` | 55 | 21.6 |
| `run_20260804_193703` | **131** | 51.4 |
| `run_20260805_140048` | 128 | 50.2 |
| `run_20260806_152810` | 77 | 30.2 |
| `run_20260806_183540` | 126 | 49.4 |
| `run_20260806_184938` | 129 | 50.6 |

v2's own table gives 131 for the 4 Aug run. The report's 134 leaves "about
47 per cent" unused; 131 leaves 48.6 %. Use 131 and 49 %, or name the run 134
came from.

### 1.7 Figure 8 quotes a step response from a log the project says cannot give one

v2 §4.3.2, unchanged on every branch:

> They do not establish a step response, because these are live driving logs
> rather than isolated-step tests, so rise time and settling time cannot be
> fitted from them.

Figure 8(b) now fits exactly that from `run_20260804_193703`: within 5 % of the
commanded −2.207 rad/s in 0.20 s, 3.5 % overshoot, held to a 0.003 rad/s mean
offset. Three problems, in increasing order of importance.

The overshoot reproduces (minimum −2.285, which is 3.53 % past target). The
0.003 rad/s offset reproduces only on a post-settling window: from t+0.85 s
onward the mean offset is −0.0036 with an s.d. of 0.0048, but across the whole
hold it is −0.0148. The caption should say which window.

The command is not a step. It ramps across four log samples, 0.138 to −0.582 to
−1.062 to −1.662 to −2.207, over 0.15 s. So the 0.20 s to within 5 % is mostly
the commanded value's own transit time, not the loop's rise time. Stated as
"reaches within 5 per cent of the commanded −2.207 rad/s in 0.20 s" it reads as
a controller property and is not one.

And the isolated-step test that would support this exists as a tool and has
never been run: `tools/nab_pid_logger.py --test steps`. It is one bench session.
Either run it and quote that, or take the rise-time and overshoot numbers out of
the caption and leave panel (b) as a picture of the transient.

### 1.8 The monitoring system's self-audit did not survive into the report

Section 6.8 says "One limitation is recorded plainly", and records the
uncalibrated gas index. The repository's register (v2 §5.3) has eight verified
findings, and four of them matter to a committee:

- The UV irradiance channel is uncalibrated. The panel reads 3.64 mW/cm² with
  the lamp off. **The report's own Figure 5 says this in red**, in the figure,
  while the text does not mention it.
- That channel appears in no control path and no alert path, so a failed lamp
  raises nothing. Year-one objective 2.3, optical verification of lamp
  emission, is recorded in the repo as not achieved. The report's Objective 4
  does not mention the requirement.
- An operator's explicit off-command is reverted within one loop iteration.
  For a UV-C lamp that is a safety property, not a usability one.
- Neither deployed LoRa frequency matches India's delicensed band. 915 MHz and
  868 MHz are shipped; the band is 865 to 867 MHz.

v2's line on this is worth re-reading before deciding: "Presenting that third
reading without being asked is the difference between an audit and an excuse."
The report currently presents the dashboard capture as evidence the loop works
while omitting the third thing that same capture shows.

### 1.9 The scan-rate claim needs the softening the datasheet work already wrote

§5.6: "does not respond to a commanded scan rate". `X4Pro_Datasheet_Findings.md`
§3, written 15 Sep against the vendor document, says M_CTR on the PH2.0-8P
connector is a documented motor-speed-control pin, default 2.15 V, range 0 to
3.3 V, with scanning frequency specified across 6 to 12 Hz and angular
resolution tabulated at each. The accurate statement is that the rate is not
commandable through the ROS driver as currently wired, and that the pin exists.
The same document flags two other files needing the same edit.

### 1.10 Navigation trials: the count, and the failure that is missing

"Three goals were commanded across three trials and all three were reached."
The record has four successful goals (two on 14 Aug at 5.5° and 3.7° with a
4.6 cm stop error, two operator-tapped at 25.9 s and 21.0 s), and one failure
that is not mentioned anywhere in the PDF: the first goal ever sent travelled
0.96 m at 88.4° to the commanded direction and was stopped after contacting an
obstacle, caused by two validated axis conventions meeting at the velocity
topic. That fault and its structural fix are one of the better stories in the
project. Leaving it out while writing "all three were reached" is the kind of
omission that reads badly if the committee finds it in the journal.

Also: "reached them in 21 and 26 s" should be 21.0 s and 25.9 s.

### 1.11 Smaller items

- §5.3, "The encoders fitted to this platform produce an output close to 4.7 V".
  That measurement is of the GTK08 front pair (`Bench_Test_Map.md` line 66).
- §6.1, "4 713 samples per wheel". 4713 is the run's row count. Per-wheel valid
  target rows in `run_20260901_112335_report.json` are 4211, 4032, 4031, 4038.
- §6.2, "durations of 162 to 233 s". `monday_recon` records ~166 s for the
  9.61 m leg; Figure 10 says 170 s. One of the two is the trimmed window.
- Reference 27 (Guo et al. 2023) is a review of postharvest storage of
  *Pleurotus eryngii* specifically, cited in §2.1 as "reviews of post-harvest
  practice for perishable produce". Narrower than the sentence implies.
- "approximately 430 points per revolution" matches the dashboard's own count
  (323 valid plus 107 masked). The vendor resolution model gives 441 at
  11.35 Hz. Worth knowing which one is being quoted if asked.

---

## 2. What was checked and holds

Recomputed from raw data, not copied from another document:

- Per-wheel RMS, wheels free, pooled over the three bench runs: 0.0397 to
  0.0471 rad/s over exactly 26,468 wheel-samples. Under chassis weight, pooled
  over the three ground runs: 0.0663 to 0.0740 over exactly 35,248. Both
  sample counts match the report to the digit.
- Drive C per-wheel RMS 0.077 / 0.066 / 0.068 / 0.075 and MAE 0.039 / 0.034 /
  0.032 / 0.039, zero saturated samples, from the run's own report JSON.
- Drive A, B and C path lengths and closures, from the pose CSVs.
- Unclassified percentages of the three 15 Sep maps, computed from the PGMs:
  84.6, 78.3, 73.0. Occupied cell counts 521, 903, 1419, matching Figure 13.
- The forward-kinematics round trip. `tools/wheel_forensics.py --selftest` run
  today returns **worst 2.22e-16**, which is what the report and the rebuilt
  Figure 14 say. See §3.2 below, because four repository documents still say
  1.7e-16 and they are the stale side.

Traced to their source documents and correct: the geometry constants and the
derived `K_o` 0.5607 and `K_i` 0.4907; the 0.0097 common-mode weighting, which
recomputes exactly; the 375.4 mm against 360 mm width reconciliation; 0.0054 m
peak and 0.0000 m final on the offline re-integration; 4.582 m closing to
3.1 mm; the 38 s square at 2.58 cm against 6.2 cm; 0.229 m over about 18 m at
1.27 % with the 21.85 m wheel path kept as a separate quantity, which is the
exact trap `Phase_234_Push.md` warns about and the report avoids; the yaw
residual at median 0.035 rad/s, p95 0.111 to 0.124, worst 0.354, zero episodes
across four drives; 107 of 430 beams and the 90° wedge; 11.35 Hz; the scanner
scatter at 12 to 14 mm below 1.5 m, 22.3 mm against 31.9 mm in the 1.5 to 2.0 m
band, 55 to 200 mm beyond 2.5 m, and the 25 mm half-cell criterion; the whole
Stage H paragraph, including 16.2 mm against 206.7 mm on the same drive, the
seventeen corrections at a 0.183 m mean spacing with a 1 cm spread, the 106.7 mm
smallest correction against a 150 mm search half-width, three of four revert
triggers fired and one keep criterion met; 19 loop closures on the 1047 s drive;
11.08 m of cumulative correction and the 2.09x and 1.54x factors; the
photogrammetry validation frames at −27.07° against −28.0° and −18.50° against
−19.4°; the rotation dead zone at 714° over 642 s for 43 cells and the 111 s arc
at 88 % of perimeter coverage in 18 % of the time; the datasheet accuracy
figures, which are the corrected ones from 15 Sep, not the old "under 2 % of
range"; mass, footprint and the 0.12 to 10 m rated range.

Bibliography is clean. All 37 references are cited in the text, every in-text
citation resolves, no gaps, and there are zero surviving `[CONFIRM]` markers,
which was a `docs/aps_report/README.md` pre-submission requirement.

### 2.1 External citations, checked against the literature record

Five load-bearing figures were verified against the papers themselves rather
than against the project's reading of them, which is what the v2 draft's own
`[CONFIRM]` on the Objective 3 audit asks for:

| Claim in the PDF | Source | Result |
|---|---|---|
| 87.9 % accuracy, LOSO, 35 participants [30] | Hwang et al. 2025, *Sensors* 25(11) 3309 | abstract gives 87.94 %, LOSOCV, 35 participants |
| 82 % accuracy, thermal facial imaging [31] | Tashakori et al. 2021, PIMechE H 236(1) | abstract gives 82 % |
| 0.02 s temporal; 4.0°, 5.6°, 7.4° [33] | Stenum et al. 2021, *PLoS Comput Biol* 17(4) | abstract gives all four values |
| 94 % and 80 % correlation [35] | Alizadeh et al. 2019, *IEEE Access* 7 | abstract gives both, subject lying down, which matches the report's own caveat |
| closed loop 0.40° and 0.17 m [2] | Galati et al. 2022 | full text: "final maximum angle deviation of 0.40 with a maximum final error of 0.17 m along a 10-m straight path on concrete" |

Two things on reference 2 that still need the author's eye. The open-loop range
(3.98 to 4.81° and 0.79 to 0.94 m) lives in that paper's Table 5, which could
not be retrieved from this environment, so it is unverified rather than wrong.
And the paper ran ten repetitions **per direction**, forward and backward, on
concrete and on asphalt, where the report says "across ten repetitions". The
DOI is `10.1038/s41598-022-24270-x`; nature.com and Crossref are both blocked
by the egress proxy here, so the article number 19608 in the reference list
could not be confirmed. Check it on a machine with open network.

---

## 3. Repository problems this audit turned up

These are not report errors. They are places where the repo will mislead the
next person, or has already.

1. **v2 §4.6.5 says "No loop closure has ever been observed to fire on this
   robot."** Journal §17.49 and v2 §4.6.1 both record 19 closures on the 1047 s
   drive, and 9 on another. The sentence is true of the matching-off
   configuration and false as written. The PDF took the correct side, which is
   luck rather than design. Fix the Markdown.
2. **1.7e-16 against 2.22e-16.** `Where_We_Stand.md` line 55, `APS_Study_Guide.md`
   line 193, and v2 in three places give 1.67e-16 or 1.7e-16 for the forward
   kinematics round trip. The selftest returns 2.22e-16 today. Four documents to
   correct, and worth a note on why the value moved.
3. **`data/bench_logs/ground/README.md` still opens "Empty on purpose, no
   ground-floor run has been done yet".** Three runs and their analyses sit in
   the same directory, and they are the source of the 24 % result.
4. **`LevelShifter_Wiring.md` describes two TXS0108E boards.** The deployed part
   is the 8-channel discrete-MOSFET board, per v2 §4.2 and the electronics
   diagram. The PDF describes the deployed one correctly.
5. **v2 §3.3, claim 5, still reads "all four motors inside the band"** while the
   corrected Figure 9 says three of four. The claim table is the one place a
   reader goes for a summary, so it is the worst place to leave stale.
6. **Eleven of v2's figures did not make it into the PDF**, among them the
   encoder CPR fault, the correction traces, the invariance A/B, the autonomy
   gates, the defect taxonomy, the timeline, and both figures carrying the
   monitoring system's audit (the dashboard capture and the control-law and
   defect register panel). Dropping those last two is what makes §1.8 possible.
   `docs/aps_report/README.md` already tracks an unresolved version of this
   problem for the v2 draft; it now applies to the PDF as well.

---

## 4. Before the file is submitted

- [ ] Fix §6.4's inversion of the photogrammetry result (§1.1). This one first.
- [ ] Correct the encoder count, the edge rate and the cycle budget in §5.2,
      and add the encoder split to the §5.1 table (§1.2).
- [ ] Reconcile the four ground-load percentages with Figure 9 (§1.3), and say
      which of three runs they come from and what the others gave (§1.4).
- [ ] Remove "autonomous" from Figure 10's title and from §6.1's Drive C
      reference (§1.5).
- [ ] Replace 134 of 255 with 131, and 47 % with 49 % (§1.6).
- [ ] Decide on Figure 8(b): run the isolated-step test, or drop the rise-time
      and overshoot numbers from the caption (§1.7).
- [ ] Restore at least the UV-channel finding and the operator-off revert to
      §6.8, since Figure 5 states the first of them already (§1.8).
- [ ] Soften the scan-rate sentence in §5.6 (§1.9).
- [ ] Correct the goal count and add the first goal's collision (§1.10).
- [ ] Verify Galati's open-loop range against that paper's Table 5, and confirm
      the Scientific Reports article number (§2.1).
- [ ] Merge `claude/determined-feynman-rw4tfh` so the figures in the PDF and the
      figures the repo generates are the same figures (§0).

Two items from `docs/aps_report/README.md`'s own checklist are still open and
are not visible in the PDF: the parallel project's dates and effort fraction,
and the IRCC consultation on whether the monitoring-system section can be
circulated given no patent has been filed.

---

## 5. If only four things get fixed

Asked on 17 Sep which changes are critical with six days left. These four, in
this order. All of them are edits to the Word file, not to the repository, and
together they are about twenty minutes of work. Paste-ready text below.

### Fix 1. Section 6.4, first sentence of the two-route paragraph

Replace:

> On two structurally different routes the robot finished 3.85° and 4.49° away
> from its commanded heading, while wheel odometry, the published estimate and
> the SLAM pose all agreed with one another to within a few hundredths of a
> degree.

With:

> On two structurally different routes, wheel odometry, the published estimate
> and the SLAM pose all reported 3.85° and 4.49° of heading change by the end
> of the drive, while the floor, read photogrammetrically against the tile
> grout, put the robot within 0.03° of the heading it started from. The robot
> came back to its heading. The estimators did not.

The sentence after it ("Three estimates agreeing while all three disagree with
the floor...") still works and should stay.

Why this is first: as printed, the report claims the platform has a physical
heading error of several degrees. That is a control and hardware failure, and
it is not what was measured. The measurement is the opposite and it is better
news, because estimator error is recoverable by calibration and by the
gyroscope that Chapter 7 asks for. Sections 6.6 and 7.1 already describe it
correctly, so the report currently disagrees with itself on the single result
that justifies the Year-2 plan.

### Fix 2. Section 5.2, the encoder paragraph

Replace the first two sentences of the third paragraph:

> Each drive motor produces 93,132 encoder counts per revolution at the wheel,
> after the optical encoder is read in full quadrature and the gear reduction
> is applied. At the rated speed the output shaft turns once per second, so one
> motor emits 93,132 counted edges per second and four motors emit 372,528.

With:

> The two front motors carry GTK08 encoders producing 186,264 counts per
> revolution at the wheel, and the two rear motors optical encoders producing
> 93,132, in both cases after full quadrature decoding and the gear reduction.
> At the rated speed the output shaft turns once per second, so the four motors
> together emit 558,792 counted edges per second.

Then change "approximately 43 cycles per edge" to "approximately 29 cycles per
edge" (16 MHz ÷ 558,792 = 28.6).

Add a row to the §5.1 table, which currently lists the motors and no encoders:

| Encoders | Front pair GTK08, 186,264 CPR at the wheel; rear pair optical, 93,132 CPR |

Why: Figure 3's caption on the same spread already says the front and rear
encoders differ in resolution, so the page contradicts itself as printed.
Anyone who checks the arithmetic gets a different edge rate. And the corrected
number makes the case for the ESP32 stronger, not weaker.

### Fix 3. Section 6.1, the ground-load paragraph

Two changes. First, the four percentages must match Figure 9 printed beside
them: **22.5, 23.6, 30.3 and 21.0**, not 22.4, 23.6, 30.3 and 21.2. The mean
stays 24.

Second, add after "against a band of 10 to 30 per cent set in advance":

> These figures come from the first of three floor runs recorded on 6 August.
> The two later runs of the same afternoon, driven over different patches of
> floor, give means of 14 and 3 per cent, so the size of the increase is not
> established to better than the width of the predicted band itself. A
> structured staircase test, held in one position while sweeping demand, is
> what would settle it, and it has not been run on the floor.

Why: the digit mismatch is visible to anyone who reads the text and the figure
together. The run-to-run spread is the real exposure, because
`data/bench_logs/README.md` records it plainly and a committee member with the
CSVs finds two other answers. Saying it first costs nothing and removes the
question.

### Fix 4. Figure 10 and its two references, the word "autonomous"

- Figure 10 title: "three autonomous drives" becomes "three logged drives".
- Figure 10 caption: "for three logged autonomous drives" becomes "for three
  logged drives, each driven manually".
- Section 6.1: "the autonomous drive shown as Drive C in Figure 10" becomes
  "the drive shown as Drive C in Figure 10".

All three drives were teleoperated. The closure numbers themselves are correct
and were reproduced from the pose logs for this audit, so nothing else in
either section has to move.

### Deliberately left for later

The peak-PWM figure (§1.6), Figure 8's step-response caption (§1.7), the
scan-rate wording (§1.9) and the navigation goal count (§1.10) are all real and
none of them is likely to be caught in a one-hour seminar. Fix them in the next
revision.

The one judgement call that is not mine is §1.8, the monitoring system's
missing self-audit. Restoring the UV-channel finding is honest and it is what
the v2 draft argued for. It also puts a second uncalibrated channel in front of
the committee, and the report's own Figure 5 already states it in red, so the
asymmetry between the figure and the text is itself a risk. Worth five minutes
with the supervisor before the file is submitted.

---

## 6. Which of these are scientific, and which are not

§5 ranks the findings by what a committee is likely to catch in an hour. That
is not the same as ranking them by scientific weight, and the two orders differ
enough to be worth writing down separately.

Nothing found in this audit is a data error or an analysis error. Every number
that could be recomputed from a raw log reproduced. The experiments hold and
the analysis tools do what they claim. What is wrong is the description.

**Claims not supported as stated.** The ground-load result (§1.4) is the most
serious item in this audit on scientific grounds, and §5 ranks it third only
because it is the least likely to be noticed from the page alone. "A prediction
registered in advance and then met" carries the paragraph, and it holds on one
of three floor runs, one of which lands outside the predicted band. That is
reproducibility, not wording.

Figure 8's step response (§1.7) belongs in the same category and §5 defers it,
which is right on seminar risk and wrong on validity. It fits a rise time and
an overshoot from a live driving log that v2 §4.3.2 says cannot support one,
and most of the quoted 0.20 s is the commanded value's own ramp across four log
samples rather than the loop following it. A controller characterisation drawn
from data that cannot produce one is a methodological fault whether or not
anyone asks about it.

**A correct finding, stated backwards.** §6.4 (§1.1) misreports a sound
measurement, and §6.6 states the same measurement correctly. The error is in
the report rather than in the science. It stays first in §5 because of what it
does to a reader's confidence in everything near it.

**A methods-description error.** Calling three teleoperated drives autonomous
(§1.5) misdescribes the conditions under which the data were collected, which
matters in its own right even though none of the numbers move.

**Factual and transcription.** The encoder CPR (§1.2), the two ground-load
digits (§1.3) and the peak-PWM figure (§1.6). Worth noting on the first of
these that the uniform 93,132 count is the exact fault v2 §4.3.1 documents, the
one that produced clean telemetry while the robot drove wrong. Restoring it to
print is unfortunate rather than damaging.
