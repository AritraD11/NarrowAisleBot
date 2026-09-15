# Gap 3 closed: the slip residual, measured over four drives

**15 Sep 2026.** Computed offline from the motor telemetry CSVs already
recorded for the 15 Sep G4 campaign (`../circular_loop_15sep/`). No new
driving. This is the measurement `Phase2_Without_IMU.md` §5.4 has been
calling free since 14 Sep, and it was.

---

## First, a correction to the documented command

`Phase2_Without_IMU.md` §5.4 said:

```bash
./tools/wheel_forensics.py --csv ~/aislebot_logs/<run>_wheels.csv     # WRONG
```

`--csv` is an **output** flag. It writes every sample to a flat CSV. The run
to analyse is a **positional** argument, and there is no `_wheels.csv` file in
this project's naming at all. The real invocation:

```bash
python3 tools/wheel_forensics.py docs/evidence/circular_loop_15sep/run_20260915_154615.csv
python3 tools/wheel_forensics.py <run>.csv --json out.json    # summary as JSON
python3 tools/wheel_forensics.py --selftest                   # validate the tool
```

Same class of stale-documentation bug as `map_integrity.py`'s two-argument
form, found the same day. Both docs described an interface the tool does not
have. §5.4 is corrected in place.

**The tool validates itself before use.** `--selftest` passed: the slip
residual is zero to 7.18e-15 over 20000 random rigid twists, a 15% single-wheel
slip is detected at 0.450 rad/s, forward kinematics inverts the teleop to
2.22e-16, and a >1 s telemetry gap is skipped rather than integrated across.

---

## The residual

Four wheels drive three degrees of freedom, so the wheel-speed vector is
over-determined by exactly one dimension. That leftover dimension is

```
slip = FR + 1.142656*FL - 1.142656*RR - RL          [rad/s]
```

where 1.142656 is `K_outer/K_inner` = 0.5607/0.4907. It is identically zero for
any rigid non-slipping motion, whatever the twist. Non-zero means at least one
wheel is not tracking the body. It needs no ground truth, no LiDAR and no map.

## Result

| Run | Trajectory | Median (moving) | p95 | Max | Episodes > 0.5 rad/s |
|---|---|---|---|---|---|
| `_140253` | wobbled, 1 lap | 0.0392 | 0.1244 | 0.3541 | **0** |
| `_154615` | 1 m circle, 3 laps, RAW | 0.0356 | 0.1123 | 0.2885 | **0** |
| `_164745` | same, AISLE | 0.0353 | 0.1140 | 0.2544 | **0** |
| `_172133` | same, STRICT | 0.0352 | 0.1113 | 0.2722 | **0** |

Worst instantaneous residual across all four drives converts to a rim speed of
**0.019 to 0.027 m/s**, against a drive speed of 0.10 m/s. The median while
moving, 0.035 rad/s, is 0.0027 m/s of rim speed, about **2.7% of drive speed**.

**Physical wheel slip is small, bounded, and remarkably stable across
trajectory type.** The deliberately irregular wobbled run sits within a few
percent of the three clean circles. Not one sample in four drives crossed the
0.5 rad/s episode threshold.

---

## The second result, which was not the one being looked for

The same tool re-integrates the recorded wheel velocities offline, with the
same model, and compares against what `odometry_publisher` actually published.

| Run | Max wheels-vs-odom divergence | Final divergence |
|---|---|---|
| `_140253` | 0.0100 m | **0.0000 m** |
| `_154615` | 0.0077 m | **0.0001 m** |
| `_164745` | 0.0102 m | **0.0001 m** |
| `_172133` | 0.0156 m | **0.0001 m** |

`odometry_publisher` is integrating faithfully. Whatever error exists is
upstream in the wheels or downstream in SLAM, and **is not in the integration
code.** Nothing in this repo had ever checked that.

On run `_154615` all three estimators land on the same point:

```
                 x         y     |pos|   yaw deg
wheels      -0.002    -0.001     0.002     -0.02
odom        -0.002    -0.001     0.002     -0.03
SLAM map    -0.002    -0.001     0.002     -0.03
```

The operator's tape and protractor at the mark on that same run read
**about -3 degrees.**

---

## What this means for Phase 2, stated carefully

Three independent estimates agree with each other to 0.001 m and 0.01 degrees,
and disagree with the floor by roughly 3 degrees. They agree because they all
consume the same wheel data. The disagreement is therefore upstream of all
three.

The residual rules out the loudest candidate: **the wheels are not slipping
much.** The offline reconstruction rules out the second: **the integration is
correct.** What is left is exactly the error class `wheel_forensics.py`'s own
docstring names as invisible to it:

> Encoder scale errors are likewise invisible to the residual, they need a tape
> measure. If ALL FOUR slip identically the wheel vector stays rigid-consistent
> and nothing here will notice.

So the remaining candidates are encoder or wheel-radius scale error, or a
rigid-consistent slip mode where all four wheels slip together. **Both are
structurally invisible to every instrument currently on this robot.**

**This is a stronger argument for an IMU than the error budget in
`Phase2_Without_IMU.md` §3, and it is a different argument.** §3 says an
inertial sensor addresses a term that is not binding at 5 m. This says the
wheel-only instrument set has a blind spot that has now been narrowed by
elimination to a specific error class, and that closing it needs either
external ground truth or an independent heading source. That is a measured
observability gap rather than a general recommendation, and it is the answer to
Phase 2's actual deliverable clause: *"an explicit account of which sensors are
required."*

---

## Caveat, and the one step still owed

These four runs are all from 15 Sep. **The phantom-yaw measurement is from
3 Sep** (`Research_Journal.md` §17.55 and §17.56), a different pair of runs, and
their telemetry CSVs are on the Pi rather than in this repo. So the claim
"phantom yaw is not an integration bug" is supported by today's runs and is
**not yet directly tested on the runs where phantom yaw was actually
observed.**

To close that properly, pull these two off the Pi and run the same tool:

```bash
# on the Pi
ls ~/aislebot_logs/run_20260903_162401* ~/aislebot_logs/run_20260903_174352*
# then, wherever the CSVs land
python3 tools/wheel_forensics.py run_20260903_162401.csv
python3 tools/wheel_forensics.py run_20260903_174352.csv
```

If wheels-vs-odom divergence is near zero on those too, the phantom yaw is
confirmed upstream of the estimator on the runs that produced it, and the
elimination argument above is complete rather than inferred.

---

## Files

- `*_slip.json`: machine-readable summary per run (slip max, episode count,
  per-wheel rms error, saturation, arc length)
- `*.txt`: the full tool output per run, including the per-wheel table and the
  wheels/odom/SLAM comparison
- Source telemetry: `../circular_loop_15sep/run_2026091*.csv`
