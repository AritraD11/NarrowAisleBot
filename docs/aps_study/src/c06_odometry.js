const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 6  Odometry, and the error nobody could see'),

h2('6.1  What was measured, and against what'),

p('Endpoint closure means: drive a route, come back to the mark you started from, and ask how far the robot _thinks_ it is from that mark. If the estimate were perfect it would read zero.'),

gap(60),
table(
  ['Route', 'Closure', 'As a fraction of path'],
  [
    ['8.00 m, 162 s', '19 mm', '0.23 per cent'],
    ['9.61 m, 179 s', '28 mm', '0.29 per cent'],
    ['10.61 m, 233 s', '96 mm', '0.91 per cent'],
    ['**18 m route**', '**0.229 m**', '**1.27 per cent**'],
    ['**18.14 m route**', '**0.257 m**', '**1.42 per cent**'],
    ['4.582 m (short, straight)', '3.1 mm', '0.07 per cent, see the caveat below'],
    ['38 s square, 1.42 m', '2.58 cm', 'Above the reference floor, so a meaningful figure'],
  ],
  [0.34, 0.26, 0.4],
),

gap(),
h3('The caveat you must give with the best number'),

p('The reference is a mark on the floor, read by tape and eye. That is good to a **few millimetres at best**. So the 4.582 m route closing to 3.1 mm should be read as "closure at or below the resolution of the reference", not as "a 3.1 mm measurement". The 2.58 cm square is comfortably above that floor and is a meaningful figure.'),

gap(60),
good('THE DEFENSIBLE STATEMENT, WHICH IS THE ONE TO MEMORISE', [
  '"Closure stays below 1 per cent of path on every route up to about 10 m, reaches roughly 0.1 per cent on short straight runs, and sits between 1.1 and 1.5 per cent on the longest routes driven. It should not be generalised past the route lengths it was measured on."',
]),

h3('Why the longest route is the worst'),

p('Look at the three logged drives again: 0.23, 0.29, then 0.91 per cent. The jump to 0.91 is on the route with the **most rotation**, not simply the longest route.'),

p('That is consistent with the physics. During a rotational manoeuvre the rollers do more lateral scrubbing than during a straight drive, and lateral scrubbing is exactly the motion the wheel encoder cannot see. So error grows with the amount of rotation a route contains, as well as with its length.'),

p('Separating those two effects needs routes that vary length and rotation **independently**, which is a direct use for a larger test space and is listed as outstanding.'),

h2('6.2  The photogrammetry result: the robot came back, the estimators did not'),

p('This is the most important measurement in Chapter 1 and it deserves to be told slowly.'),

h3('The method'),

p('Heading at the end of a drive was measured from video against world-static floor features, using the orientation of the tile grout as the reference. (The alignment criterion used throughout the project is the chassis edge parallel to the tile line, so the grout was already the operational reference.) Frames were extracted with ffmpeg, position taken from a threshold centroid on floor brackets, and heading from a gradient-orientation histogram on the grout lines.'),

h3('The instrument was validated before its output was believed'),

p('This is the part that makes the result usable.'),

gap(60),
table(
  ['Commanded rotation', 'Instrument reported', 'Agreement'],
  [
    ['-28.0 degrees', '-27.07 degrees', 'within 1 degree'],
    ['-19.4 degrees', '-18.50 degrees', 'within 1 degree'],
  ],
  [0.34, 0.33, 0.33],
),

gap(),
p('That agreement is the **only** uncertainty estimate available for the method, so its resolution is taken as of order one degree. That matters, because it is what makes the result below interpretable: the errors found are several times the instrument\'s demonstrated agreement, not comparable to it.'),

gap(60),
warn('TWO FAILURE MODES WERE FOUND DURING VALIDATION', [
  'The first one is almost funny and is worth telling: the original attempt measured the robot against a **camera mounted on the robot\'s own mast**, which by construction reports no rotation at all. A camera that turns with the thing it is measuring can never see that thing turn.',
  'This is the same class of mistake as the settling-time bug in Part 5: an instrument that structurally cannot produce the answer you are looking for. Catching both is a methodology story, and it is a good one.',
]),

h3('The result'),

p('On two structurally different routes:'),

gap(60),
table(
  ['Source', 'Heading change reported at the end of the drive'],
  [
    ['Wheel odometry', '3.85 degrees and 4.49 degrees'],
    ['The published pose estimate', 'the same'],
    ['The SLAM pose', 'the same'],
    ['**The floor, read photogrammetrically**', '**within 0.03 degrees of the starting heading**'],
  ],
  [0.44, 0.56],
),

gap(),
p('The robot came back to its heading. The estimators did not.'),

gap(60),
good('THE LOGICAL MOVE, AND IT IS THE GOOD BIT', [
  '"Three estimates agreeing with one another while all three disagree with the floor is the signature of an error they **share**, not one that separates them."',
  'This is why agreement between your own estimators means nothing on its own. They all derive from the same wheel measurements, so they will all inherit the same wheel-level error and all report it confidently.',
]),

h3('What this narrows the error to, stated carefully'),

p('Two candidates survive:'),

num('**An encoder or wheel-radius scale error.** This is estimator error. The wheels turned a certain amount, the model converted it to a heading with a slightly wrong constant. **Recoverable by calibration.**'),
num('**A rigid all-wheel slip mode**, in which all four wheels slip together and the platform\'s motion stays rigid. This is physical. The wheels genuinely turned that much; the robot genuinely did not rotate that much. **Not recoverable by calibration.**'),

p('What rules the other candidates out: the yaw-consistency residual rules out significant _differential_ slip between wheels, and the offline re-integration rules out an integration fault.'),

gap(60),
warn('THE ELIMINATION IS NOT EXHAUSTIVE, AND THE REPORT SAYS SO', [
  'A geometric parameter error, a systematic mounting offset, or a timing error between the encoder and pose streams would all produce a similar signature, and none has been separately excluded.',
  'Say this. A panel that hears "we narrowed it to two possibilities" will immediately think of a third, and it is much better if you got there first.',
]),

h2('6.3  Why there is no IMU, and how to defend it'),

p('Expect this question. Expect it to be the first one. Here is the full argument in the order to deliver it.'),

h3('The argument'),

num('Objective 2 asks for a pose estimate characterised against an independently measured physical reference, **with an explicit account of which sensors are required to reach it**. That third clause is the research content. It is a question about sensing, not a requirement to own a particular sensor.'),
num('Fitting inertial measurement at the start would have removed the ability to answer it. Fusion improves an estimate; that is not in doubt. But **without a characterised unfused baseline at the operating scale, there is no way to say by how much, or which error it removed.**'),
num('The unfused platform is that baseline, and it is now characterised: 0.23 to 0.91 per cent closure to 10 m, 1.27 to 1.42 per cent on 18 m routes, and 3.85 and 4.49 degrees of heading error invisible to every fitted instrument.'),
num('A rate gyroscope measures angular rate **independently of the wheels**. Integrating it gives a heading estimate that drifts with bias but that does not share the wheel-derived error. That is precisely what would make this class of error observable, and precisely what would separate an encoder scale error from a rigid all-wheel slip mode.'),
num('So the next measurement is not a general improvement. It is a **falsifiable test with a number already written down**: fit the sensor, re-run the same two routes, and see whether the 3.85 and 4.49 degrees go away.'),

gap(60),
good('THE DISCLAIMER THAT MAKES THE ARGUMENT CREDIBLE', [
  '"What is not claimed is that the platform is better off without one. Fusion would reduce heading error, an inertial sensor is the right next purchase, and nothing here argues otherwise. The claim is about **order of work**."',
  'Without that sentence the argument sounds like a rationalisation. With it, it is a research-design decision.',
]),

h3('The honest limit of the argument'),

p('The report goes further and admits something most would leave out. Which instrument binds the error at the 5 m operating scale is **not** something this year\'s data settles.'),

bullet('Endpoint closure was never measured at 5 m. The routes driven were either short and straight (about 0.1 per cent) or long and rotation-heavy (1.1 to 1.5 per cent). Applying either rate to an intermediate distance is extrapolation, not measurement.'),
bullet('The scanner is characterised on its own terms instead: stationary ray scatter of 22.3 mm in the 1.5 to 2.0 m band in one capture and 31.9 mm in a second, the latter failing the 25 mm half-cell criterion the mapping resolution implies. Beyond 2.5 m the two captures do not agree with each other.'),
bullet('What that establishes is that the **scanner** is unreliable at the ranges a corridor-width map depends on, not that it is the larger of two quantified error terms.'),

p('So: both estimators have limitations at the intended scale, and separating their contributions needs the third measurement an inertial sensor would provide. Objective 2 therefore closes as **characterised** rather than as **optimal**.'),

h2('6.4  The lateral scale correction, and why it is called a constant rather than a model'),

p('A detail from the repository that is worth having, because it is the concrete face of mecanum slip.'),

p('Controlled tests, robot re-zeroed at the mark each time: driving 1.00 m forward read 1.009 m in the odometry (0.9 per cent, accurate). Driving 1.00 m sideways read **1.245 to 1.248 m**, twice, 3 mm apart. Too tight to be floor noise, too large to be rounding.'),

p('Before blaming software, the wheel-level check was done: the live wheel velocities during a pure right strafe read exactly what the asymmetric inverse kinematics predict, with the computed forward and yaw components landing on precisely zero. The teleoperation node, the odometry\'s reverse kinematics, the serial bridge\'s channel ordering and the firmware\'s per-motor sign table were all read and are internally consistent. **Nothing is miswired.** The error is physical: mecanum rollers scrub sideways across the floor during a strafe, so the wheels turn further than the chassis actually travels, and the ideal kinematic model has no way to know that.'),

p('The fix is a single `lateral_scale` parameter applied where the lateral velocity is produced, so the integrated position, the published twist and everything downstream inherit one correction. The longitudinal axis was left untouched, because it measured accurate and "fixing" an axis that is not broken is how you introduce a new error.'),

gap(60),
bad('WHY IT IS A CONSTANT AND NOT A MODEL', [
  'The value needed on one floor was 0.80. On a second floor it was **0.92**. Two independent routes to the same number on that second surface. **Surface dependence is the finding here, not a footnote.**',
  'That is why the parameter is live-readable rather than cached at startup, and why the report calls it an empirical single-floor constant rather than a model of slip. A model would predict the value on a new floor. This does not.',
  'One more thing measured and deliberately **not** modelled: during a 1.00 m pure strafe the chassis visibly drifted 2 to 3 cm off the tape line while the odometry reported zero forward-axis change. That is a small unmodelled cross-coupling, about 0.6 cm over a 0.25 m nudge. Recorded, not corrected.',
]),

h1('Part 7  The lidar, and what it can and cannot see'),

h2('7.1  What was measured rather than assumed'),

p('Three properties of the installed sensor were measured directly, because each affects what the mapping layer can achieve, and because a data sheet describes a class of part rather than the unit on your robot.'),

h3('One: the scan rate and point count'),

p('The scanner returns approximately **430 points per revolution at 11.35 Hz** and does not respond to a commanded scan rate.'),

p('That second clause is a genuine finding. The driver has a `frequency` parameter, and lowering it should trade scan rate for angular density (points per revolution is roughly the sample rate divided by the frequency, so 5000 divided by 6 would give about 833 points instead of 500). The parameter was set to 6.0. Measured result: **it has no effect on this unit**, because the driver never commands the motor, so the head free-runs at its own native speed. Measured 11.35 Hz with about 8 ms of deviation on an 88 ms period: stable, just not requested.'),

gap(60),
good('WHY THIS IS A GOOD THING TO TELL', [
  'A whole planned improvement ("reduce the frequency for 67 per cent more points, for free") turned out not to exist on this hardware. It was found by measuring the live topic rather than by trusting the configuration file. That is the same discipline as verifying a parameter against the running node rather than reading the YAML, and it is one of this project\'s two standing conventions.',
  'The measured 430 points also confirms the model: 5000 divided by 11.35 is about 441, against 430 measured, a 2.5 per cent error. So the model is right; the lever simply is not connected.',
]),

h3('Two: range accuracy, measured as scatter'),

p('The manufacturer states 2 cm absolute below 1 m and 3.5 per cent of range between 1 and 6 m, with nothing specified beyond 6 m despite a 10 m rated range.'),

p('The report treats that as a **factory acceptance condition rather than a runtime error distribution**, and measures the installed unit instead: the robot parked with nothing moving in the room, every ray logged for 60 s, and the scatter reported per range bin as the spread of a given bearing\'s returned range across consecutive sweeps.'),

gap(60),
table(
  ['Range band', 'Capture 1', 'Capture 2 (different parking spot)', 'Reading'],
  [
    ['Below 1.5 m', '12 to 14 mm', '12 to 14 mm', 'Solid in both. Well inside what the map needs.'],
    ['1.5 to 2.0 m', '22.3 mm', '**31.9 mm**', 'The second capture **fails the 25 mm half-cell criterion** the 0.05 m occupancy resolution implies.'],
    ['Beyond 2.5 m', '55 to 200 mm', '55 to 200 mm', 'Both large, and **they do not agree with each other**.'],
  ],
  [0.18, 0.18, 0.24, 0.4],
),

gap(),
p('Neither a linear nor a quadratic degradation model reproduces that pattern, since both predict a single smooth curve. The behaviour is **scene-dependent** and is not explained by range alone in these captures.'),

gap(60),
good('WHICH IS ITSELF THE RESULT', [
  '"A range cap derived in one position is a fact about that position until it reproduces elsewhere."',
  'That sentence is the honest conclusion and it is better than a fitted curve would have been. It also explains why the SLAM range cap is treated as policy to be tested rather than as a derived constant.',
]),

h3('Three: self-occlusion'),

p('The robot blocks part of its own sweep, because the mast and payload sit within the scan plane.'),

gap(60),
table(
  ['Property', 'Value'],
  [
    ['Blind sector', 'Approximately **90 degrees**, centred on directly behind the robot'],
    ['Beams affected', '**107 of the 430** returned per revolution, about a quarter of every scan'],
    ['Measured at', '**Five independent headings**, one full rotation'],
    ['Handling', 'Masked in software before the scan reaches the mapping layer'],
  ],
  [0.3, 0.7],
),

h3('The discriminator, which is the clever part'),

p('How do you tell a self-occlusion return from a real wall, when both look like "something close, every scan"?'),

gap(60),
analogy([
  'Stand in a room and spin slowly with your arm held out in front of your face. The room sweeps past your eyes. **Your arm does not.** Anything that stays in the same place in your own field of view as you turn is attached to you.',
  'That invariance is the entire test, and it needs no props, no reference objects and no measuring equipment.',
]),
gap(),

p('Run in practice: the bearing analysis was done at five headings roughly 90 degrees apart. Exactly one contiguous bearing block returned a nonzero close reading in **every one of the five independent headings**, at consistent percentages each time (one bin read 42, 43, 39, 41 and 40 per cent across the five runs, a four-point spread despite the robot facing a completely different way each time). Every other sector that any individual run flagged appeared in exactly one run and nowhere else: those are real walls the robot happened to be facing, correctly _not_ persisting.'),

p('The single nearest point across all five scans clustered at the same bearing and at 0.12 to 0.13 m range every time, right at the lidar\'s own minimum range. Five-way agreement at that scale is not plausible for a real object.'),

h2('7.2  Why the masking must be "invalid", not "free" and not "occupied"'),

p('This is a subtle point and a good one to be asked.'),

gap(60),
table(
  ['If those beams were treated as...', 'What happens'],
  [
    ['**Occupied** (the original bug)', 'The costmap marks cells occupied at a fixed bearing relative to the body. They translate and rotate **with the robot**: a permanent obstacle welded to the chassis that can never be escaped or cleared. The inflation layer expands it, and the planner concludes that entire direction is blocked. Everywhere. Forever.'],
    ['**Free**', 'Worse in a different way. A beam that returns nothing is used to **clear** cells along its path, so the robot would confidently erase real obstacles behind its own mast.'],
    ['**Invalid** (correct)', 'The beams neither mark nor clear. Cells behind the mast simply stay unknown. With the planner configured to allow unknown space, that is tolerable: the robot has no information there, which is the truth.'],
  ],
  [0.26, 0.74],
),

gap(),
good('THE PRINCIPLE', [
  '"A beam carrying no information must be dropped, not reinterpreted." Turning an absence of data into either positive evidence or negative evidence is how a mapping layer poisons itself.',
]),

h2('7.3  The scan relay, and why an extra node sits in the path'),

p('The raw scan from the driver is republished by a small relay node before it reaches anything else. Two jobs:'),

bullet('**A quality-of-service bridge.** The driver publishes best-effort; several consumers want reliable. A mismatch there means a subscriber silently receives nothing, which is one of the more frustrating ways for a ROS 2 stack to fail.'),
bullet('**The self-occlusion mask.** It is the natural place, because it is one node, already in the path, already touching every scan.'),

p('**Why it is stated as a design decision rather than an implementation detail:** because it is the single point where a scan can be edited before it reaches both SLAM and the costmap. Doing the masking in two places would eventually let them disagree.'),

];
