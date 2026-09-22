# Slide plan, slides 1–12

Not built yet. Same rule as always: nothing in `content.py` or the
`.pptx` changes until you say build, then it happens slide by slide with
its own commit, same as slides 3/5/9/10 already patched in.

All images referenced below are committed under `assets/context/` (or the
existing `assets/photo/` and `assets/slide/` for report/robot photos).
Videos stay as placeholders carrying the exact filename — no video files
are stored in the repo.

---

## Slide 1 — Title
**Image:** `assets/photo/title.jpg`. Unchanged.

## Slide 2 — Indian warehouses are growing
**Images:** `assets/context/warehouse_floor.jpg`, `assets/context/fedex_dock.jpg`.
Already built and pushed. Unchanged.

## Slide 3 — Three problems, one engineering method
**No image.** Already built and pushed. Unchanged.

## Slide 4 — Five objectives
**No image.** Unchanged, original report text.

## Slide 5 — Strand One divider
**No image.** Already built and pushed. Unchanged.

## Slide 6 — The aisle sets the problem
**Image:** `assets/photo/platform_side.jpg`.
One addition pending (not yet built): the holonomic/omnidirectional/DOF
bullet from last round. Everything else unchanged.

---

## Slide 7 — Asymmetric layout & kinematics model
**Images:** `assets/context/dims_schematic.png` (your tape-measured
dimension drawing) and `assets/context/paper_fig3_schematic.png` (the
prior lab paper's own Figure 3). Both committed.
**No video.**
Inverse and forward kinematics, independently verified last round —
correct, and the inverse-kinematics equations are the report's own Eq.
1.2 under clearer notation. Still open: the caption collision (both
images can't be "Fig. 3" on one slide), whether equations render as
styled text or as typeset images, and whether the motor-size "why this
arrangement" paragraph still belongs here.

## Slide 8 — What the non-collinearity actually changes
**Image:** `assets/slide/fig02.png`.
Unchanged — K₀ = 0.5607 m, K₁ = 0.4907 m, 14% difference, 0 translation
terms changed. Re-verified against the report, nothing unverified found.
Still waiting on what specifically you meant by "unverified" here.

---

## Slide 9 — The starting condition **(now carries a trimmed spec table)**

This is the change from last round: the spec table moves here, and it's
cut down to only what was actually present before this year's work began.
No ESP32, no lidar, no host computer — those didn't exist yet at this
point in the story.

**Video:** `robot_demo_under25MB.mp4` — the open-loop joystick drive.
**No static image** (the video carries the "what it looked like" job).

**Bullets**, present-at-start / absent, largely as before:
- Present: chassis, four mecanum wheels (asymmetric layout), four geared
  drive motors, two motor drivers, the power system, Arduino Mega 2560
  control.
- Absent: closed-loop velocity regulation, odometry, on-board kinematic
  model, perception, autonomy.

**Trimmed spec table** — motor, driver, battery, booster, buck, wheels,
chassis only, as instructed:

| | |
|---|---|
| Chassis | 1.00 × 0.36 m footprint (tape-measured); four mecanum wheels, non-collinear layout, 0.0762 m radius |
| Drive motors | 4 × geared DC, 24 V, 1:47 reduction, 60 rpm rated |
| Motor drivers | 2 × dual-channel (Cytron MDD20A), 20 A continuous, 6–30 V |
| Battery | LiFePO₄ 12.8 V, 30 Ah, 384 Wh |
| Boost converter | 12.8 V → 24 V, 1200 W, feeds the motor rail |
| Buck converter | 12.8 V → 5 V, 60 W, feeds logic |

**One honesty flag on this table.** The chassis, wheels, motors, drivers
and "the power system" are explicitly stated in the report as present at
the start (Section 1.3, quoted above in the bullets). The *specific*
battery/boost/buck part numbers and ratings, though, come from the current
deployed-electronics diagram, which describes the system **after** the
ESP32 migration — the report never separately confirms whether this exact
battery and these exact converters were already in place on day one, or
were added/upgraded as part of that migration. The 24 V motors would have
needed *some* 24 V supply even under the Mega, so it's plausible the same
core power chain was there from the start, but "plausible" isn't
"confirmed." Since this table is specifically framed as "what was there
before this year," it's worth you confirming the battery/boost/buck row
before it goes on a slide with that framing.

---

## Slide 10 — Why the drive controller changed, in one calculation
**No image, no video.**
Unchanged content — the four tiles (558,792 edges/s, 16 MHz, ≈29
cycles/edge, 4 ESP32 quadrature units) and the two-column timing-argument
/ interface-problem layout. Just moved here, right after the starting
condition it's explaining the departure from.

## Slide 11 — Deployed electronics
**Image:** `assets/context/deployed_electronics.png` (your diagram,
now committed at its full 1433×1450). Replaces the report's Figure 5.
**No video.**
This is the payoff slide for the previous one: here's the full system
that resulted from the ESP32 decision. Fact-check from last round still
holds — its stated gains match the report's deployed values exactly.
Still open: a higher-resolution source if one exists beyond this export.

---

## Slide 12 — The machine as built
**Image:** `assets/slide/fig03.png` (Figure 3, unchanged, "as it is" per
your instruction).
**No video.**

This is the final-state slide — the fully assembled machine, mast and all,
closing out the build-history arc that started at slide 9.

**Mass — needs your confirmation before it goes on a slide.** You wrote
"more than <70kg," which reads as contradictory (more-than and less-than
in the same phrase). My best guess at what you mean is a bounded estimate
— more than 45 kg (the bare chassis) and somewhere under 70 kg fully
assembled with the mast, battery and electronics — but I'm not putting a
number on a slide from a guess. Confirm the actual range (or point value)
and I'll use exactly that.

**The mast, briefly** (your instruction: "just a line or two"):

> The vertical mast is a tube holder carrying three stepper motors — one
> for the mast's up/down travel, two for opening and closing the cargo
> arm — all controlled by the Arduino Mega, reassigned to this job once
> the ESP32 took over drive control.

Fact-check: consistent with the report's Table 1.1 ("Cargo arm and
lighting: two lateral and one vertical stepper axis, three-tube staged
UV") and with the existing deck's own electronics bullet ("the original
Arduino Mega reassigned to the cargo arm and the ultraviolet lighting
rather than discarded"). Your "one for up/down, one for opening/closing"
matches "one vertical, two lateral" once you count the two lateral axes
as the two sides of the opening/closing motion — same mechanism, just
described from the operator's-eye view instead of the axis-count view. No
conflict.

---

## Then slide 13 onward: closed-loop control, one topic at a time

The per-wheel velocity loop, the feedforward fit, where the gains came
from, the anti-windup/slew-limit/safety-trip arrangements, then results.
Unchanged from the current deck, just renumbered to start after slide 12.

---

## Honest read on the narrative, slides 1–12

Asked directly, so a direct answer.

**It holds together, with one real seam** — not a break, but a place a
sharp listener could ask "wait, why are we back at the beginning?"

The shape is: problem and geometry first (6–8, the math that's true
regardless of what was ever built), then build history in order (9–12:
what existed at the start, why the controller changed, what the resulting
electronics look like, what the finished machine is). That's a legitimate
structure — geometry doesn't depend on build sequence, so establishing it
before the history is reasonable — but the jump from slide 8 (talking
about the finished asymmetric machine's kinematics) back to slide 9
(talking about the machine *before any of this year's work*) is a real
step backward in time that the deck doesn't currently signal out loud.
Nothing on slide 8 or slide 9 says "now, here's how we actually got
there." It'll probably read fine spoken aloud, because you'll say
something like that naturally — but on the page, nothing marks the time
jump.

Two ways to close that seam, your call:
1. Cheapest: add one clause to slide 9's kicker or opening line — something
   like "Before any of this: what was actually on the bench" — so the
   time-reversal is explicit rather than implicit.
2. Structural: swap 7–8 and 9–12, so the story runs strictly chronologically
   (what existed → what changed → the finished machine → *then* the
   geometry/kinematics that machine embodies). This is a bigger reshuffle
   and would need the kinematics slides re-anchored to "the machine you
   just saw" instead of "the machine we're about to build."

I'd take option 1 — it's a one-line fix and the current order (theory,
then history) is a perfectly normal way to present engineering work. But
it's your call, not mine to make silently.

Past that seam, 9 → 10 → 11 → 12 is clean: starting point, the one
decision that changed everything about the electronics, the resulting
system, the finished machine. No abrupt drops — each slide's last idea is
what the next slide is about.
