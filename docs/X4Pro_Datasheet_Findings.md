# What the X4 PRO datasheet actually says, and what it changes

Written 15 Sep 2026 against the official EAI/YDLIDAR document
`DOC#:01.13.001700`, X4PRO DATA SHEET, Copyright 2022 EAI, 8 pages.
Read in full as text. Alongside it, a supplied synthesis of the six-part
MathWorks Autonomous Navigation video series.

**Two of the findings below change numbers that are currently in the APS
report.** One changes the shape of the project's central argument about the
sensor, in a direction that makes it stronger.

---

## 0. Provenance, stated first

| Source | Status |
|---|---|
| X4 PRO datasheet PDF | Read in full, text layer, 8 pages |
| MathWorks synthesis (.docx) | Read in full: 353 paragraphs, 3 tables |
| The six YouTube links | **Not accessed.** The network egress proxy blocks `youtu.be` and `www.mathworks.com` from this environment |

The .docx describes itself as a paraphrased synthesis of exactly those six
videos, and its part durations (11:29, 15:51, 16:21, 17:54, 17:08, 14:47)
sum to the 93:30 it states for the series. So the video content here is
second-hand through that document and was not verified against the
originals.

**Datasheet figures were not seen.** Pages 3, 5 and 7 carry a mechanical
drawing, an interface photograph and the polar-coordinate diagram. Those
are images; `pdftoppm` is not available in this environment, so only the
text layer was read. Anything depending on those drawings (connector
orientation, exact mounting hole geometry, the zero-angle reference
picture) is not covered here.

---

## 1. The "< 2 % of range" figure does not appear in the datasheet

This project states, in at least thirteen places including both APS report
drafts and the seminar deck, that the X4 Pro is "rated at under 2 % of
range," giving 32 mm at 1.6 m and 200 mm at 10 m.

The datasheet's actual accuracy specification, Chart 1:

| Item | Min | Typical | Max | Unit | Remarks |
|---|---|---|---|---|---|
| Absolute error | / | **2** | / | cm | **Distance ≤ 1 m** |
| Relative error | / | **3.5 %** | / | / | **1 m < Distance ≤ 6 m** |

Three things follow, and none of them match what the repo says:

1. Below 1 m the spec is a **fixed 20 mm**, not a percentage.
2. From 1 to 6 m the spec is **3.5 %**, not 2 %.
3. **Above 6 m there is no accuracy specification at all**, even though
   ranging distance is rated to 10 m.

Corrected numbers:

| Claim in the repo | Datasheet-corrected |
|---|---|
| under 2 % of range | 2 cm absolute ≤ 1 m; 3.5 % from 1 to 6 m; unspecified above 6 m |
| 32 mm at the 1.6 m median | **56 mm** at 1.6 m |
| 100 mm at 5 m | **175 mm** at 5 m |
| 200 mm at 10 m | **no specification exists at 10 m** |

This also settles the discrepancy `Phase2_Without_IMU.md` §5.2 already
flagged. It noticed that StageG's 32/100/200 figures are "exactly 2 % of
range, which is linear" while StageG's own prose called the growth
quadratic, and it scheduled a measurement to decide between them. The
answer is that **neither model is the vendor's**. The vendor's model is
piecewise: a fixed absolute error in the near field, a fixed percentage in
the mid field, and silence beyond 6 m.

### 1.1 Where this needs fixing

`docs/Stack_Assessment_2026-09-01.md`, `docs/Research_Journal.md`,
`docs/StageG_Deploy.md` §1.1, `docs/StageF_Ablation.md`,
`docs/Phase2_Without_IMU.md`, `docs/aps_report/APS_Report_Draft.md`,
`docs/aps_report/APS_Report_Draft_v2.md` (several sites including §12.1's
Gap 2), `docs/aps_report/deck_src/build_deck.js`, and the comment block in
`system/slam_nodom_stageB.yaml`.

**Gap 2 in the report gets stronger, not weaker.** It argues that the
low-cost sensor tier does not close a corridor-width error budget, using
"2 % of range gives 32 mm at 1.6 m" as its backbone. At 3.5 % that becomes
56 mm against the same few-centimetre lateral budget. The gap holds and the
margin against it widens.

---

## 2. The datasheet specifies accuracy and never specifies repeatability

This is the finding that changes the argument rather than a number.

Datasheet Note 2 defines the relative error term precisely:

> Relative error (mean value) = (average measured distance - actual
> distance)/actual distance *100%, sample size: 100pcs.

That is a **mean bias across a production sample of 100 units**. It is not
scatter, not standard deviation, not a p90, not a valid-return rate, and
not a temporal-stability figure.

The project's 22.8 mm p90 (§17.45) is **scatter on one unit**. So the
sentence currently in the report, that a measured 90th-percentile scatter
of 22.8 mm "is inside specification," compares a precision measurement
against an accuracy specification. Those are different quantities. A
committee member who works with rangefinders can ask about that.

**The stronger claim, and the one the document actually supports:**

> The datasheet specifies accuracy and says nothing whatsoever about
> repeatability. It carries no figure for scatter, none for valid-return
> rate, and none for temporal stability between consecutive sweeps. The
> property that breaks pose-graph SLAM on this platform, 47.4 % valid
> returns with roughly 86 % of returning beams flickering while the robot
> is stationary, is not specified by the vendor at all.

That is a better position than "performing to specification and the
specification is not good enough," because it forecloses the two obvious
committee responses. It is not a bad unit, and it is not a calibration
problem. The vendor never promised the thing that matters here, and the
measurement campaign is what established that it matters.

---

## 3. Motor speed control exists, is documented, and is quantified

The repo currently records that the scan-rate lever "does not exist on this
hardware." That is true of the current wiring and false of the sensor.

§2.5 and Chart 3:

- **M_CTR** on the PH2.0-8P connector is the "Motor speed control end",
  default **2.15 V**, range **0 to 3.3 V**, PWM speed control.
- "The lower the voltage/PWM duty cycle, the higher the motor speed.
  0V / Maximum speed at 0% duty cycle."
- Chart 5: PWM frequency typical **10 kHz**, duty min 0, typical 65 %,
  max 100 %. "Smaller duty value, higher scan rate."
- Chart 1: scanning frequency **6 to 12 Hz**, by "PWM or voltage speed
  regulation."
- Chart 1, angle resolution: **0.43° at 6 Hz, 0.50° at 7 Hz, 0.86° at
  12 Hz**.

### 3.1 What this confirms and what it corrects

The measured 11.35 Hz free-run sits near the top of the 6 to 12 Hz band,
which is consistent with the default 2.15 V on M_CTR.

**The relationship is inverted and easy to get backwards.** To scan
*slower*, and therefore denser, M_CTR must go *higher*, toward 3.3 V or a
higher duty cycle.

The vendor's resolution table independently confirms this project's
`5000/f` model: 0.86° at 12 Hz to 0.43° at 6 Hz is exactly a factor of two,
matching 441 points per revolution at the measured rate against 833 at
6 Hz.

Two repo statements need softening:

- `docs/Nodding_LiDAR_Assessment.md`: "NAB cannot command its scan rate at
  all" should read that it is not commandable through the ROS driver as
  currently wired, but is commandable at the M_CTR pin.
- `system/ydlidar_params.yaml`: the note that the lever "does not exist on
  this hardware without motor control" is right in substance. Worth adding
  the pin, the voltage range, the inversion, and the vendor resolution
  figures so the next person does not have to re-derive them.

### 3.2 What the datasheet does not answer

It describes the LiDAR's own connector, not the USB adapter board. So it
does not say whether that adapter breaks M_CTR out or ties it to a fixed
divider. A fixed 2.15 V default is exactly what a divider would produce,
which would explain a head that free-runs at one stable rate and ignores
everything.

It also says nothing about `support_motor_dtr`. DTR is a serial handshake
line; on many YDLIDAR adapters it is wired to motor enable, on or off,
rather than to speed. **That remains an inspection, not an assumption**,
and the existing caution about flipping it blind still stands.

### 3.3 If it is ever pursued

NAB already carries an ESP32 with an LEDC peripheral. A 10 kHz PWM at
settable duty into M_CTR is a few lines of firmware and one wire, and the
result is directly measurable with `ros2 topic hz /scan`. This is the only
route to more points per revolution on this sensor.

**Not before APS.** It is a hardware modification with an unknown adapter
in the path, eight days out, and it does not unblock G4. One bounded
experiment afterwards.

---

## 4. Smaller datasheet items worth having on record

| Item | Datasheet | Why it matters here |
|---|---|---|
| Tilt angle | 0.25 / 1 / 1.75 deg | The scan plane is not guaranteed horizontal. At 4 m, 1.75° is about 12 cm of vertical wander. A grazing beam can catch a feature on one sweep and miss it on the next, which is a *mechanism* for range-dependent flicker that nobody in this project has listed. Hypothesis, testable, not a claim |
| Lighting environment | 0 / 2000 / 40000 Lux | The deferred "ambient IR as a candidate for the §17.47/§17.48 intermittency" item now has a vendor number to test against |
| Laser wavelength | 775 / 793 / 800 nm, Class I, 3 mW typical | Same, and it identifies which interfering sources would matter |
| Service life | 1500 h typical | Worth logging cumulative hours. This unit has been running since at least July |
| Operating temperature | 0 / 20 / 40 °C | Worth a check inside the enclosure given the Pi's thermal history |
| Zero-angle deviation | plus or minus 3 deg, individual units | Vendor-acknowledged unit-to-unit variance. Retroactively justifies this project's refusal to assume the mirror/offset and its insistence on measuring it on this unit |
| Interface | Tx-only downlink, 128000 baud | Confirms the config, and confirms there is no per-ray diagnostic channel to reject a bad measurement with |
| Ranging distance | 0.12 to 10 m | Config `range_min: 0.1` sits just below the vendor minimum of 0.12. Harmless, since scan_relay floors well above it, but it should read 0.12 |
| Ranging frequency | 5000 Hz | Confirms the `5000/f` model's numerator |

---

## 5. The MathWorks material: what is usable

Treat its video content as second-hand, per §0. Its own ROS2/Nav2 bridge
and AisleBot sections are clearly labelled as additions beyond the videos.

**5.1 The corrections table (§12) is directly usable for report language.**
Several entries map onto claims this report makes, in particular that map
inflation establishes a *planning* clearance under modelled assumptions
while real physical clearance also depends on localisation, control,
latency and footprint calibration.

**5.2 §10.1 gives the right defensive framing for the viva.** The obvious
question is "you turned scan matching off, isn't that just disabling
SLAM?" The narrow claim is the defensible one: under the tested sensor
quality, robot motion and parameter set, the added scan-matching correction
degraded the measured result. That is a system-identification result about
this configuration, not a general claim that scan matching is bad. Any
broader phrasing in the report should be pulled back to this.

**5.3 §4.4 is in direct tension with the current loop-closure thresholds.**
It states that missing a real loop closure is usually safer than accepting
a false one, because a wrong constraint contaminates the optimisation.
The deployed config relaxed `loop_match_minimum_response_coarse` to 0.25
and `_fine` to 0.35, down from stock 0.35 and 0.45, which trades in the
direction of accepting more. That was a reasoned trade, made when the
measured state was zero closures and half a metre of drift, and the config
comment already says these are the first thing to raise back if the map
folds. What is new is a citable principle behind that instinct.

**5.4 Two things §10.3 lists that this project does not currently measure:**
loop-closure acceptance rate and false-loop rate, and Nav2 obstacle
persistence and clearing latency.

**5.5 §7's V-model and metric structure** maps cleanly onto the existing
G-gate ladder. GOSPA and the tracking metrics are not relevant yet, since
nothing here tracks dynamic objects.

**5.6 What it does not provide:** anything operational. Its own §11 says so,
listing driver behaviour, self-occlusion, mecanum kinematics, TF timing and
costmap semantics as outside the series' scope.

---

## 6. What to do, ranked against eight days to APS

1. **Fix the sensor-spec numbers** across the docs and both report drafts,
   per §1.1. Costs an hour, no hardware, and the corrected figures make
   Gap 2 stronger.
2. **Rewrite the sensor argument** to §2's form. This is the higher-value
   half of the same edit.
3. **Nothing here changes the G4 plan.** Coverage is still the blocker, and
   no datasheet finding moves the unknown-cells number.
4. **Cheap, this week if a slot appears:** the range-repeatability run that
   `Phase2_Without_IMU.md` §5.2 already specifies, now with the correct
   comparison target (3.5 %, and only valid from 1 to 6 m). It settles the
   linear-versus-quadratic question with this unit's own numbers, and it
   measures the repeatability the vendor never specified.
5. **Post-APS:** the M_CTR experiment, §3.3.
6. **Post-APS:** the two unmeasured items in §5.4, of which false-loop rate
   is the one with a live risk attached.
