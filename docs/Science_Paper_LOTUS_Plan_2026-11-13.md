# Finding the science, a paper, IP and the LOTUS route

*13 Nov 2026. Desk work only. One new tool was run on telemetry that was
already in the repo; nothing ran on the robot. Evidence grades as usual:
measured (this robot's logs), computed (a model I ran today), retrieved (a
paper or page a search tool returned this session), memory (mine, unverified,
flagged every time).*

You said the project feels like product development with nothing much left to
do. I read the whole record before answering, and I think the feeling is
accurate about the plan and wrong about the project.

The Year 2 plan is a queue of integration chores. Bring up AMCL. Tune MPPI.
Decide REP-103. Every item ends in "it works now", and none of them ends in a
sentence somebody outside this lab would want to read. That's why it feels
flat. A chore has a finish line. It doesn't have a question.

But the repo is sitting on at least one measurement nobody has explained, and
unexplained measurements are where papers come from.

---

## 1. The anomaly worth a paper

APS report §4.6.4, your own table: the robot physically returned to its
starting heading on three drives, and odometry said it was off by 3.85°, 4.49°
and 1.74°. All three have the same sign. The error scales with distance driven
(0.37 to 0.60 °/m) and not with rotation commanded. The report calls this
estimator error, files it under "buy an IMU", and moves on.

An IMU will hide it. It won't explain it. And the explanation is the
publishable part.

Here is the piece I think has been missed. The slip residual in
`wheel_forensics.py` lives in velocity space. The ESP32 closes a velocity loop
on every wheel, and the four targets it gets are rigid-consistent by
construction, so the PID drives that residual to zero whether the wheels are
slipping or not. Its 2.7 % median is tracking error. It can't see a wheel that
holds its commanded speed while the floor moves under it, which is exactly the
class of error the phantom yaw belongs to. (The tool's own docstring half says
this. The report's "physical wheel slip is small, bounded" claim leans on it
harder than it should.)

The spare dimension doesn't vanish, though. It moves. Four motors, three
degrees of freedom: wheel torques reach the chassis through Jᵀ, and Jᵀ has a
one-dimensional null space. It is the same vector as the slip residual,

```
n = [1, k, -k, -1]   (FR, FL, RR, RL),   k = Ko/Ki = 1.1427
```

Torque along `n` moves nothing. It is the wheels working against each other
through the floor. A velocity loop can't suppress it, because suppressing it
would mean letting the wheel speeds disagree. So if anything on this robot is
kinematically inconsistent (an effective wheel radius, a lever arm, a roller
that creeps), the evidence should be sitting in the PWM columns of every CSV
you have ever logged.

I checked.

### 1.1 What the archived logs say (measured, exploratory)

`tools/effort_nullspace.py` is new in this commit. It fits a per-motor air
model `pwm = Kff·ω + Kstat·sgn(ω)` from a wheels-off-ground run, subtracts it
from floor runs, and splits what is left into forward, strafe, yaw and null
parts. It has a `--selftest` (five checks, all pass). Air model from
`run_20260805_140048`. Numbers are PWM counts, mean ± block standard error.

| Run | Motion | Speed (m/s) | Load FR / FL / RR / RL | Null part |
|---|---|---|---|---|
| air, 5 Aug | forward | 0.10 | −0.2 / 0.4 / −0.2 / 1.0 | −0.23 ± 0.05 |
| air, 5 Aug | reverse | 0.10 | −0.8 / 0.1 / −0.7 / 1.0 | −0.41 ± 0.07 |
| floor, 6 Aug `_184938` | forward | 0.10 | 1.0 / 2.4 / 0.1 / −0.3 | **+1.83 ± 0.12** |
| floor, 6 Aug `_184938` | reverse | 0.10 | −1.3 / −0.6 / 0.2 / 0.8 | **−1.41 ± 0.14** |
| floor, 31 Aug `_191509` | forward | 0.07 | 2.4 / 2.9 / 0.1 / −0.1 | **+2.65 ± 0.17** |
| floor, 31 Aug `_191509` | reverse | 0.10 | −1.0 / −3.2 / 3.3 / 1.1 | **−4.46 ± 0.09** |
| floor, 1 Sep `_112335` | forward | 0.05 | 2.6 / 3.0 / 0.4 / 0.0 | **+2.60 ± 0.15** |
| floor, 1 Sep `_112335` | reverse | 0.05 | −1.1 / −3.3 / 1.0 / 0.6 | **−3.08 ± 0.11** |

Read the forward rows. The front pair is doing essentially all the floor work
and the rear pair is doing none. Total forward drag is about 5 counts, and the
part of it that pushes the chassis nowhere is about 2.6. Half the effort the
motors spend on the floor in a straight line is spent on each other.

Three more things in that table.

The sign flips with direction, in every run where the signal is present. In
air it stays under one count. And in reverse on 31 Aug the RR motor reads
+3.3, meaning it needed *less* PWM than it does spinning free: the floor was
pushing that wheel along. A resisting load can't do that. Only another wheel
can.

One detail I like and don't trust yet. If the forward load is a uniform
rolling resistance plus a pure fight along `n`, FL should carry more than FR
by the ratio k = 1.14. Measured: 2.9/2.4 and 3.0/2.6. Two runs. Cute, not
evidence.

What this doesn't show, stated as plainly. Two of the five floor runs (both
from 6 Aug) show nothing: −0.76/+0.12 and +0.48/−0.67. The signal seems to
grow from 6 Aug to 1 Sep and I don't know what changed on the robot in between
(a mast? a payload? speed?). Strafing and rotating give null parts that
disagree between runs, so the clean result today is forward and reverse only.
PWM is not torque, the air model is from another day, and battery voltage
moves the scale by a few percent, so I'd treat anything under 1.5 counts as
floor. And reverse isn't a mirror image of forward, which the simple
"resistance plus fight" picture doesn't explain.

So: a real signal, seen in three sessions, not yet an understood one. That's
the right state for the start of a paper.

### 1.2 What a creep model predicts (computed)

The standard quasi-static picture (Gracia and Tornero 2007; Hijikata et al.
2023 use the same assumption for omni wheels) says each wheel pushes with a
force proportional to its slip speed and its normal load. The body then moves
at the load-weighted least-squares compromise of what the four wheels are
asking for. I ran that model for this geometry and for a symmetric one of the
same mean length, driving straight ahead:

| Imperfection | Yaw drift, this chassis | Yaw drift, symmetric |
|---|---|---|
| Front pair 1 % larger effective radius than rear | 0.036 °/m | exactly 0 |
| Same, plus 70/30 load on one diagonal | 0.24 °/m | 0.22 °/m |
| One wheel 1 % large | 0.29 °/m | 0.27 °/m |
| One side 1 % larger than the other | 0.54 °/m | 0.55 °/m |

I went into this expecting the asymmetry to be the villain. A front-rear
effort imbalance is a pure internal force on a symmetric chassis, and on this
one it carries a yaw moment with a lever arm of 2(l₁ − l₂) = 0.14 m. That's
true, it's specific to this robot, and the model says it's small: about
0.04 °/m per percent of mismatch. It would take a 14 % front-rear radius
difference to produce your 0.5 °/m. No.

The boring candidate is the strong one. A 1 % left-right difference in
effective rolling radius (0.76 mm on a 76 mm wheel, well inside what roller
wear and uneven load can do) gives 0.54 °/m, distance-proportional, always the
same sign when driving nose-first. That matches all three rows of your table.

Which sounds like bad news for novelty and I think it's the opposite. Because
of what the null space does with it:

- On a symmetric mecanum chassis, a left-right mismatch is a rigid motion (a
  gentle arc). The wheels don't fight. Nothing on board can see it.
- On this chassis it isn't quite rigid. 6.6 % of it lands on `n`. The wheels
  fight, slightly, and the fight is readable from PWM.
- In both layouts, the fights seen in three motions (forward, strafe, rotate)
  are three independent combinations of the four radius errors. Everything
  except the overall scale is identifiable in principle, from encoders and PWM
  alone.

That last point is the idea. Trim the per-wheel speed commands until the fight
disappears in all three motions, and the wheel set becomes rigid-consistent.
No tape, no camera, no IMU. If the phantom yaw then drops, the robot has
calibrated a systematic odometry error using only the fact that it has one
motor more than it needs.

### 1.3 The paper

Working title: *The fourth motor as a sensor: internal effort reveals and
corrects systematic odometry error on an over-actuated mecanum platform.*

Four contributions, and they aren't equally safe.

The first is the observation that closed-loop velocity control empties the
velocity-space redundancy residual and fills the effort-space one. That is
close to a one-paragraph proof plus your logs. Safe.

The second is the weighted-creep sensitivity analysis for a general
four-mecanum layout with l₁ ≠ l₂, in closed form, saying which error terms
vanish under symmetry and which don't. This also gives Gap 1 of the APS report
a first quantitative answer (what does the asymmetry cost in drift? very
little, and here is the expression) without building a second robot. Safe,
modest.

Third, fight-nulling self-calibration, validated against a gyro and your
tile-grout photogrammetry. This is the risky one and the one that makes the
paper. It could simply fail: per-wheel friction differences may swamp the
signal, or the creep law may be too nonlinear at 0.05 to 0.10 m/s.

Fourth, a payload experiment. Move a known ballast between corners, predict
how the drift map changes from the load weights, measure it. This closes
Gap 6 of the report on the way past.

Predictions, registered now, before anything runs:

1. A straight 5 m nose-first drive with zero rotation commanded yaws the
   chassis physically by 1.5° to 3°, same sign every repeat, and the opposite
   rotational sense when the same line is driven tail-first. 70 %.
2. The forward null effort is present in at least 8 of 10 fresh floor runs at
   0.10 m/s. 65 %. (Today it's 3 of 5, and the logs don't settle whether it
   scales with speed: 1 Sep at 0.05 m/s reads the same as 31 Aug at 0.07.)
3. Strafing shows a repeatable fight once runs are long enough (30 s per
   direction). 50 %. Today's strafe data is too short to say.
4. After fight-nulling trims, drift on the 5 m line falls below 0.15 °/m from
   roughly 0.5. 35 to 40 %. I'd rather say that number out loud than pretend.
5. Moving 5 kg from one diagonal to the other changes the drift by an amount
   the model predicts within a factor of two. 50 %.

If 4 fails and 1 to 3 hold, there's still a paper: the diagnosis and the
sensitivity analysis, with the calibration reported as a negative result. If 2
fails on fresh data, the idea is dead and you've lost two weeks. That's a good
bet.

### 1.4 Who got here first (retrieved, and the gap is not yet proven)

I searched Consensus, Scite and the open web for this specific combination
and did not find it. Not finding something in an afternoon is weak evidence.
The neighbours:

- Manzl et al. 2023 (*Mechanism and Machine Theory*) built an
  orthotropic-friction mecanum model and showed that centre-of-mass changes
  move a real robot away from ideal kinematics. That is the closest physics.
  Symmetric layout, simulation-led, no effort-space observable.
- Tezel et al. 2024 (*IJRR*) model variable roller contact forces with a
  ground-truth rig. Same comment.
- Hijikata, Miyagusuku and Ozaki 2022 and 2023 (*Applied Sciences*) study
  asymmetric omni-wheel arrangements for compactness and show that a
  "velocity moment" balance governs straightness. This is the nearest thing in
  the world to your chassis problem, on omni wheels instead of mecanum. It
  matters again in §4.
- Galati et al. 2022 (*Scientific Reports*) adapt heading correction to floor
  surface on a heavy mecanum robot, with rolling-radius variability named as
  the cause.
- Vandewal et al. 2022 (IEEE AMC) fit a simplified mecanum slip model per
  surface. Mamat et al. 2026 (*Sensors*) calibrate mecanum odometry scale
  factors, with an external reference.
- Gracia and Tornero 2007 (*Advanced Robotics*) is the weighted-least-squares
  slip kinematics the §1.2 model rests on.

"Wheel fighting" and internal forces are a known idea in swerve drives, in
over-actuated road vehicles and in multi-robot payload transport. Somebody may
have carried it to mecanum calibration under a name I didn't search for. Two
days on IEEE Xplore and Google Scholar with "kinematic incompatibility",
"antagonistic torque", "internal force" and "over-constrained" come before
any experiment. None of the papers above has been added to
`research_articles/README.md`, because I haven't done that file's retraction
check on them.

---

## 2. Two more papers, and one I'd skip

### 2.1 A robot that can't turn around

This is where "reversing and holonomic
motion are my work" belongs. The body needs a 1.22 m circle to rotate and the
aisles are narrower than that, so heading is a resource, the direction of
travel and the direction of the nose are decoupled, and a 90° wedge of the
world is unseen. Nav2 quietly assumes a forward axis in five places you have
already been bitten by, and Year 2 adds at least three more. The research version of your Nav2 pain is: a
planner and MPPI critics that budget heading against aisle width (your own
table in `Year2_Autonomy_Research.md` §1 is the start of the theory) and
refuse to move into space the scanner hasn't seen recently, compared against
stock Nav2 and Smac Lattice in 0.6, 0.8 and 1.1 m aisles. Simulation first,
which means it can move on days when the robot is being difficult. I haven't
done the literature check for this one (the search tool rate-limited me), so
treat novelty as unknown. Perception-aware MPC exists for drones and I'd
expect something for ground robots. Target: second half of 2027.

### 2.2 When scan matching hurts

The 32× degradation, the search-window
saturation and the invariance across parameter sets, completed by the DTOF
comparison and the IMU re-test already planned as G10 and G12. The report
called this the most novel result of the year. I'd call it the most useful and
rank it second for novelty, because negative results about one cheap sensor
are a hard sell at good venues. It's a solid workshop or short paper, and it
costs two parts you're buying anyway.

### 2.3 The other two

The UV-C dose gap (Gap 8) is the one with biology in it, and Japan is where
far-UVC lamp work is concentrated (memory, unverified). If a LOTUS host or
your department wants a life-science hook, a dose-verified disinfection pass
in an aircraft-width aisle is the honest way to supply one. It's also tangled
in the unanswered IRCC disclosure question. Park it; don't delete it.

And the systems paper the report lists first, the platform plus the fault
taxonomy? I'd fold its best material into the papers above as method sections.
On its own it's a tour of a robot, and reviewers have read that tour.

---

## 3. "A design patent"

Two different things hide in that phrase, and India only has one of them
under that name. (This section is from memory and general knowledge. I'm not
a patent agent. IRCC decides, and you should ask them before believing me.)

A *design registration* under the Designs Act 2000 protects how an article
looks: shape, configuration, pattern, judged by eye. It doesn't protect what
the thing does, and features dictated purely by function don't count. It's
cheap and quick. A *patent* protects function, needs an inventive step, takes
years, and Section 3(k) keeps out algorithms and mathematical methods on their
own. India has no general grace period, so anything you want to patent must be
filed before it is published, pre-printed or presented.

What is already gone: the asymmetric wheel layout itself. The lab published
it at ICC 2024. Ask Prof. Kunwar whether IIT Bombay filed anything before that
paper. If not, the layout is prior art against everyone, including you.

What I'd take to IRCC, in this order.

The fight-nulling calibration of §1, if prediction 4 holds, claimed as a
system (motors, drivers, controller, a defined procedure with a technical
effect), with a provisional application filed before the paper goes anywhere
public. This is the one with substance. It's also the one most exposed to
3(k), so the drafting matters.

The corner sensor pod. Your own `tools/sensor_coverage.py` result is that
eight multizone ToF modules pointing outward see 15 to 22 % of the robot's
outline at 10 cm, and the same eight mounted two per corner, aimed *along*
the body and toed out by half their field of view, see 100 %. That is a
physical article with a shape: a corner bumper block holding two modules at
fixed grazing angles. It's what I'd design if you want a design registration,
and the arrangement might carry a modest patent claim too, after a prior-art
search (robot vacuums use grazing wall sensors; AMRs put safety scanners at
diagonal corners).

A first brief for it, so there's something to draw from:

- One moulded pod per chassis corner, four identical parts if the corner
  radius allows, or two mirrored pairs.
- Two windows per pod. One looks down the long flank, one across the end
  face. Each module's optical axis is toed out 30° from the face it watches
  (half of a VL53L7CX's 60° field), so the inner edge of the cone runs along
  the chassis skin.
- Module centre about 10 cm above the floor, which puts the lowest zone rows
  on the floor at roughly 17 cm and gives drop-off detection for free.
- A recess deep enough that the pod, and not the window, takes a wall strike.
  No cover glass until ST's crosstalk calibration has been done with it.
- One 4-wire I²C tail and one LPn line per module, routed inside the pod.

I can turn that into a CAD model in a later session. I'd want two real numbers
first: the corner profile from the SolidWorks assembly, and the bare module's
measured outline. A design registration on a guess gets redrawn.

Being straight about value: a design registration is a line on a CV and a
small fence around a part. It won't carry a thesis or a LOTUS application. The
paper will.

---

## 4. LOTUS

What I could establish, with the caveat that `jst.go.jp` is blocked from this
session's network, so everything below comes from search summaries of JST's
pages and from third-party guides (retrieved, second-hand).

- It is JST's India-Japan programme for bringing Indian master's students,
  doctoral students and postdocs into Japanese labs. LOTUS Basic funds up to
  12 months of living costs. LOTUS-ASPIRE runs up to 36 months and adds
  research funds.
- You cannot apply. The applicant is a principal investigator at a
  Japanese university or institute, who names you. No Japanese PI, no
  application.
- The FY2026 call closed on 9 June 2026, with results from late August and
  stays starting around October. If FY2027 follows the same calendar (an
  inference, not an announcement), the call opens around March 2027 and closes
  around early June 2027, for a stay starting about October 2027.
- IITs made up roughly three quarters of the pilot selections, per a JST news
  item.
- Stipend figures online disagree (¥200,000 to ¥240,000 a month). Some guides
  give an age limit of 40. Read the real guideline PDF before quoting either.
- I found nothing specific about how IIT Bombay supports it. You said the
  institute helps. Ask the Dean (International Relations) office exactly what
  that help is: a matching list, an MoU partner list, or a letter.

So the scholarship is downstream of one thing: a Japanese professor who wants
you in their lab enough to write the application. Professors say yes to people
who arrive with a specific question that touches their own work and a figure
that shows it's real. A good CV with "interested in robotics" gets no reply.

That changes what the next four months are for. Working backwards:

| When | What |
|---|---|
| Nov to Dec 2026 | Prior-art search, then the straight-line drift experiment and ten fresh floor runs (§5). A go or no-go on the idea by year end |
| Jan 2027 | IMU on the robot. Fight-nulling attempt. One clean figure: drift before and after, or the fight signal against speed |
| Late Jan 2027 | Ask Prof. Kunwar, and I'd strongly suggest Prof. Vachhani (she co-authored the ICC 2024 paper and sits in Systems and Control), who they know in Japan. A warm introduction beats any cold email |
| Feb 2027 | Write to five to eight PIs. One page: the anomaly, the figure, what you'd do in their lab in 12 months, and that LOTUS would fund it. Ask one question: would they consider hosting |
| Mar to May 2027 | Draft the proposal with the PI who said yes. Submit the paper (or post it, after IRCC has had its say) so it can be cited in the application |
| Jun 2027 | PI submits |

Who to write to. Evidence first, then memory.

- Koichi Ozaki, Renato Miyagusuku and Masaaki Hijikata, the authors of the two
  asymmetric omni-wheel arrangement papers in §1.4. I believe they are at
  Utsunomiya University but my search could not confirm the affiliation, so
  check the paper header. This is the group in Japan whose published problem
  is closest to yours, and "your velocity-moment analysis, extended to mecanum
  with an effort-space observable" is a one-line pitch they'd understand
  immediately.
- Hiroshi Igarashi's group at Tokyo Denki University published skid
  correction for mecanum robots using a disturbance observer and slip control
  (JSME conference, 2017, retrieved by title only).
- From memory, unverified, to be checked against their current pages: the
  motion-control groups at Keio descended from the lab where the disturbance
  observer was developed, which fits `Adaptive_Control_Roadmap.md` Stage 2;
  the mobile-robot navigation groups at the University of Tsukuba; Tohoku's
  robotics labs. Verify every name before sending anything.

One more honest point. A year in Japan on LOTUS Basic is a research visit, so
it needs your supervisor's active support, a plan for the robot (does it
travel, or do you work on theirs?), and a topic that still makes sense away
from your own hardware. The effort-space idea ports well: it needs any
four-wheel omni platform with PWM or current telemetry. That is a point in its
favour as the LOTUS topic.

---

## 5. The next three weeks, and nothing after that yet

I'm not writing a twelve-week plan, because the first result decides the rest
and because long plans are part of what went flat after the APS.

1. Two days of prior-art reading (§1.4). Write the five nearest papers into
   `research_articles/README.md` with the retraction check done. If someone
   has published fight-based mecanum calibration, tell me and we re-aim at the
   payload experiment or at the navigation paper.
2. One afternoon on the floor, no new hardware. Write the predictions from
   §1.3 into the journal first. Then: a 5 m line along tile grout, nose-first,
   tail-first, strafe left, strafe right, three repeats each, at 0.10 m/s,
   zero rotation commanded, heading read from the grout at both ends by the
   photogrammetry method that already works. That gives a four-direction map
   of true drift, which the project has never had.
3. Same afternoon: 30 s of steady driving in each of the six motions, logged.
   Run `tools/effort_nullspace.py` on it. This is prediction 2 and 3.
4. Order the BNO085. It was already first on the list, and now it's the
   ground-truth instrument for a paper instead of a patch.
5. Then stop and look. If the drift map and the fight agree in sign and
   roughly in size, the paper is on.

Skills this builds, in the order the work forces them on you: least-squares
estimation and observability (the null-space argument, done properly), contact
mechanics of rolling (creep, the bit most roboticists skip), experiment design
with registered predictions (you already do this better than most), and
writing a theory section. None of it is a course. All of it is on the CV as a
result.

About the motivation. I can't fix that from here, and I won't pretend a
document does. What I can say is that the flat feeling arrived at the same
time as the questions ran out, and that the afternoon in step 2 is small,
physical, has a prediction that might be wrong, and takes no debugging of
Nav2. Start there.

---

## 6. Sources

Retrieved this session through Consensus, Scite or web search. DOIs are given
only where a tool returned one; add the rest through Scite before citing.

- Arunkumar G. K., Devkar, S., Vachhani, L., & Kunwar, A. (2024). An
  omnidirectional asymmetric mobile robot for narrow aisle spaces. *2024 Tenth
  Indian Control Conference (ICC)*. https://doi.org/10.1109/ICC64753.2024.10883714
  (PDF in `docs/`.)
- Chaichumporn, C., et al. (2025). Experimental validation of an adaptive
  controller for a mecanum-wheel robot with unknown center-of-gravity offset
  and slope inclination. *International Journal of Advanced Computer Science
  and Applications*.
- Galati, R., et al. (2022). Adaptive heading correction for an industrial
  heavy-duty omnidirectional robot. *Scientific Reports*.
- Gracia, L., & Tornero, J. (2007). Kinematic modeling of wheeled mobile
  robots with slip. *Advanced Robotics*.
- Hijikata, M., Miyagusuku, R., & Ozaki, K. (2022). Wheel arrangement of four
  omni wheel mobile robot for compactness. *Applied Sciences*.
- Hijikata, M., Miyagusuku, R., & Ozaki, K. (2023). Omni wheel arrangement
  evaluation method using velocity moments. *Applied Sciences, 13*(3), 1584.
  https://doi.org/10.3390/app13031584
- Kim, S., et al. (2020). Slip analysis and experimental verification for an
  omni-directional mobile robot based on mecanum wheels. *Journal of the
  Korean Society for Precision Engineering*.
- Mamat, T., et al. (2026). A high-precision odometry calibration method for
  mecanum-wheeled mobile robots based on ZUPT and closed-loop pose estimation.
  *Sensors*. https://doi.org/10.3390/s26185692
- Manzl, P., et al. (2023). A mecanum wheel model based on orthotropic
  friction with experimental validation. *Mechanism and Machine Theory*.
- Sgrò, R., & Cacciatori, S. (2026). Asymmetric configuration for a four-motor
  omnidirectional robot. *Archives of Advanced Engineering Science*.
- Tezel, C., et al. (2024). Theoretical and experimental investigation of
  variable contact forces on the rollers of a mecanum wheeled mobile robot.
  *The International Journal of Robotics Research*.
- Vandewal, B., et al. (2022). Simplified wheel slip modeling and estimation
  for omnidirectional vehicles. *IEEE International Workshop on Advanced
  Motion Control (AMC)*.

LOTUS, all second-hand because JST's own site was unreachable from here:

- JST, LOTUS Programme overview and FY2026 call pages:
  https://www.jst.go.jp/program/india/en/outline/ and
  https://www.jst.go.jp/program/india/en/call/
- JST, FY2026 call overview PDF:
  https://www.jst.go.jp/program/india/dl/2026/lotus_fy2026call_overview_en.pdf
- Science Japan (JST), "Bringing young talent from India to Japan: JST's LOTUS
  Program launches": https://sj.jst.go.jp/news/202509/n0930-01k.html
- SBJ, "Call for Applications: FY2026 India-Japan LOTUS Programme":
  https://www.sbj.or.jp/e/news/jst_lotus_20260325.html

To reproduce §1.1:

```
python3 tools/effort_nullspace.py --selftest
python3 tools/effort_nullspace.py --air data/bench_logs/bench/run_20260805_140048.csv \
    data/bench_logs/ground/run_20260806_152810.csv \
    data/bench_logs/ground/run_20260806_183540.csv \
    data/bench_logs/ground/run_20260806_184938.csv \
    data/field_runs/run_20260831/run_20260831_191509.csv \
    data/field_runs/run_20260901/run_20260901_112335.csv
```

And §1.2 (a model, with two self-test checks of its own, not a measurement):

```
python3 tools/effort_nullspace.py --sensitivity
```
