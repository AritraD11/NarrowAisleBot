# Adaptive Control & Dynamic Modeling — Citation Validation, Feasibility, and Roadmap

Written in response to two research documents (`Asymmetric_Mecanum_AMR_Control_Architecture.md` and a deep-research report, both dated 7 Aug 2026) proposing that the project move from static PID+feedforward to online parameter estimation, disturbance observers, and full dynamic modeling. This document: (1) verifies the citations in the deep-research report against the actual literature via Scite, since one is dated 2026 and none had been independently checked; (2) gives an honest engineering assessment of both documents' recommendations against what's actually been measured on *this* robot; (3) answers the ML question directly; (4) lays out a staged, feasibility-rated roadmap.

**Bottom line up front:** the core architectural insight in both documents — separate "is my structural model right" from "should I retune PID live," and prefer adapting the *feedforward model* over adapting the *PID gains* — is correct and matches standard control theory. But it is not a reason to treat the calibration work in progress as obsolete; it's the reference baseline that any adaptive method needs to initialize from and be checked against. One citation's specific claims don't match the paper it's attached to. And "smart AMR" does not imply machine learning — the right tools here (RLS, Kalman filtering, disturbance observers) are 60-year-old classical estimation theory, not trained models.

---

## 1. Citation validation (via Scite)

Four named citations in the deep-research report, checked against the actual literature. Full search details available on request; verdicts below.

| Citation | Verdict | Notes |
|---|---|---|
| **Williams, Carter & Gallina (2002)**, "Dynamic model with slip for wheeled omnidirectional robots," *IEEE Trans. Robotics and Automation*, 18(3):285–293. DOI: [10.1109/TRA.2002.1019459](https://doi.org/10.1109/tra.2002.1019459) | ✅ **Verified, accurately represented** | Real paper, 207 citing publications. Abstract confirms exactly what was claimed: derives the dynamics model, measures friction coefficients experimentally, and — the specific detail cited — identifies that "solid material existing in the discontinuities between omni-directional wheel rollers plays an equally important role in determining... dynamic slip motion, even at low rates." |
| **Li & Li (2025)**, "Dynamic Modeling and Disturbance-Observer-Enhanced Control for Mecanum-Wheeled Vehicles Under Load and Noise Disturbance," *Mathematics* (MDPI), 13(5):789. DOI: [10.3390/math13050789](https://doi.org/10.3390/math13050789) | ✅ **Verified, accurately represented** | Real, open-access. Cascaded state-space model (PWM→torque, torque→speed), Lagrangian derivation, IMC+DOB controller. The specific numbers cited (97.6% faster stabilization than IMC, 98.3% faster than PID) are the paper's own reported results, not paraphrased loosely. |
| **Villarreal-López, Coral-Enríquez & Hurtado-Cortés (2026)**, "Extended-state observer control with online payload identification for HRI in series elastic actuators," *TELKOMNIKA*, 24(4):1409. DOI: [10.12928/telkomnika.v24i4.27787](https://doi.org/10.12928/telkomnika.v24i4.27787) | ✅ **Verified real** — the 2026 date is genuine, not a hallucination | Worth flagging what it's *actually* about: series elastic actuators for human-robot interaction (e.g. robot arms), not mobile-robot payload. The technique (online payload ID feeding an extended-state observer) transfers conceptually, but this is a same-technique-different-domain citation, not a direct AMR precedent. The deep-research report's "in principle" phrasing was appropriately hedged — fair citation, just don't read it as AMR-specific validation. |
| **Zhang et al. (2019)** — cited as "adaptive SMC for mecanum tracking under slip... fuzzy/SMC method achieved good accuracy under payload changes," with a further reference to "HFN-based fuzzy SMC" | ⚠️ **Paper is real; the specific claims attached to it are not what that paper says** | The real 2019 Zhang mecanum paper is: Renhui Zhang, Haiyan Hu & Yongsi Fu, "Trajectory tracking for omnidirectional mecanum robot with longitudinal slipping," *MATEC Web of Conferences*, 256:02003. Open access, full text checked directly. It is a **Lyapunov-based adaptive nonlinear controller** — not sliding-mode control, no fuzzy logic anywhere in it, and the paper addresses **longitudinal slip**, not payload variation. None of "SMC," "fuzzy," or "payload" match this paper's actual content. This looks like either a mis-attribution or a merge of details from multiple unnamed sources under one citation. **Recommendation: don't cite this claim as "Zhang et al. 2019" in anything written for your APS or a paper** — the mecanum+SMC+fuzzy+payload combination this citation is used to support may exist somewhere in the literature, but it isn't in the paper actually named. |

**One more claim spot-checked, not attached to a named citation:** the deep-research report states Nav2's MPPI "was demonstrated at 100+ Hz on an i5 CPU." A directly relevant 2025 benchmark (Kulathunga et al., *Journal of Field Robotics*, comparing Nav2 local planners) measured MPPI at **20 Hz** in their test configuration, with TEB and NMPC at 12–17 Hz. This doesn't make the "100+ Hz" claim false — MPPI's frequency is highly sensitive to sample count and horizon length, and much higher rates are achievable with aggressive tuning — but it means **don't assume 100+ Hz out of the box on the Pi 5**. Budget time to tune and measure it empirically once you get there, the same way every other number in this project has been measured rather than assumed.

**What this exercise is worth, beyond fact-checking:** three of four named citations checked out cleanly, including a paper you'd have had every reason to assume was hallucinated on sight (2026 date). That's a genuinely good hit rate for AI-generated research synthesis, and worth knowing before you decide how much to trust the rest of either document's unverified claims. The one miss is exactly the kind of error that's invisible unless someone actually opens the paper — which is the whole reason to check before it goes in front of a committee.

---

## 2. Where the documents are right

Both are making a structurally sound argument, worth keeping regardless of the citation issue above:

- **Adapt the feedforward model, not the PID gains, as the primary mechanism.** This matches something already established in this project's own calibration work: feedforward supplies ~90% of the required output, PID cleans up the rest (`docs/PID_Calibration.md` §4). If the feedforward model is wrong, PID is doing 100% of the work through a slow channel (integration) — which is *precisely* what the v2.0→v3.0 recalibration fixed (Ki 30→250). Making the feedforward model track reality automatically, rather than re-deriving it by hand every time conditions change, is the natural next step of the same idea, not a different one.
- **RLS/Kalman-based parameter estimation is not the same question as self-tuning PID**, and conflating them is a real and common mistake. The user's framing of this distinction in their own message is correct.
- **Disturbance observers are a good fit for payload/CoM changes specifically.** This is the single most operationally relevant risk for an industrial-deployment AMR (see §4).
- **MPPI is a mid-level trajectory controller, not a replacement for the wheel-velocity loop.** Confirmed independently by the citation check above — every source found agrees MPPI assumes the low-level loop can track its (vx, vy, ω) output. This project's existing architecture (ESP32 wheel PID underneath, Nav2/MPPI above once Phase 4 arrives) is already the right shape.

---

## 3. Where I'd push back or add nuance

### "The modelling method we are using is very old and trivial" — disagree, and this matters for how you sequence the work

PID + two-term feedforward, tuned via IMC/lambda synthesis from a measured plant model, is not a naive baseline — it's the textbook-correct foundation, and it's what the adaptive methods in both documents would *sit on top of*. An RLS estimator updating a feedforward model whose *structure* is wrong (wrong friction model, wrong Kp/Ki relationship, unmeasured plant time constant) will converge to compensate for structural error as if it were legitimate parameter drift — you won't be able to tell "battery sagged" from "the model was never right to begin with." The static calibration in progress isn't work being superseded by this research; it's the reference the online estimator needs in order to know what "normal" looks like. **Finish it first.** Concretely: the ground `staircase`/`plant` tests are still the next action, not a detour from this plan.

### The battery-voltage-sag scenario is weaker on this specific robot than the documents assume

Doc 1's illustrative timeline (25V morning → 22V lunch → 20V evening, "motors get weaker") is a real phenomenon in general, but this project already made a specific hardware choice that blunts it: the battery is LiFePO₄ (`Master_Reference.md` §2.5/§3.5), chosen specifically for its flat discharge curve — "the flatter discharge curve keeps motor performance consistent until the battery is genuinely empty," in this project's own documented reasoning. LiFePO₄ sits near its nominal voltage for most of its usable capacity and then drops sharply near empty, rather than sagging steadily like Li-ion or lead-acid. The battery-compensation motivation in both documents is real *in general* and worth building for regardless (see the roadmap below — it's still useful, and it's needed once the pack does approach empty), but it is not the most urgent case for *this* robot. **Payload and floor-surface variation are.**

### Payload/CoM variation is the real near-term case, and it's already in this project's own open questions

`Research_Journal.md` Appendix B.5 already asks: *"Should per-motor Kff be a single scalar, or a 2-D table over (target velocity × load)?"* — logged before either research document existed. This project's roadmap already anticipates exactly the problem both documents are describing, and it's concrete: the robot's own cargo/UV-arm subsystem (Part IX) is a variable, non-trivial payload directly on the chassis. This is the case worth prioritizing.

### The ESP32-feasibility assessment in the deep-research report is more pessimistic than it needs to be, for the specific case that matters here

Doc 2 says: *"On the ESP32, heavy iterative algorithms (UKF for parameters, etc.) may be too much; but a simple RLS (few parameters) at low frequency might work."* That's a fair general caution — but our actual need is a **2-parameter RLS** (Kff, Kstat) per motor, not a general UKF. Two-parameter linear RLS is a handful of scalar multiply-adds per update (see §5) — nothing an ESP32 running a 100 Hz loop with 10 ms of budget per tick will notice. Don't let the general caution about "heavy iterative algorithms" cause hesitation about the specific, small case this project actually needs first.

### Two different Kalman filters are being discussed as if they're one, and they should stay separate

Both documents move between "estimate motor parameters online" and "fuse IMU+encoders+LiDAR for pose" without always marking which one they mean. These are different filters, different states, different places in the architecture, and conflating them will cause real design mistakes:

| | Per-motor parameter estimator | Pose/velocity state estimator |
|---|---|---|
| Estimates | `Kff`, `Kstat` (2 numbers per motor) | robot (x, y, θ) and velocities |
| Input | commanded PWM, measured wheel velocity | wheel odometry, IMU, SLAM pose |
| Runs on | **ESP32**, inside the existing 100 Hz loop | **Pi 5**, via `robot_localization` |
| Status in this project | **Not yet built — this document's Stage 1** | **Already planned and configured** (`ekf_params.yaml`, Phase 2, currently waiting on physical IMU procurement) |

The second one is not new work this research motivates — it's already in the roadmap. Don't let "we need a Kalman filter" become one undifferentiated task; it's two, in two different places, for two different reasons.

---

## 4. Is machine learning needed? Direct answer: no, and conflating the two costs you something

RLS, Kalman/Extended Kalman filtering, and disturbance observers are **classical adaptive control and recursive estimation theory** — the Kalman filter dates to 1960, RLS to the same era of adaptive control literature. None of it is machine learning in the sense the term usually implies (trained neural networks, learned from data offline, generalizing via statistical pattern-matching). They're deterministic recursive algorithms operating on a known model structure, updated in closed form every control tick. This distinction is not pedantic — it has real consequences for this project:

- **No training data pipeline needed.** RLS/Kalman filters initialize from a prior (your current calibrated `Kff`/`Kstat`) and update online from live operation — not from a labeled dataset you'd need to collect and curate first.
- **No GPU, no training infrastructure, no model-versioning problem.** Runs in closed-form arithmetic on the ESP32 you already have.
- **Verifiable and provably stable under known conditions**, in the sense that matters for something that will physically move in a workspace with people. A trained neural-network controller is comparatively very hard to certify — you can't easily prove it won't do something strange outside its training distribution, which is a serious concern for an industrial deployment target, not an academic nicety.
- **"Smart AMR" is being answered by this at the wrong layer.** A robot that correctly identifies its own changing physical parameters in real time via RLS *is* smart, in the fully legitimate control-engineering sense — without a neural network anywhere in the wheel-control path.

**Where genuine ML would earn its place in this project** is a different layer entirely: perception (semantic understanding of what a LiDAR/camera is seeing — is that a person, a shelf, a spill), not motor control. That's downstream of everything in this document, in Phase 3/4 territory, and it's a separate research thread from adaptive control. Keep them separate in how you plan and in how you frame this for your APS — "adaptive control via classical estimation" and "perception via learned models" are two different, both-legitimate contributions; merging them into one "we need ML" story undersells the control-theory work, which is the more immediately actionable and more rigorously groundable of the two.

---

## 5. Staged roadmap, sequenced against where this project actually is

Both documents proposed a staged rollout; the sequencing below adjusts it against what's actually been measured on this robot so far, not a generic AMR.

### Stage 0 — in progress, don't skip: finish the static calibration
Ground `staircase`/`plant` tests (`tools/nab_pid_logger.py`), fitted `Kff`/`Kstat`/`Kp` on real ground data. This is the reference model everything below needs. Status: air side done, ground side blocked on floor space until `--mode rotate` gets used.

### Stage 1 — Recursive Least Squares for `Kff`/`Kstat`, on the ESP32
Once per motor, maintain a 2-parameter linear model `pwm = Kff·ω + Kstat` and update it recursively from every control tick's (commanded PWM, measured velocity) pair — data the firmware already has, currently thrown away after each tick. Standard 2-parameter RLS update, per motor, per tick:

```
θ = [Kff, Kstat]ᵀ            (state to estimate)
φ = [ω, sgn(ω)]ᵀ             (regressor, from this tick's target velocity)
e = pwm_actual − φᵀθ         (prediction error)
K = Pφ / (λ + φᵀPφ)          (gain; P is a 2×2 covariance matrix)
θ ← θ + K·e
P ← (P − K·φᵀP) / λ
```

`λ` (forgetting factor, typically 0.99–0.999) is the real design decision — too close to 1 and it barely adapts to real drift over minutes; too low and it chases tick-to-tick noise instead of tracking slow change (battery, wear, ground). This needs tuning against real data, not guessing.
**Feasibility: high.** Two states, a 2×2 covariance matrix, a handful of scalar ops — trivial against a 10 ms budget on a 240 MHz dual-core part already running four independent 100 Hz PID loops.
**What it buys:** automatic tracking of exactly the slow drift both research documents are worried about (wear, temperature, gradual battery sag), without touching Kp/Ki or needing to re-run a bench test.

### Stage 2 — Disturbance observer for payload/CoM
Layer on top of Stage 1 once its estimates are trusted. Estimates unmodeled load torque directly and feeds a compensating term into the feedforward, rather than waiting for RLS to slowly re-converge Kff after every payload change. This is what most directly addresses the "will actually carry variable industrial payloads" requirement, and it's the strongest connection to real recent literature — Li & Li (2025), verified above, report large, real, measured gains from exactly this combination (IMC+DOB) over both plain IMC and plain PID.
**Feasibility: high**, same order of computational cost as Stage 1 — a filter and a subtraction, not an optimizer.

### Stage 3 — `robot_localization` EKF (already planned, runs in parallel, not gated on Stages 1–2)
This is the *other* Kalman filter (§3 table). Already configured (`ekf_params.yaml`), blocked only on physically procuring the IMU (Part XVII in progress). Worth stating plainly: this can proceed on its own timeline — it doesn't need Stages 1–2 finished first, because it estimates a different thing from a different set of inputs.

### Stage 4 — only if Stages 1–3 don't already solve the practical problem
Gain-scheduled or self-tuning PID, sliding-mode control, full Lagrangian dynamic modeling with online mass/inertia/CoM identification. This is where doc 1's own "Stage 4, only if needed" framing is right, and I'd keep that framing rather than front-load it: a well-tuned two-degree-of-freedom PID+FF loop with an adapting feedforward and a disturbance observer already covers most of what SMC or full dynamic modeling would buy, at a fraction of the tuning and verification cost. Revisit only if real operating data (once you have it) shows Stages 1–3 aren't enough — not as a default next step.

### Where full Lagrangian dynamic modeling (deep-research report's §"Dynamic Modeling") fits
Valuable as an **offline design and simulation tool** — e.g. for sizing motors/gearboxes for a heavier future payload variant, or for a simulation environment to test Stage 4 controllers before risking hardware. Not needed *online* for Stages 1–3 to work; RLS and a DOB both operate on the same simplified per-wheel model already in the firmware, not the full multi-body dynamics. Doc 2's own "essential vs optional" list agrees with this ("full dynamic model inversion in the controller — hard to compute online").

---

## 6. What actually needs building, ranked by what unlocks the most next

1. **Finish Stage 0.** No new code — it's the ground `staircase`/`plant` tests already built and waiting on floor space (`--mode rotate` already implemented).
2. **Stage 1 RLS**, added to the existing `computePID()`/velocity-read path in `aislebot_esp32.ino`. Smallest new-code footprint of anything here, biggest immediate payoff (automatic drift tracking with zero new hardware).
3. **Stage 2 DOB**, once Stage 1 is validated against a known payload-change experiment (add a known mass, confirm the observer's estimate tracks it).
4. **Procure the IMU** — unblocks Stage 3, which is independent of 1–2 and already fully planned.
5. **Everything else** — genuinely deferred, and correctly so, until real operating data says otherwise.
