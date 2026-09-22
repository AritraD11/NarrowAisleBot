# Slide plan, strand-one opening (slides 6–10+)

Not built yet. This is the record of what was decided in chat, so nothing
gets lost between sessions. Read it, mark it up, and we edit from here —
nothing in `content.py` or the `.pptx` changes until you say build.

Numbering below is the **new** sequence the author gave, not the numbering
in the currently-built deck. Slides 1–5 are unaffected by this plan (title,
growth/gap slide, three-strands slide, objectives, and the strand-one
divider — all already edited and pushed in earlier commits).

---

## Slide 6 — "The aisle sets the problem" (existing, confirmed good)

Author's note: "slide 6 is good, just one more bullet point about
holonomic movement and omnidirectional movement, degree of freedom."

**Add this bullet**, fact-checked against standard mobile-robotics
terminology (not report-specific, but directly load-bearing for why
mecanum was chosen at all):

> A holonomic drive commands all three planar degrees of freedom —
> forward, lateral, yaw — independently and at the same time. A
> conventional drive (differential, Ackermann) is non-holonomic: it has
> three configuration variables but only two commandable velocities, so
> heading and translation are coupled. Mecanum wheels make the platform
> holonomic, which is exactly the property a lateral aisle correction
> needs.

Fact-check: this is the standard definition (configuration DOF vs.
controllable DOF; a differential-drive robot cannot instantaneously
translate sideways without first rotating). Solid, not report-sourced
because it doesn't need to be — it's the textbook reason mecanum exists.

No other change to this slide.

---

## Slide 7 — the prior lab's solution, why it takes this shape, then the kinematics

New, merged slide. Three things on it, in this order:

1. **The prior solution.** Images from the earlier lab paper (report's own
   Figure 1 — the two chassis variants, panel (a)/(b), and the kinematic
   schematic, panel (c)) plus the new image you're supplying: a physical
   Type-1 chassis with tape-measured marks. **I don't have that photo yet —
   send it and I'll add it as a committed asset, same as the two warehouse
   photos on slide 2.**

2. **Why this arrangement — the motor-size argument.** Your framing:
   heavy-duty motors (needed for torque and payload) are physically large.
   Placed at the four corners of a symmetric rectangle, two motors have to
   sit side by side at the same cross-section, forcing the chassis wide.
   The non-collinear layout staggers the pairs longitudinally instead, so
   the motors don't compete for width at the same cross-section — cutting
   the required width roughly in half.
   **This is not yet fact-checked and I want to flag that clearly before
   it goes on a slide**: the report's own stated reason for non-collinearity
   is the general packaging one ("the width of the machine is set by the
   wheel layout rather than by the payload"), not a motor-housing-dimension
   argument specifically. Your version is a real, more concrete engineering
   reason and I have no reason to doubt it — I just don't have the actual
   motor housing dimensions (length/diameter of the RMCS-2086 / GTK08
   geared motors) to state it with real numbers rather than "large" and
   "this much." Send me those two numbers (or the datasheet) and I'll write
   it precisely instead of vaguely.

3. **The kinematics.** The forward/inverse-kinematics equations already in
   the deck (report Eq. 1.1–1.2, K₀ = l₁+d, Kᵢ = l₂+d, the four wheel-speed
   equations). You called this "the proposed inverse kinematics equation" —
   worth being precise on terminology once, since a panel may ask: going
   from commanded body twist (u, v, ω) to the four wheel speeds is the
   inverse-kinematics direction (task space → joint space), and that's what
   Eq. 1.2 is. The reverse (recovering body twist from measured wheel
   speeds, which the odometry uses) is the forward direction. Both are
   already in the report; I'll keep both directions clearly labelled rather
   than just calling one of them "the kinematic model."
   **On equations rendering properly**: right now they're plain styled text
   runs (Unicode subscripts, ω/K characters) — they render cleanly in the
   current deck (checked in the QA screenshots) but aren't real typeset
   equations. If you want them to look like textbook equations rather than
   styled text, I can render them with LaTeX/mathtext to a small PNG and
   place that instead — cleaner, but it's a real change to how equations
   are built in this deck, not a wording edit. Say if you want that.

---

## Slide 8 — asymmetric vs. symmetric, main differences

Existing content (K₀ = 0.5607 m, Kᵢ = 0.4907 m, 14% difference, 0
translation terms changed) — this is the current "What the non-collinearity
actually changes" slide. I re-checked it against the report (Section 1.2):
every number on it traces directly to the report's own derivation. I don't
see anything unverified in the version I have.

**Question back to you**: is there something specific on your working copy
of this slide that's unverified, or is this a general "double-check before
we lock it" instruction? If you've added anything to this slide on your own
copy since I last saw it, tell me what, and I'll check it the same way.

---

## Slide 9 — the machine as built (old slides 8+9, clubbed)

Merging: the old "starting condition" slide (present-at-start /
absent bullets, video placeholder for the open-loop drive) and the old
"machine as built" slide (dimension tiles, wheel/mast bullets) into one.

Draft structure:
- **Tiles**: mass (more than 45 kg), footprint (1.00 × 0.36 m, tape-measured), wheel
  longitudinal offsets (0.403 / 0.333 m), wheel radius (0.0762 m).
- **Video placeholder**: `robot_demo_under25MB.mp4` — the open-loop
  joystick drive on the original Arduino Mega control, as the "before"
  picture.
- **Bullets** (trimmed to fit both slides' content in one): present at the
  start (chassis, four mecanum wheels, motors, drivers, power, Arduino
  Mega) / absent at the start (no closed-loop control, no odometry, no
  perception, no autonomy) / what changed (wheel offset visible in the
  photo, mast carries UV tubes and the cargo-arm stepper, mast sits in the
  lidar's scan plane — the cause of the self-occlusion sector measured
  later).

This is a genuine content squeeze (two slides' worth of bullets into one),
so expect it to need trimming once built — I'll flag if anything doesn't
fit rather than silently cutting it.

---

## Slide 10 — deployed electronics (your new diagram)

You've built a considerably more detailed block diagram than the report's
own Figure 5 — full rail colouring, actual part numbers (SSR-50DD boost/buck
converters, Cytron MDD20A drivers, Rhino RMCS-2086 motors, the 8-channel
level shifter, the common-ground-bus warning at the bottom). This is a real
upgrade in clarity over the report figure and I'd use it in place of Figure
5, not alongside it.

**One thing to confirm**: the diagram's own text states Kp 45 / Ki 250 /
Kd 0.5 and Kff 37.3–38.4 PWM/(rad/s) — these match the report's deployed
gains exactly, so no conflict there. Good sign the diagram is accurate to
the actual deployed firmware, not just aspirational.

**What I need**: the source file (not the 1433×1450 webp preview) if you
have a PDF/SVG/PNG export at higher resolution — the webp is usable but a
full-bleed slide image benefits from more resolution than a preview
thumbnail gives. If the webp is all there is, I'll use it as-is; just
flagging that a proper export would look sharper.

**Sequence check, as asked**: slide 9 (machine + dimensions + open-loop
video) → slide 10 (deployed electronics, the whole system) → next
(unbuilt yet) "why the drive controller changed" — the ESP32/Arduino Mega
swap and the timing-budget argument. This ordering holds together: show the
whole electronics picture first, then zoom into the one specific decision
worth defending (why swap controllers) with the calculation behind it. Yes,
the narrative makes sense — whole system, then the one decision inside it
that needs justifying, in that order.

---

## Open questions before anything gets built

1. Motor housing dimensions (length/diameter) for the width-halving
   argument on slide 7 — needed or the claim stays qualitative.
2. The Type-1 chassis photo with tape marks, for slide 7.
3. A higher-resolution export of the deployed-electronics diagram, for
   slide 10, if one exists.
4. What specifically (if anything) is unverified on slide 8, from your side.
5. Whether to keep equations as styled text (current, works, not real
   typesetting) or move to rendered LaTeX/mathtext images (cleaner,
   bigger change).

Nothing here is built into the deck. Next step is you marking this up,
then I apply the approved parts slide by slide, same as slides 3/5/9/10
already pushed.
