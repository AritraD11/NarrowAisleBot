# -*- coding: utf-8 -*-
"""Every slide in the deck, as data.

Rules this file keeps to, because the deck is being presented against a report
a committee has already read:

  * No number appears here that is not in APS_Report_Aritra_.pdf. Where a
    number is quoted, the section it comes from is named in the notes.
  * The notes are the report's own sentences, lightly cut for speaking. That is
    what "the narration as it is" means: the slide is the headline, the notes
    are the argument, and the argument is the one that was submitted.
  * A claim keeps its qualifier. "Below 1 per cent out to about 10 m" does not
    become "below 1 per cent". "Demonstrated within a live mapping session"
    does not become "demonstrated".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import ACCENT, GREEN, AMBER, RED, GREY, MUTED

A = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
FIG = lambda n: os.path.join(A, 'slide', 'fig%02d.png' % n)
PIC = lambda n: os.path.join(A, 'photo', n + '.jpg')

R = 'The Narrow-Aisle Robot'
E = 'Environmental Monitoring'
F = 'Contactless Fatigue'
C = 'Conclusions'

SLIDES = [

# ============================================================== OPENING ======
dict(layout='title',
     kicker='Annual Progress Seminar · First year of PhD',
     title='Development and Validation of Narrow-Aisle Robotic '
           'and IoT-Based Systems for Warehouse Management',
     image=PIC('title'),
     meta=[('', 'Aritra Das'),
           ('Roll No', '25D0074'),
           ('Supervisor', 'Prof. Ambarish Kunwar'),
           ('Department', 'Biosciences and Bioengineering, IIT Bombay')],
     date='23 September 2026',
     notes="""
Three strands in parallel: an autonomous mobile platform dimensioned for a narrow
storage aisle, an instrumented environmental monitoring system for the space that
platform traverses, and a proposed method for assessing the physical fatigue of the
people who share that space without requiring them to wear an instrument.

The photograph is the machine itself, on the laboratory floor, August 2026. Every
image in this deck is either a photograph of this robot or a figure generated from
this project's own logs.
"""),

dict(layout='content', kicker='Overview',
     title='Three strands, one problem',
     sub='They share instrumentation, not a subject',
     tiles=[('Strand 1', 'The machine that moves through the aisle', None),
            ('Strand 2', 'The air it moves through', None),
            ('Strand 3', 'The people who share it', None)],
     bullets=[
        ('Built, instrumented and measured. 45.54 kg, closed-loop control at every wheel, '
         'four results established against physical references.', None, 'Robot. '),
        ('Deployed and running. Four zones, two radio-isolated installations, one database, '
         'three concurrent communication channels.', None, 'Monitoring. '),
        ('A hypothesis and a completed literature survey. No hardware built, no data collected.',
         None, 'Fatigue. '),
        ('Multi-sensor integration, calibration against a physical reference, real-time '
         'acquisition, and control that fails safe, recur in all three.', None, 'What is shared. '),
     ],
     takeaway='An error made in one strand has repeatedly become a method in the next.',
     notes="""
The three are treated as strands of a single problem rather than as three projects, and
not because they share a subject. They share instrumentation.

The monitoring system established the practice of verifying a configuration against the
running system rather than against a file, which was then applied to the platform. The
platform work established that a control law must be observed responding to a change
rather than inferred from a steady-state snapshot, which was then applied to the
monitoring system.

The three strands are at markedly different stages, and the report states each position
as it stands. I will do the same here, in that order.
"""),

dict(layout='content', kicker='Overview',
     title='Five objectives',
     size=14.5, gap=10,
     bullets=[
        ('Development and experimental characterisation of a full-scale asymmetric '
         'mecanum platform for narrow-aisle operation.', None, 'O1  '),
        ('~Closed: controller, kinematics and odometry characterised against measured references.'),
        ('Localisation and autonomous navigation at corridor-width clearances.', None, 'O2  '),
        ('~Closes as characterised rather than as optimal. Navigation demonstrated within a live mapping session.'),
        ('Quantification of the cost and benefit of the asymmetric wheel layout.', None, 'O3  '),
        ('~Open. No matched symmetric baseline has been built, so the effect of the asymmetry is unquantified.'),
        ('An instrumented, closed-loop environmental monitoring system for warehouse '
         'environments.', None, 'O4  '),
        ('~Deployed across four zones. Two physical calibrations outstanding before readings can be quoted.'),
        ('A contactless framework for assessing worker fatigue.', None, 'O5  '),
        ('~Proposed. Survey complete, hypothesis stated, nothing built.'),
     ],
     takeaway='Two close on measurement, one closes as characterised rather than optimal, one is open for a reason that is not the platform\u2019s, and one has not begun.',
     notes="""
Read the sub-lines out as the status of each objective, because the committee will ask
and it is better to state it up front than to be drawn to it.

The three strands are at markedly different stages, and this slide is the honest version
of that: two objectives closed on measurement, one closing as characterised rather than
optimal, one open for a reason that is not the platform's, and two on the supporting
strands at opposite ends of their own development.
"""),

# =========================================================== STRAND ONE ======
dict(layout='divider', numeral='01', kicker='Strand One',
     title='The Narrow-Aisle Robot',
     line='A prototype establishes that the transformation between wheel and body velocity '
          'is correct. It establishes nothing about a 45.54 kg machine.',
     status='Built · instrumented · measured',
     notes="""
This is the principal strand and it occupies most of the report. The open question
identified in the introduction is one of scale, and it is specific: whether four geared
motors will hold a commanded velocity to a useful tolerance, whether the pose estimate
derived from them is adequate for navigation, and whether a perception stack can be built
above the asymmetry without the geometry introducing an unanticipated failure.

None of those can be resolved analytically. Each requires a built machine and an
instrument directed at it.
"""),

dict(layout='content', kicker=R,
     title='The aisle sets the problem',
     side='right', image=PIC('platform_side'), image_w=0.30, frame=True,
     bullets=[
        'A storage aisle is sized for the goods it holds and for a human picker, not for a vehicle.',
        'Available clearance is of the order of centimetres rather than metres.',
        'A differential-drive or steered platform cannot correct a lateral offset without a '
        'manoeuvre, and the manoeuvre consumes longitudinal space the corridor does not have.',
        'Mecanum rollers at 45° give a contact force component along the roller axis, so four '
        'wheels at different velocities produce motion in any direction in the plane.',
        'A lateral offset is then corrected by translating sideways, in the ideal case with '
        'no fore-aft travel at all.',
     ],
     takeaway='Warehouse automation has grown around wide, well-structured routes. '
              'The aisle is the part of the building where the geometric constraint is most severe.',
     notes="""
Introduction. Once a differential-drive platform is misaligned inside an aisle, recovering
alignment requires either reversing out or a sequence of short forward and backward
motions, both of which cost time and both of which risk contact with the racking.

Mecanum kinematics alone do not solve the aisle problem, because a conventional four-wheel
mecanum platform places its wheels at the four corners of a rectangle. The chassis must
then be wide enough to carry that rectangle, and the width of the machine is set by the
wheel layout rather than by the payload. That is the next slide.
"""),

dict(layout='content', kicker=R,
     title='The geometry is inherited, not proposed here',
     sub='Figure 1 · prior work in this laboratory [1]',
     side='right', image=FIG(1), image_w=0.52,
     bullets=[
        'Earlier work in this group derived the kinematics for an asymmetric, non-collinear '
        'mecanum layout intended for narrow aisles, and demonstrated the principle on a small '
        'prototype.',
        'Panels (a) and (b) are the two chassis variants that paper proposes. Variant (a), with '
        'the lateral wheels close together, is the arrangement built here.',
        'Panel (c) is that paper’s kinematic schematic: wheel origins at longitudinal '
        'distances l₁ and l₂ from the body centre, half track d.',
        'Point-symmetric rather than mirror-symmetric placement preserves the three planar '
        'degrees of freedom while relaxing the constraint that sets vehicle width.',
     ],
     takeaway='What the prior work did not establish is whether the geometry survives '
              'the transition to a full-scale machine.',
     notes="""
Section 1.2. The geometric premise for such a machine already exists. Mecanum drive is
mature as a mechanism and the symmetric four-wheel configuration is standard. The
asymmetric, non-collinear placement used here is far less common, and the prior work
establishing its kinematics for narrow-aisle application is the laboratory study cited
as reference 1.

Say plainly: this slide is somebody else's result. Mine begins at full scale.
"""),

dict(layout='content', kicker=R,
     title='What the non-collinearity actually changes',
     sub='Figure 2 · drawn at the dimensions of the machine built here',
     side='bottom', image=FIG(2), image_w=1.0,
     tiles=[('Kₒ = 0.5607 m', 'Outer diagonal pair: l₁ + d', None),
            ('Kᵢ = 0.4907 m', 'Inner diagonal pair: l₂ + d', None),
            ('14 %', 'Difference between the two lever arms', AMBER),
            ('0', 'Translation terms that change', GREEN)],
     takeaway='Only the yaw column changes. That is the whole of the difference, and it is '
              'also the whole of the risk.',
     notes="""
Section 1.2. On a symmetric platform the four wheels sit at the corners of a rectangle,
every wheel is the same longitudinal distance from the body centre, and one yaw
coefficient serves all four. Move one diagonal pair inward and that is no longer true.
The outer pair keeps a lever arm of the outer longitudinal distance plus the half track,
the inner pair gets a shorter one, and the two differ here by 14 per cent.

The translation terms are identical in both layouts, which is why forward and lateral
motion feel the same on either machine.

The risk: a wheel driven with the wrong lever arm produces a yaw rate wrong by that
14 per cent, and nothing else in the transformation gives any sign of it.
"""),

dict(layout='content', kicker=R,
     title='The starting condition, stated plainly',
     side='right', image=PIC('chassis_wheels'), image_w=0.42, frame=True,
     two_col=None,
     bullets=[
        ('Chassis, four mecanum wheels on the asymmetric layout, four geared drive motors, '
         'two motor drivers and the power system. Control by an Arduino Mega 2560.',
         None, 'Present at the start. '),
        ('No closed-loop velocity regulation, no odometry, no on-board kinematic model, '
         'no perception, no autonomy.', None, 'Absent. '),
        ('The firmware, the ROS 2 software, the instrumentation and every measurement '
         'quoted in this report were carried out end to end.', None, 'Everything beyond that. '),
     ],
     takeaway='Establishing which way the scanner counts its angles took a drive against a '
              'placed block, because nothing on the sensor says which way it is looking.',
     notes="""
Section 1.3. Work began from an assembled mechanical platform.

The takeaway line is Figure 4, the commissioning step: a fault of that kind is trivial to
correct once identified, and costly for as long as it is not. It is worth one sentence
here because the same pattern recurs through the year: the faults that cost time were the
ones that produced entirely normal-looking telemetry.
"""),

dict(layout='content', kicker=R,
     title='The machine as built',
     sub='Figure 3 · 1.00 m long, 0.36 m wide across the wheels',
     side='right', image=FIG(3), image_w=0.34,
     tiles=[('45.54 kg', 'Mass, measured', None),
            ('1.00 × 0.36 m', 'Footprint, tape-measured', None),
            ('0.403 / 0.333 m', 'Outer and inner wheel longitudinal distance', None),
            ('0.0762 m', 'Wheel radius', None)],
     bullets=[
        'The four mecanum wheels sit non-collinearly rather than at the corners of a rectangle: '
        'the pair nearer the camera is visibly offset along the length from the pair behind.',
        'The vertical mast carries the three ultraviolet tubes and the stepper axis of the cargo arm.',
        'The mast and its payload sit within the plane of the lidar (the black unit above the '
        'battery) and are the cause of the self-occlusion sector measured later.',
     ],
     notes="""
Section 1.3, Figure 3. Point at the wheels: the offset is visible in the photograph, which
is the easiest way to make the geometry concrete before the equations.

Point at the mast: it is the reason for the 90-degree blind sector, and that is a general
consequence of carrying a payload above a single-plane scanner rather than a mistake
specific to this machine.
"""),

dict(layout='content', kicker=R,
     title='The platform, as measured rather than as specified',
     sub='Table 1.1 · every figure read off the machine, except the lidar range specification',
     table=(['', ''], [
        ('Mass', '45.54 kg'),
        ('Half track width', '0.15769 m, identical for all four wheels'),
        ('Drive motors', '4 × geared DC, 24 V, 1:47 reduction, 60 rpm rated'),
        ('Encoders', 'Front pair GTK08, 186,264 counts/rev at the wheel; rear pair optical, 93,132'),
        ('Motor drivers', '2 × dual-channel, 20 A continuous, 1.5 V logic threshold'),
        ('Real-time controller', 'ESP32, 100 Hz control loop, hardware quadrature decoding'),
        ('Host computer', 'Raspberry Pi 5, Ubuntu 24.04, ROS 2'),
        ('Lidar', 'YDLIDAR X4 Pro, single-plane triangulation, 360°, 0.12–10 m rated'),
        ('Power', 'LiFePO₄ 12.8 V 30 Ah, boost to 24 V drive, buck to 5 V logic'),
        ('Cargo arm and lighting', 'Two lateral and one vertical stepper axis, three-tube staged UV'),
        ('Operating velocity limit', '0.12 m/s linear, 0.30 rad/s yaw'),
     ]),
     col_w=[0.27, 0.73], table_size=12.5,
     takeaway='The manufacturer’s lidar accuracy figure is treated as a factory acceptance '
              'condition, not as a runtime error distribution.',
     notes="""
Table 1.1. Do not read this table out. Let it sit while you say the three things that
matter about it: it is measured rather than taken from data sheets; the two encoder types
differ by a factor of two in resolution and in wiring convention, which caused a
miswiring during commissioning; and the operating velocity limit is low on purpose,
because the machine works in a corridor.

The lidar row is the one exception to "measured", and the report says so. Section 1.12
measures the installed unit's stationary scatter instead of extrapolating from the
specification.
"""),

dict(layout='content', kicker=R,
     title='Why the drive controller changed, in one calculation',
     tiles=[('558,792', 'Counted encoder edges per second, four motors at rated speed', None),
            ('16 MHz', 'ATmega2560 instruction rate', None),
            ('≈ 29', 'Cycles available per edge for the entire interrupt routine', RED),
            ('4', 'ESP32 hardware quadrature units, one per motor', GREEN)],
     two_col=(
        ('The timing argument', [
            'Front encoders give 186,264 counts per revolution at the wheel, rear 93,132, '
            'both after quadrature decoding and gear reduction.',
            'At rated speed the output shaft turns once per second.',
            'Interrupt entry, register save, decode, counter update and return do not fit in '
            '29 cycles. Encoder counting alone saturates the processor.',
            'The ESP32’s pulse counter decodes quadrature in hardware, so the processor is '
            'free for the 100 Hz loop and the serial link.',
        ]),
        ('The interface problem it created', [
            'ESP32 inputs are 3.3 V parts with an absolute maximum near 3.6 V. The fitted '
            'encoders produce close to 4.7 V.',
            'All eight encoder channels pass through an eight-channel bidirectional level '
            'translator on discrete transistors.',
            'Only the feedback direction is translated. The drivers threshold at 1.5 V and '
            'accept 3.3 V command signals directly.',
            'A fault in the command path moves the machine. A fault in the feedback path '
            'only misreports it.',
        ])),
     size=12.5,
     notes="""
Section 1.4. The ESP32 removes the problem rather than optimising around it.

Two further properties of the part were useful: substantially greater processing
capability and memory than the part it replaced, and an integrated 2.4 GHz radio, which
allowed the first phone-based control surface to be hosted on the controller itself
before the host computer was introduced.

The asymmetry in the level translation is deliberate, and the last line on the right is
the reason: fewer components in the command path is worth having.
"""),

dict(layout='content', kicker=R,
     title='Deployed electronics, end to end',
     sub='Figure 5 · organised in three layers, each on its own rail colour',
     side='right', image=FIG(5), image_w=0.36,
     bullets=[
        ('LiFePO₄ 12.8 V 30 Ah, boosted to the 24 V drive rail and bucked to the 5 V logic '
         'rail.', None, 'Power distribution. '),
        ('Raspberry Pi 5 for planning and perception; ESP32 for the 100 Hz real-time loop; the '
         'original Arduino Mega reassigned to the cargo arm and the ultraviolet lighting rather '
         'than discarded.', None, 'Compute and command. '),
        ('Four motors through two dual-channel drivers, with all eight encoder channels returning '
         'through the level translator.', None, 'Drive and odometry feedback. '),
        'The control constants shown against the microcontroller are the deployed ones, and they '
        'are the values derived later in this section.',
        'The encoder rows carry their wire colours, because the front and rear motors do not '
        'share a convention, and that difference has already put a channel on the wrong pin '
        'once during commissioning.',
     ],
     size=13,
     notes="""
Section 1.4, Figure 5. Do not walk through this figure block by block. Trace one path and
stop: battery to the 24 V drive rail and the 5 V logic rail; the ESP32 command out to a
driver; the encoder return back through the level shifter.

The control constants shown against the microcontroller are the deployed ones, and they
are the values derived in Section 1.6, which is the next part of the talk.
"""),

dict(layout='content', kicker=R,
     title='Kinematic model',
     sub='Figure 6 · dimensioned plan view, taken from the mechanical assembly',
     side='right', image=FIG(6), image_w=0.46,
     bullets=[
        'The outer diagonal pair (front-right and rear-left) sits at l₁ = 0.403 m from the '
        'body centre; the inner pair at l₂ = 0.333 m. Half track d = 0.15769 m is common to all four.',
        'Two derived constants carry the asymmetry through every equation: '
        'Kₒ = l₁ + d = 0.5607 m and Kᵢ = l₂ + d = 0.4907 m.',
        'ωᶠᴿ = (u + v + ωKₒ)/r,  ωᶠᴸ = (u − v − ωKᵢ)/r,  '
        'ωᴿᴿ = (u − v + ωKᵢ)/r,  ωᴿᴸ = (u + v − ωKₒ)/r.',
        'Two width figures appear in the report and they measure the same span by different '
        'means: 360 mm by tape, 375.4 mm from the assembly. Every experimental result is '
        'referenced to the tape figure.',
     ],
     takeaway='Substituting a single shared coefficient anywhere in the software reduces the '
              'machine, in that code path alone, to an ordinary symmetric mecanum platform.',
     notes="""
Section 1.5. Each wheel carries its own yaw coefficient, which is the practical
consequence of the asymmetry.

Inverting that system recovers the body twist from the four measured wheel velocities,
and this inverse is what the odometry integrates.

The two width figures differ by 15.4 mm. The report states which one every result is
referenced to, because a collision footprint set from the wrong one would be wrong by
that much in a corridor with centimetres of clearance.
"""),

dict(layout='content', kicker=R,
     title='A free observable, and why it is worth less than it looks',
     bullets=[
        'The first and fourth rows of the inverse kinematic matrix share a translational term, '
        'and the second and third share its complement. Each diagonal pair therefore yields '
        'an independent yaw-rate estimate on its own lever arm.',
        'The mean of the two is the published yaw rate. Their difference is an encoder-derived '
        'yaw-consistency residual, obtained without any additional sensor.',
        'It is not a calibrated measurement of slip. Unequal effective wheel radii, encoder '
        'scale error, backlash and mechanical compliance all contribute to the same residual.',
        'The two estimates are formed from disjoint pairs of wheels, which is what makes them '
        'separate estimates, not the lever arms differing. A symmetric platform carries a '
        'residual of exactly the same form.',
        'What the differing lever arms change is the weighting: '
        'eω = (r/2)(δₒ/Kₒ − δᵢ/Kᵢ). On a symmetric platform the common-mode component '
        'cancels exactly. Here it survives, scaled by (r/2)(1/Kₒ − 1/Kᵢ) = 0.0097.',
     ],
     size=14,
     takeaway='The asymmetry does not create the observable. It makes the residual sensitive '
              'to a class of error a symmetric layout cancels, at about one per cent of that '
              'error’s magnitude.',
     notes="""
Section 1.5. The contribution of the asymmetry is stated narrowly here, because it is
readily overstated.

The two estimates are not statistically independent, since a disturbance common to both
pairs enters both.

Whether that one-per-cent sensitivity is useful for drivetrain diagnostics is a question
for measurement rather than for algebra, and I report what the residual actually did
across four drives later in the talk.
"""),

dict(layout='content', kicker=R,
     title='The per-wheel velocity loop',
     sub='Figure 7 · as the deployed firmware runs it, one loop per wheel at 100 Hz',
     side='right', image=FIG(7), image_w=0.54,
     bullets=[
        'Not a plain PID. A two-term feedforward model supplies most of the drive from the '
        'commanded velocity alone, and the three feedback terms correct only what the '
        'feedforward gets wrong.',
        'That separation is what permits the integral gain to be as large as it is without '
        'the loop becoming oscillatory.',
        'The derivative term acts on the measurement rather than on the error, so a step in '
        'the commanded velocity produces no derivative kick.',
        'It is taken through a heavier filter than the velocity signal, because '
        'differentiating amplifies whatever noise survives the first filter.',
     ],
     notes="""
Section 1.6. Green marks the three blocks this version of the firmware added, orange the
command path out to the wheel, purple the controller and the measurement path back from
the encoder.

The two notes at the left of the figure are details a block diagram cannot show and that
change how the loop behaves.

Say the distinction out loud, because everything that follows depends on it: the
feedforward carries the bulk of the command, so the feedback terms are correcting a small
residual rather than supplying drive from zero.
"""),

dict(layout='content', kicker=R,
     title='The feedforward was fitted, not tuned',
     sub='Figure 8 · two-term model against measured open-loop data',
     side='right', image=FIG(8), image_w=0.50,
     bullets=[
        'Form: a speed-proportional term plus a static term carrying the sign of the command.',
        'The speed-proportional coefficient sits between 37.3 and 38.4 drive counts per rad/s '
        'across the four motors, a spread of 3 per cent. The static term is 8 counts on all four.',
        'Fitted against three independent open-loop campaigns: a manual drive logged at steady '
        'state, an automated sweep in 1.5 s windows, and a back-calculation from an earlier '
        'closed-loop run.',
        'The ratio of drive command to resulting wheel speed rises as speed falls, the '
        'signature of breakaway friction that a straight line through the origin cannot reproduce.',
        'The two-term fit holds every measured point inside 8 per cent, and the two '
        'high-confidence points inside 2.2 per cent.',
     ],
     size=13.5,
     takeaway='The static term is faded in across 0.05 to 0.20 rad/s rather than stepped, '
              'so a very small commanded velocity does not produce a discontinuity in the drive.',
     notes="""
Section 1.6. The feedforward came first, because it was the part that could be fitted to
data rather than tuned by hand.

The inadequacy of a single-slope model is evident in the raw data, before any fit is
attempted. That is worth emphasising: the second term was not added to improve a fit, it
was added because the raw ratio told you the model was the wrong shape.
"""),

dict(layout='content', kicker=R,
     title='Where the gains came from',
     sub='Including the part of the argument that does not work out',
     size=13.5,
     two_col=(
        ('Computed, not searched', [
            'Inverting the fitted slope gives a plant gain of about 0.0263 rad/s per drive count.',
            'For a first-order plant, direct synthesis fixes the integral gain from that and a '
            'chosen closed-loop time constant alone.',
            'τ = 0.15 s chosen (fifteen control periods, deliberately conservative), giving '
            'Kᵢ = 253. The deployed value is 250.',
            'That is the single largest change from the previous firmware, where it was 30. At 30 '
            'the integral moved roughly three drive counts per second; an air run in May settled '
            'in up to 3.79 s, and what was settling it was mostly the proportional term.',
            'Raising it eightfold was only safe because of the feedforward.',
        ]),
        ('The gain whose argument was wrong', [
            'Kₚ = 45, from an assumed plant time constant of 0.18 s, plausible for a 100 W '
            'motor behind a 47:1 gearbox, but never measured, because every bench run to that '
            'point had logged steady-state points and no transients.',
            'Plant identification later put the true constant at about 0.09 s, half what had been '
            'assumed, which by the same formula calls for roughly 22.',
            'Two recomputed gains were run against the gain already in service, across sixteen '
            'combinations of setpoint and motor. Both produced more overshoot.',
            'The original value was kept, on measured evidence rather than on the theory that '
            'produced it.',
        ])),
     takeaway='The deployed gain is right. The argument that originally justified it rested on '
              'a number that was wrong by a factor of two, and the report records it as such.',
     notes="""
Section 1.6. This is the least satisfying part of the tuning and the report says so
explicitly. Do not smooth it over in the talk; a committee will find it, and it is better
delivered than discovered.

The derivative gain is 0.5, small on purpose. Against a genuinely first-order plant a
matched proportional-integral pair needs no derivative action at all, and everything this
term does is damp lag the first-order model does not contain: driver delay, gearbox
compliance, and the velocity filter itself.
"""),

dict(layout='content', kicker=R,
     title='Three arrangements that do more than the gains do',
     bullets=[
        ('Clamped dynamically, to whatever command range is left after the feedforward and the '
         'proportional and derivative terms have taken their share, rather than to a fixed bound. '
         'The previous firmware’s fixed clamp let the integral state reach values it could '
         'never usefully act on.', None, 'The integral. '),
        ('12 rad/s², applied before the loop sees the command, so a step from the host cannot '
         'ask for an acceleration the hardware will not produce, the condition that drives an '
         'integrator into saturation in the first place.', None, 'A slew limit of '),
        ('Lowered from 15 counts to 5. The larger value suppressed audible hum but cut a dead '
         'zone through the middle of the range in which the controller does its fine regulation, '
         'and produced a limit cycle at low speed.', None, 'Minimum drive output. '),
        ('Overspeed, stall, and a runaway detector looking for a saturated command pushing one '
         'way while the wheel turns the other. Drive sign and encoder sign must agree; if they '
         'disagree the loop sees positive feedback, and a motor rated at 60 rpm cannot overspeed '
         'its way past the overspeed threshold, so nothing else would catch it.',
         None, 'Three trips per wheel. '),
     ],
     size=13.5,
     takeaway='Velocity ceiling 5.20 rad/s per wheel, chosen so the worst of the four motors '
              'needs about 208 of 255 drive counts, leaving roughly 18 per cent as feedback '
              'authority. That is an in-air figure.',
     notes="""
Section 1.6. With breakaway friction now handled properly by the static feedforward term,
the minimum-output threshold can sit at the level where the motor is genuinely silent.

The last line matters for the next result but one: the 18 per cent margin is measured in
air, and the ground measurement is the reason it has to be revisited.
"""),

dict(layout='content', kicker=R,
     title='Result: the loop tracks, in air and on the floor',
     sub='Figure 9 · wheel velocity against command, wheels free of the ground',
     side='right', image=FIG(9), image_w=0.50,
     tiles=[('0.040–0.047', 'rad/s RMS per wheel, unloaded · 26,468 samples', GREEN),
            ('0.066–0.074', 'rad/s RMS per wheel, under chassis weight · 35,248 samples', GREEN),
            ('0.0 %', 'Saturated samples, every channel, every recorded run', GREEN)],
     bullets=[
        'The wheel reaches within 5 per cent of the commanded −2.207 rad/s in 0.20 s, '
        'overshoots by 3.5 per cent, and holds to a mean offset of 0.003 rad/s.',
        'Tracking error excursions coincide with commanded step edges, not with steady state.',
        'The autonomous drive falls in the same band as the loaded case, which is the band that '
        'matters operationally.',
        'Largest drive demand observed at the operating velocity limit was 131 of 255, '
        'headroom in the command, not a measurement of torque or traction reserve.',
     ],
     size=12.5,
     notes="""
Section 1.10. The two conditions are reported separately because the figures differ by
about half. The unloaded figure is reported because it separates the controller from the
wheel-ground interaction, not because it is the number the robot works at.

No channel saturated at any point and no feedback channel was lost, so these figures are
controller performance rather than an artefact of the drive reaching its limit.

Be precise about the 131 of 255: it bounds what the controller was asked for, not what
the drivetrain could deliver.
"""),

dict(layout='content', kicker=R,
     title='Result: a prediction written down, then tested',
     sub='Figure 10 · steady-state drive demand per unit wheel speed, unloaded against loaded',
     side='right', image=FIG(10), image_w=0.50,
     bullets=[
        'The band of 10 to 30 per cent was written down before the measurement was made.',
        'Measured increases: 22.5, 23.6, 30.3 and 21.0 per cent, a mean of 24.',
        'Three of the four motors fall inside the predicted band. The rear-right reaches '
        '30.3 per cent, 0.3 points above its upper bound, and is reported as an exceedance '
        'rather than rounded into agreement.',
        'Two later runs the same afternoon, at the same commanded levels but over different '
        'patches of floor, gave means of 14 and 3 per cent.',
        'So the increase is real while its size is not established to better than the width of '
        'the band it was predicted against. The likeliest reason is the surface rather than '
        'the load.',
     ],
     size=13,
     takeaway='A staircase test holding position and sweeping demand is what would settle the '
              'figure. It has not been run on the floor. The one motor at the edge of the band '
              'is worth keeping in view when it is.',
     notes="""
Section 1.10. The ground-load result is stated as a prediction and a test rather than as
an observation, because the predicted band was written down before the run. That is a
convention adopted after early errors, and it is stated in Section 1.9 alongside the other
one: configuration is verified by querying the running system rather than by reading a
configuration file.

Casual driving covers different floor patches and headings, where a staircase test holds
position and sweeps demand instead.
"""),

dict(layout='content', kicker=R,
     title='Result: two checks that do not involve the floor',
     tiles=[('2.22 × 10⁻¹⁶', 'Worst-case forward-kinematic round trip, 20,000 generated cases', GREEN),
            ('0.0054 m', 'Largest divergence, live estimate against offline re-integration', GREEN),
            ('0.0000 m', 'Divergence at the end of the drive', GREEN),
            ('0.035 rad/s', 'Median yaw-consistency residual while moving, four drives', GREEN)],
     bullets=[
        'The implemented forward-kinematic transformation reproduces independently generated '
        'reference twists to the order of machine epsilon for double precision. The '
        'transformation is coded correctly and contributes no numerical error of its own.',
        'Position recomputed offline from the raw encoder record agrees with the estimate the '
        'robot published live. That rules out a discrepancy between them as the source of the '
        'observed drift. It does not rule out an error shared by both.',
        'Yaw-consistency residual across four analysed drives, one of them deliberately '
        'irregular: 95th percentile 0.111 to 0.124 rad/s, worst instantaneous value 0.354 rad/s. '
        'No sample crossed the 0.5 rad/s episode threshold, which was fixed before the drives '
        'were analysed.',
        'That threshold sits about four times the observed 95th percentile, so it detects gross '
        'events and would not resolve a slow systematic drift.',
     ],
     size=12.5,
     takeaway='Within the sensitivity of this measure, the asymmetric geometry is not producing '
              'the sustained wheel-fight or scrubbing a non-symmetric layout might be expected to. '
              'The measure is blind to all four wheels slipping together.',
     notes="""
Sections 1.11. These say nothing about the physical wheel-ground model, which is what the
floor measurements address next.

Be careful with the yaw-residual claim. The episode threshold is the default of the
analysis tool rather than a value derived from the drivetrain. The honest statement is the
one on the slide: within the sensitivity of this measure, and at the roughly one-per-cent
common-mode weighting derived earlier.

The blindness to a rigid all-wheel slip mode matters, and it comes back in the
photogrammetry result.
"""),

dict(layout='content', kicker=R,
     title='Result: endpoint closure, against a mark on the floor',
     sub='Figure 11 · three logged drives, each driven back to its starting mark',
     side='right', image=FIG(11), image_w=0.52,
     bullets=[
        '19 mm over 8.00 m, 28 mm over 9.61 m and 96 mm over 10.61 m, which is 0.23, 0.29 and '
        '0.91 per cent of path travelled.',
        'The longest of the three, which includes the most rotation, is the worst.',
        'On an 18 m route the same estimator closed 0.229 m (1.27 per cent), and on a second long '
        'route 0.257 m over 18.14 m (1.42 per cent).',
        'Marking and re-reading a floor position by tape and eye is good to a few millimetres at '
        'best, so a 4.582 m route closing to 3.1 mm reads as closure at the resolution of the '
        'reference rather than as a 3.1 mm measurement.',
        'Error grows with the amount of rotation a route contains as well as with its length, '
        'consistent with increased lateral roller motion during rotational manoeuvres.',
     ],
     size=13,
     takeaway='Closure stays below 1 per cent of path out to about 10 m, and sits between 1.1 and '
              '1.5 per cent on the longest routes driven. It should not be generalised past that.',
     notes="""
Section 1.11. The precision of the reference bounds what the numbers mean, and the report
says so before it quotes the best of them.

Separating length from rotation calls for routes that vary the two independently, which is
a direct use for the larger test space. That is one of several places the test-space
constraint shows up, and they all resolve to the same cause later in the talk.

Wheel odometry, which is the least expensive sensing on the platform, is currently its most
extensively characterised source of state estimation.
"""),

dict(layout='content', kicker=R,
     title='Result: what the robot cannot see',
     sub='Figure 12 · the occluded sector, re-measured at five independent headings',
     side='right', image=FIG(12), image_w=0.44,
     tiles=[('≈ 90°', 'Blind wedge, mast and payload in the scan plane', AMBER),
            ('107 / 430', 'Beams masked, per revolution', AMBER),
            ('5', 'Independent headings the sector was measured at', GREEN)],
     bullets=[
        'The robot occludes its own scanner over part of the sweep, because the mast and payload '
        'sit within the scan plane.',
        'Those beams are masked in software before the scan reaches the mapping layer. Unmasked, '
        'a self-return is interpreted as a stationary obstacle travelling with the robot.',
        'It is stated as a result because it is a general consequence of carrying a payload above '
        'a single-plane scanner, and the trade-off between sensor placement, sector masking '
        'and accepted coverage loss does not appear to be characterised quantitatively in the '
        'literature.',
     ],
     size=12.5,
     notes="""
Section 1.12. The sector was measured at five independent headings rather than assumed
from the geometry, and it is consistent across all five.

Also from Section 1.12, if asked about the scanner itself: stationary ray scatter is 12 to
14 mm below 1.5 m in both captures; 22.3 mm in the 1.5 to 2.0 m band in one capture and
31.9 mm in a second taken from a differently obstructed parking spot, which fails the 25 mm
half-cell criterion the occupancy resolution implies. Beyond 2.5 m both captures return
55 to 200 mm and do not agree with each other. Neither a linear nor a quadratic degradation
model reproduces that, so the behaviour is scene-dependent: a range cap derived in one
position is a fact about that position until it reproduces elsewhere.
"""),

dict(layout='content', kicker=R,
     title='Result: rotating in place maps almost nothing',
     sub='Figure 13 · map coverage accumulated under three drive patterns',
     side='right', image=FIG(13), image_w=0.52,
     bullets=[
        'A deliberate 714-degree rotation over 642 s produced 43 occupied cells, 2.1 m on '
        'this measure.',
        'A 111 s arc combining rotation with translation produced 1545 cells, 77.2 m: '
        '88 per cent of what a full perimeter drive accumulates, in 18 per cent of its duration.',
        'The commissioning procedure in use had specified rotating in place at each corner to '
        'survey the space. That procedure discards its own corner observations.',
        'The effect is a property of this mapping configuration rather than of lidar in general: '
        'the thresholds governing scan integration and pose-graph node insertion are both '
        'motion-dependent, and neither was varied here.',
     ],
     size=13,
     takeaway='Coverage accumulates through translation. Turns are taken as rounded arcs while '
              'rolling, not as stationary pivots. No hardware modification is needed, and it is the '
              'highest-value procedural change identified during this work.',
     notes="""
Section 1.12. This is the most operationally consequential perception result obtained.

The quantity plotted is an occupied-cell equivalent length: occupied-cell count multiplied
by the 0.05 m cell size. It is a proxy for how much occupancy the map has committed to
rather than a physical wall length, and a single wall rendered several cells thick
contributes several times its own length, which is why the totals exceed the perimeter of
the room. Say that if anyone asks why 77 m appears in a room that size.

It is nonetheless the configuration the robot maps in, so the procedural consequence stands.
"""),

dict(layout='content', kicker=R,
     title='Result: repeatable maps, one criterion the room refuses',
     sub='Figure 14 · the three commissioning maps of 15 September, from the saved occupancy grids',
     side='right', image=FIG(14), image_w=0.50,
     bullets=[
        ('None of the three is folded.', GREEN, 'Not folded: pass.  '),
        ('Passes comfortably on each; best measured at 6.4 mm.', GREEN, 'Return to mark < 0.15 m: pass.  '),
        ('0.7, 0.8 and 2.9 per cent. Two clear the bar; the third misses by close to a factor '
         'of three.', AMBER, 'Doubled walls < 1 %: two of three.  '),
        ('73.0, 78.3 and 84.6 per cent against a threshold of 50.', RED, 'Unclassified < 50 %: fail.  '),
        'The run with the best coverage has the worst doubled-wall figure, because it was driven '
        'with the loosest lidar quality gate. Tightening the gate reduced doubled walls to 1.1 and '
        '0.9 per cent, but tore the free space into disconnected regions and the map graded folded.',
        'The looser gate was retained: a connected map with thicker walls is more useful than a '
        'clean one that has come apart.',
     ],
     size=12.5,
     takeaway='Coverage accumulates through translation past surfaces, and the available circuit '
              'is a few metres of it. The robot classifies what it drives past.',
     notes="""
Section 1.13. The four acceptance criteria were defined before the mapping work began.
They are engineering thresholds set by this project, not values from the literature. The
0.15 m return figure is the one with a physical basis, being the order of clearance the
target aisle geometry allows.

One qualification to state if asked, because the report volunteers it: the unclassified
percentage is computed over every cell in the published occupancy grid, which is the
bounding extent the mapper allocated rather than the traversable floor area. It therefore
overstates the fraction of reachable space left unobserved. It is used because it is the
criterion written down in advance and the same definition applies to every run compared.
A coverage criterion over a fixed region of interest would be the better measure and is owed.
"""),

dict(layout='content', kicker=R,
     title='Result: scan matching, measured rather than assumed',
     sub='Table 1.3 · same wheel data and same scans on each row',
     table=(['Route', 'Range cap', 'Wheel odometry alone', 'With the scan-matching front end'], [
        ('38 s square, 1.42 m of path', '10 m', '2.58 cm', ('6.2 cm', RED)),
        ('1047 s drive, 21.85 m of wheel path', '10 m', '0.229 m, 10.53°', ('0.477 m, 16.18°', RED)),
        ('82.5 s circle, 3.193 m of path', '5 m', '16.2 mm, 0.51 %', ('206.7 mm, 6.47 %', RED)),
     ]),
     col_w=[0.34, 0.12, 0.24, 0.30], table_size=12.5, table_h=1.55,
     bullets=[
        'On the 21.85 m route the front end applied 11.08 m of cumulative correction and roughly '
        'doubled the error. Nineteen loop closures fired, so this is not a back end that never ran.',
        'The third row was run last, to test the objection that every earlier measurement used a '
        'cap of 10 m or more. The cap was reduced to 5 m and verified against the live node before '
        'the drive. The cap did not rescue the matcher.',
        'All seventeen corrections in that run fired at a mean odometry spacing of 0.183 m, with '
        'about a centimetre of spread across the whole drive. The smallest was 106.7 mm against a '
        'search half-width of 150 mm.',
        'Four revert criteria had been written down before the drive and three fired. Of five keep '
        'criteria, the only one met was the one predicted to be neutral.',
     ],
     size=12.5,
     takeaway='A front end that corrects at a fixed odometric interval is responding to a '
              'schedule, not to disagreement between scans. It is switched off.',
     notes="""
Section 1.13. Scan matching is the mechanism by which lidar precision is meant to reach the
pose estimate. Here it increased pose error instead of reducing it.

The third row carries its own control: the same 3.193 m of driving, the same wheels and the
same scans, with the robot physically returned to its mark. The matching-on drive's own
wheel odometry closed at 16.2 mm, which is healthy, and the matched estimate on that same
data closed at 206.7 mm.

The corrections tracking the creation of pose-graph nodes rather than scan disagreement also
explains the zero loop closures on a route that returns to its own start: a closure would
arrive off-cadence, and none did.

Bound the finding, because it is easy to overstate. This scanner, this front-end
configuration, three routes of which two are tight circuits, which are poor geometry for a
matcher. A one-variable comparison on the 12.04 m perimeter route against an existing
matching-off baseline is still owed.
"""),

dict(layout='content', kicker=R,
     title='Result: the robot came back. The estimators did not.',
     tiles=[('3.85° and 4.49°', 'Heading change reported by wheel odometry, the published '
             'estimate and the SLAM pose, on two structurally different routes', RED),
            ('0.03°', 'What the floor said, read photogrammetrically against the tile grout', GREEN),
            ('≈ 1°', 'Demonstrated resolution of the instrument itself', None)],
     bullets=[
        'Heading was measured from video against world-static floor features, using tile-grout '
        'orientation as the reference. Frames extracted with ffmpeg, position from a threshold '
        'centroid on floor brackets, heading from a gradient-orientation histogram on the grout.',
        'The instrument was validated before its output was believed: −27.07° against a '
        'commanded −28.0°, and −18.50° against −19.4°. Two failure modes were found and '
        'corrected during that validation, the first being a camera mounted on the robot’s own '
        'mast, which by construction reports no rotation at all.',
        'Three estimates agreeing with one another while all three disagree with the floor is the '
        'signature of an error they share, not one that separates them.',
        ('Either an encoder or wheel-radius scale error, which is estimator error and recoverable '
         'by calibration, or a slip mode in which all four wheels slip together and the platform’s '
         'motion stays rigid, which is physical and is not.', None, 'Two candidates remain. '),
     ],
     size=12.5,
     takeaway='The elimination is not exhaustive. A geometric parameter error, a systematic '
              'mounting offset or a timing error between the encoder and pose streams would '
              'produce a similar signature and have not been separately excluded.',
     notes="""
Section 1.13. This is the result that sets the next stage of the work, so give it time.

The yaw-consistency residual rules out significant differential slip between wheels, and
the offline re-integration rules out an integration fault. That is what narrows it to two.

No instrument currently fitted to the robot can distinguish any of them. That is the
specific reason an independent heading reference is the next measurement rather than a
general improvement.

The 3.85 and 4.49 degrees are several times the instrument's demonstrated agreement, not
comparable to it. That is what makes them interpretable.
"""),

dict(layout='content', kicker=R,
     title='Result: autonomous navigation, as far as it goes',
     side='right', image=PIC('three_quarter'), image_w=0.36, frame=True,
     bullets=[
        'The first complete autonomous round trip, in August: the robot drove out, reversed its '
        'heading and returned, holding direction to within 5.5 and 3.7 degrees on the two legs and '
        'stopping 4.6 cm short of the commanded stop point.',
        'In later trials goals were selected by tapping the map in the dashboard, and the platform '
        'reached them in 21 and 26 s. Three goals were commanded across three trials and all three '
        'were reached.',
        'The operator interface was verified geometrically rather than by eye: the tapped-pixel to '
        'world-coordinate transform agrees with its analytic value to within one part in a million '
        'at three display pixel densities, well under a millimetre over the test map.',
        'That is a check that the transformation is coded correctly, not a statement about pointing '
        'accuracy, which is set by the size of a fingertip against the map scale and was not measured.',
     ],
     size=13,
     takeaway='Demonstrated within a live mapping session rather than against a saved map. '
              'The number of trials is small, and it is reported as what it is.',
     notes="""
Section 1.14. Establishing a success rate, a stopping-error distribution and behaviour
against obstacles requires a larger trial count in a space that permits varied routes,
which places this alongside the mapping work behind the same test-space constraint.

If asked about the local controller: a dynamic-window controller was adopted first, on the
reasoning that it is computationally lighter, and replaced with a sampling-based predictive
controller after the deployed configuration was found to stall on rotation-only goals. Its
rotate-to-goal critic invalidates candidates carrying translational motion in the final
phase, and because that configuration sampled velocities on a full cross-product grid, only
a small fraction of candidates survived. That is a property of the configuration rather
than of the approach: the goal tolerance, velocity sample set and simulation horizon were
none of them varied before the controller was replaced.
"""),

dict(layout='content', kicker=R,
     title='No inertial sensor: a decision, not an omission',
     bullets=[
        'Objective 2 asks for a pose estimate characterised against an independently measured '
        'physical reference, with an explicit account of which sensors are required to reach it. '
        'That third clause is the research content, and it is a question about sensors rather '
        'than a requirement to own one.',
        'Fitting inertial measurement at the start would have removed the ability to answer it. '
        'Fusion improves the estimate; without a characterised unfused baseline at the operating '
        'scale there is no way to say by how much, or which error it removed. The unfused platform '
        'is that baseline.',
        'Heading errors of 3.85° and 4.49° were invisible to every instrument on the robot, '
        'because all of them derive from the same wheel measurements.',
        'A rate gyroscope measures angular rate independently of the wheels. Integrating it gives a '
        'heading estimate that drifts with bias but does not share the wheel-derived error, which '
        'is what would separate an encoder scale error from a rigid all-wheel slip mode.',
        ('That the platform is better off without one. Fusion would reduce heading error, an '
         'inertial sensor is the right next purchase, and nothing here argues otherwise. The claim '
         'is about order of work.', None, 'What is not claimed. '),
     ],
     size=13.5,
     takeaway='Objective 2 closes as characterised rather than as optimal, and inertial '
              'measurement now carries a specific number to be tested against rather than a '
              'general expectation.',
     notes="""
Section 1.15. This is the first question the estimator results invite, which is why it gets
its own slide rather than a defensive footnote.

Which instrument binds the error at the 5 m operating scale is not something this year's
data settles, and the report does not claim it does. Endpoint closure was not measured at
5 m: the routes driven were either short and straight, closing to roughly 0.1 per cent, or
long and rotation-heavy, closing at 1.1 to 1.5 per cent, and applying either rate to an
intermediate distance is extrapolation rather than measurement.

The scanner is characterised on its own terms instead, and what that establishes is that it
is unreliable at the ranges a corridor-width map depends on, not that it is the larger of
two quantified error terms. Both estimators have limitations at the intended scale, and
separating their contributions needs the third measurement an inertial sensor would provide.
"""),

dict(layout='content', kicker=R,
     title='What is established, and on what evidence',
     sub='Figure 15, upper half · green: measured and reproduced. Orange: works, below its '
         'requested update rate.',
     side='full', image=os.path.join(A, 'slide', 'fig15a.png'),
     caption='The evidence is not all of one kind: closure against the floor is an external '
             'reference; the kinematics and odometry rows are checks against an independent '
             'implementation; the planner, controller and safety rows are operational '
             'demonstrations rather than measurements against a reference.',
     notes="""
Section 1.16. The layers below the map are measured and working: the motors track, the
encoders are clean, the kinematic and odometry implementations are numerically consistent
to machine precision across the cases tested, the frame composition reproduces to four
decimal places, the planner plans, the local controller reaches goals, and the operator
interface is geometrically correct.

For the five layers that are not yet established, the entry states the specific reason
rather than recording a failure. In three of those five the reason is the size of the
available test area rather than anything on the platform.

Three further components work correctly but run below their requested update rates because
of the processing available on the host computer. That is a property of the computer rather
than of the software, and a faster host raises all three.
"""),

dict(layout='content', kicker=R,
     title='What is not, and the reason stated against each row',
     sub='Figure 15, lower half \u00b7 remaining work, with the reason it has not been done',
     side='full', image=os.path.join(A, 'slide', 'fig15b.png'),
     caption='For the five layers that are not yet established, the entry states the specific '
             'reason rather than recording a failure, and in three of those five the reason '
             'is the size of the available test area rather than anything on the platform.',
     notes="""
Section 1.16. Walk these five rows and notice that three of them carry the same reason.

Scan matching is the one entry switched off by choice rather than by constraint, on the
measurement reported a few slides ago. Inertial measurement is deferred by decision, for the
reason on the previous slide. The other three - a commissioning map meeting all four criteria,
localisation against a saved map, and the named-location library - are one cause wearing three
faces, and that is the next slide.
"""),

dict(layout='content', kicker=R,
     title='Everything still open resolves to two constraints',
     size=13.5,
     two_col=(
        ('One: the size of the available test area', [
            'Coverage accumulates through translation past surfaces, at a rate set by how far the '
            'robot can drive while observing new geometry. The laboratory available permits a '
            'traversable circuit of a few metres.',
            'That single limit holds the coverage criterion below threshold, which withholds an '
            'accepted commissioning map, which leaves localisation against a saved map unexercised, '
            'which gives the named-location library no coordinates to store.',
            'Four entries in the status figure, and one cause. No further work on the platform '
            'moves any of them.',
        ]),
        ('Two: the deliberate absence of inertial measurement', [
            'Working without it is what made the unfused baseline measurable.',
            'The cost is one specific error class that stays unobservable to a wheel-only '
            'instrument set.',
            'Adding the sensor is the first item of the research plan, and it now has a measured '
            'target to be tested against.',
            'Scan matching is the one entry switched off by choice rather than by constraint, on '
            'the measurement reported earlier in this section.',
        ])),
     takeaway='A test space offering a continuous traversable loop lifts all four together. '
              'An initial target of fifteen to twenty metres of path is proposed.',
     notes="""
Section 1.16. The fifteen-to-twenty-metre figure is proposed on the grounds that it is
several times the few metres currently available, not derived from a measured
coverage-accumulation rate. Establishing that rate, and with it the path length a
50 per cent coverage criterion demands, is itself one of the first measurements the new
space would support. Say that; do not let the number sound harder than it is.

Securing such a space is the principal practical prerequisite for the next stage of the
work, and it is the reason the localisation mode that depends on a saved map has not yet
been exercised.
"""),

dict(layout='content', kicker=R,
     title='Conclusions on the robot',
     bullets=[
        ('No asymmetry-specific penalty has been detected in any experiment performed. The '
         'transformation is implemented correctly to the limit of double precision, tracking is '
         'clean on every axis including the lateral and rotational ones, endpoint closure holds '
         'below 1 per cent of path out to 10.61 m, and no yaw-consistency residual above the '
         'episode threshold has appeared.', None, 'The geometry survives full scale. '),
        ('An absence of penalty across a year of measurement is not the same thing as a measured '
         'cost of zero. Objective 3 is not closed until a matched symmetric baseline exists to '
         'compare against.', None, 'Stated in the form the evidence supports. '),
        ('The motors track to a known error loaded and unloaded, the encoder path is clean after '
         'the level-translation work, the feedforward is fitted rather than guessed, and the '
         'kinematic and odometry implementations have been checked against an independent '
         'reference rather than against themselves.', None, 'Below the map, characterised. '),
        ('Mapping produces consistent and repeatable geometry but cannot meet a coverage criterion '
         'in a room this size. Localisation against a saved map has never been run, because there '
         'is no accepted map to run it against. And a scan-matching front end, measured rather than '
         'assumed, made the pose estimate worse on all three routes it was tested on.',
         None, 'At and above the map, three layers are not. '),
     ],
     size=13,
     notes="""
Section 1.17. Those shortfalls resolve to two constraints, and only one of them is about
the robot. A test area of the size available is an environmental limit and the binding one.
The absence of an inertial sensor is the other, and it is a decision rather than an
omission: working without one is what made the unfused behaviour of the wheel estimate
visible in the first place.
"""),

# =========================================================== STRAND TWO ======
dict(layout='divider', numeral='02', kicker='Strand Two',
     title='Environmental Monitoring for the Warehouse Space',
     line='A treatment duct running on a timer cannot raise airflow when the air is '
          'contaminated, and it cannot report the failure of its own lamp.',
     status='Deployed · four zones · running unattended',
     status_color=GREEN,
     notes="""
The second strand concerns the environment inside the warehouse rather than motion through
it. It was developed over the same period as the platform, not after it.

Two considerations motivated it. Environmental variables relevant to storage conditions and
worker exposure are measurable but are not necessarily incorporated into the control of
air-treatment systems. And timer-based operation of treatment equipment provides no feedback
from the condition of the air being treated.
"""),

dict(layout='content', kicker=E,
     title='Why a closed loop, and why local',
     bullets=[
        'Storage temperature and relative humidity are the principal levers on quality loss and '
        'shelf life for perishable produce. Carbon dioxide concentration is a long-established '
        'surrogate for ventilation adequacy. Particulate load affects both product quality and '
        'worker health. In Indian conditions these quantities frequently sit outside the range in '
        'which either people or goods do well.',
        'Continuous monitoring in a laboratory or store room is usually done one of two ways: with '
        'proprietary instruments, which are costly and closed to modification, or by manual '
        'transcription, which introduces recording error and leaves a gap in the record whenever '
        'the space is unattended.',
        'An air-treatment appliance adds a second requirement. It must act on what it measures, '
        'and the effect of that action must be independently confirmable.',
        'Cloud-hosted monitoring makes continuity of monitoring dependent on external connectivity. '
        'For a facility where the monitored condition matters most during a disruption, that '
        'dependency is misplaced. A locally hosted data platform removes it.',
     ],
     size=13.5,
     takeaway='The same architecture is intended to transfer to cold storage, to '
              'controlled-atmosphere rooms used for produce ripening, and to general warehouse '
              'environmental monitoring.',
     notes="""
Sections 2.1 and 2.2. The engineering difficulty is rarely the individual sensor. It lies in
integration, in calibration, in keeping a deployed system reporting reliably without
attention, and in ensuring that the quantity driving a control decision is the quantity
intended. That last clause comes back twice in this chapter.

Note the qualifier on the takeaway if asked: the system has so far been deployed in one
application, and transferability is a design expectation rather than a demonstrated result.
"""),

dict(layout='content', kicker=E,
     title='The appliance and the sensing node, as built',
     sub='Figure 16 · the integrated unit, and both control boxes powered and linked',
     side='full', image=FIG(16),
     caption='The displays are reading live, which is how a node is checked without attaching '
             'a computer to it: irradiance and gas state on the left, uptime and firmware build '
             'on the right.',
     notes="""
Section 2.3. Air is drawn through an aluminium duct by a fan set into its end face, passes a
germicidal lamp, and leaves at the other end. The sensing and control enclosure is mounted on
top of the duct near one end, so the electronics sit outside the treated path and the only
things inside it are the lamp and the airflow.

The enclosure was designed rather than bought. Acrylic, each face a separate panel held by
3D-printed corner standoffs and slotted machine screws, so any one face can come off without
disturbing the others. The helical long-range antenna passes through the top panel; the
cellular whip mounts externally through a bulkhead connector.

One correction worth recording, because earlier project documents have it wrong: the
enclosure is not a cube. The photographs show a box visibly wider than it is deep.
"""),

dict(layout='content', kicker=E,
     title='Five sensing devices, two actuators, one microcontroller',
     sub='Table 2.1 · parts as fitted, read off the assembled unit or out of its firmware',
     table=(['', ''], [
        ('Sensing node', 'Arduino UNO R4 WiFi, Renesas RA4M1 core'),
        ('CO₂, temperature, humidity', 'Sensirion SCD40, 400–5000 ppm. Three quantities, '
         'one device, one calibration'),
        ('Particulate matter', 'MPM10-AS optical counter on the same bus, PM2.5 and PM10'),
        ('Gas', 'MQ-135 metal-oxide module, an index of 0 to 500, not a concentration'),
        ('Ultraviolet irradiance', 'GUVA-S12SD photodiode, 240–370 nm'),
        ('Actuators', 'Opto-isolated relay switching the lamp mains; 120 mm four-wire fan with '
         'tachometer feedback'),
        ('Control law', 'Lamp on above gas index 200, off below 150; fan ramped from half to full '
         'across 200–500'),
        ('Alert thresholds', '38 °C, 1200 ppm CO₂, gas index 200, 55 µg/m³ PM2.5'),
        ('Power', 'Two isolated 12 V supplies brought to a single common ground point'),
     ]),
     col_w=[0.26, 0.74], table_size=12,
     takeaway='The fan is the one actuator in the system whose response can be confirmed rather '
              'than assumed. The power split is not an elegance: the next slide gives the '
              'failure it exists to prevent.',
     notes="""
Section 2.3. The two actuators are driven differently and for different reasons. The lamp
runs from mains and is switched through an opto-isolated relay, so there is no electrical
path between the mains side and the logic.

Non-selective metal-oxide gas sensors respond to a mixture of reducing gases rather than to
any one species, which is why the index they produce is treated in this work as a relative
signal rather than a concentration.

One measurement channel did not do what the system design assumes, and the report records it
rather than leaving it for a reader to discover: ultraviolet irradiance was reported in
milliwatts per square centimetre while the responsivity coefficient was still set to one. The
quantity reported was a voltage carrying the label of a concentration. It reached the display
and both telemetry payloads but appeared in no control path and no alert path, which means the
loop described in some project documents as taking two inputs in fact took one.
"""),

dict(layout='content', kicker=E,
     title='Three channels at once, not a failover chain',
     sub='Figure 17 · devices, three transports, and the containerised stack that ingests and stores',
     side='right', image=FIG(17), image_w=0.56,
     bullets=[
        ('A full message every 5 s to a broker on the server, where a flow engine ingests it and '
         'writes to the time-series database.', None, 'Wi-Fi. '),
        ('At most 240 bytes every 30 s to a gateway microcontroller; a dedicated service reads that '
         'gateway over serial and writes to the same database with the same schema, distinguished '
         'only by a source tag.', None, 'Long-range radio. '),
        ('A short message on any threshold breach, on the corresponding clear, and a summary every '
         '30 minutes. It delivers to a person; nothing on the server records it.', None, 'Cellular. '),
        'A failover design must detect failure before it can switch, and detection is the first '
        'thing to fail in a dead network. Running independent channels concurrently avoids that '
        'dependency, at a bandwidth cost a low-rate telemetry system can absorb.',
     ],
     size=12.5,
     takeaway='Only two of the three reach the database. A reader who assumes all three converge '
              'on the broker would draw the wrong conclusion about what a server outage costs.',
     notes="""
Section 2.4. The figure is drawn so each channel can be followed separately, because they are
not interchangeable: the three arrive at three different places.

The cellular channel is also the only one bidirectional at the human end. The node accepts the
same command vocabulary on every channel, including short messages from a handset, so an
operator with no network access can still ask a node for a snapshot or switch its lamp.

Commands from the dashboard travel one of two ways, selected at runtime by a variable read from
the browser address rather than by a firmware change: through the flow engine and the broker
when the node is inside Wi-Fi coverage, or through the control service and out by radio when it
is not. That is what lets a zone move in and out of coverage without anything being reflashed.
"""),

dict(layout='content', kicker=E,
     title='Three design decisions that answered observed failures',
     bullets=[
        ('Attempted and abandoned. The command protocol requires deterministic timing that a '
         'non-real-time operating system does not provide, and scheduler jitter produced dropped '
         'packets that were indistinguishable from radio link failures. Interposing a dedicated '
         'microcontroller moved the timing-critical work to where timing is deterministic.',
         None, 'Driving the long-range radio from the host computer’s GPIO. '),
        ('Sharing a supply rail with the microcontroller produced brownout resets. Two supplies '
         'with a single common ground point eliminated them.',
         None, 'The cellular modem draws approximately 2 A in transmit bursts. '),
        ('The three channels run concurrently rather than as a chain, for the detection '
         'reason on the previous slide.',),
        ('Separation between the two co-located deployments is by network identifier, which the '
         'transceiver filters at the protocol layer. That is an addressing filter, not a security '
         'mechanism: the control path carries no message authentication, so any transmitter within '
         'range configured to the right identifier can actuate a lamp. Acceptable on an isolated '
         'laboratory network, and not acceptable anywhere else.', RED, 'Stated rather than implied. '),
     ],
     size=13,
     takeaway='Separately: the two deployments were configured on different frequencies, and '
              'neither matches the delicensed band available in India. Nothing has been obstructed, '
              'and it would have to be settled before the system went near a real facility.',
     notes="""
Section 2.4. These three were responses to observed failures rather than anticipatory choices,
and it is worth saying so: each one is a fault that was diagnosed and designed out, not a
precaution taken in advance.

The security and frequency statements are in the report for the same reason. A bench deployment
on an isolated network does not need message authentication, and the report says exactly that
rather than implying the system has a security posture it does not have.
"""),

dict(layout='content', kicker=E,
     title='The control law, and the dashboard the operator sees',
     sub='Figure 18 · the dashboard in service, photographed off the screen',
     side='right', image=FIG(18), image_w=0.50,
     bullets=[
        'The lamp switches on above a gas index of 200 and off below 150, so the two thresholds are '
        'separated by a band in which nothing changes and the relay cannot chatter around a single '
        'setpoint.',
        'The fan is not switched but ramped, from half command at the lamp-on threshold to full at '
        'an index of 500, and never below half duty while the lamp is energised, because '
        'irradiating stationary air accomplishes little.',
        'A breach fires simultaneously on all three channels and the alert state is latched, so a '
        'sustained breach does not generate a message on every cycle. Particulate matter is '
        'evaluated only when the reading is valid, and a sensor that fails to respond is transmitted '
        'as a negative marker rather than as zero.',
        ('It compares a noisy signal against a bare threshold, so a reading sitting near a limit '
         'flaps, and each transition sends a message.', AMBER,
         'What the alert path does not have is the dead band the control path does. '),
     ],
     size=12.5,
     takeaway='Twenty-three panels templated per zone, so one layout serves all four installations.',
     notes="""
Section 2.5. The figure happens to catch the system 40 ppm above the carbon dioxide threshold,
which is well inside that flapping range.

The dashboard is also where the most interesting defect lived. An operator command to switch the
lamp or the fan off actuated correctly and then did not clear automatic mode, so the closed loop
reverted it on its next pass. The on-commands did clear it. The off command is the one an operator
issues to halt automatic actuation, and it is the one that did not persist, which makes it a safety
defect rather than an inconvenience. It has since been fixed, and that is the next slide.
"""),

dict(layout='content', kicker=E,
     title='Deployed, audited, and what is still owed',
     size=13,
     two_col=(
        ('Deployed and operating', [
            'Four zones across two radio-isolated installations sharing one database. All three '
            'communication channels, both control paths and the dashboards are in service.',
            'The system recovers automatically after a power interruption without intervention.',
            'The control law was checked against the deployed system: a capture shows the gas index '
            'below its actuation threshold with the lamp correspondingly off, and the carbon dioxide '
            'reading at the same instant above its alert threshold with alerts raised on all three '
            'channels.',
            'That establishes the deployed logic produces the configured states for the inputs '
            'present at an instant. A time-resolved recording (measurement, threshold crossing, '
            'actuator command and response on one time axis) is the next capture the control '
            'path needs.',
        ]),
        ('Closed by the source-level audit', [
            'Lamp-failure detection now runs from the irradiance the unit was already measuring: '
            'once the relay has been closed longer than the lamp strike time, irradiance above a '
            'threshold is required, and its absence raises an alert. That is the capability which '
            'separates the unit from a timer.',
            'The operator off-command persists rather than being reverted on the next automatic pass.',
            'The cellular inbox poll no longer blocks the main loop, which removed the publish jitter '
            'and the command latency together.',
            'The gas channel is driven from the stored calibration rather than from a rescaled '
            'analogue count.',
        ])),
     takeaway='What remains is instrumentation, not software: the gas channel against a reference '
              'gas, and the ultraviolet channel against a reference radiometer at a fixed geometry. '
              'Both need instruments rather than development time.',
     notes="""
Section 2.6. Be careful with the distinction the report is careful with: this is an engineering
result rather than a measured one. A complete system was taken from nothing to a deployment
running unattended, which is real, and it is a different kind of claim from the four measured
results on the robot.

The responsivity coefficient that converts photodiode voltage to irradiance is a property of the
installed part and cannot be recovered from firmware, which is why that calibration needs a
radiometer rather than a code change.

Beyond those two, the direction is sensor integration, which this architecture was built to
accommodate: a channel is added by configuration, not by rebuilding the node. Zones are templated,
the database takes one schema regardless of transport, retargeting a gateway is three constants and
retargeting its service is four values in a configuration file.
"""),

# ========================================================= STRAND THREE ======
dict(layout='divider', numeral='03', kicker='Strand Three',
     title='Contactless Assessment of Worker Fatigue',
     line='A hypothesis, a completed literature survey, and a research proposal built on both. '
          'No hardware has been built, no data has been collected, and nothing has been measured.',
     status='Proposed · survey complete · nothing built',
     status_color=AMBER,
     notes="""
This chapter is brief because the work it describes has not yet been carried out. It is carried
in the report because the argument is already specific enough to state, to criticise and to test,
and because the first year of a doctorate is the right time to establish whether a direction is
worth pursuing at all.

Do not oversell this strand. The committee will respect a clearly bounded proposal and will not
respect a proposal dressed as a result.
"""),

dict(layout='content', kicker=F,
     title='The setting, and where each established method stops',
     sub='Figure 19 · the operating condition against the class of instrument each method belongs to',
     side='right', image=FIG(19), image_w=0.54,
     bullets=[
        'India’s logistics and warehousing sector employs over 22 million people, is expanding '
        'under the National Logistics Policy of 2022, and records more than 26,800 workplace '
        'incidents a year. Nearly 70 per cent of that workforce is in the unorganised sector, where '
        'occupational health protocols are minimal or absent.',
        'Shifts of ten to twelve hours, sustained walking and lifting, and ambient temperatures that '
        'routinely exceed 40 °C. Occupational heat stress in Indian workplaces has been measured '
        'directly, with documented exceedances and associated health and productivity consequences.',
        ('Unreliable at its source, and no instrument corrects that.', RED, 'Subjective report. '),
        ('Reliable in themselves, and cannot be maintained in contact across a ten-hour shift above '
         '40 °C. That is a limitation of the instrument rather than of the measurement principle, '
         'and therefore a tractable one.', AMBER, 'Contact methods. '),
     ],
     size=12.5,
     takeaway='It is that second class of failure, and only that class, which this strand addresses.',
     notes="""
Sections 3.1 and 3.2. The three reasons in the figure are not equivalent, and the distinction is
the whole argument for the strand.

The objections to instrumenting the worker instead of the space are practical rather than
evidential, and the report gives them as design reasoning rather than as findings: a sensor worn
against the skin for an eight-hour shift in these conditions is uncomfortable, electrode contact
and signal quality degrade with perspiration, compliance depends on the worker choosing to wear it,
and a facility employing hundreds of people acquires a daily charging and maintenance burden. None
of these is fatal alone. Together they are why this strand asks whether the measurement can be made
without contact at all.
"""),

dict(layout='content', kicker=F,
     title='The hypothesis, and the gap it sits in',
     bullets=[
        ('Physical fatigue shows itself as a correlated signature across several physiological '
         'domains at once: gait regularity deteriorating, heart and respiration rates rising, and '
         'facial skin temperature climbing.', None, 'The hypothesis. '),
        ('A system watching all of those at the same time should beat any system watching one of '
         'them, and should beat it hardest under exactly the conditions where single modalities '
         'struggle, which are occlusion, heat and an uncontrolled floor.', None, 'What follows if it holds. '),
        'Surface electromyography with inertial measurement is the established laboratory approach, '
        'reporting 87.9 per cent accuracy on induced fatigue under leave-one-subject-out validation '
        'across 35 participants. The requirement for skin-contact electrodes and per-subject '
        'placement is what prevents its use on an operating floor.',
        'The most mature deployed fatigue systems monitor drivers, and thermal facial imaging alone '
        'reaches 82 per cent against observer-rated drowsiness in a simulator. These assume a seated, '
        'stationary, forward-facing and cooperative subject at fixed distance. A worker walking an '
        'aisle under load satisfies none of those assumptions.',
        ('The fusion of contactless modalities for whole-body physical fatigue assessment in an '
         'uncontrolled industrial environment. No study meeting the criteria used in this review was '
         'identified.', None, 'The gap. '),
     ],
     size=12.5,
     takeaway='A bounded search, not an exhaustive one: Crossref and scite, June to September 2026, '
              'peer-reviewed work only. The claim is a gap in a search rather than a gap in the field.',
     notes="""
Sections 3.1 and 3.2. The gap is not a shortage of capable sensors. It is that they have not been
fused for this purpose. Existing multi-modal fatigue work is overwhelmingly contact-based or aimed
at seated drivers, and the contactless studies are single-modality and laboratory-bound.

The second gap is regulatory rather than technical. India's data protection legislation of 2023 has
created real uncertainty about workplace monitoring, and an architecture that extracts a derived
score on the device and never transmits raw video is a different legal object from one that streams
a camera feed to a server. That distinction is designed in here rather than argued for afterwards.

Reported accuracies for the individual contactless modalities, if asked: camera pose estimation at
0.02 s on temporal gait parameters and 4.0, 5.6 and 7.4 degrees on sagittal hip, knee and ankle;
millimetre-wave radar correlating with a reference at 94 per cent on respiration and 80 on heart
rate, though established for near-stationary subjects and degrading with body motion.
"""),

dict(layout='content', kicker=F,
     title='The framework proposed',
     sub='Figure 20 · one crossing of the monitored zone, capture to a single score',
     side='right', image=FIG(20), image_w=0.54,
     bullets=[
        'Camera with on-device pose estimation: stride, cadence, trunk sway, left-right asymmetry. '
        'Solid-state lidar: the same geometry in three dimensions, plus step width and '
        'centre-of-mass motion, insensitive to illumination. 60 GHz radar: heart rate, '
        'respiration and variability through clothing. Long-wave infrared: facial skin '
        'temperature and the forehead-to-cheek gradient.',
        ('Rather than tracking several people across a floor, the node sits at one point everybody '
         'passes, mounted two and a half to three and a half metres up and angled down, working at '
         'one to five metres. Each crossing yields one clean measurement of one person.',
         None, 'Decision one: capture is fixed and single-subject. '),
        ('That converts an absolute measurement, which varies enormously between people, into a '
         'within-subject change, which is the quantity the question is actually about.',
         None, 'Decision two: every feature is referred to the worker’s own shift-start baseline. '),
        'Gait carries enough information to identify a person. A system installed to estimate fatigue '
        'must not become one that recognises individuals, so the pipeline has to discard identity by '
        'construction rather than by policy.',
     ],
     size=12,
     takeaway='The fused estimate is computed without any raw video or point cloud leaving the sensor '
              'bracket, which makes the privacy position a property of the architecture rather than '
              'an undertaking.',
     notes="""
Section 3.3. The dashed rule in the figure marks the limit of what the proposal fixes: the sensor set
and its mounting are specified and costed, and everything to the right of the rule is design.

The single-subject trade is deliberate. Continuous multi-person tracking is a harder problem than the
one being asked about, and solving it is not a prerequisite for answering whether fatigue is legible
at all.

The fusion itself is a convolutional branch per stream followed by a recurrent stage over the sequence,
with attention across the modalities so the model can lean on whichever streams are usable when one is
occluded. It produces a single number per crossing.

On identity: the point-cloud gait benchmark cited in the review exists to demonstrate exactly that
capability, which is a thing this strand has to constrain deliberately rather than a feature to exploit.
"""),

dict(layout='content', kicker=F,
     title='How it would be validated, and the bar set in advance',
     sub='Figure 21 · the three objectives, and the reference each is measured against',
     side='right', image=FIG(21), image_w=0.50,
     bullets=[
        'Gait from the camera and the lidar is checked against marker-based motion capture, an '
        'external physical reference rather than another estimate.',
        'A subset of volunteers wears surface electromyography on the calf muscles and inertial bands '
        'at the same time as the contactless capture, so the proposed method is compared directly '
        'against the established contact method it proposes to replace, on the same subjects during '
        'the same task.',
        'Field deployment then runs in an operational, non-air-conditioned warehouse across thirty to '
        'fifty workers and several shifts, scored against the vigilance and sleepiness instruments.',
        ('The fused score must beat four single-modality baselines (camera, lidar, radar and '
         'thermal alone), together with an ablation over the four.', None, 'The comparison that decides it. '),
     ],
     size=12.5,
     takeaway='Setting that bar before any data is collected is deliberate, because it is exactly the '
              'comparison that becomes easy to avoid once a pipeline exists and produces '
              'plausible-looking numbers.',
     notes="""
Section 3.4. Where the previous figure gives the signal path, this one gives the order of work.
Reading down the right-hand column establishes that order: a modality that has not been checked
against motion capture cannot sensibly be fused, and a fused score has nothing to be compared
against until the contact reference has been recorded on the same subjects during the same task.

A fused score that cannot beat the best single modality has bought nothing for four sensors and an
edge processor. Say that line; it is the one that shows the strand is set up to be falsified rather
than to be confirmed.

One practical constraint sits across all of it. Simultaneously processing four high-bandwidth
streams on a single edge platform generates heat, and a non-air-conditioned Indian warehouse above
40 degrees is precisely where that platform will throttle. That is a design constraint on the node
rather than a footnote, and it is one of the reasons the hardware objective has to be completed and
tested in situ before the algorithmic one means anything.
"""),

dict(layout='content', kicker=F,
     title='What exists, and the sequence that follows',
     bullets=[
        ('The survey, the hypothesis it produced, and a research proposal built on both. Alongside '
         'the sensing literature the survey covered occupational fatigue physiology, Indian '
         'industrial environmental conditions and the data protection position, because a sensing '
         'method that cannot be deployed lawfully in the place it was designed for is not a method.',
         None, 'What exists at the end of the year. '),
        ('The technical feasibility argument rests entirely on other people’s results. Each of the '
         'four modalities has been demonstrated to high accuracy individually, and fusion using this '
         'class of architecture has outperformed single-modality baselines in related fatigue tasks. '
         'None of that is evidence that the combination works here. It is evidence that the '
         'combination is worth attempting.', None, 'Stated rather than blurred. '),
        ('Until one exists there is no data of any kind.', None, 'First: the capture node. '),
        ('The step most likely to end the strand, which is a reason to reach it early rather than '
         'late: if two of the four modalities carry no usable fatigue signal on walking subjects, the '
         'design changes before anything is built around them.',
         None, 'Second: per-modality laboratory validation. '),
        ('Because they are the only steps that need every preceding one to have worked.',
         None, 'Last: fusion, field deployment, the baseline comparison. '),
     ],
     size=12.5,
     takeaway='A negative result is a useful contribution while there is still time to act on it, '
              'and stops being one once there is not.',
     notes="""
Section 3.5. The sequence matters more than the schedule.

The comparison against surface electromyography on the same subjects during the same task comes as
early as the hardware allows, specifically because it is the step most likely to show that the
approach does not work.
"""),

# ========================================================== CONCLUSIONS ======
dict(layout='content', kicker=C,
     title='What the first year established',
     size=12.5,
     bullets=[
        ('0.040 to 0.047 rad/s RMS unloaded and 0.066 to 0.074 under chassis weight, with no channel '
         'saturating in any recorded run.', GREEN, '1. The velocity controller tracks to '),
        ('are numerically consistent to machine precision across twenty thousand generated cases, and '
         'against an offline re-integration of a complete drive.', GREEN,
         '2. The kinematic and odometry implementations '),
        ('stays below 1 per cent of path to about 10 m, and sits between 1.1 and 1.5 per cent on the '
         'longest routes driven.', GREEN, '3. Wheel-odometry endpoint closure '),
        ('on three separate routes, most tightly on a drive where the same wheels and the same '
         'scans gave 16.2 mm unmatched and 206.7 mm matched, with corrections firing on a fixed '
         'odometry cadence rather than on scan disagreement.', GREEN,
         '4. Scan matching was measured to increase pose error '),
        ('A complete system taken from nothing to a deployment running unattended across four zones in '
         'two radio-isolated installations sharing one database, with three concurrent communication '
         'channels, two control paths and automatic recovery from a power interruption. That is an '
         'engineering result rather than a measured one, and the report is careful about the '
         'difference.', ACCENT, '5. Of a different kind. '),
     ],
     takeaway='Established rather than asserted, each against a physical reference or an '
              'independent implementation, not against itself.',
     notes="""
Section 4.1. The year also produced a preliminary demonstration of autonomous navigation, and the
deployed monitoring system, which are on the slide as the fifth item and in the body of the talk.

The fifth result is deliberately marked as a different kind of claim. The deployed logic has been
shown to produce the configured states for the inputs present at an instant, and has not been shown
responding to a change on a single time axis.
"""),

dict(layout='content', kicker=C,
     title='What remains open, and why the reasons differ',
     tiles=[('The room', 'A commissioning map meeting all four criteria, and localisation against '
             'a saved map', AMBER),
            ('The baseline', 'The effect of the asymmetric geometry itself', AMBER),
            ('The instrument', 'Several degrees of heading error that every fitted sensor misses', RED)],
     bullets=[
        'A commissioning map meeting all four acceptance criteria, and localisation against a saved '
        'map, are blocked by the size of the available test area, not by the platform. Coverage '
        'accumulates through translation, and the robot cannot see what it cannot drive past.',
        'The effect of the asymmetric geometry is unquantified, because no matched symmetric baseline '
        'has been built. A consistent absence of penalty is not a measured cost of zero.',
        'Several degrees of heading error survive every instrument currently fitted. Narrowed to an '
        'encoder or wheel-radius scale error, or a rigid all-wheel slip mode, which cannot be '
        'separated without an independent angular-rate measurement.',
        'On the other strands: the monitoring system has closed the firmware items from its source '
        'audit and waits on two physical calibrations. The fatigue strand has nothing to correct '
        'because it has nothing built, which is itself the thing to change.',
     ],
     size=12.5,
     takeaway='Adding inertial measurement to a platform whose unfused behaviour is now characterised '
              'gives a specific quantity to test the improvement against, rather than a general '
              'expectation that fusion helps.',
     notes="""
Section 4.2. Three things remain unresolved, and the reasons differ. That is the point of the slide:
they are not three items on one list of shortfalls. One is environmental, one is a comparison not yet
built, and one is an instrument not yet fitted.

The question the next stage tests follows directly from the last of those.
"""),

dict(layout='content', kicker=C,
     title='Research plan, ordered by what unblocks what',
     sub='Not by calendar. Within each strand the order is real.',
     size=11.5,
     two_col=(
        ('The robot', [
            'Securing a representative test space. A continuous traversable loop with unobstructed '
            'wall on at least one side and aisle widths representative of the application. An initial '
            'target of fifteen to twenty metres of path. The first practical task.',
            'Inertial measurement and fused state estimation. An inertial sensor near the geometric '
            'centre, where the rotationally induced accelerometer terms are smallest, fused with the '
            'wheel estimate. The 3.85° and 4.49° already measured give the quantity to test against.',
            'Sensor comparison. Repeating the same routes with a higher-grade scanner, using the same '
            'analysis tools, converts an inference into a controlled result. That question is '
            'currently answered in the literature by convention rather than by measurement.',
            'Completing the geometric comparison. A matched symmetric baseline, in simulation first '
            'and on hardware if the wheelbase can be reconfigured without a new chassis. Closes '
            'Objective 3.',
            'Extending the platform to warehouse tasks. Inventory scanning, environmental survey, '
            'surface disinfection and cargo transfer. Each is integration work on top of the '
            'autonomy layer rather than a change to it.',
        ]),
        ('The other two strands', [
            'Monitoring: calibration first, because it is what converts a unit that behaves '
            'correctly into one whose readings can be quoted. That means the gas channel driven '
            'from the stored calibration, and the ultraviolet channel referred to a reference '
            'radiometer at a fixed geometry.',
            'Then sensor integration, which is why the architecture was built the way it was: a new '
            'measurement channel is a configuration change rather than a redesign. That makes the unit '
            'worth extending to cold storage, controlled-atmosphere rooms, and the perishable-goods '
            'areas where temperature, humidity and gas composition together set shelf life.',
            'Fatigue: the sequence of the previous section, with one ordering decision that belongs '
            'in a plan: the per-modality validation, and in particular the comparison against surface '
            'electromyography on the same subjects during the same task, comes as early as the '
            'hardware allows.',
            'No dates. The work depends on securing a test space, on the procurement of a sensor, and '
            'on a result that may be negative. A schedule asserted over those contingencies would not '
            'be a plan.',
        ])),
     notes="""
Section 4.3. Within each strand the order is real: the items are listed so that each one is possible
once the one above it is done.

If pressed on the absence of dates, the last bullet is the answer and it is the report's own. Offer
the dependency order instead: the test space unblocks four entries in the status figure; the inertial
sensor unblocks the heading question; the symmetric baseline closes Objective 3.

Each monitoring deployment adds its own sensing and tests the architecture against an application it
was not built for, which is the useful measure of whether it generalises.
"""),

dict(layout='closing', kicker='In closing',
     title='Three statements',
     image=PIC('closing'),
     lines=[
        'The robot is built, instrumented and characterised, with four results established against '
        'physical references and three specific shortfalls, two of which are the size of a room '
        'rather than anything on the machine. The monitoring system is deployed and running across '
        'four zones. The fatigue strand has an argument and no data. Three distinct kinds of position, '
        'and the report has been written so as not to flatten them into one.',
        'What the three share is more modest than a combined system and more useful: multi-sensor '
        'integration, calibration against something physical, acquisition that has to keep its own '
        'schedule, and control that fails safe. An error made in one has already become a method in '
        'the next, and that return accrues whether or not the strands ever converge.',
        'The next step in each strand is specific rather than general, and none of the three waits on '
        'the others. The useful question is not whether a direction is promising, but how quickly it '
        'can be placed in a position to fail.',
     ],
     notes="""
Section 4.3, the closing three paragraphs of the report, given as they were written.

Stop on the last sentence. It is the methodological conclusion of the year and it is the line to
leave the room with.

Thank the supervisor, the laboratory, and the IITB-FedEx ALFA fellowship, then take questions.
"""),
]
