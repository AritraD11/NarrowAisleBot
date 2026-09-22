# Slide plan, slides 1–12

Not built yet. Same rule as before: this is the record of what's decided,
nothing in `content.py` or the `.pptx` changes until you say build, slide
by slide, the same way slides 3/5/9/10 were already patched in and pushed.

Slide numbers below are the **new** sequence — 1 is the title, 12 is "why
the drive controller changed."

---

## Slide 1 — Title

**Image:** `assets/photo/title.jpg` (the robot on the lab floor, existing).
No change from the current deck.

---

## Slide 2 — Indian warehouses are growing

**Images:** your two supplied photos — `assets/context/warehouse_floor.jpg`,
`assets/context/fedex_dock.jpg`.
**No video.**
Already built and pushed (commit `946d9a2` / patched again since). Growth
stats, automation-outpaces-the-sector, environmental-monitoring gap,
fatigue gap, closing bullet ties to the project. No further change pending.

---

## Slide 3 — Three problems, one engineering method

**No image**, three stat-style tiles (Strand 1/2/3, one-line problem each).
Already built and pushed (commit `2074598`). Retitled from "one problem,"
"what is shared" reworded to instrumentation/control/communication, weight
fixed to "more than 45 kg."

---

## Slide 4 — Five objectives

**No image.** Unchanged from the original report text, O1–O5 as submitted.
Not yet touched by any recent edit.

---

## Slide 5 — Strand One divider

**No image** (full-bleed tint background is the layout itself).
Already built and pushed (commit `101e624`). Line rewritten: "A small
prototype proved the maths were right. It said nothing about whether a
machine of more than 45 kg would track, sense or navigate correctly."

---

## Slide 6 — The aisle sets the problem

**Image:** `assets/photo/platform_side.jpg` (existing robot photo, side
view). **No video.**
Confirmed good by you, one addition pending (not yet built):

> A holonomic drive commands all three planar degrees of freedom —
> forward, lateral, yaw — independently and at the same time. A
> conventional drive (differential, Ackermann) is non-holonomic: three
> configuration variables, only two commandable velocities, so heading and
> translation stay coupled. Mecanum wheels make the platform holonomic,
> which is exactly the property a lateral aisle correction needs.

Fact-check: standard mobile-robotics definition, not report-specific,
solid.

---

## Slide 7 — Asymmetric layout & kinematics model **(your new mockup — confirmed, this is it)**

**Images, left column:**
1. Your new annotated top-down schematic — l₁ = 403 mm, l₂ = 333 mm, chassis
   width 252 mm (wheels excluded), wheel-to-wheel width 360 mm (tape-measured),
   L = 1000 mm front-to-back (tape-measured). **Have it** — extracted from
   your mockup composite and committed at
   `assets/context/dims_schematic.png` (780×420).
2. The prior lab paper's own Figure 3 schematic (the l₁/l₂/d/θ coordinate-frame
   drawing, world frame {W} and body frame {B}) — this is the "Fig. 3:
   Schematic diagram of kinematic model" image you've been pasting. **Have
   it** — same extraction, committed at
   `assets/context/paper_fig3_schematic.png` (500×404).
   Resolution note: both are cropped from your composite mockup image
   (2000×824 total), so they're only as sharp as that source. Fine for a
   slide at their current size; if you have either as a separate
   higher-resolution original, send it and I'll swap it in.

**No video on this slide.**

**Right column — the equations, verified:**

*Inverse kinematics* (body twist → wheel speeds):
```
ω_FR = (1/a)(u + v + r(l₁+d))      ω_FL = (1/a)(u − v − r(l₂+d))
ω_RR = (1/a)(u − v + r(l₂+d))      ω_RL = (1/a)(u + v − r(l₁+d))
```

*Forward kinematics* (wheel speeds → body twist):
```
v_x = (a/4)(ω_FR+ω_FL+ω_RR+ω_RL)
v_y = (a/4)(ω_FR−ω_FL−ω_RR+ω_RL)
ω_z = a/(2(l₁+l₂+2d)) · (ω_FR−ω_FL+ω_RR−ω_RL)
```
with l₁ = 0.403 m, l₂ = 0.333 m, d = 0.1577 m, a = 0.0762 m (wheel radius),
u = v_x, v = v_y, r = ω_z.

**I checked this by hand, both ways:**
- The inverse-kinematics equations are the report's own Eq. 1.2, just
  relabelled — your notation keeps l₁, l₂, d separate and uses `a` for
  wheel radius instead of overloading `r`/`ω`, which is clearer than the
  report's own symbol choice, not a different model.
- I independently re-derived the forward equations from your four inverse
  ones (summing all four gives v_x, the FR−FL−RR+RL combination gives v_y,
  the FR−FL+RR−RL combination gives ω_z after the l₁, l₂, d terms cancel
  and regroup) and got exactly what's on the slide. It's correct, not just
  plausible.
- l₁ = 403 mm and l₂ = 333 mm match the report exactly. The 360 mm
  wheel-to-wheel figure matches the report's own tape-measured width
  exactly. L = 1000 mm matches "1.00 m long." The one number I can't
  independently verify against the report is the 252 mm chassis-width
  (wheels excluded) — the report never states a wheels-excluded width, so
  this is presumably your own fresh tape measurement. No conflict with
  anything, just noting it's new rather than report-sourced.

**One labelling note**: your new schematic's caption currently reads "Fig.
3 — generic kinematic model (reference)," and the paper's own image below
it is captioned "Fig. 3: Schematic diagram of kinematic model." Two things
both called "Fig. 3" on one slide will read as a typo to anyone who's read
the report. Suggest renaming your new one to something like "This
platform's dimensions, tape-measured" and reserving "Fig. 3" for the
paper's original.

**Content not yet placed**: the "why this arrangement" motor-size
reasoning (heavy motors forcing width unless staggered) from the previous
version of this plan. Your new mockup is dimensions + equations only — say
if you still want the motor-size paragraph on this slide too, and I still
need the actual motor housing dimensions to write it with real numbers.

---

## Slide 8 — What the non-collinearity actually changes

**Image:** `assets/slide/fig02.png` (K₀/K₁ diagram, existing report figure).
**No video.**
Unchanged from the current deck (K₀ = 0.5607 m, K₁ = 0.4907 m, 14%
difference, 0 translation terms changed). Re-checked against the report;
nothing unverified found. Still waiting on your answer to what specifically
you flagged as unverified here, if anything beyond a general "double-check"
instruction.

Given slide 7 now carries l₁, l₂, d and the full equations, this slide's
job narrows to one thing: what the asymmetry actually *costs and changes*
(the 14% lever-arm difference, and that translation is unaffected) — the
consequence, not the setup. Worth keeping distinct from slide 7 rather than
merging; they're doing different jobs.

---

## Slide 9 — The machine as built (old "starting condition" + "machine as
built," clubbed)

**Video:** `robot_demo_under25MB.mp4` — open-loop joystick drive, the
"before" picture, as its own placeholder box.
**Image:** none additional planned (Figure 3, the chassis photo, would be
the natural second visual but there may not be room alongside a video
placeholder and four dimension tiles — flagging that this slide may need
to choose between the photo and the video rather than carrying both; video
wins on the "the video needs to actually be watched" argument already
made for the other video slides).

**Tiles:** mass (more than 45 kg), footprint (1.00 × 0.36 m, tape-measured),
wheel longitudinal offsets (0.403 / 0.333 m), wheel radius (0.0762 m).

**Bullets** (squeezed from two slides into one — expect this to need
trimming once built):
- Present at the start: chassis, four mecanum wheels, motors, drivers,
  power, Arduino Mega 2560 control.
- Absent at the start: no closed-loop control, no odometry, no perception,
  no autonomy.
- What changed: the wheel offset visible in the photo/video, the mast
  carrying the UV tubes and cargo-arm stepper, the mast sitting in the
  lidar's scan plane (the cause of the self-occlusion sector measured
  later).

---

## Slide 10 — Deployed electronics

**Image:** your new detailed block diagram (rail-coloured, real part
numbers — SSR-50DD, Cytron MDD20A ×2, Rhino RMCS-2086 ×4, 8-channel level
shifter, common-ground-bus warning). Replaces the report's own Figure 5.
**No video.**

Fact-check done: the diagram's own stated gains (Kp 45, Ki 250, Kd 0.5,
Kff 37.3–38.4 PWM/(rad/s)) match the report's deployed values exactly — the
diagram is accurate to the real firmware, not just a nice picture.

Still need: a higher-resolution export than the 1433×1450 webp preview, if
one exists, since this is a full-bleed slide image with a lot of small
text on it.

---

## Slide 11 — The platform, as measured rather than as specified *(my
inference — confirm or reject)*

You haven't said what happens to the current spec table (Table 1.1: mass,
half-track width, drive motors, encoders, motor drivers, real-time
controller, host computer, lidar, power, cargo arm, operating velocity
limit). I've placed it here as a "full picture" reference slide between
the electronics diagram and the one specific decision (the controller
swap) that slide 12 zooms into. **This is my guess at where it goes, not
something you asked for — say if it should move, get cut, or merge into
slide 9 or 10 instead.**

**No image, no video** — it's a table.

---

## Slide 12 — Why the drive controller changed, in one calculation

**No image, no video** — four tiles (558,792 edges/s, 16 MHz, ≈29
cycles/edge, 4 ESP32 quadrature units) plus a two-column timing-argument /
interface-problem layout. Unchanged from the current deck.

**Sequence check, confirmed**: 9 (machine + dimensions + open-loop video)
→ 10 (deployed electronics, whole system) → 11 (full spec table) → 12 (the
one decision worth defending, with the calculation behind it). Whole
picture, then the specific thing that needs justifying. Holds together.

---

## Open items, all of them

1. ~~The annotated dimension schematic for slide 7~~ — done, have it.
2. ~~A clean copy of the paper's Figure 3~~ — done, have it.
3. Whether the motor-size "why this arrangement" paragraph still goes on
   slide 7, and the actual motor housing dimensions if so.
4. The Type-1 chassis photo with tape marks, mentioned two rounds ago —
   assuming this is the same image as item 1 (the annotated schematic IS
   a Type-1 chassis with tape-measured marks on it). Say if it's a
   different, separate photo.
5. A higher-resolution export of the electronics diagram for slide 10.
6. What specifically was flagged as unverified on slide 8.
7. Confirm or reject slide 11 (the spec table) — my placement, not yours.
8. Equations as styled text (current, works) vs. rendered LaTeX/mathtext
   images (matches the look of your slide-7 mockup) — the mockup you sent
   uses real typeset fractions, which the current deck's equations don't.
   If slide 7 should look like your mockup, this needs a real build change,
   not a wording edit: I'd render each equation block to a small transparent
   PNG (matplotlib mathtext, matching deck fonts/colours as closely as
   mathtext allows) and place that image instead of a text run. Worth
   doing once and reusing the same method everywhere else an equation
   appears (slide 7's inverse/forward kinematics, and the report's Eq. 1.1
   on the same slide if it goes there too).
