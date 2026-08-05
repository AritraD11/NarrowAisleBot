# PID & Feedforward Calibration — v3.0

Where every number in `aislebot_esp32.ino` came from, which ones are
measured, which one is still an estimate, and the exact bench run that
would settle it.

**Status: air-calibrated on confirmed-good encoder hardware. Not yet
ground-calibrated.**

---

## 1. What the hardware actually is now

The 4 Aug 2026 bench campaign (`Bench_Test_Map.md`) changed two things
that invalidate every gain shipped before it.

**The front encoders are not the rear encoders.** FR and FL now carry
GTK08 1000-PPR units; RR and RL keep the original RMCS-2086 500-line
optical. Exactly 2× apart:

| Motor | Encoder | PPR | CPR at the wheel |
|---|---|---|---|
| FR, FL | GTK08 | 1000 | 1000 × 4 × 46.566 = **186 264** |
| RR, RL | RMCS-2086 optical | 500 | 500 × 4 × 46.566 = **93 132** |

v2.0 hard-coded a single `ENCODER_CPR = 93132`. On this hardware that
makes the fronts report **double** their true speed. The controller
believes them and backs off, so the fronts settle at roughly **half** the
commanded velocity while the rears track correctly — a permanent,
silent, speed-dependent yaw bias that no amount of gain tuning fixes.
This is the single most important change in v3.0.

The bench cross-check confirms the constants rather than just assuming
them: at matched PWM and duration the front/rear raw-count ratio came
out at 2.0–2.1× across hundreds of thousands of counts, on physically
identical gearmotors.

**The old per-motor spread was an artefact.** v2.0 shipped
`Kff = {42.1, 40.2, 43.7, 47.9}` — a 19 % spread between FL and RL. That
came from the era of the faulty feedback path, before the FR/FL
cross-connection was found. Re-measured on the confirmed-good path, all
four motors fall inside a **3 % band**. The four near-identical numbers
in v3.0 are what the hardware actually does.

### How two different encoders produce the same number

Worth being explicit about, because "half the robot has a different
sensor" sounds like it should need correction factors scattered through
the code. It doesn't. The entire mechanism is one array and one division.

Both encoders measure the same physical thing — rotation of the wheel —
and differ only in how finely they slice it. The velocity calculation in
`pidControlTask()` is:

```c
int32_t delta   = readEncoderDelta(i);              // counts this tick
float   rev     = (float)delta / ENCODER_CPR[i];    // counts -> revolutions
float   raw_vel = rev * (2.0f * PI) / PID_DT;       // revolutions -> rad/s
```

`ENCODER_CPR[i]` is *counts per revolution of that motor's own wheel*.
Dividing each motor's raw count by its own constant converts a
sensor-specific quantity (edges) into a physical one (revolutions). The
2× scale difference cancels exactly, because the encoder that produces
twice as many counts is divided by a twice-larger number:

| One full wheel revolution | Front (GTK08) | Rear (RMCS-2086) |
|---|---|---|
| Counts produced | 186,264 | 93,132 |
| `ENCODER_CPR[i]` | 186,264 | 93,132 |
| `delta / CPR` | **1.000 rev** | **1.000 rev** |

Two wheels turning at identical speed report identical rad/s. Everything
downstream — PID, feedforward, the mecanum IK, odometry — sees only rad/s
and never learns which encoder produced it. There is no scaling term
anywhere else in the firmware, and no per-motor special-casing.

**What genuinely differs is resolution**, and only resolution:

| | Front (GTK08) | Rear (RMCS-2086) |
|---|---|---|
| One count = | 3.37 × 10⁻⁵ rad of wheel rotation | 6.75 × 10⁻⁵ rad |
| Velocity quantum at 100 Hz | **0.0034 rad/s** | **0.0067 rad/s** |

Both sit far below the mechanical and electrical noise floor, so neither
limits the velocity loop — which is why the velocity filter can stay
light (`VEL_FILTER_ALPHA = 0.4`) without the derivative term picking up
quantisation hash. The fronts being twice as precise matters for
**odometry integration** (Phase 2), where counts accumulate over minutes,
rather than for control.

**Why getting this wrong is silent and serious.** Under a single shared
`ENCODER_CPR = 93132`, a front wheel turning one revolution reports
186,264 / 93,132 = **2.0 revolutions** — double its true speed. The
controller believes it, sees itself overshooting, and cuts PWM until the
*reported* speed matches the target, i.e. until the wheel is physically
turning at **half** the commanded velocity. The rears, correctly scaled,
track properly. The result is a permanent front/rear speed split that
scales with commanded velocity: the robot yaws under pure translation and
curves under commanded rotation, with no error, no warning, and clean
tracking in every telemetry plot — because the loop *is* tracking, just
tracking a lie. It is invisible to any test that doesn't independently
cross-check front against rear, which is exactly why the 4 Aug bench
campaign's front/rear count-ratio check (~2.0×) mattered so much.

---

## 2. Source data

Three independent in-air campaigns. All wheels free, no load.

### 2a. 4 Aug 2026 — manual drive, steady state

Reported while running, so this is true steady-state velocity. Highest
confidence point in the set.

> All four motors converge to a narrow **1.83–1.94 rad/s** band at the
> same PWM (**80**). — `Bench_Test_Map.md`

Mean **1.885 rad/s at PWM 80**.

### 2b. 4 Aug 2026 — AUTO TEST, PWM 110, 1.5 s windows

Raw counts, converted with the per-motor CPR above:

| Motor | fwd counts | rev counts | v_fwd | v_rev | mean |
|---|---|---|---|---|---|
| FR | +119 085 | −118 067 | 2.678 | 2.655 | **2.667** |
| FL | +115 121 | −115 607 | 2.589 | 2.600 | **2.594** |
| RR |  +57 416 |  −58 244 | 2.583 | 2.620 | **2.601** |
| RL |  +57 358 |  −59 139 | 2.580 | 2.660 | **2.620** |

Overall mean **2.621 rad/s at PWM 110**.

Caveat worth stating: the counting window starts from rest, so it
includes spin-up and therefore *under*-reads true steady-state velocity
by however long the mechanical time constant is. It is excellent for the
**relative** comparison between motors (identical window for all four)
and only approximate in absolute terms.

Forward and reverse agree to within 3 % on every motor, so there is no
meaningful directional asymmetry to compensate.

### 2c. 14 May 2026 — closed-loop back-calculation

From the air validation run at ±0.6 to ±2.2 rad/s, back-calculating
pwm/ω at steady state gave 46.9 / 46.9 / 45.3 / 48.4. Lower confidence
(this is the campaign with the encoder faults), but it carries one piece
of information nothing else does: **the pwm/ω ratio is higher at low
speed than at high speed.** That is the signature of static friction,
and it is why v3.0 uses a two-term feedforward.

---

## 3. The feedforward fit

A single-slope `pwm = Kff·ω` cannot be right if the pwm/ω ratio changes
with ω. Two terms can:

```
    pwm_ff  =  Kff · ω  +  Kstat · sgn(ω)
                └ viscous ┘   └ Coulomb / breakaway ┘
```

Fitting **Kff = 38, Kstat = 8** against all three campaigns:

| ω (rad/s) | model pwm | measured pwm | error | source |
|---|---|---|---|---|
| 1.50 |  65.0 |  70.4 | −8 % | 2c (low confidence) |
| 1.885 |  79.6 |  80   | −0.5 % | 2a (high confidence) |
| 2.621 | 107.6 | 110   | −2 % | 2b |
| 2.77 | 113.3 | 120   | −6 % | 2c |

Every point inside ~8 %, and the two highest-confidence points inside
2 %. Residual error is exactly what a correctly-tuned integral term is
for, and v3.0's integral closes an 8 % gap in about 0.3 s.

**Honest limitation:** the split between `Kff` and `Kstat` is *not*
well-determined by this data. Every measurement sits between ω = 1.8 and
2.8 rad/s, and over that narrow span many (Kff, Kstat) pairs fit almost
equally well — a fit with Kff = 34.5 / Kstat = 15 is barely
distinguishable. What *is* well-determined is the value of the whole
expression across the measured range, which is what the controller
actually consumes. §6 says how to separate the two properly.

Above ~3 rad/s the model extrapolates, and it will over-predict near the
top of the range because the motor approaches its rated 60 RPM and stops
behaving linearly. Over-prediction is the safe direction: the output
saturates and the integral unwinds it, rather than the wheel coming up
short.

### Per-motor values

Scaling by each motor's velocity relative to the group mean in 2b:

| Motor | rel. speed | `Kff` | `Kstat` |
|---|---|---|---|
| FR | 1.018 | **37.3** | 8.0 |
| FL | 0.990 | **38.4** | 8.0 |
| RR | 0.992 | **38.3** | 8.0 |
| RL | 1.000 | **38.0** | 8.0 |

`Kstat` is one number for all four because nothing in the data
distinguishes them — the staircase test in §6 is what gives per-motor
breakaway values.

---

## 4. PID gains

The feedforward fit hands over the plant DC gain directly:

```
    K = 1 / 38 = 0.0263 rad/s per PWM
```

For a first-order plant, **direct-synthesis (lambda) tuning** gives:

```
    Ki = 1 / (K · λ)          Kp = τ · Ki
```

where λ is the chosen closed-loop time constant and τ the plant's
mechanical time constant.

**The useful property here: `Ki` does not contain τ.** It follows from K
and λ alone, both of which are known. With λ = 0.15 s — deliberately
conservative, 15 control periods at 100 Hz:

```
    Ki = 1 / (0.0263 × 0.15) = 253      ->   Ki = 250
```

| Gain | v2.0 | v3.0 | Basis |
|---|---|---|---|
| `Kp` | 50 | **45** | τ · Ki, assuming τ ≈ 0.18 s — **estimated, see §5** |
| `Ki` | 30 | **250** | 1/(K·λ), λ = 0.15 s — fitted |
| `Kd` | 3.0 | **0.5** | small by design, see below |

### Why Ki was the real problem

At `Ki = 30`, a 0.1 rad/s tracking error moved the output **3 PWM per
second**. Closing a realistic 10 PWM feedforward gap took over three
seconds — which is precisely the 3.79 s worst-case settling time
recorded on 14 May, and precisely why the journal noted that "the
integral term has been silently absorbing the under-calibration." It was
absorbing it, just far too slowly to matter inside a manoeuvre.

At `Ki = 250` the same error moves the output 25 PWM per second, and
that same 10 PWM gap closes in **0.4 s**.

The old anti-windup made this worse, not better: `INTEGRAL_MAX = 200`
with `Ki = 30` permitted an integral term of **6000 PWM** — 23× the
output range. The clamp existed but could never bind. v3.0 clamps the
integral against the PWM headroom genuinely left over after FF + P + D,
recomputed every tick, so windup is structurally impossible and recovery
from saturation is immediate.

### Why Kd is small now

Against a first-order plant with a matched PI controller, derivative
action contributes nothing — it only amplifies noise. `Kd = 0.5` damps
the *unmodelled* lag (driver delay, gearbox compliance, the velocity
filter itself) and no more. At a typical step acceleration of ~30 rad/s²
that is about 15 PWM of damping; v2.0's `Kd = 3.0` would have applied 90
PWM, actively fighting the acceleration the controller had just asked
for.

`Kd` also now acts on **measurement**, not error. The Pi sends stepped
setpoints at 20 Hz; differentiating the error means every one of those
steps produces a derivative spike proportional to the step size.
Differentiating the measurement gives identical damping with no kick.

---

## 5. The one number that is still a guess

**`Kp` — because the plant time constant τ has never been measured on
this robot.**

Every bench run so far has logged steady-state points only. τ lives in
the *transient*, and no campaign has captured one. `Kp = 45` assumes
τ ≈ 0.18 s, which is plausible for a 100 W motor behind a 47:1 planetary
but is an assumption, not a measurement.

What that uncertainty actually costs:

| If τ is… | correct Kp | shipped Kp = 45 behaves as |
|---|---|---|
| 0.08 s | 20 | over-damped — sluggish, safe |
| 0.18 s | 45 | matched |
| 0.30 s | 75 | under-damped — slower than it could be, still stable |

`Kp` being wrong within this range costs response speed, not stability —
`Ki`, which is the gain that was genuinely broken, is right regardless.
So this is safe to fly with, and worth 40 seconds on the bench to fix.

---

## 6. The bench runs that would finish this

All three are already implemented in `tools/nab_pid_logger.py`, which
runs on the Pi, drives the sequence over serial, and writes a CSV
straight to `~/aislebot_logs/`. No serial-monitor copy-paste.

**Wheels in the air for all of them.**

### Run 1 — plant identification (highest value, ~40 s)

```bash
./tools/nab_pid_logger.py --test plant
```

Open-loop PWM steps with the PID bypassed, logged at 50 Hz. Measures τ
and K per motor and prints the resulting Kp/Ki directly. **This is the
run that removes the last estimate from §5.**

### Run 2 — static friction staircase (~2 min)

```bash
./tools/nab_pid_logger.py --test staircase --max-pwm 60
```

PWM stepped up from rest in increments of 2 until each wheel breaks
away. Gives per-motor `Kstat` and separates it from `Kff` properly (§3),
which the current data cannot do.

Worth running **twice** — once in the air, once on the floor. The
difference between those two numbers *is* the ground-load correction.

### Run 3 — closed-loop verification (~1 min)

```bash
./tools/nab_pid_logger.py --test steps --setpoints 1.0,2.0,3.0,4.5
```

Rise, overshoot, settle, steady-state error, PWM saturation. This is the
run that says whether a gain set is any good. To compare candidates in
one go:

```bash
./tools/nab_pid_logger.py --test sweep \
    --gains "45,250,0.5  70,250,0.5  45,400,1.5"
```

Every CSV also opens directly in `aislebot_pid_analysis_v2.py` — the
first 13 columns are unchanged.

---

## 7. Before this touches the floor

The gains above are **air values**. Ground load raises feedforward by an
expected 10–30 %, and raises `Kstat` by considerably more than that.

1. Re-run the staircase on the floor. Push the new numbers with
   `<K,fr,fl,rr,rl>`, then re-run `--test steps` and check saturation.
2. Re-run plant ID on the floor. K drops under load; `Ki = 1/(K·λ)`
   therefore rises.
3. **Lower `max_wheel_speed`.** At the air value of 5.20 rad/s the worst
   motor needs 38.4 × 5.2 + 8 = 208 PWM, leaving 47 PWM (18 %) of
   authority for the controller. A 25 % ground-load increase eats all of
   it and the controller has nothing left to regulate with. Drop it to
   roughly **4.2 rad/s** — `<X,4.2>` live, then make it permanent.
4. Leave the trips on (`<Y1>`, the default). The runaway trip is the
   only thing standing between a sign-inversion fault and a stripped
   gearbox.

Ground calibration is also the point to revisit `max_wheel_accel`
(currently 12 rad/s²). In the air it is barely exercised; on the floor
with a loaded chassis it becomes the main defence against wheel slip and
current spikes.

---

## 8. Quick reference

```c
ENCODER_CPR = {186264, 186264, 93132, 93132}   // FR FL | RR RL
Kff         = { 37.3,   38.4,   38.3,  38.0}   // PWM per rad/s
Kstat       = {  8.0,    8.0,    8.0,   8.0}   // PWM breakaway
Kp = 45      Ki = 250     Kd = 0.5             // 100 Hz loop
max_wheel_speed = 5.20 rad/s   (= 0.396 m/s)   // AIR — lower for ground
max_wheel_accel = 12.0 rad/s²
```

Live tuning without a reflash:

| Command | Sets |
|---|---|
| `<G,kp,ki,kd>` | PID gains |
| `<F,fr,fl,rr,rl>` | `Kff` per motor |
| `<K,fr,fl,rr,rl>` | `Kstat` per motor |
| `<A,accel>` | slew limit, 0 = off |
| `<X,vmax>` | wheel speed clamp |
| `<I>` | dump everything currently loaded |

Live values are lost on reset — once a set is confirmed, write it into
`aislebot_esp32.ino` and reflash.
