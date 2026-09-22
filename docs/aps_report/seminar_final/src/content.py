# -*- coding: utf-8 -*-
"""Every slide in the deck, as data.

Rules this file keeps to, because the deck is being presented against a report
a committee has already read:

  * No number appears here that is not in APS_Report_Aritra_-_final.docx.
    Where a number is quoted, the section it comes from is named in the notes.
  * The notes are the report's own sentences, lightly cut for speaking. That is
    what "the narration as it is" means: the slide is the headline, the notes
    are the argument, and the argument is the one that was submitted.
  * A claim keeps its qualifier. "Below 1 per cent out to about 10 m" does not
    become "below 1 per cent". "Demonstrated within a live mapping session"
    does not become "demonstrated".
  * Video slides carry the exact source filename from the Drive folder, so a
    placeholder can be matched against the real clip without guessing.

42 slides, condensed from the original 51 by cutting slides whose single
point could be folded into a neighbour's notes without losing the point
itself, and by pairing figures that make the same kind of argument onto one
slide rather than two. Four videos are placed at the results they are
evidence for, not narrated as more than that: the two circle-trajectory
clips are the scan-matching result, not a demonstration of wheel-level
control, which is proven separately by the RMS tracking numbers.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theme import ACCENT, GREEN, AMBER, RED, GREY, MUTED

A = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
FIG = lambda n: os.path.join(A, 'slide', 'fig%02d.png' % n)
PIC = lambda n: os.path.join(A, 'photo', n + '.jpg')
CTX = lambda n: os.path.join(A, 'context', n + '.jpg')

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

dict(layout='content', kicker='Introduction',
     title='India’s warehouses are growing. The aisle is where automation stops.',
     images=[(CTX('warehouse_floor'), 'A modern automated distribution floor'),
             (CTX('fedex_dock'), 'A logistics operator loading for last-mile delivery')],
     tiles=[('~$27B → ~$41B', 'India’s warehousing market, 2026 to a 2031 forecast, at roughly '
             '8.5% a year', None),
            ('~15% a year', 'Growth of warehouse automation specifically, faster than the sector '
             'as a whole', AMBER),
            ('Top 6', 'Where India is expected to rank globally in warehouse-automation adoption '
             'in 2026', None)],
     bullets=[
        'Automation is arriving fastest in the largest, most standardised spaces: sorting hubs, '
        'cross-docks, high-bay pallet storage. It has been slower to reach the aisle, where a '
        'human picker still walks a corridor a vehicle barely fits.',
        'The National Logistics Policy of 2022 is pushing the sector toward organised, '
        'standardised warehousing, and organised space is where an automated platform has '
        'somewhere to work.',
        'This project sits in that specific gap: a full-scale platform built around aisle '
        'geometry, and a method, calibration against a physical reference, a measured failure '
        'mode stated rather than assumed, that recurs across the robot, the monitoring system '
        'and the proposed fatigue work alike.',
     ],
     size=13,
     takeaway='Growth in the warehouse does not by itself reach the aisle. That is the specific '
              'space this work is built around.',
     notes="""
Market figures: India warehouse market size, IMARC Group and Mordor Intelligence, 2026
editions (roughly USD 27 billion in 2026 toward roughly USD 41 billion by 2031, about 8.5
per cent CAGR); India warehouse automation market, IMARC Group, 2026 (automation segment
growing at roughly 14.75 per cent CAGR, and India expected among the top six countries by
warehouse-automation adoption in 2026). These are market figures, not report figures, and
are sourced to industry market research rather than to the APS report.

The last bullet earns the fellowship name (Advanced Logistics, Focused Analytics) without
saying it outright: the platform is the advanced-logistics half, the calibrated,
evidence-graded method is the focused-analytics half. Say the fellowship name only if
asked; the slide is built so the connection is visible without being announced.

Frame the project around the aisle specifically, not around "warehouse automation" in
general. The important distinction the whole talk rests on is the geometric constraint,
not the sector's growth on its own.
"""),

dict(layout='content', kicker='Overview',
     title='Three problems, one engineering method',
     sub='Robotics, IoT and AI, aimed at making the warehouse a better place to work and operate in',
     tiles=[('Strand 1', 'A corridor a vehicle barely fits through', None),
            ('Strand 2', 'Air nobody is watching in real time', None),
            ('Strand 3', 'Fatigue nobody can measure without contact', None)],
     bullets=[
        ('Built, instrumented and measured. More than 45 kg, closed-loop control at every '
         'wheel, four results established against physical references.', None, 'Robot. '),
        ('Deployed and running. Four zones, two radio-isolated installations, one database, '
         'three concurrent communication channels.', None, 'Monitoring. '),
        ('A hypothesis and a completed literature survey. No hardware built, no data collected.',
         None, 'Fatigue. '),
        ('Not the problem — the method. Instrumentation, control and communication run through '
         'all three, applied the same way whether the target is a wheel, a duct, or a data '
         'stream.', None, 'What is shared. '),
     ],
     takeaway='Three different problems, at three different stages, solved with the same '
              'engineering discipline: measure, calibrate, act in real time, fail safe.',
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

Say plainly if asked: the fatigue strand has designed for "control that fails safe" (the
validation plan is built to fail loudly if a modality carries no usable signal) but has not
demonstrated it, since nothing is built yet. The other two have.
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
     takeaway='Two close on measurement, one closes as characterised rather than optimal, one is open for a reason that is not the platform’s, and one has not begun.',
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

The asymmetric, non-collinear version used here is not proposed in this report: it was
derived and demonstrated on a small prototype in earlier work in this group (Figure 1 in
the report). This year's contribution begins at full scale, which is what the next slide
measures.
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
     side='right', image_w=0.42,
     video='robot_demo_under25MB.mp4',
     video_caption='Open-loop joystick drive · the original Arduino Mega control',
     bullets=[
        ('Chassis, four mecanum wheels on the asymmetric layout, four geared drive motors, '
         'two motor drivers and the power system. Control by an Arduino Mega 2560.',
         None, 'Present at the start. '),
        ('No closed-loop velocity regulation, no odometry, no on-board kinematic model, '
         'no perception, no autonomy.', None, 'Absent. '),
        ('The firmware, the ROS 2 software, the instrumentation and every measurement '
         'quoted in this report were carried out end to end.', None, 'Everything beyond that. '),
     ],
     takeaway='Establishing which way the scanner counts its angles took a drive against a '
              'placed block, because nothing on the sensor says which way it is looking.',
     notes="""
Section 1.3. Work began from an assembled mechanical platform.

Do not oversell this clip: it shows the platform before this year's work, open-loop and
hand-joysticked. It is a before-picture, not a result.

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
        ('Host computer', 'Raspberry Pi 5, Ubuntu 24.04, ROS 2'),
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
            'ordinarily just misreports it, except where the loop treats the corrupted signal '
            'as authoritative for direction, which is why a dedicated trip catches that case.',
        ])),
     size=12.5,
     notes="""
Section 1.4. The ESP32 removes the problem rather than optimising around it.

Two further properties of the part were useful: substantially greater processing
capability and memory than the part it replaced, and an integrated 2.4 GHz radio, which
allowed the first phone-based control surface to be hosted on the controller itself
before the host computer was introduced.

The full deployed wiring, battery through the 24 V drive rail and 5 V logic rail to the
four motors and their encoder return, is Figure 5 in the report, organised in three
layers each on its own rail colour. The control constants shown against the
microcontroller there are the ones derived a few slides from now.

The asymmetry in the level translation is deliberate, and the last line on the right is
the reason: fewer components in the command path is worth having.
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
         'disagree the loop sees positive feedback that drives the command toward saturation '
         'without the wheel speed itself crossing the overspeed threshold, so the detector checks '
         'command against response direction rather than speed alone.',
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
     title='Result: the loop tracks, loaded and unloaded',
     images=[(FIG(9), 'Fig 9 · wheel velocity vs command, unloaded'),
             (FIG(10), 'Fig 10 · steady-state demand, unloaded vs loaded')],
     tiles=[('0.040–0.047', 'rad/s RMS per wheel, unloaded · 26,468 samples', GREEN),
            ('0.066–0.074', 'rad/s RMS per wheel, under chassis weight · 35,248 samples', GREEN),
            ('0.0 %', 'Saturated samples, every channel, every recorded run', GREEN),
            ('22–30 %', 'Ground-load drive-demand increase, mean 24 %', AMBER)],
     bullets=[
        'The wheel reaches within 5 per cent of the commanded −2.207 rad/s in 0.20 s, '
        'overshoots by 3.5 per cent, and holds to a mean offset of 0.003 rad/s. No channel '
        'saturated at any point in any recorded run.',
        'The autonomous drive falls in the loaded band, which is the one that matters '
        'operationally. Largest drive demand at the operating velocity limit was 131 of 255, '
        'headroom in the command rather than a torque measurement.',
        'The 10 to 30 per cent ground-load band was written down before the measurement was '
        'made. Three of the four motors landed inside it; the rear-right reached 30.3 per '
        'cent, an exceedance rather than rounded into agreement.',
        'Two later runs the same afternoon, different floor patches, gave means of 14 and 3 '
        'per cent: the increase is real, its size is not settled past the width of the band '
        'it was predicted against.',
     ],
     size=12,
     takeaway='Controller performance, not an artefact of hitting a limit: tracking holds and '
              'no channel saturates, loaded or not, even as steady-state demand rises with the ground.',
     notes="""
Sections 1.9 and 1.10. Two conditions, reported separately because the figures differ by
about half. The unloaded figure separates the controller from the wheel-ground
interaction; the loaded figure is the one the robot actually works at.

The ground-load result is a prediction and a test rather than an observation, because the
band was written down before the run. That convention, verifying against the running
system rather than a file or a guess, recurs across both this strand and the monitoring
one. A staircase test holding position and sweeping demand is what would settle the exact
size of the effect; casual driving covers different floor patches and headings instead.
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
        'The yaw-consistency residual comes from the two diagonal wheel pairs’ independent '
        'yaw-rate estimates on their own lever arms. On a symmetric platform a shared '
        'disturbance cancels out of that comparison exactly; here it survives, at about one '
        'per cent of whatever the two pairs share.',
        'Across four analysed drives, one deliberately irregular: 95th percentile 0.111 to '
        '0.124 rad/s, worst instantaneous value 0.354 rad/s. No sample crossed the 0.5 rad/s '
        'episode threshold, which was fixed before the drives were analysed.',
     ],
     size=12,
     takeaway='Within the sensitivity of this measure, the asymmetric geometry is not producing '
              'the sustained wheel-fight or scrubbing a non-symmetric layout might be expected to. '
              'The measure is blind to all four wheels slipping together.',
     notes="""
Sections 1.5 and 1.11. These say nothing about the physical wheel-ground model, which is
what the floor measurements address next.

Be careful with the yaw-residual claim. The episode threshold is the default of the
analysis tool rather than a value derived from the drivetrain, and the one-per-cent
weighting is not a calibrated slip measurement: unequal effective wheel radii, encoder
scale error, backlash and mechanical compliance all contribute to the same residual. The
honest statement is the one on the slide: within the sensitivity of this measure.

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
     title='Result: two perception constraints the room exposes',
     images=[(FIG(12), 'Fig 12 · the occluded sector'),
             (FIG(13), 'Fig 13 · coverage by drive pattern')],
     tiles=[('≈ 90°', 'Blind wedge, mast and payload in the scan plane', AMBER),
            ('107 / 430', 'Beams masked, per revolution', AMBER),
            ('88% in 18%', 'Of a full perimeter drive’s coverage, in that share of its duration', GREEN)],
     bullets=[
        'The robot occludes its own scanner over part of the sweep, because the mast and '
        'payload sit within the scan plane. Those beams are masked in software before the '
        'scan reaches the mapping layer; measured consistent at five independent headings.',
        'A deliberate 714-degree rotation over 642 s produced 43 occupied cells; an 111 s arc '
        'combining rotation with translation produced 1545 cells, 88 per cent of a full '
        'perimeter drive’s coverage in 18 per cent of its duration.',
        'The commissioning procedure in use specified rotating in place at each corner to '
        'survey the space. That procedure discards its own corner observations: coverage '
        'accumulates through translation, not rotation.',
     ],
     size=12.5,
     takeaway='Two different limits on what the robot can see: a fixed blind wedge from its own '
              'payload, and a mapping procedure that discards most of what rotation alone shows it.',
     notes="""
Section 1.12. Both results are properties of this configuration rather than of lidar or of
mapping in general: sector masking trades sensor placement against coverage loss in a way
that does not appear to be characterised quantitatively in the literature, and the
thresholds governing scan integration and pose-graph node insertion are both
motion-dependent here and neither was varied.

The quantity plotted in Figure 13 is an occupied-cell equivalent length, occupied-cell
count multiplied by the 0.05 m cell size, a proxy for committed occupancy rather than a
physical wall length. Say that if anyone asks why the totals exceed the room's perimeter.

Unmasked, a lidar self-return reads as a stationary obstacle travelling with the robot,
which is the practical reason the occlusion sector has to be handled in software.
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
data closed at 206.7 mm. The video on the next slide is that third row, played twice.

The corrections tracking the creation of pose-graph nodes rather than scan disagreement also
explains the zero loop closures on a route that returns to its own start: a closure would
arrive off-cadence, and none did.

Bound the finding, because it is easy to overstate. This scanner, this front-end
configuration, three routes of which two are tight circuits, which are poor geometry for a
matcher. A one-variable comparison on the 12.04 m perimeter route against an existing
matching-off baseline is still owed.
"""),

dict(layout='content', kicker=R,
     title='See it: scan matching, on and off',
     sub='The same circle route, wheel odometry alone against the same drive with matching on',
     videos=[('Circel Trajectory .mp4', 'Wheel odometry alone · closes to 16.2 mm'),
             ('Circle_with_pose_estimation_under25MB.mp4', 'Same drive, matching on · closes to 206.7 mm')],
     bullets=[
        'Same wheels, same scans, the robot returned to its own mark: this is the third row '
        'of the table on the previous slide, played twice.',
        'This pair is the scan-matching result, not a demonstration of wheel-level control. '
        'Rotation and translation tracking accurately is the PID and feedforward result '
        'reported earlier, on the floor and in the air, and it is the same in both clips.',
     ],
     size=13,
     takeaway='Watch the drift appear only once matching is switched on. The wheels were '
              'already accurate; the front end made the estimate worse.',
     notes="""
Do not overclaim from this pair. It is easy to look at a circle drawn cleanly and read it
as proof of accurate closed-loop wheel control, but that claim is made and measured
elsewhere in this talk, by the RMS tracking numbers, not by these two clips.

What these two clips are evidence for is narrower and specific: the same wheel data and
the same scans, once with the scan-matching front end engaged and once without, on the
route in Table 1.3's third row. Say the qualifier every time this plays.
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
     side='right', image_w=0.36,
     video='autonomous_under25MB.mp4',
     video_caption='Goal-directed autonomous drive, inside a live mapping session',
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
     size=12.5,
     takeaway='Demonstrated within a live mapping session rather than against a saved map. '
              'The number of trials is small, and it is reported as what it is.',
     notes="""
Section 1.14. Do not overclaim from this clip: three goals, three trials, inside a live
mapping session, not against a saved map. Say the qualifier every time this plays.

Establishing a success rate, a stopping-error distribution and behaviour against obstacles
requires a larger trial count in a space that permits varied routes, which places this
alongside the mapping work behind the same test-space constraint.

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
     sub='Figure 15, lower half · remaining work, with the reason it has not been done',
     side='full', image=os.path.join(A, 'slide', 'fig15b.png'),
     caption='For the five layers that are not yet established, the entry states the specific '
             'reason rather than recording a failure, and in three of those five the reason '
             'is the size of the available test area rather than anything on the platform.',
     notes="""
Section 1.16. Walk these five rows and notice that three of them carry the same reason.

Two causes account for all five. The size of the available test area accounts for three:
an accepted commissioning map, localisation against a saved map, and the named-location
library, in that dependency order, since each of the last two needs the one before it. The
deliberate absence of inertial measurement accounts for a fourth, fused state estimation.
Scan matching is the fifth, switched off by choice on the measurement reported a few
slides ago, not blocked by either constraint.

A test space offering a continuous traversable loop lifts the first three together. An
initial target of fifteen to twenty metres of path is proposed, several times the few
metres currently available rather than derived from a measured coverage-accumulation rate;
establishing that rate is itself one of the first things the new space would support.
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

Continuous monitoring in a room is usually done one of two ways: with proprietary
instruments, costly and closed to modification, or by manual transcription, which
introduces recording error and leaves a gap whenever the space is unattended. An
air-treatment appliance adds a further requirement on top of measuring correctly: it must
act on what it measures, and that action has to be independently confirmable, which a
timer cannot do. Note if asked: the system has so far been deployed in one application,
and transferability to cold storage or controlled-atmosphere rooms is a design expectation
rather than a demonstrated result.
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
     title='Four sensing devices, two actuators, one microcontroller',
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
Section 2.3. The four sensing devices, one microcontroller framing corrects an earlier
miscount in project documents that also called the character display a fifth device; it
reports state and drives no control decision.

The two actuators are driven differently and for different reasons. The lamp runs from
mains and is switched through an opto-isolated relay, so there is no electrical path
between the mains side and the logic.

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

Three design decisions followed directly from observed failures rather than anticipation:
driving the long-range radio from the host computer's GPIO was tried and abandoned, because
a non-real-time operating system cannot meet the protocol's deterministic timing and
scheduler jitter looked identical to a radio failure, so a dedicated microcontroller took
over the timing-critical work. The cellular modem draws about 2 A in transmit bursts, which
produced brownout resets on a shared supply rail; two supplies with one common ground point
eliminated them. And the three channels run concurrently rather than as a chain, for the
detection reason above.
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
issues to halt automatic actuation, and it is the one that did not persist, which made it a safety
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
            ('Separation between the two co-located deployments is by network identifier alone, not '
             'message authentication, and neither deployment’s frequency matches India’s '
             'delicensed band. Acceptable on an isolated laboratory network; not acceptable '
             'anywhere else.', RED, 'Stated rather than implied. '),
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
     title='The setting, and the hypothesis it doesn’t yet answer',
     sub='Figure 19 · the operating condition against the class of instrument each method belongs to',
     side='right', image=FIG(19), image_w=0.50,
     bullets=[
        'A large and growing workforce, shifts of ten to twelve hours, ambient temperatures '
        'routinely above 40 °C, and minimal occupational health protocols across much of the '
        'sector.',
        ('Reliable in themselves, but cannot be maintained in contact across a ten-hour shift '
         'above 40 °C. A limitation of the instrument, not of the measurement principle, and '
         'therefore tractable.', AMBER, 'Contact methods, the established approach. '),
        ('Physical fatigue shows itself as a correlated signature across several physiological '
         'domains at once: gait deteriorating, heart and respiration rates rising, facial skin '
         'temperature climbing. A system watching all of them should beat any system watching '
         'one, especially under occlusion, heat and an uncontrolled floor.', None, 'The hypothesis. '),
        ('87.9 per cent (surface electromyography, leave-one-subject-out) and 82 per cent '
         '(thermal imaging, drivers) is what each single modality already reaches alone; the gap '
         'is that they have not been fused for whole-body fatigue in an uncontrolled industrial '
         'setting.', None, 'The gap. '),
     ],
     size=12.5,
     takeaway='A bounded search, not an exhaustive one, and the technical case rests entirely on '
              'other people’s results: each modality is proven alone, not yet fused for this purpose.',
     notes="""
Sections 3.1 and 3.2. The objections to instrumenting the worker instead of the space are
practical rather than evidential: a sensor worn against the skin for an eight-hour shift in
these conditions is uncomfortable, electrode contact and signal quality degrade with
perspiration, compliance depends on the worker choosing to wear it, and a facility employing
hundreds of people acquires a daily charging and maintenance burden. None of these is fatal
alone; together they are why this strand asks whether the measurement can be made without
contact at all.

The two accuracy figures come with their own limits: surface electromyography needs
skin-contact electrodes, and the thermal figure assumes a seated, stationary, cooperative
subject at fixed distance, which a walking warehouse worker is not.

The gap is not a shortage of capable sensors, it is that they have not been fused for this
purpose. India's data protection legislation of 2023 also created real uncertainty about
workplace monitoring, and an architecture that extracts a derived score on the device and
never transmits raw video is a different legal object from one that streams a camera feed,
which is designed in on the next slide rather than argued for afterwards.
"""),

dict(layout='content', kicker=F,
     title='The framework proposed, and how it would be validated',
     images=[(FIG(20), 'Fig 20 · the framework proposed'),
             (FIG(21), 'Fig 21 · how it would be validated')],
     bullets=[
        'Camera, solid-state lidar, 60 GHz radar and long-wave infrared: one crossing of a fixed '
        'monitored zone, capture to a single score, referred to the worker’s own shift-start '
        'baseline. Only that number leaves the sensor bracket, never raw video or a point cloud.',
        'Gait is checked against marker-based motion capture; a subset of volunteers wears '
        'surface electromyography and inertial bands alongside the contactless capture, compared '
        'directly against the method this strand proposes to replace.',
        ('Thirty to fifty workers in a non-air-conditioned warehouse. The fused score must beat '
         'four single-modality baselines and an ablation over them, a bar set before any data '
         'exists.', None, 'Field deployment. '),
     ],
     size=11.5, gap=7,
     takeaway='The bar is set before any data is collected, because it is exactly the comparison '
              'that becomes easy to avoid once a pipeline exists and produces plausible numbers.',
     notes="""
Section 3.3 and 3.4. The single-subject, fixed-point capture is deliberate: continuous
multi-person tracking is a harder problem than the one being asked about, and solving it is
not a prerequisite for answering whether fatigue is legible at all. Gait carries enough
information to identify a person, so the pipeline has to discard identity by construction
rather than by policy.

A fused score that cannot beat the best single modality has bought nothing for four sensors
and an edge processor. Simultaneously processing four high-bandwidth streams on one edge
platform generates heat, and a non-air-conditioned Indian warehouse above 40 degrees is
precisely where that platform will throttle, which is a design constraint on the node
rather than a footnote.
"""),

dict(layout='content', kicker=F,
     title='What exists at the end of the year',
     bullets=[
        ('The survey, the hypothesis it produced, and a research proposal built on both. '
         'Alongside the sensing literature, the survey covered occupational fatigue physiology, '
         'Indian industrial conditions and the data protection position, because a sensing method '
         'that cannot be deployed lawfully in the place it was designed for is not a method.',
         None, 'What exists. '),
        ('The technical feasibility argument rests entirely on other people’s results. Each of '
         'the four modalities has been demonstrated individually; none of that is evidence the '
         'combination works here. It is evidence the combination is worth attempting.',
         None, 'Stated rather than blurred. '),
        ('First the capture node, because until one exists there is no data of any kind. Then '
         'per-modality laboratory validation, the step most likely to end the strand and '
         'therefore worth reaching early: if two of four modalities carry no usable signal on '
         'walking subjects, the design changes before anything is built around them. Last, '
         'fusion, field deployment and the baseline comparison, because they are the only steps '
         'that need every one before them to have worked.', None, 'The sequence that follows. '),
     ],
     size=13,
     takeaway='A negative result is a useful contribution while there is still time to act on it, '
              'and stops being one once there is not.',
     notes="""
Section 3.5. The comparison against surface electromyography on the same subjects during the
same task comes as early as the hardware allows, specifically because it is the step most
likely to show the approach does not work.
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
            'correctly into one whose readings can be quoted. That means the gas channel checked '
            'against a reference gas, and the ultraviolet channel referred to a reference '
            'radiometer at a fixed geometry. Both need instruments, not development time.',
            'Then sensor integration, which is why the architecture was built the way it was: a new '
            'measurement channel is a configuration change rather than a redesign. That makes the unit '
            'worth extending to cold storage, controlled-atmosphere rooms, and the perishable-goods '
            'areas where temperature, humidity and gas composition together set shelf life.',
            'Fatigue: first the capture node, then per-modality laboratory validation, the step most '
            'likely to end the strand and therefore worth reaching early, then fusion, field '
            'deployment and the baseline comparison. The comparison against surface '
            'electromyography on the same subjects during the same task comes as early as the '
            'hardware allows.',
            'No dates. The work depends on securing a test space, on the procurement of a sensor, and '
            'on a result that may be negative. A schedule asserted over those contingencies would not '
            'be a plan.',
        ])),
     notes="""
Section 4.3. Within each strand the order is real: the items are listed so that each one is possible
once the one above it is done.

If pressed on the absence of dates, the last bullet is the answer and it is the report's own. Offer
the dependency order instead: the test space unblocks three entries in the status figure; the inertial
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
