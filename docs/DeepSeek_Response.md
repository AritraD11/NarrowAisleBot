# Answering the outside opinion

Written 15 Sep 2026, against the reply DeepSeek gave to
`docs/DeepSeek_Brief.md`. Eight days to APS.

The reply is good. It is also answering a brief that was written before the
15 Sep evening work landed, and its single headline recommendation had
already been executed by the time it arrived. That is worth saying first,
because most of what follows is either "already done" or "already closed",
and the two items that survive are worth more than the rest of the reply
put together.

---

## 1. The headline recommendation was already run, and it agreed

DeepSeek's §10, the one-thing-above-all-others: *"Run `wheel_forensics.py`
on the existing logs before you do anything else. It costs 30 minutes. You
wrote it and never ran it against a campaign."*

It was run on 15 Sep, on four telemetry CSVs, and it closed Gap 3. Results
are in `docs/evidence/gap3_slip_residual/` and summarised in
`Phase2_Without_IMU.md` §5.4.1. Slip residual median while moving is
0.035 rad/s, about 2.7% of drive speed, with zero episodes above threshold
across all four runs including a deliberately irregular one.

DeepSeek predicted a fork: *"if they agree, you've eliminated slip and
localized the problem to calibration or firmware."* That is exactly the
branch that fired. Two independent models producing the same answer on the
same question is worth something, so the credit stands even though the
advice arrived late.

The tool also did something DeepSeek did not anticipate. It re-integrates
the recorded wheel velocities offline and compares against what
`odometry_publisher` actually published. Final divergence, 0.0000 to
0.0001 m on all four runs. The integration is faithful.

Read carefully, that second result is narrower than it looks, and §4 below
is about the gap it leaves.

---

## 2. The rotation-scaling argument is right, and it is new here

This is the best thing in the reply.

> Run 1 had ~724° of commanded rotation and produced −3.85° of phantom yaw.
> Run 2 had ~365° and produced −4.49°. If this were a scale error on `wz`,
> the error should scale with total rotation. It doesn't. The shorter run
> has *more* error. That rules out a simple multiplicative bias on yaw rate.

The numbers are correct, read straight off §17.56's table. The inference is
correct too. And although this repo recorded both runs and computed a
per-metre rate for each, it never explicitly asked what the error is
proportional to. So this is a real contribution from outside.

Pushing it further than DeepSeek did, because the answer gets sharper. Four
candidate proportionalities, scored against the two runs:

| Model | Run 1 | Run 2 | Predicted run 2 from run 1 | Observed | Miss |
|---|---|---|---|---|---|
| ∝ rotation | 723.8° | 364.5° | 1.94° | 4.49° | 2.3× |
| ∝ distance | ~6.46 m | 12.04 m | 7.17° | 4.49° | 1.6× |
| ∝ time | ~216 s | 482 s | 8.59° | 4.49° | 1.9× |
| **constant per run** | −3.85° | −4.49° | **3.85°** | **4.49°** | **1.17×** |

Run 1's distance and duration are derived by subtracting §17.56's figures
from the two-run combined totals in §17.57 (698 s, 18.5 m), not read
directly, so treat those two rows as approximate. The ranking survives the
uncertainty comfortably.

Nothing here is proportional to anything. The quantity that stays closest
to constant is the raw magnitude, about −4° per run, while rotation differs
by 2×, distance by 1.9× and duration by 2.2×. Two points is a hint and not
a result. But it is a hint that points somewhere specific: at an error that
accrues a bounded number of times per run rather than continuously.

Which kills DeepSeek's own candidate (a) and promotes its candidate (b).

**The Stage H drive tests this for free.** §17.56's perimeter route is the
route Stage H drives. A third run on identical geometry, and if the phantom
yaw comes back near −4.5° again, per-run constancy goes from hint to
replicated observation at zero extra cost. If it comes back near −2°,
matching is correcting heading and that is a different and also interesting
result. Either way, record the heading closure. It is free data on the most
open question in the project and the drive is happening regardless.

---

## 3. The integer-division hypothesis is falsified from source

DeepSeek's candidate (a):

> The 2× encoder resolution difference is a rounding trap. If the ESP32
> firmware does any integer arithmetic, fixed-point scaling, or integer
> division when reconciling front and rear counts, you get a systematic
> truncation bias. Check the firmware for integer division, fixed-point
> types, and any place where front and rear counts are put into the same
> variable.

Checked. The CPR figures are right (`aislebot_esp32.ino:143-147`, fronts
186264, rears 93132, exactly 2× apart, which is a genuinely sharp thing to
notice from a document). The arithmetic is not.

```c
const float ENCODER_CPR[NUM_MOTORS] = { 186264.0f, 186264.0f, 93132.0f, 93132.0f };
...
int32_t delta   = readEncoderDelta(i);
float   rev     = (float)delta / ENCODER_CPR[i];
float   raw_vel = rev * (2.0f * PI) / PID_DT;
motors[i].position_rad += (double)rev * 2.0 * PI;
```

`ENCODER_CPR` is a float array, `delta` is cast to float before the
division, and accumulated position widens to double. There is no integer
division and no fixed-point anywhere in the count-to-velocity path. Front
and rear counts are never mixed in one variable; each motor divides by its
own constant. Quantisation is 0.0034 rad/s front and 0.0067 rad/s rear
against drive speeds around 1.3 rad/s, which is noise, not bias.

Dead. Worth having asked.

---

## 4. Where the elimination argument still has a hole, and DeepSeek got close

DeepSeek's candidate (b), which it stated as a guess:

> Turn-onset/offset transient in the PID. If each turn has a small
> consistent overshoot or undershoot during acceleration, the odometry
> integrates that error.

This survives, and reading the source makes it considerably more concrete
than DeepSeek could have known. There is a real mechanism here, and this
repo has never looked at it.

The firmware computes two independent things from the same encoder counts.
One is `position_rad`, an exact unfiltered count integral accumulated in
double. The other is `actual_velocity`, a low-pass filtered velocity:

```c
motors[i].actual_velocity = VEL_FILTER_ALPHA * raw_vel
                          + (1.0f - VEL_FILTER_ALPHA) * motors[i].actual_velocity;
```

with `VEL_FILTER_ALPHA = 0.4`, about a 15 ms time constant at the 100 Hz
PID rate.

Telemetry publishes `actual_velocity`, the filtered one
(`aislebot_esp32.ino:1067`). `odometry_publisher.py`'s `velocity_cb`
integrates those velocities, rectangular rule, against a dt measured from
ROS message arrival times:

```python
self.theta += wz * dt
```

So the exact count integral exists on the microcontroller, is correct by
construction, and is not what the robot's pose is built from. Pose is built
from a filtered velocity sampled at 20 Hz off a 100 Hz filter and
multiplied by a jittery ROS-side dt.

An exponential moving average has unity DC gain, so on its own it does not
bias an integral over a run that starts and ends at rest. Two things break
that.

First, the sampling. A 20 Hz sample of a 100 Hz filtered signal, integrated
rectangularly against wall-clock dt, does not preserve the integral of the
underlying quantity when the signal is accelerating. Error is proportional
to the second derivative, so it lands entirely on the accelerations and
decelerations and vanishes at constant speed.

Second, the asymmetry. There is a slew limiter on the target
(`float step = max_wheel_accel * PID_DT`), so the velocity profile going
into a turn is not the mirror of the profile coming out of it. When accel
and decel are shaped differently, the rectangular-rule errors on the two
halves do not cancel.

That gives an error which is sign-consistent, bounded in magnitude, and
accrues once per maneuver rather than per degree or per metre. Which is
precisely the per-run-constant signature §2 above just measured.

**And `wheel_forensics.py` cannot see any of it, by construction.** The
tool re-integrates the recorded velocities and compares against published
odometry. Both sides of that comparison consume the same already-filtered,
already-sampled quantity. Agreement to 0.0001 m proves `odometry_publisher`
faithfully integrates what it was handed. It proves nothing at all about
whether what it was handed is what the wheels did.

`Phase2_Without_IMU.md` §5.4.1 currently says what survives elimination is
"encoder or wheel-radius scale error, or a rigid-consistent slip mode where
all four wheels slip together." That list is incomplete. A third survivor
belongs on it: **bias in the velocity path itself, upstream of every
instrument fitted, from filtering and sampling rather than from physics.**

This does not weaken the Phase 2 argument. It arguably strengthens it,
because it is a second independent reason the wheel-only instrument set has
a blind spot, and it is one an IMU also resolves.

### The check, which is cheap and nobody has run it

Compare `Δposition_rad` against `Σ(actual_velocity × dt)` over a full run,
per wheel. If they agree, the filter and sampling path is exonerated and
what is left really is scale error or rigid slip. If they diverge, and
diverge by roughly the phantom yaw, that is the answer to a question this
project has carried since 3 Sep.

The catch is that `position_rad` only ships in telemetry mode 2, the
extended `<L2>` format (`aislebot_esp32.ino:1070`). Normal drive logging
uses the 13-column compat form, which drops it. So this is not free from
the CSVs already on disk. It costs one drive logged in extended mode.

There is a drive happening today anyway.

---

## 5. Falsified from measurements already in the repo

Three of DeepSeek's LiDAR suggestions are answered by work that predates
the brief it was given.

**`isSingleChannel`.** DeepSeek suggests the setting may be wrong for the
hardware and halving the return rate. `LiDAR_SLAM_Bringup.md` and
`Research_Journal.md` §1534 record the test: running the X4 Pro as
two-way, `isSingleChannel: false`, makes it die outright with `Fail to
start the lidar` and health code −2. The `Fail to get baseplate device
information` log line is expected on this part and harmless. Settled by
trying it.

**`sample_rate: 3` or `4` for better SNR.** The X4 Pro datasheet gives
ranging frequency as a fixed 5000 Hz (`X4Pro_Datasheet_Findings.md` §207).
`sample_rate` declares what the device does; it is not a throttle on
integration time. The `5000/f` model was then confirmed empirically on
3 Sep, 430 beams measured against 441 predicted at the real 11.35 Hz, a
2.5% error. And the companion parameter `frequency` is already proven inert
on this unit because `support_motor_dtr: false` means the driver never
commands the motor at all. Changing `sample_rate` downward would make the
driver's arithmetic disagree with the hardware, not lengthen a dwell.

**Room reflectivity.** Fair as a general point and not testable in the time
available, since it needs a second room and a controlled comparison. Filed,
not actioned.

---

## 6. The LiDAR mount point survives, narrowed

DeepSeek offers this as the assumption nobody has challenged:

> The LiDAR is mounted correctly and its scan plane is where the URDF says
> it is. You've validated the scan relay against known objects, but you
> haven't validated the physical LiDAR mount against a known world frame.
> Those are different things.

Half right, and the half that is right is the half it did not name.

Bearing was validated, thoroughly, on 11 Aug. `LiDAR_Orientation_Calibration.md`
records a single opaque block placed at three known bearings, which found a
front/back reflection nobody suspected and solved it to
`reported = 270° − true (mod 360°)`. That work also caught a subtler trap
worth re-reading: an earlier attempt assumed REP-103 and landed 90° away
from the answer that actually matches this robot. So the azimuth mapping is
measured, not assumed, and DeepSeek's proposed 360°-rotation test would be
re-running a test that has already been run and passed.

**Scan-plane tilt is a different degree of freedom and it genuinely has not
been measured.** That much is a real gap.

Whether it is worth a slot in eight days is a separate question, and I do
not think it is. At the 1.6 m median scan range in this lab, a 2° tilt
inflates measured range by 1.6/cos(2°) − 1.6, which is about 1 mm. Against
a datasheet relative error of 3.5% in that band, roughly 56 mm, that is
three orders of magnitude below the noise it would hide in. Tilt matters at
long range and this configuration caps at 5 m. Record it as an
unmeasured assumption in the report, which is honest and costs nothing, and
do not spend a drive on it.

---

## 7. The no-return clearing idea is the one live LiDAR lever

DeepSeek on `invalid_range_is_inf`:

> The right experiment is not `true` vs `false`. It's a finite no-return
> range. Set `invalid_range_is_inf: true` but cap the cleared range at, say,
> 2 m. This clears the nearby free space, which is where coverage is
> failing, without clearing through distant unseen obstacles. It's a middle
> path that nobody in the brief has proposed.

Correct that nobody proposed it, and it is a better idea than the binary
this repo has been avoiding for weeks. One correction on mechanism: the
ydlidar driver parameter is a boolean and has no finite-cap form, so it
cannot be done by flipping that value. It would go in `scan_relay.py`, which
already sits between the driver and everything downstream and already
implements the rear mask, so the insertion point exists and is tested.

It stays parked until Stage H is scored, and that is deliberate rather than
dismissive. The evening handoff's §5 makes the call explicitly: re-derive
the coverage question after matching is scored, because a map built with
loop closure is not the same map. Tuning the coverage lever against a map
whose geometry is about to change would measure the wrong thing. If Stage H
is kept, this is the first coverage experiment to run afterwards. If Stage H
is reverted, it is still the first one.

---

## 8. Where DeepSeek is right about framing

**Calling this SLAM.** Under Stage G, with matching off and no corrections
ever observed, DeepSeek is right that `map→odom` is constant and the honest
description is mapping with dead-reckoned pose. §17.56 had already reached
the sharper version of the same worry from the inside: `graph_residuals.py`
found no publisher on the graph topic twice, and the live hypothesis became
that `use_scan_matching: false` suppresses pose-graph construction
entirely, making `do_loop_closing: true` inert and slam_toolbox a pure
scan-stamper. That was logged as unverified.

Stage H settles it, and the check is now wired into the deploy. Section 6 of
`tools/verify_live_config.sh` reads `ros2 topic info
/slam_toolbox/graph_visualization` before the first metre. A publisher count
of zero means loop closure is unreachable and the drive's most valuable
success criterion cannot be scored, which is something to learn while parked
rather than afterwards from a CSV.

**The coverage gate.** DeepSeek argues the bounding-box unknown-cell
fraction measures the room's shape rather than the drive's quality, and
proposes coverage of free space within the expected navigation radius
instead. That is a better gate and the reasoning for it is sound. Same
deferral as §7: restate it after Stage H is scored, and restate it in the
report before the exam rather than quietly relaxing it, which is the part
DeepSeek is most right about.

**The no-IMU argument being circular as written.** This lands. If LiDAR
precision only reaches pose through scan matching, and scan matching was
measured to make pose worse, then the error-budget framing assumes its own
conclusion. The honest version, which DeepSeek states well, is that with
matching off there is no closed-loop correction of heading at all, so
heading error is the one error that never gets fixed, and Phase 2 closes as
characterised rather than optimal. `Phase2_Without_IMU.md` §5.4.1's
elimination argument is already most of the way there. §4 above adds a
second blind spot to it.

And DeepSeek's point that a gyro is a *diagnostic* and not only a fusion
input is better than the 88%-drift-reduction citation it replaces. An
independent heading measurement is what turns the phantom yaw from an
anomaly into a measurement.

---

## 9. Priority ordering

DeepSeek says, with some force, that the multi-lap coverage experiment is
the wrong next step because it measures a symptom whose causes are
upstream.

Agreed, and so did the evening handoff, independently and for a different
reason. §5 of that document: *"Not on this list, deliberately: more laps of
the circle for G4 coverage. That plan was correct under Stage G and is
superseded by Stage H."* Two models reaching the same call from different
directions is mild evidence the call is right.

Where the ordering has gone stale: DeepSeek's Day 1 is already done, its
LiDAR items in §5 above are closed or falsified, and its Day 3 is the thing
the handoff already dropped. What is left of its plan that this session
should actually carry is the §4 velocity-path check, riding along with a
drive that is happening anyway.
