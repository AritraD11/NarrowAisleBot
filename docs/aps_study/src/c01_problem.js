const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 1  The problem, and why the robot looks like this'),

h2('1.1  Why the aisle, and not the rest of the warehouse'),

p('Warehouse automation already works. Goods move on conveyors, on pallet shuttles, on autonomous forklifts that drive down wide, well-marked main routes. What almost nothing works in is the aisle itself: the narrow slot between two racks where the stock actually sits.'),

p('The reason is geometry, not intelligence. An aisle is sized for two things: the boxes on the racks, and a human being who has to walk in and pick from them. It is not sized for a vehicle. So a robot working there has a few centimetres of clearance on each side, not a few metres.'),

gap(60),
analogy([
  'Think of a corridor in a crowded hostel, with a suitcase against each wall. You can walk down it. You cannot turn a bicycle around in it. That is exactly the difference between a human picker and a conventional mobile robot, and it is the whole problem this project starts from.',
]),
gap(),

p('Now add the second problem. A normal robot (differential drive, like a wheelchair, or car-like steering) cannot move sideways. If it ends up 5 cm too close to the left rack, it cannot simply shuffle 5 cm to the right. It has to perform a manoeuvre: turn slightly, drive forward, turn back. That manoeuvre eats forward distance, and the corridor does not have spare forward distance to give. Worse, once such a platform is misaligned inside an aisle, getting straight again means either reversing all the way out or doing a long sequence of short forward and backward moves. Both cost time and both risk scraping the racking.'),

h2('1.2  Why mecanum wheels'),

p('A mecanum wheel is an ordinary wheel with a ring of small barrel-shaped rollers bolted around its rim, each roller set at 45 degrees to the wheel axle. The rollers spin freely; nothing drives them.'),

p('Because the roller is at 45 degrees, when the wheel is driven forward the patch of rubber touching the floor cannot simply push straight backwards. It pushes at 45 degrees. So every wheel produces a force with two parts: one along the direction the wheel is rolling, and one sideways along the roller axis.'),

gap(60),
analogy([
  'Imagine four people standing at the corners of a stretcher, each of them allowed to push only along a diagonal, like a bishop on a chessboard. One person alone can only go diagonally. But if all four push their diagonals at the right speeds, the unwanted sideways parts cancel and the wanted parts add, and the stretcher can be made to move in **any** direction, or to spin on the spot, without anybody turning their feet.',
  'That is a mecanum base. Nothing steers. The direction of travel is chosen purely by picking four wheel speeds.',
]),
gap(),

p('The practical consequence for the aisle problem: a mecanum platform corrects a 5 cm lateral error by translating sideways 5 cm. In the ideal case that manoeuvre uses zero forward distance. That is the property the whole platform is built around.'),

h3('The cost of mecanum, which you should volunteer before being asked'),

bullet('**Slip is built in.** The rollers are supposed to slide sideways. That is the mechanism. But it means the contact patch is small, and the relationship between how far a wheel turns and how far the robot actually moves is not exact. This is the root of the odometry error later in this document.'),
bullet('**Efficiency is lower.** Some of the motor torque always goes into sideways scrubbing rather than into useful motion.'),
bullet('**Floor sensitivity.** Performance depends on the surface. This project measured it directly: the same commanded drive on different patches of the same laboratory floor gave ground-load increases of 24 per cent, 14 per cent and 3 per cent.'),
bullet('**Four independent motors.** There is no mechanical coupling to average out an error. If one wheel is wrong, the robot goes somewhere the model did not predict.'),

h2('1.3  Why asymmetric, and what "asymmetric" actually means'),

p('A conventional four-wheel mecanum robot puts its wheels at the four corners of a rectangle. That is the standard layout in every textbook.'),

p('The trouble is that the rectangle sets the width of the machine. The chassis has to be wide enough to carry the wheel rectangle, whether or not the payload needs that width. So the vehicle is wide because of its wheels, not because of its job. In a narrow aisle that is exactly the wrong thing to be.'),

p('The alternative used here moves one diagonal pair of wheels inward along the length of the robot. The layout becomes point-symmetric (it looks the same if you rotate it 180 degrees about its centre) instead of mirror-symmetric. Front-right and rear-left sit 0.403 m from the centre; front-left and rear-right sit 0.333 m. The difference, 70 mm, is the asymmetry.'),

gap(60),
analogy([
  'Think of four people carrying a long plank. In the standard arrangement they stand at the four corners, so the plank has to be as wide as their shoulders. In the asymmetric arrangement two of them step inward along the plank. The plank can now be narrower, and it is still carried at four points, and it can still be moved in any direction. What changes is that the two people standing further out have more leverage when the group wants to spin the plank, and the two standing inward have less.',
]),
gap(),

p('That leverage difference is the entire technical consequence, and it is worth being exact about it, because this is where marks are won.'),

h3('The lever arm, precisely'),

p('When a robot rotates about its own centre, each wheel has to travel around a circle. The radius of that circle is the wheel\'s "lever arm": how far it is from the centre of rotation, measured perpendicular to the direction it pushes. For a mecanum wheel that lever arm works out as the longitudinal distance plus the half track width.'),

eq('Ko = l1 + d = 0.403 + 0.15769 = 0.5607 m      (outer pair: FR, RL)'),
eq('Ki = l2 + d = 0.333 + 0.15769 = 0.4907 m      (inner pair: FL, RR)'),

p('Those two differ by 14 per cent. On a symmetric platform there is one number and it serves all four wheels. Here there are two, and each wheel must use its own.'),

gap(60),
bad('THE RISK, IN ONE SENTENCE', [
  'If a wheel is driven with the wrong lever arm, the robot yaws at a rate that is wrong by 14 per cent, and **nothing else in the transformation gives any sign of it.** Forward motion looks perfect. Sideways motion looks perfect. The tracking plots look clean. Only the heading is quietly wrong. This is why the report says the 14 per cent is both the whole of the difference and the whole of the risk.',
]),
gap(),

p('And notice what does _not_ change: the translation terms. Forward and lateral motion use exactly the same coefficients on both layouts. Push the robot forward and it behaves like any other mecanum robot. Only the yaw column of the transformation is different. If you remember one sentence about the geometry, make it that one.'),

h2('1.4  What was inherited and what was built'),

p('Be precise about this in the viva, because it is a fairness question and examiners ask it directly.'),

gap(60),
table(
  ['Inherited', 'Built during this year'],
  [
    ['The geometric idea. Earlier work in this laboratory derived the kinematics for the asymmetric non-collinear layout and demonstrated it on a small prototype.',
     'The transition to full scale: a 45.54 kg machine, and the measurement campaign that says whether the geometry survives that transition.'],
    ['An assembled mechanical platform: chassis, four mecanum wheels on the asymmetric layout, four geared motors, two motor drivers, the power system.',
     'All firmware. Closed-loop velocity control at every wheel, the two-term feedforward, the safety trips.'],
    ['Motor control by an Arduino Mega 2560, with no velocity regulation at all.',
     'The move to an ESP32, the level-translation hardware for the encoder return path, and the 100 Hz control loop.'],
    ['Nothing above that.',
     'The whole ROS 2 stack: serial bridges, the asymmetric inverse kinematics node, odometry, the scan relay, the operator dashboard, the analysis tools, and every measurement quoted in the report.'],
  ],
  [0.5, 0.5],
),

gap(),
note('THE SENTENCE FROM THE REPORT', [
  '"Everything reported beyond that point, the firmware, the ROS 2 software, the instrumentation and every measurement quoted in this report, was carried out by the author."',
]),

h2('1.5  The three strands, and the honest reason they are together'),

p('The project runs three things in parallel. A panel will ask why, and the weak answer is "they are all about warehouses". The strong answer is the one the report gives.'),

bullet('**Strand 1, the robot.** The machine that moves through the aisle. Built, instrumented, measured. This is the principal strand and most of the report.'),
bullet('**Strand 2, environmental monitoring.** The condition of the air in the space the robot moves through. Deployed and running across four zones.'),
bullet('**Strand 3, contactless fatigue assessment.** The condition of the people who share that space. A hypothesis and a completed literature survey. Nothing built, no data.'),

p('What links them is not the subject. It is the instrumentation. Multi-sensor integration, calibration against a physical reference, real-time acquisition, and control that fails safe are common to all three. And the traffic between them is real, not decorative:'),

bullet('The monitoring system established the practice of verifying a configuration against the _running system_ rather than against a file. That practice was then applied to the robot, and it is why the scan-matching experiment could be trusted.'),
bullet('The robot work established that a control law must be _observed responding to a change_ rather than inferred from a steady-state snapshot. That was then applied back to the monitoring system, and it is exactly what Chapter 2 admits it still owes.'),

gap(60),
good('THE LINE TO USE', [
  '"An error made in one strand has repeatedly become a method in the next, and that return accrues whether or not the three ever converge into a single system."',
]),

h2('1.6  The five objectives, and where each one honestly stands'),

gap(60),
table(
  ['Objective', 'Status, stated honestly'],
  [
    ['**O1.** Build and experimentally characterise a full-scale asymmetric mecanum platform.',
     '**Closed.** Controller, kinematics and odometry are characterised against measured references.'],
    ['**O2.** Localisation and autonomous navigation at corridor-width clearances.',
     '**Closes as characterised, not as optimal.** Navigation demonstrated inside a live mapping session, not against a saved map.'],
    ['**O3.** Quantify the cost and benefit of the asymmetric layout.',
     '**Open.** No matched symmetric baseline has been built, so the effect of the asymmetry itself is unquantified. A consistent absence of penalty is not a measured cost of zero.'],
    ['**O4.** A closed-loop environmental monitoring system.',
     '**Deployed** across four zones. Two physical calibrations outstanding before any reading can be quoted as a quantity.'],
    ['**O5.** A contactless framework for worker fatigue.',
     '**Proposed.** Survey complete, hypothesis stated, nothing built.'],
  ],
  [0.46, 0.54],
),

gap(),
p('Saying this table out loud early in the talk is a strong move. It tells the panel you know exactly what you have and have not proved, which means everything you claim afterwards is more credible.'),

];
