const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 14  The corridor sheet'),

p('Read this in the ten minutes before you go in. Nothing here is new; it is the whole document compressed.'),

h2('Geometry'),

gap(60),
table(
  ['', '', '', ''],
  [
    ['Footprint', '1.00 x 0.36 m', 'Mass', '45.54 kg'],
    ['l1, outer (FR, RL)', '0.403 m', 'l2, inner (FL, RR)', '0.333 m'],
    ['Asymmetry offset', '70 mm', 'Half track d', '0.15769 m'],
    ['Wheel radius r', '0.0762 m', 'Roller angle', '45 degrees'],
    ['Ko = l1 + d', '0.5607 m', 'Ki = l2 + d', '0.4907 m'],
    ['Ko vs Ki', '14 per cent apart', 'Common-mode weight', '0.0097'],
    ['Operating limit', '0.12 m/s, 0.30 rad/s', 'Wheel speed ceiling', '5.20 rad/s (air)'],
  ],
  [0.24, 0.26, 0.24, 0.26],
),

h2('Control'),

gap(60),
table(
  ['', '', '', ''],
  [
    ['Loop rate', '100 Hz, four independent', 'Controller', 'Two-term FF plus PID'],
    ['Kff (FR/FL/RR/RL)', '37.3 / 38.4 / 38.3 / 38.0', 'Kstat', '8.0, all four'],
    ['Kstat fade', '0.05 to 0.20 rad/s', 'Fit band', 'all points inside 8 %'],
    ['Kp', '45 (confirmed, not derived)', 'Ki', '250 (was 30)'],
    ['Kd', '0.5, on measurement', 'Plant gain K', '0.0263 rad/s per count'],
    ['lambda chosen', '0.15 s = 15 periods', 'tau measured', '0.09 s (assumed 0.18)'],
    ['Slew limit', '12 rad/s^2', 'Min drive output', '5 counts (was 15)'],
    ['Velocity filter', 'alpha = 0.4', 'Encoder quantum', '0.0034 / 0.0067 rad/s'],
    ['Encoder CPR front', '186,264', 'Encoder CPR rear', '93,132'],
    ['Edge rate, 4 motors', '558,792 per second', 'ATmega budget', '29 cycles per edge'],
  ],
  [0.24, 0.26, 0.24, 0.26],
),

h2('Results, with their qualifiers'),

gap(60),
table(
  ['Result', 'Number', 'The qualifier that must travel with it'],
  [
    ['Tracking, unloaded', '0.040 to 0.047 rad/s RMS', '26,468 samples, three bench runs, wheels in the air.'],
    ['Tracking, loaded', '0.066 to 0.074 rad/s RMS', '35,248 samples, three floor runs. **The band that matters operationally.**'],
    ['Saturation', '0.0 per cent', 'Every channel, every recorded run. So these are controller performance, not an artefact of hitting a limit.'],
    ['Ground load increase', 'mean 24 per cent', 'Predicted 10 to 30 before the run. Three of four inside; rear-right at 30.3 is an exceedance. Two later runs gave 14 and 3 per cent, so the **size** is not settled.'],
    ['Kinematics round trip', '2.22 x 10^-16', '20,000 cases. Says the arithmetic is right, nothing about the physics.'],
    ['Offline re-integration', '0.0054 m peak, 0.0000 m final', 'Rules out a discrepancy between implementations, not an error they share.'],
    ['Endpoint closure', '0.23, 0.29, 0.91 per cent', 'Over 8.00, 9.61, 10.61 m. **Below 1 per cent out to about 10 m.** 1.27 and 1.42 per cent on 18 m routes.'],
    ['Yaw residual', 'median 0.035 rad/s', 'p95 0.111 to 0.124, worst 0.354. Threshold 0.5 never crossed, and it is the tool default, not derived.'],
    ['Self-occlusion', '90 degrees, 107 of 430 beams', 'Measured at five independent headings.'],
    ['Rotation coverage', '43 cells in 642 s', 'Against 1545 cells in a 111 s arc. 88 per cent of a perimeter drive in 18 per cent of the time.'],
    ['Map criteria', '3 of 4 pass or near', 'Unclassified 73.0 / 78.3 / 84.6 per cent against 50. Denominator is the whole allocated grid, which overstates it.'],
    ['Scan matching', '16.2 mm vs 206.7 mm', 'Same wheels, same scans, matcher off vs on. Bounded to this scanner, this config, three routes, two of them circles.'],
    ['Photogrammetry', '3.85 and 4.49 deg vs 0.03 deg', 'Instrument validated to about 1 degree. Narrowed to scale error or rigid all-wheel slip; elimination not exhaustive.'],
    ['Autonomous navigation', '3 goals, 3 trials, all reached', '**Inside a live mapping session, not against a saved map.** 5.5 and 3.7 deg heading hold, 4.6 cm stopping error.'],
  ],
  [0.2, 0.22, 0.58],
),

h2('Strand two, in six numbers'),

gap(60),
table(
  ['', ''],
  [
    ['Deployment', '4 zones, 2 radio-isolated installations, 1 database'],
    ['Channels', 'Wi-Fi every 5 s, radio every 30 s at 240 bytes, cellular on breach and every 30 min'],
    ['Control law', 'Lamp on above gas index 200, off below 150; fan ramped half to full across 200 to 500'],
    ['Alert thresholds', '38 C, 1200 ppm CO2, gas index 200, 55 ug/m3 PM2.5'],
    ['Recovery', 'Automatic after power interruption, without intervention'],
    ['Outstanding', 'Two physical calibrations: reference gas, reference radiometer at fixed geometry'],
  ],
  [0.22, 0.78],
),

h2('Strand three, in six numbers'),

gap(60),
table(
  ['', ''],
  [
    ['Sector size', 'Over 22 million people; more than 26,800 incidents a year; nearly 70 per cent unorganised'],
    ['Conditions', '10 to 12 hour shifts, routinely above 40 degrees C'],
    ['Contact benchmark', '87.9 per cent accuracy, leave-one-subject-out, 35 participants'],
    ['Driver benchmark', '82 per cent, thermal facial imaging, simulator'],
    ['Capture', 'One fixed node, 2.5 to 3.5 m up, working at 1 to 5 m, one person per crossing'],
    ['Field target', '30 to 50 workers, several shifts, non-air-conditioned warehouse'],
  ],
  [0.22, 0.78],
),

h2('The eight sentences'),

gap(60),
good('SAY THESE, VERBATIM IF YOU CAN', [
  '**1.** "Only the yaw column of the transformation changes. That is the whole of the difference and the whole of the risk."',
  '**2.** "The feedforward supplies most of the drive; the PID corrects only what the feedforward gets wrong. That is why the integral gain can be 250."',
  '**3.** "The deployed proportional gain is right. The argument that originally justified it rested on a number that was wrong by a factor of two, and the report records it as such."',
  '**4.** "Coverage accumulates through translation, not rotation. The robot classifies what it drives past, and the room is a few metres across."',
  '**5.** "Scan matching was measured against wheel odometry rather than assumed better. A front end that corrects at a fixed odometric interval is responding to a schedule, not to disagreement between scans."',
  '**6.** "Three estimates agreeing with one another while all three disagree with the floor is the signature of an error they share."',
  '**7.** "The inertial sensor is absent by decision, not by omission. It is the right next purchase, and the claim is only about order of work."',
  '**8.** "An absence of penalty across a year of measurement is not the same thing as a measured cost of zero. Objective 3 stays open until a matched symmetric baseline exists."',
]),

h2('The three habits'),

gap(60),
note('WHAT THE PANEL IS ACTUALLY MARKING', [
  '**Evidence grading.** Every number arrives with how it was obtained. Measured on this robot, checked against an independent implementation, reasoned but not tested, or not yet done. Four different grades, and saying which one you are using is worth more than the number.',
  '**Qualifiers survive.** "Below 1 per cent out to about 10 m" never shortens to "below 1 per cent". "Demonstrated inside a live mapping session" never shortens to "demonstrated".',
  '**Failures are results.** Scan matching making things worse, the proportional-gain argument collapsing, the coverage criterion failing: each one is a measurement with a diagnosed mechanism. Lead with them rather than being led to them.',
]),

gap(),
p('Last thing. If you do not know, say you do not know, and then say what measurement would find out. That answer is never wrong, and on this project it is almost always available, because the open items all have a named next step.'),

];
