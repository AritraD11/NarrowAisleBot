const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 2  Every piece of hardware, and why it is there'),

p('An examiner can point at any component and ask "why that one?". The answer should never be "it was available". Every item below has a reason, and where the reason is a trade-off rather than a fact, the trade-off is stated so you can defend the side you took.'),

h2('2.1  The chassis and the wheel layout'),

p('Steel chassis, 1.00 m long, 0.36 m across the wheels, carrying four mecanum wheels on the asymmetric non-collinear layout inherited from the prior work in this laboratory.'),

p('**Why steel and not aluminium.** Mass is not a problem here, it is almost a feature: the machine has to hold its line in a corridor and a heavier base is less easily deflected by a roller slipping. The real requirement is stiffness. A mecanum base puts four independent forces into the frame at four different points, and if the frame flexes, the four wheels are no longer where the kinematic model says they are. A flexible frame quietly changes l1, l2 and d under load, and every equation downstream inherits the error.'),

gap(60),
warn('THE TWO WIDTH NUMBERS, AND WHICH ONE TO QUOTE', [
  'Two width figures appear in the report and they measure the same span by different means. **0.360 m** is the tape measurement of the built machine, wheel outer edge to wheel outer edge. **0.3754 m** is derived from the assembly drawing (twice the 157.69 mm half track, plus two 30 mm wheel half-widths). They differ by 15.4 mm.',
  '**Every experimental result in the report is referenced to the tape figure, and so is the collision footprint.** If asked, say that plainly: in a corridor with centimetres of clearance, a 15 mm disagreement is not a rounding detail, so the report states which one it used rather than quietly averaging them.',
]),

h2('2.2  The mecanum wheels'),

p('Four 6-inch mecanum wheels, radius 0.0762 m, rollers at 45 degrees. Chosen for the reason in Part 1: they are the only common wheel type that gives true sideways translation with no steering mechanism and no fore-aft travel.'),

p('**Why 45 degrees specifically.** At 45 degrees the forward and sideways components of the contact force are equal in magnitude. That makes the inverse kinematics come out with coefficients of exactly 1 on the forward and lateral terms, which is why the equations in Part 3 look as clean as they do. Other roller angles work but produce an asymmetric authority between the forward and lateral axes.'),

p('**Why 6 inch.** Bigger wheels roll over floor joints and debris better and give a larger contact patch, which matters because a mecanum contact patch is already small. Smaller wheels would lower the deck and reduce the mast lever arm, but would make the machine more sensitive to exactly the floor irregularity that a warehouse has.'),

h2('2.3  The drive motors'),

p('Four Rhino RMCS-2086 geared DC motors: 24 V, 1:47 planetary reduction, 60 rpm rated at the output shaft, roughly 1.57 N m rated torque and 3.73 N m stall.'),

bullet('**Why geared, and why 1:47.** A bare DC motor spins fast and weakly. A 45.54 kg machine needs torque at low speed, which is exactly what a reduction gearbox trades speed for. 60 rpm at the output is 6.28 rad/s, which at a 0.0762 m radius is about 0.48 m/s of rim speed, comfortably above the 0.12 m/s the robot actually operates at. The margin is deliberate: the controller must never be asking the motor for something near its limit, or there is no authority left for correction.'),
bullet('**Why DC and not stepper.** A stepper holds position open-loop but stalls silently under load and has no useful torque at speed. A geared DC motor with an encoder gives closed-loop velocity, which is what a velocity controller needs.'),
bullet('**Why four independent motors and no mechanical differential.** The mecanum principle requires four independently commandable wheel speeds. Any coupling between them would remove degrees of freedom and defeat the point.'),

gap(60),
note('THE NUMBER TO HAVE READY', [
  'Stall current is up to 30 A per motor. That is why the drivers are rated 20 A continuous, why the battery is a 30 Ah LiFePO4 rather than a small pack, and why the runaway trip in the firmware exists at all: a motor pinned at stall is a gearbox failure waiting to happen.',
]),

h2('2.4  The encoders, and the trap hidden in them'),

p('This is one of the best stories in the project and it is worth telling well.'),

p('The two front motors carry GTK08 encoders. The two rear motors carry the original optical units. After full quadrature decoding and the gear reduction they produce different counts per revolution of the wheel:'),

gap(60),
table(
  ['Motor', 'Encoder', 'Counts per wheel revolution', 'One count is'],
  [
    ['FR, FL (front)', 'GTK08, 1000 PPR', '1000 x 4 x 46.566 = **186,264**', '3.37 x 10^-5 rad of wheel rotation'],
    ['RR, RL (rear)', 'Optical, 500 line', '500 x 4 x 46.566 = **93,132**', '6.75 x 10^-5 rad'],
  ],
  [0.2, 0.22, 0.33, 0.25],
),

gap(),
h3('What "quadrature" means, in plain words'),

p('A quadrature encoder has two output channels, usually called A and B, and they are deliberately offset so that their pulses do not line up. As the shaft turns, A and B each produce a square wave, but one leads the other by a quarter of a cycle.'),

gap(60),
analogy([
  'Two people clapping at the same tempo, but one of them deliberately claps slightly late. If you listen to the pattern of claps you can tell not just how fast they are going but **which one is leading**, and therefore which direction the shaft is turning. That is the whole trick: one channel gives speed, two channels give speed and direction.',
  'And because each channel has a rising and a falling edge, there are four distinguishable edges per cycle, which is why a 1000 pulse-per-revolution encoder gives 4000 counted edges per revolution. That is what "full quadrature decoding" means, and it is where the x4 in the table comes from.',
]),
gap(),

h3('The bug that this arrangement caused, and why it was invisible'),

p('An earlier firmware version hard-coded a single constant, `ENCODER_CPR = 93132`, for all four motors. On this hardware, the front wheels produce 186,264 counts per revolution. Divide 186,264 by 93,132 and you get 2.0. So a front wheel turning once reported that it had turned **twice**.'),

p('Now follow what the controller does with that lie. The controller sees a wheel apparently going twice as fast as commanded. It believes the sensor. It cuts the drive until the _reported_ speed matches the target. The wheel is then physically turning at **half** the commanded velocity. The rear wheels, correctly scaled, track properly.'),

gap(60),
bad('WHY THIS IS THE SCARIEST CLASS OF FAULT', [
  'The result is a permanent front-to-rear speed split that scales with commanded velocity. The robot yaws when told to go straight, and curves when told to rotate. And **every diagnostic looks clean**: no error is raised, no warning is printed, and the tracking plots are beautiful, because the loop genuinely is tracking. It is just tracking a lie.',
  'The only test that can catch it is one that cross-checks front against rear independently of the software. That is exactly the bench campaign that was run: at matched drive and matched duration, the front-to-rear raw count ratio came out at 2.0 to 2.1 on physically identical gearmotors, which confirms the constants rather than assuming them.',
]),
gap(),

h3('The fix, and why it needs no scaling factors anywhere else'),

p('`ENCODER_CPR` became a per-motor array. The velocity calculation in the control loop is three lines:'),

code([
  'int32_t delta   = readEncoderDelta(i);              // counts this tick',
  'float   rev     = (float)delta / ENCODER_CPR[i];    // counts -> revolutions',
  'float   raw_vel = rev * (2.0f * PI) / PID_DT;       // revolutions -> rad/s',
]),

gap(60),
p('Each motor\'s raw count is divided by _its own_ constant. That converts a sensor-specific quantity (edges) into a physical one (revolutions), and the factor of two cancels exactly, because the encoder that produces twice as many counts is divided by a twice-larger number. Two wheels turning at the same speed report the same rad/s. Everything downstream, the PID, the feedforward, the inverse kinematics, the odometry, sees only rad/s and never learns which encoder produced it. There is no per-motor special-casing anywhere else in the firmware.'),

p('**What genuinely differs is resolution, and only resolution.** At a 100 Hz loop the smallest velocity change a front encoder can see is 0.0034 rad/s; for a rear encoder it is 0.0067 rad/s. Both sit far below the mechanical and electrical noise floor, so neither limits the velocity loop. That is why the velocity filter can stay light without the derivative term picking up quantisation hash. The extra front resolution matters for odometry, where counts accumulate over minutes, not for control.'),

h2('2.5  The level shifter, and why it is on one side only'),

p('An ATmega2560 runs at 5 V logic and accepts a 5 V encoder output directly. An ESP32 does not: its input pins are 3.3 V parts with an absolute maximum near 3.6 V, and they are not 5 V tolerant. The encoders on this platform produce an output close to 4.7 V. Feeding that straight into a 3.3 V pin exceeds its specified limit and risks permanent damage.'),

p('So all eight encoder channels (two quadrature channels on each of four motors) pass through an eight-channel bidirectional level translator, a discrete-transistor board with separate low-voltage and high-voltage supply rails.'),

p('**One asymmetry here is deliberate, and it is a good question to be asked.** Only the feedback direction is translated. The motor drivers have a logic threshold of 1.5 V, so they accept the ESP32\'s 3.3 V drive and direction signals directly with no translation at all. The translator sits only on the encoder returns.'),

gap(60),
good('THE JUSTIFICATION, WORD FOR WORD', [
  '"Fewer components in the command path is worth having, because a fault in the command path moves the machine while a fault in the feedback path only misreports it."',
  'This is a safety-ordering argument, and it is the kind of reasoning a panel rewards. Every component you add to the path that commands motion is another thing that can fail in a way that drives a wheel. A component in the sensing path can only ever tell you the wrong thing, which the safety trips are there to catch.',
]),

h2('2.6  The motor drivers'),

p('Two dual-channel drivers, 20 A continuous each, 1.5 V logic threshold. Four motors, two channels per driver.'),

bullet('**Why 20 A continuous.** Each motor can draw up to 30 A at stall. A driver sized to the running current would survive normal operation and fail on the first jam. Sizing to the stall case is the only defensible choice on a machine that operates next to racking.'),
bullet('**Why the 1.5 V threshold matters.** It is what makes the no-translation command path legal. A driver with a 2.5 V or 3.5 V threshold would have forced level shifting on the command side too, and the safety argument above would have had to be given up.'),
bullet('**Why dual channel.** Fewer boards, fewer connectors, fewer wiring runs on a 360 mm-wide chassis. Every connector is a place where a channel can end up on the wrong pin, which has already happened once during commissioning.'),

h2('2.7  The ESP32, and the calculation that forced it'),

p('This is the cleanest quantitative justification in the whole project and you should be able to do it on a whiteboard.'),

p('The four motors together, at rated speed, produce:'),

eq('2 x 186,264 + 2 x 93,132 = 558,792 counted edges per second'),

p('At rated speed the output shaft turns once per second, so that is exactly one wheel revolution\'s worth of counts, per second, per motor.'),

p('An ATmega2560 runs at 16 MHz, which is 16 million instruction cycles per second. Divide:'),

eq('16,000,000 / 558,792 = 28.6 cycles per edge'),

p('Twenty-nine cycles. That is the entire budget for interrupt entry, saving registers, decoding the quadrature state, updating the counter, and returning, **before a single cycle has been spent on the velocity loop, the serial protocol or the safety logic.** A minimal interrupt service routine on that architecture does not fit in that budget. Encoder counting alone saturates the processor.'),

gap(60),
analogy([
  'A receptionist who has to personally answer every single phone call in the building. If the calls come in fast enough, she never gets to do anything else, and eventually she cannot even answer the phones. The ATmega is that receptionist.',
  'The ESP32 has a **pulse counter peripheral**: dedicated silicon that decodes quadrature in hardware and keeps the count without the processor being involved at all, across four independent units, one per motor. That is an answering machine. The processor is then free for the 100 Hz control loop and the serial link to the host.',
]),
gap(),

p('Two further properties of the part were useful and are worth mentioning if asked whether the choice was over-determined: substantially more processing capability and memory than the part it replaced, and an integrated 2.4 GHz Wi-Fi radio, which allowed the first phone-based control surface to be hosted on the controller itself before the host computer existed.'),

gap(60),
warn('THE HONEST FOOTNOTE', [
  'That early Wi-Fi joystick path applied **one shared yaw coefficient** rather than the two the geometry requires, so it never actually carried the asymmetry the platform is built around. It was also the only point at which two writers could contend for the same wheel setpoints. It was removed when the host computer became the single command source. Volunteer this if the conversation reaches it; it is a bug that was found and closed, not one that is still open.',
]),

h2('2.8  The Raspberry Pi 5 host, and the division of labour'),

p('The Pi 5 runs Ubuntu 24.04 and ROS 2, and does the planning and perception. The ESP32 keeps the real-time control. The split follows directly from the timing argument above.'),

gap(60),
table(
  ['Runs on the ESP32', 'Runs on the Pi 5'],
  [
    ['Work that must happen on a fixed schedule: the 100 Hz velocity loop, quadrature decoding, the safety trips.',
     'Work that benefits from an operating system: SLAM, path planning, the costmaps, the dashboard web server, logging.'],
    ['Failure mode if late: a wheel is controlled badly, which is dangerous.',
     'Failure mode if late: a plan arrives a few milliseconds late, which the velocity layer absorbs.'],
  ],
  [0.5, 0.5],
),

gap(),
p('**Why a Pi 5 and not something smaller.** SLAM and a costmap stack on a live scan are genuinely demanding. The report records the consequence of the limit honestly: three components, the global planner, the local controller and the safety chain, all work correctly but run below their requested update rates because of the processing available. The global planner runs at 1.25 Hz against 5 Hz requested; the local controller at 7.5 to 13.7 Hz against 20 Hz. That is a property of the computer, not of the software, and a faster host raises all three.'),

p('**Why not a GPU machine.** It was considered and ruled out by measurement rather than assumption. The MPPI controller comes from a paper whose own experiments ran on a GPU, and the fear was that a CPU-only Pi could not sustain it. Measured on hardware, 500 sampled trajectories at 20 Hz with full-footprint collision checking held the loop rate. So the GPU origin of the algorithm did not turn out to be the binding constraint on this platform.'),

h2('2.9  The lidar'),

p('A YDLIDAR X4 Pro: a single-plane triangulation scanner, 360 degrees, rated 0.12 to 10 m.'),

h3('How a triangulation lidar works'),

gap(60),
analogy([
  'Shine a laser pointer at a wall and photograph the dot with a camera mounted a few centimetres to the side. If the wall is close, the dot appears near one edge of the photo. If the wall is far, it appears nearer the middle. The distance from the camera to the wall can be worked out from where the dot lands, because the laser, the camera and the dot form a triangle with one known side (the gap between laser and camera) and one measured angle.',
  'Spin that whole assembly and you get a 360-degree slice of the room, 430 times per revolution on this unit.',
]),
gap(),

p('**Why triangulation and not time-of-flight.** Triangulation units are an order of magnitude cheaper. The cost is accuracy that degrades with range, because the triangle gets thinner and thinner as the target moves away, so a fixed pixel error on the sensor turns into a growing distance error. That degradation is exactly what this project measured, and it is why Part 6 spends time on it.'),

h3('What was measured rather than assumed'),

bullet('**430 points per revolution at 11.35 Hz.** Not the data sheet figure and not what the configuration file asks for. The driver has a `frequency` parameter set to 6.0 Hz, and it does nothing on this unit: the motor is not commanded by the driver, so the head free-runs at its own native speed. Measured 11.35 Hz with about 8 ms of deviation on an 88 ms period, so it is stable, just not requested.'),
bullet('**Range accuracy.** The manufacturer states 2 cm below 1 m and 3.5 per cent of range from 1 to 6 m, with nothing specified beyond 6 m despite a 10 m rated range. The report treats that as a factory acceptance condition rather than a runtime error distribution, and measures the installed unit directly instead.'),
bullet('**A range cap set to 10 m, not 5 m, on purpose.** The driver reports what the sensor can genuinely do. The SLAM configuration separately chooses to use only 5 m. Two different questions: `range_max` is a hardware fact, `max_laser_range` is a policy. Capping at the driver would destroy the data before anything could measure what the cut cost.'),

gap(60),
good('A GOOD LINE ABOUT THIS SENSOR', [
  '"The case against the present lidar is now quantitative rather than impressionistic. Repeating the same routes with a higher-grade scanner, using the same analysis tools, would convert that inference into a controlled result. That question is currently answered in the literature by convention rather than by measurement."',
]),

h2('2.10  Power'),

p('A LiFePO4 pack, 12.8 V nominal, 30 Ah, with a boost converter to the 24 V drive rail and a buck converter to the 5 V logic rail.'),

bullet('**Why LiFePO4 and not lithium-ion.** Thermal safety. A LiFePO4 cell does not go into thermal runaway the way a standard lithium-ion cell can, which matters on a machine that will eventually be left charging unattended in a warehouse. It also tolerates far more charge cycles, and its discharge voltage is flat, so the drive rail stays stable as the pack depletes.'),
bullet('**Why 30 Ah.** Four motors capable of 30 A each at stall. The pack has to hold the rail up during a current transient without sagging, and a small pack would brown out the logic every time the machine started from rest against a load.'),
bullet('**Why boost to 24 V rather than a 24 V pack.** A single lower-voltage pack is simpler to charge and safer to handle, and the boost converter isolates the drive rail\'s transients from the logic rail.'),
bullet('**Why a separate buck to 5 V.** The logic must not see what the motors do to the supply. This is the same principle that the monitoring system learned the hard way in Chapter 2, where a cellular modem drawing 2 A in bursts on a shared rail caused brownout resets until the supplies were split.'),

h2('2.11  The mast, the cargo arm and the lighting'),

p('A vertical mast carries three ultraviolet tubes and the stepper axis of the cargo arm. Two lateral and one vertical stepper axis in total. These are retained on the original Arduino Mega, which was reassigned to the payload rather than discarded.'),

bullet('**Why keep the Mega at all.** It is perfectly capable of sequencing an arm and a lamp, neither of which has a hard real-time requirement. Reassigning it costs nothing and keeps the payload logic off the controller doing the 100 Hz work.'),
bullet('**Why the lighting is sequenced on that controller rather than from the host.** So the staging survives loss of the serial link, with a latched emergency stop. If the Pi crashes, the lamp does not stay on in an uncontrolled state.'),

gap(60),
bad('THE COST OF THE MAST, AND YOU SHOULD SAY IT FIRST', [
  'The mast and its payload sit **inside the lidar scan plane**. That is the direct cause of the 90-degree self-occlusion wedge, 107 of 430 beams, a quarter of every scan, permanently missing in a fixed direction relative to the body.',
  'This is not a mistake so much as an unavoidable consequence of carrying a payload above a single-plane scanner, and the report says the trade-off between sensor placement, sector masking and accepted coverage loss does not appear to be characterised quantitatively in the literature. If asked how you would fix it: raise the lidar above the payload, or move to a multi-plane sensor, or accept the wedge and mask it, which is what is done today.',
]),

h2('2.12  What is deliberately NOT on the robot'),

p('Absences are as defensible as presences, and examiners probe them. Each of these has a reason.'),

h3('No inertial measurement unit'),

p('This gets its own full treatment in Part 5, because it is the single most likely question. The short version: Objective 2 asks which sensing a pose estimate requires. Fitting an IMU at the start would have removed the ability to answer that question, because there would be no unfused baseline to compare against. The absence is what made the wheel-only behaviour measurable.'),

p('**What is not claimed:** that the platform is better off without one. It is the right next purchase, and the part is already chosen (a BNO085, on the ESP32\'s I2C pins that have been reserved for it, run in 6-axis mode with the magnetometer held out because a 24 V 30 A motor bus sits a few centimetres away).'),

h3('No optical flow ground sensor'),

p('An IMU fixes heading. It does nothing for translational slip, which is the other half of the odometry error: a commanded 1.00 m sideways move reads 1.245 m in the raw odometry, measured twice, 3 mm apart. An optical flow sensor measures true ground velocity and does not care what the wheels are doing. It is on the roadmap, not on the robot. The candidate parts are chosen but ground clearance has never been measured on this chassis, which is the honest blocker.'),

h3('No proximity ring'),

p('A 360-degree, roughly 1 m short-range ring is specified as a hard override that stops the robot when something enters a cushioning zone, working alongside SLAM rather than inside it. The part choice is worked out (time-of-flight rather than ultrasonic, because ultrasonic pings bounce away off cloth, foam or any oblique surface, which is precisely what warehouse cargo is made of) but nothing is fitted.'),

gap(60),
note('HOW TO TALK ABOUT A ROADMAP ITEM', [
  'The rule this project uses is a good one to quote: a value in a document is not a value on the robot, and by the same rule, a part in a roadmap is not a part in the parts bin. Say clearly that none of these is installed. Then say what each would buy and what measurement would prove it. That is a much stronger position than implying they are nearly done.',
]),

];
