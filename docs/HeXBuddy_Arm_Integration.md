# AisleBot's Next Objective — Integrating the HeXBuddy Manipulator

> **Filed into this repo 2026-09-07.** Copied verbatim from the bridge document
> supplied for this repository, with two corrections marked below against this
> repo's own numbers: a stale firmware citation, and a chassis-mass input to the
> tipping model that this repo's measured mass nearly doubles. Everything else is
> as handed over —
> unbuilt design work from a separate, private repository, not yet reflected in
> `APS_Report_Draft.md` or the seminar deck. See `docs/Research_Journal.md` and
> `docs/aps_report/APS_Report_Draft.md` §12 for this repo's own evidence-grading
> convention (measured / single-run / hypothesis / retracted / never run); nothing
> in this file has been re-graded against it yet, because none of it has been run
> on this repo's hardware or in this repo's simulation — it is HeXBuddy's own
> first-order model, honestly labelled as such in §6.3 below.

**Purpose of this file.** This repository (`AisleBot` / Mecanum) is the mobile base:
mecanum chassis, drive electronics, and — until now — a simple UV-disinfection arm.
**HeXBuddy** (`AritraD11/HeXBuddY`, private) is a separate repository that designs and
evaluates the *next* arm for this base: a real cargo-picking manipulator for narrow
warehouse aisles. This document is the bridge — everything AisleBot needs to know about
what HeXBuddy is, what it has found, and how the two come together — so a session
working in *this* repo has the full picture without switching context.

**Status at a glance:** HeXBuddy has gone from a CAD viewer → an evaluation platform →
an optimizer that *generated* a design (`Periscope-Opt`) which strictly beats the
hand-authored reference on every axis. That design is not yet built, but it is fully
specified: geometry, actuators, real purchasable parts, cost, and a ROS 2 URDF ready
to sit on this chassis.

---

## 1. What AisleBot is today (verified from this repo)

AisleBot started as a **UV-disinfection robot**: a mecanum-drive chassis with a simple
two-arm-and-lift mechanism that opens/closes and raises/lowers a UV platform. IIT
Bombay, Department of Biosciences and Bioengineering — Aritra Das (25D0074), supervised
by Prof. Ambarish Kunwar.

### 1.1 Drive base (the part HeXBuddy's arm will ride on)

| Parameter | Value | Source |
|---|---|---|
| Configuration | 4-wheel **asymmetric mecanum**, fully omnidirectional | `mecanum_teleop_asymmetric.py` |
| Outer wheel offset (FR/RL), `l1` | 403 mm | SolidWorks model |
| Inner wheel offset (FL/RR), `l2` | 333 mm | SolidWorks model |
| Half track width, `d` | 157.69 mm | SolidWorks model |
| Wheel radius, `a` | 76.2 mm (DekuPro 6") | ESP32 firmware v2 |
| **Chassis footprint (derived)** | **≈ 74 cm long × ≈ 32–40 cm wide** | l1+l2 length; 2d+tire width |
| Drive motors | Rhino RMCS-2086, 1:47 gearbox, 500-line quad encoder (93,132 CPR) | `arduino_bridge.py`, ESP32 v2 |
| Max wheel speed | 60 RPM = 6.28 rad/s | firmware |
| Max linear / angular (launch defaults) | 0.15 m/s / 0.30 rad/s (bench-safe; hardware max ≈0.48 m/s) | `aislebot_full.launch.py` |
| Drive controller | ESP32, dual-core FreeRTOS: Core 1 = 50 Hz PID+feedforward, Core 0 = WiFi/WebSocket/serial | `aislebot_esp32_v2.ino` |
| Compute | Raspberry Pi 5, Ubuntu 24.04, **ROS 2 Jazzy** | setup guide |
| Arm/attachment controller | Arduino Mega 2560 over USB serial (115200 baud) | `arm_bridge.py` |

> **Correction on import.** The 50 Hz PID figure and its `aislebot_esp32_v2.ino`
> citation are stale: that file now lives under `past_iterations/firmware/` in this
> repo. The controller actually running is root-level `aislebot_esp32.ino`, whose own
> header records the upgrade ("Control loop 50 Hz -> 100 Hz. Affordable because PCNT
> counts in hardware..."), and it is what `APS_Report_Draft.md` §5.1 reports: **100 Hz**.
> Read every rate in this document as provisional against HeXBuddy's own source tree,
> the same way this correction was caught against AisleBot's.

**Important correction to carry into HeXBuddy:** the base is **hardware-omnidirectional**
— it can strafe and yaw in the open. HeXBuddy's "forward/back only" assumption is an
**aisle-clearance constraint**, not a drivetrain limitation: in a sub-1 m aisle there is
no lateral room to use the strafe capability the mecanum wheels actually have. Keep this
distinction precise — it matters if HeXBuddy is ever asked to plan a move in open floor
space (docking, staging, wide aisles), where full omnidirectional motion is available.

### 1.2 The arm being superseded

The current arm (`aislebot_arm_v7.ino` + `arm_bridge.py`) is a **UV-disinfection**
mechanism, not a manipulator: two NEMA23 steppers (TB6600 drivers) that open/close a
pair of arms, and one NEMA34 stepper (BH-MSD driver) that raises/lowers the platform.
Three DOF total, no gripper, no shelf-picking capability. Serial protocol
(`<A,arm,lift>` velocity commands, `<H>` home, `<S>`/`<C>` e-stop) over the same Mega +
115200-baud link the new arm will use.

**This is the slot HeXBuddy's manipulator fills.** The control architecture pattern —
Pi 5 running ROS 2, a dedicated MCU per subsystem, neither aware of the other, arbitrated
on the Pi — is already proven here and should be reused, not reinvented, for the picking
arm (see §6).

---

## 2. What HeXBuddy is

HeXBuddy (`AritraD11/HeXBuddY`) is a React/TypeScript/three.js **engineering decision
platform** — not a CAD tool. Its job: given a candidate arm architecture and a warehouse
geometry, compute whether that arm can actually do the job, with real numbers, before
any part is bought.

**The one architectural idea:** every panel reads one function,
`evaluate(design, warehouse) → DesignReport` (`src/eval/DesignEvaluator.ts`), which
returns reachability (per-shelf-cell, via IK + manipulability), stability (tipping
margin), inverse dynamics (energy-per-pick, peak/RMS torque, peak power, battery life),
and a bill-of-materials cost. Nothing is eyeballed; everything is computed once and
shared.

**How it got here (phases, each shipped and tested):**

| Phase | What it built |
|---|---|
| P0 | The evaluation engine itself — the spine every later phase extends |
| P1 | The shelf-accessibility field (% of cells reachable, colour-mapped) |
| P2 | Real inverse dynamics → energy/pick, torque, power, battery, ₹ cost |
| P3 | Compare mode (pin design A, load design B, see deltas on every axis) |
| **P4** | **A Pareto optimizer that searches the design's own variables (lift stroke, boom reach, arm scale) and returns the designs no other candidate beats on every axis at once** |

P4 is the phase that matters most for this document: it stopped the project from
re-authoring one hand-picked design over and over, and it **found something better than
the hand-authored one.**

---

## 3. The current best design: Periscope → Periscope-Opt

### 3.1 The shape (unchanged by optimization)

A **lift · turn · extend** machine, engineered so gravity is held with ~0 motor power
everywhere — every load-bearing axis is self-locking:

| Joint | Type | Mechanism | Role |
|---|---|---|---|
| J1 | prismatic Z | DR4B fold-flat lift, self-locking lead screw | Raise to any shelf level, 0 W hold |
| J2 | revolute Z | turntable | Aim boom at either rack face (±180°) |
| J3 | prismatic (horiz) | telescopic boom | Reach into the shelf cell, retracts inside the chassis |
| J4 | revolute | **roll-roll wrist** (see §3.3) | Orient the grasp, 0 W hold |
| J5 | revolute | tool roll | Final grasp rotation |
| gripper | — | screw-driven jaw ("TalonGrip") | Self-locking, 0 W hold |

The base supplies the one axis this arm deliberately omits: lateral travel, via
forward/back motion in the aisle (§1.1).

### 3.2 What the optimizer changed

Searching the Periscope's own design variables (lift stroke, boom reach, arm scale) at
a 100 cm aisle, P4 found **`Periscope-Opt`**: lift 120 cm · boom 80 cm · arm structure
scaled ×0.70. It is **strictly better on every axis** than the hand-authored seed:

| Metric | Hand-authored Periscope | **Periscope-Opt (P4)** |
|---|---|---|
| Shelf cells reachable | 75% | **100%** |
| Energy / pick | ~210 J | **~204 J** |
| Arm mass (excl. 25 kg chassis) | 12.8 kg | **11.2 kg** |
| Build cost (arm only) | ₹61k | **₹58k** |
| Min tip margin over the pick (25 kg chassis) | not modelled | **+1.8 cm — never tips** |

A taller self-locking lift plus a lighter, shorter arm covers the *whole* shelf for
*less* of everything. The hand-authored design was over-armed and under-lifted — this
is the optimizer doing its job: generating a design nobody hand-picked.

### 3.3 The one hand-edit that mattered: the roll-roll wrist

The wrist (J4) was originally a **pitch** joint — gravity-loaded, and the single worst
actuator in the whole machine (84% of its continuous thermal rating at 5 kg payload;
**425% — burns out — at 20 kg**). Re-orienting it 90° so the payload hangs *along* the
rotation axis instead of cantilevered off it collapses that load to **2% at 5 kg, 9% at
20 kg.** The cost: the tool can no longer tilt up/down (fine for straight-in shelf
picking; the gripper can carry its own tilt if ever needed). This is now the adopted
wrist in `Periscope-Opt`.

### 3.4 The binding constraint is tipping, not torque

Once the mobile base's real mass entered the model (25 kg chassis — a conservative
estimate for a 100×30 cm steel frame + 4 mecanums + LiFePO4, vs a MiR100's 65 kg), the
actual limiting factor at any payload became **tipping**, not actuator torque:

| Boom reach | 5 kg | 10 kg | 20 kg |
|---|---|---|---|
| 40 cm | +7.6 cm | +4.7 cm | +0.5 cm |
| 60 cm | +3.3 cm | −1.5 cm | −8.4 cm |
| 80 cm | −1.0 cm | −7.8 cm | −17.3 cm |

**Unanchored rated reach ≈ 75 cm @ 5 kg · 55 cm @ 10 kg · 41 cm @ 20 kg.** No actuator
choice fixes this — it's a moment-arm problem. Three practical mitigations, ranked:

> **Correction on import.** This table is anchored on a 25 kg chassis, called
> "conservative" above. AisleBot's actual mass, measured and reported in
> `APS_Report_Draft.md` §5.1, is **45.54 kg** — very close to double. A heavier
> base has a larger restoring moment about the same tip line, so real margins are
> almost certainly better than this table shows at every reach and payload; how
> much better is unquantified until someone reruns the model with the real mass
> (and the real CG height, which this document does not state). Treat every
> number in this section as pessimistic until that rerun happens, and do that
> rerun before it drives any purchase or build decision.

1. **Load-moment envelope (software, zero hardware)** — like a crane or reach truck:
   derate payload with reach, enforced by the planner. Ship this day one.
   Live at `research/HARDWARE_BOM.md`§ / `ROADMAP_TO_HARDWARE.md`§4.
2. **Shelf-beam support foot** — a small roller/skid that rests on the rack's own front
   beam during a deep reach. Required reaction force is tiny (~1–21 kgf across 5–20 kg
   payloads) against a beam rated for hundreds of kg. Enables the full 80 cm boom at any
   payload the actuators can carry.
3. **Cross-aisle brace** — in a 100 cm aisle the opposite rack is ~35 cm from the base
   edge; a strut extends back to brace against it, tip-proofing the machine using the
   narrow aisle itself as the anchor point.

---

## 4. Research foundation — literature, gaps, and the novelty thesis

The full literature review lives in HeXBuddy's `research/RESEARCH_MASTER.md` (deployed
commercial landscape, academic landscape, references A–I). The load-bearing findings:

### 4.1 The ten open gaps this design targets

| Gap | What's missing in the field | Where AisleBot lands on it |
|---|---|---|
| **GAP-1** | No co-design work counts the mobile base's own x/y travel against the arm's DOF budget, or imposes a stow envelope | **The core thesis** — a 5-DOF arm is sufficient once the base supplies lateral travel |
| **GAP-2** | No arm platform or vendor reports energy-per-pick or static hold-power | HeXBuddy's headline metric; direction-aware (charges self-locking descent honestly) |
| GAP-3 | Telescoping stows well but nobody rates it as a payload-class *research-arm* joint | The lift/boom *are* telescoping, sized for 5–20 kg |
| GAP-4 | No shoulder gravity-compensator both downsizes the joint *and* survives a flat stow fold | Open — future work |
| GAP-5 | No payload-class revolute chain folds under ~180 mm | Open — the DR4B fold-flat lift is the current answer |
| **GAP-6** | Dual-encoder virtual joint-torque sensing (motor-side vs output-side deflection ≈ torque) is unexploited on smart actuators — zero added hardware | Directly applicable to the RMD-X6 joints already in the BOM |
| GAP-7 | Shelf-edge bracing (rest the forearm on the rack edge to shrink the effective cantilever) is dead literature since the 1980s, untouched in warehouse context | Related to §3.4's beam-foot idea |
| GAP-8 | Using arm posture as *active ballast* against tipping is unpublished for a narrow-track mecanum AMR | Directly relevant — AisleBot's tipping math (§3.4) is exactly this problem |
| GAP-9 | No grasp-verification method reads "I have it and it weighs ~X" from joint signals alone (attacks the #1 commercial failure mode: exception volume) | Open — future work, pairs with GAP-6 |
| GAP-10 | Reduced-DOF arms that close residual reach gaps with small learned base micro-motions ("mecanum crab") are unstudied | Directly available — the base is already mecanum |

### 4.2 The synthesized novelty thesis (verbatim thrust)

> **Architecture:** reduced-DOF by counting the base's x,y; a self-locking lift replaces
> the shoulder (pushed to 5 kg+ and stow-optimized, which prior art is not); folds flat
> where a box-frame gantry cannot. **No prior work co-designs DOF-reduction + stow +
> base-DOF-accounting together.**
> **Control:** dual-encoder deflection-torque sensing (zero added hardware) enables
> force-aware picking, shelf-edge bracing, and grasp verification — all attacking
> exception volume, the deployment literature's #1 failure mode.
> **Deployment:** very-narrow-aisle capable (the market's explicit unserved niche — see
> §5), with a software-first cycle-counting on-ramp that earns revenue before grasping
> needs to be perfect, and arm-posture-as-ballast turning the base's tipping liability
> into a control asset.
> **Benchmark:** energy-per-pick / hold-power — a metric no competitor reports, and
> directly monetizable for a battery-powered fleet.

### 4.3 Ranked opportunity shortlist (from HeXBuddy's own prioritization)

1. Base-DOF-aware reduced-DOF + stow co-design (GAP-1/3/5) — **done, this is the arm**
2. Dual-encoder virtual torque sensing (GAP-6) — clean science, zero extra hardware,
   directly buildable on the RMD-X6 joints already specified
3. Zero-hold-power + energy-per-pick metric (GAP-2) — **done**, it's the headline number
4. Arm-as-ballast whole-body stability (GAP-8) — ties directly into AisleBot's own
   tipping math
5. Shelf-edge bracing (GAP-7) — needs #2 first
6. Grasp verification from joint signals (GAP-9) — needs #2

---

## 5. Competitive position — why this, not a bigger arm or a bought system

The nearest commercial category is **Hai Robotics' HaiPick** ACR fleets — but they solve
a structurally different problem: Hai moves **containers** (a telescopic-mast robot forks
a whole tote off a rack to a human workstation); AisleBot's arm manipulates **individual
items** in place.

| Axis | Hai Robotics | AisleBot | Verdict |
|---|---|---|---|
| Container throughput | 63 totes/h/robot, up to 600/h/station | ~145 item-picks/h, one unit | Hai wins by design — different job |
| Vertical reach | 12 m telescopic mast | ~1.2 m lift + boom | Hai wins — don't chase high-bay |
| Item-level grasp on existing shelving | **Cannot** — needs pre-decanted totes | **Can** — wrist + gripper picks in place | **AisleBot wins — the open gap** |
| Very-narrow-aisle | Needs a stable broad base for a tall mast — explicitly unserved | 30–40 cm chassis fits where Hai cannot | **AisleBot wins** |
| Energy-per-pick reporting | Not reported by any vendor | HeXBuddy's core metric | **AisleBot wins — new axis entirely** |
| Maturity | 1,100+ deployments, certified | Prototype | Hai wins — respect it |

**The positioning line:** *"Hai brings the shelf to a person; AisleBot is the person at
the shelf."* Don't compete on container throughput or high-bay reach. Own item-level
picking on existing racking in aisles too narrow for a fork-mast ACR to enter — brownfield
deployments, SMEs that can't justify a full automated storage system, and the VNA
(very-narrow-aisle) niche the literature already flags as unserved.

**Lowest-risk on-ramp:** VNA cycle-counting (inventory scanning) is software-first — it
earns revenue with the wrist camera before item-grasping needs to be bulletproof.

---

## 6. The path to real hardware — and how it plugs into *this* repo

### 6.1 Why this integrates cleanly with AisleBot's existing architecture

AisleBot already proved the pattern the picking arm needs: **Raspberry Pi 5 running ROS 2
Jazzy, talking to a dedicated MCU over USB serial, arbitrated centrally, neither MCU aware
of the other** (§1, and see `Complete_Implementation/AisleBot_Unified_Control_v1.docx`).
The picking arm is a new subsystem in that same shape — it does not require a new
architecture, only a new bridge node and a new URDF/joint set on the existing Pi 5.

### 6.2 What HeXBuddy already hands off

- **A ROS-ready URDF**: `designs/hexbuddy_periscope_optimized.urdf` — joint types, limits,
  and (placeholder) inertials for all 5 arm DOF + gripper.
- **A real-parts BOM** (`research/HARDWARE_BOM.md`), mapping every joint to a buyable
  part with verified specs and CAD source:

| Joint | Recommended part | Spec | Price band |
|---|---|---|---|
| J1 lift (120 cm) | Rollon TLS telescopic actuator, vertical | flat torque curve, ≤6 m/s, ±0.05 mm | ₹35–70k |
| J2 turntable | MyActuator RMD-X6-8 (CAN, integrated BLDC+encoder) | 8 N·m, 335 g, 5 arcmin backlash | ₹22–40k |
| J3 boom (80 cm) | Rollon TLS telescopic actuator, horizontal *or* MISUMI SAR rail + belt (DIY) | telescopes, retracts inside 30 cm chassis | ₹30–60k / ₹11–25k |
| J4 wrist (roll-roll) | Worm-geared BLDC (self-locking by geometry) | ~8 N·m, non-back-drivable | ₹6–15k |
| J5 tool roll | Feetech STS3235 serial-bus servo | 3 N·m stall, magnetic encoder | ₹3.5–5k |
| Gripper | Screw-driven parallel jaw ("TalonGrip") | self-locking, 0 W hold | ₹6k |

  **Arm subtotal (Build tier): ~₹95–180k** — higher than the model's optimistic ₹58k
  because real integrated servos and telescopic modules cost more than the provisional
  actuator library assumed; that gap is itself useful, and feeds back into re-anchoring
  HeXBuddy's cost model.

- **The control-stack layer that plugs straight into AisleBot's Pi 5**:

| Layer | Part | Role |
|---|---|---|
| Bus | CAN HAT (Pi 5) | RMD-X6 joints (J2, and a stronger alt for J4) are CAN-native |
| Serial | Feetech TTL bus | J5 (STS3235) |
| Framework | **ros2_control + MoveIt 2** (already Jazzy — matches AisleBot's Pi 5) | Loads the HeXBuddy URDF; plans orientation-true trajectories; maps them to real drivers |
| Safety | Self-locking screws + worm hold pose on power loss | Intrinsically safe in an aisle with people — same virtue the UV arm's steppers already have |

### 6.3 The honest caveat, upfront

HeXBuddy's own physics is first-order (point-mass, Coriolis neglected, provisional
actuator specs). **Before any purchase**, re-run the P4 optimizer with a bending-moment
and duty-cycle penalty on the lift/boom (nothing currently stops it from choosing an
oversized stroke — the 120 cm lift is the one part of this spec worth re-checking before
buying). Then graduate the URDF into Gazebo (Harmonic) + ros2_control with CAD-derived
inertias for real dynamics validation before cutting metal.

### 6.4 Phased build plan

1. **Bench the actuators** (~₹35k) — J2 (RMD-X6-8) + J5 (STS3235) + CAN HAT + Pi 5.
   Single-joint closed-loop control, de-risks the electronics stack independent of the
   mechanical build.
2. **Wrist + gripper** — the worm wrist + screw jaw; this was the thermal bottleneck
   before the roll-roll fix, instrument it under real duty cycle regardless.
3. **Boom** — verify 80 cm reach, retract-inside-chassis, and bending under a 5 kg tip
   load.
4. **Lift** — the long pole; re-run the bending-moment-penalized optimizer first (§6.3).
5. **Integrate on AisleBot; close the sim loop** — full URDF → MoveIt → ros2_control on
   the existing Pi 5, alongside (eventually replacing) the current `arm_bridge.py` /
   `aislebot_arm_v7.ino` UV-arm pipeline. Compare measured cycle time/energy against the
   HeXBuddy report and correct the model.

---

## 7. Repository status — read before you start work

**HeXBuddy has an unmerged branch you need.** `main` on `AritraD11/HeXBuddY` is at P2
(dynamics + cost) only. The P3 (compare mode) + P4 (optimizer) work — everything in
§§2–6 above, including `Periscope-Opt`, the roll-roll wrist fix, the real stability model,
the hardware BOM, and the Hai competitive analysis — lives on branch
**`claude/jump-to-p4-myfiud`**, not yet merged to `main`. Before treating any of this as
"the current design," either merge that branch or point directly at it. (A second branch,
`claude/setup-update-hook`, is identical to `main` — nothing to recover there.)

**This repo (AisleBot/Mecanum)** has one prior branch, `claude/hexbuddy-repo-overview-rryo1g`
(a hook that checks HeXBuddy for new commits before each prompt — added, then reverted;
currently a no-op). `main` here holds the working UV-arm + mecanum-drive ROS 2 stack
described in §1.

---

## 8. Should the two repos be merged into one?

**Recommendation: keep them separate, linked by this document and by the exchanged
artifacts — do not merge into one monorepo.** Reasoning:

- **Different toolchains, different lifecycles.** HeXBuddy is a Node/TypeScript/Vite web
  app (npm, vitest, a browser build) used for *design-time* trade studies. AisleBot is a
  ROS 2/Python/Arduino embedded stack used for *run-time* control. Folding a `node_modules`
  tree into a ROS 2 workspace (or vice versa) buys nothing and complicates both CI setups.
- **The real interchange is artifacts, not source.** What AisleBot actually needs from
  HeXBuddy is the **URDF, the BOM, and the design JSON** — not its React components. That
  boundary is exactly where a clean interface belongs.
- **If single-clone convenience matters**, the lighter option is a **git submodule**
  (`git submodule add <hexbuddy-url> design/hexbuddy` in this repo) — AisleBot's clone can
  pull HeXBuddy's design artifacts without merging histories or toolchains. Use this only
  if you find yourself frequently needing both repos checked out together; otherwise two
  repos + this bridge document is simpler and already works.
- **What should actually flow between them, concretely:** HeXBuddy's
  `designs/hexbuddy_periscope_optimized.urdf` → this repo's ROS 2 workspace, once §6
  begins. That's a file copy (or the submodule above), not a repository merge.

---

## 9. Immediate next objectives (actionable)

1. **Merge or pull from `claude/jump-to-p4-myfiud`** in HeXBuddy — it holds the actual
   current-best design; treat `main` as stale for arm decisions until this happens.
2. **Re-run the P4 optimizer with the bending-moment/duty-cycle penalty** on lift+boom
   before ordering the 120 cm lift actuator (§6.3) — cheapest possible fix, changes a
   number instead of a purchase order.
3. **Decide the submodule question (§8)** if both repos will be worked in the same
   session routinely; otherwise proceed with the two-repo + bridge-doc setup as is.
4. **Bench-test Phase 1** (§6.4 step 1): RMD-X6-8 + STS3235 + CAN HAT on the existing
   Pi 5, independent of the mechanical build.
5. **Add the load-moment envelope** (§3.4 item 1) to the planner before any payload
   testing above ~5 kg at extended reach — it is a software change, not a purchase.
