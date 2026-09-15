# APS run-up plan — 12 to 23 September 2026

The APS is booked for 23 September, 2:30–3:30 PM, and doubles as the
comprehensive exam. Three objectives go up that day, each with its own repo:

| Objective | Repo | Status going in |
|---|---|---|
| 1. Narrow-aisle warehouse robot (stacking, retrieval, monitoring, disinfection) | `NarrowAisleBot` (this repo) | Priority. Draft report, deck, and study guide already exist and are current to 3–9 Sept |
| 2. IoT warehouse environment monitoring | `IoT-Box` | Not yet reviewed for this report |
| 3. IoT contactless warehouse fatigue monitoring | `Fatigue-Detection-` | Not yet reviewed for this report |

NAB goes first and gets the most days, both because it is furthest along and
because it is the objective with a physical machine a panel can ask hard
questions about.

## Day by day

| Date | Focus |
|---|---|
| Sat 12 Sep | Housekeeping: `academic-writing` skill added to this repo's `.claude/skills/`, this plan written. No claims drafted yet. |
| Sun 13 Sep | Off / light reading only. Skim `APS_Study_Guide.md` for anything rusty — SLAM front vs. back end, AMCL, MPPI. |
| **Mon 14 Sep** | **NAB validation day.** Pull together every circle-path, complex-trajectory, and yaw-out-and-return-to-base run already recorded, with its video and telemetry. Attach the strongest of these into the report as the evidence for Objective 4 (asymmetry cost/benefit). Also the day to get the four `[CONFIRM]` items in `APS_Report_Draft.md`'s header answered — the APS deadline/cycle, the department's report format and length, the supervisor's view on how much of §11 to include, and the IRCC position on the UV-C disclosure — since all four gate formatting and none of them can be resolved from inside the repo. |
| Tue 15 Sep | Finish folding Monday's evidence into the report. Second pass with the academic-writing skill over §§1–6 (motivation, kinematics, closed-loop control) — check no claim outruns what §6's measured numbers actually show. |
| Wed 16 Sep | Same pass over §§7–12 (SLAM, navigation, critical evaluation, the UV-C parallel project, research gaps). Freeze the NAB section of the report. |
| Thu 17 Sep | Pull the `IoT-Box` material into review (see "connecting the other repos" below) and draft the Objective 2 section. |
| Fri 18 Sep | Same for `Fatigue-Detection-` — Objective 3 section. |
| Sat 19 – Sun 20 Sep | Assemble all three objectives into one narrative, update `NarrowAisleBot_APS_Seminar.pptx` to carry the three-objective structure, run the skill's "before finalizing" checklist over the whole document. |
| Mon 21 Sep | Full timed run-through of report and deck against the 60-minute slot. Check tense consistency, that every objective heading reads on its own, that every citation still matches its renumbered position. |
| Tue 22 Sep | Final rehearsal. Backup copies of the deck and videos on the presenting device, offline. Light re-read of `APS_Study_Guide.md` for the comprehensive-exam side of the panel's questions. |
| Wed 23 Sep | APS + comprehensive, 2:30–3:30 PM. |

## On the "equally effective as symmetric" claim

Worth being precise about this before it goes in front of a panel, because
there are two different claims sitting next to each other and only one of
them has evidence behind it right now.

**What the data actually supports:** the asymmetric wheelbase (l₁ = 0.403 m
per `Where_We_Stand.md`) does not cost any degree of freedom. The forward
kinematic model reproduces ground-truth twist to 1.7×10⁻¹⁶ over 20,000 random
twists, and the field runs show circles, compound trajectories, and
yaw-in-place-then-return-to-base all executed on the real hardware. That is a
strong, specific, and already-measured result: asymmetry does not reduce the
platform's motion repertoire.

**What would need a symmetric robot that doesn't exist:** "equally effective
as a normal symmetric mecanum robot" read literally is a head-to-head
comparison, and no symmetric platform has been built to run next to this one.
Objective 4 in the report already states this correctly as a deliverable —
"a controlled comparison against a symmetric baseline of matched
capability" — and it isn't marked achieved in the §4.2 outcomes table.

The honest, still-strong framing for Monday: claim motion-capability
preservation (measured, exact) and state the symmetric-baseline comparison
as the specific piece of Objective 4 still open, rather than blurring the two
into one 90%-done line. A panel that builds mecanum robots for a living will
ask the difference between those two claims directly.

## The fuzzy-logic question

No, and it should stay that way for this APS. Closed-loop velocity control on
this platform is classical: per-motor PID with a two-term feedforward
calibration (`PID_Calibration.md`). `Adaptive_Control_Roadmap.md` already
contains a fact-check on this exact point — a "fuzzy logic / SMC" claim once
attributed to a 2019 mecanum paper was checked against the actual paper and
found not to be there at all (Lyapunov-based adaptive control, no fuzzy logic,
different problem). Fuzzy control is listed there only as a possible future
direction, correctly out of scope for this year's report.

## Connecting the other two repos

`IoT-Box` and `Fatigue-Detection-` stay separate repos — there's no need to
merge them into `NarrowAisleBot`, and the report already has a precedent for
citing outside work without absorbing its codebase: §11 treats the UV-C
disinfection unit as a "parallel project" section rather than moving that
code into this tree.

Two things happen at different layers:

1. **To read and pull from them at all**, this session (or whichever session
   does the Thursday/Friday drafting) needs `add_repo` called for
   `AritraD11/IoT-Box` and `AritraD11/Fatigue-Detection-`. That's a
   per-session grant, not something that persists in the repo — it has to be
   called again in whatever session actually drafts those two sections.
2. **To make the borrowed material part of this repo's traceable record**,
   the way every other number in this report is traceable to a file and a
   line, copy in only what the report cites — a figure, a table of measured
   numbers, a short summary paragraph — under something like
   `docs/aps_report/objective2_iot_box_summary.md` and
   `objective3_fatigue_summary.md`, each opening with a one-line source
   citation (`Source: IoT-Box@<commit>, path/to/file`). That keeps the same
   "every claim traceable to a file in the tree" property this report
   already relies on for NAB, without turning this repo into a monorepo or
   taking on git submodules for material that only needs to feed one
   document.

Submodules are the other real option (`git submodule add` under
`external/iot-box`, `external/fatigue-detection`) if those two projects turn
out to need live, ongoing sync with this report rather than a one-time pull
of figures and numbers. That's more machinery than a single seminar
justifies unless the next few years keep coming back to all three objectives
together.
