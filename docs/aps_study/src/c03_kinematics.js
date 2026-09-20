const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 3  Kinematics, in plain language'),

p('Kinematics is the dictionary between two languages. One language is what you want the robot to do, spoken as three numbers. The other is what the four wheels must do, spoken as four numbers. Nothing here involves forces, masses or motors: kinematics is pure geometry.'),

h2('3.1  The three numbers that describe any motion on a flat floor'),

p('A rigid body moving on a plane has exactly three degrees of freedom, and there is no fourth.'),

bullet('**u**, forward velocity, in metres per second.'),
bullet('**v**, lateral (sideways) velocity, in metres per second.'),
bullet('**omega**, yaw rate, how fast the body is spinning about its own centre, in radians per second.'),

p('Together these three are called the body twist. A differential-drive robot can only produce two of them (forward and yaw) and is therefore called non-holonomic: it cannot move in a direction it is not pointing. A mecanum robot can produce all three independently and is holonomic. That is the whole reason it is here.'),

h2('3.2  Inverse kinematics: from what you want to what the wheels must do'),

p('Inverse kinematics takes the three body numbers and gives you the four wheel speeds. For this platform:'),

gap(60),
eq('omega_FR = (1/r) ( u + v + omega * Ko )'),
eq('omega_FL = (1/r) ( u - v - omega * Ki )'),
eq('omega_RR = (1/r) ( u - v + omega * Ki )'),
eq('omega_RL = (1/r) ( u + v - omega * Ko )'),
gap(60),

p('Read those four lines column by column rather than row by row, because that is where the structure is.'),

bullet('**The u column.** Every wheel has a `+u`. Tell the robot to go forward and all four wheels turn the same way. Obvious, and identical on a symmetric platform.'),
bullet('**The v column.** The signs alternate: `+ - - +`. Tell the robot to strafe right and one diagonal pair turns forward while the other turns backward. The forward components cancel, the sideways roller components add, and the robot slides. Also identical on a symmetric platform.'),
bullet('**The omega column.** Here is the asymmetry. `+Ko`, `-Ki`, `+Ki`, `-Ko`. Two wheels use the long lever arm and two use the short one.'),

gap(60),
good('THE SENTENCE THAT EARNS THE MARK', [
  '"The translation terms are identical between the symmetric and the non-collinear layouts, which is why forward and lateral motion feel the same on either machine. **Only the yaw column changes.** That is the whole of the difference, and it is also the whole of the risk, because a wheel driven with the wrong lever arm produces a yaw rate wrong by 14 per cent and nothing else in the transformation gives any sign of it."',
]),
gap(),

p('The practical warning that follows: substituting a single shared coefficient anywhere in the software reduces the machine, in that code path alone, to an ordinary symmetric mecanum platform. That is not a hypothetical. It happened in the early Wi-Fi joystick firmware, which is one of the reasons that path was removed.'),

h2('3.3  Forward kinematics and odometry: from what the wheels did to where you are'),

p('Run the dictionary the other way. Measure the four wheel speeds with the encoders, invert the system above, and you recover the three body numbers. Integrate those over time and you get a position and a heading. That is wheel odometry.'),

gap(60),
analogy([
  'Walking across a dark room counting your steps. You know your stride length, so after 40 steps forward and 10 steps to the left you can say roughly where you are. You are not looking at anything; you are adding up what your legs did.',
  'It works beautifully at first and gets worse the further you walk, because every step carries a small error and the errors add up and never cancel. That is dead reckoning, and it is exactly what wheel odometry is.',
]),
gap(),

p('Two things make it worse on a mecanum base than on a normal robot. First, the rollers are designed to slip sideways, so the relationship between wheel rotation and ground travel is not exact by construction. Second, there are four wheels contributing rather than two, so there are four places for the error to enter.'),

p('This project measured the mecanum penalty directly. Driving 1.00 m forward read 1.009 m in the odometry, a 0.9 per cent error, which is accurate. Driving 1.00 m sideways read **1.245 m**, twice, 3 mm apart. The wheels genuinely turned that far; the chassis simply did not travel that far, because the rollers scrubbed. A correction factor of 0.92 is applied to the lateral term for that reason, and the report is careful to call it an empirical constant for one floor rather than a model.'),

h2('3.4  The free observable, and why it is worth less than it first looks'),

p('This is a genuinely novel piece of the work and it is easy to overstate, so learn the careful version.'),

p('Look again at the four inverse-kinematic rows. The first and fourth (FR and RL) share the same translational combination `u + v`. The second and third (FL and RR) share its complement `u - v`. That means you can take the difference within each diagonal pair and the translation cancels, leaving only yaw:'),

gap(60),
eq('omega_outer_estimate  =  r ( omega_FR - omega_RL ) / ( 2 Ko )'),
eq('omega_inner_estimate  =  r ( omega_RR - omega_FL ) / ( 2 Ki )'),
gap(60),

p('So the robot has two independent estimates of its own yaw rate, from two disjoint pairs of wheels, with no extra sensor at all. The **mean** of the two is what gets published as the yaw rate. The **difference** is a residual: if the drivetrain were perfect, it would be exactly zero, so whatever is left is a measure of something being wrong.'),

gap(60),
analogy([
  'Two people independently counting the crowd at a gate. If both say 400, you believe it. If one says 400 and the other says 460, you do not know which is right, but you do know something is off. The published number is the average; the disagreement is the alarm.',
]),
gap(),

h3('Now the honest qualifications, which are the part that scores'),

num('**It is not a calibrated measurement of slip.** Unequal effective wheel radii, encoder scale error, backlash and mechanical compliance all contribute to the same residual. Separating them needs an external reference.'),
num('**The two estimates are not statistically independent.** A disturbance that hits both pairs enters both estimates.'),
num('**The asymmetry does not create the observable.** What makes them separate estimates is that they come from _disjoint pairs of wheels_, and a symmetric platform has disjoint pairs too. A symmetric mecanum platform carries a residual of exactly the same algebraic form, and it does not vanish there either once slip and measurement error are present.'),

p('So what does the asymmetry actually change? The **weighting**. Write each measured pair difference as its ideal value plus an error term, and the residual comes out as:'),

eq('e_omega  =  (r/2) ( delta_outer / Ko  -  delta_inner / Ki )'),

p('On a symmetric platform Ko and Ki are equal, the two error terms enter with identical weight, and any component common to both pairs **cancels exactly**. Here they enter with different weights, so a common-mode component survives, scaled by:'),

eq('(r/2) ( 1/Ko - 1/Ki )  =  0.0097'),

gap(60),
good('THE CAREFUL CLAIM', [
  '"The asymmetry does not create the observable. It makes the residual sensitive to a class of error that a symmetric layout cancels, at roughly one per cent of the magnitude of that error. Whether that sensitivity is useful for drivetrain diagnostics is a question for measurement rather than for algebra."',
  'Say it that way. If you claim the asymmetry gives you a slip sensor, a good examiner will derive the symmetric case on the board and you will be in trouble.',
]),

h3('What the residual actually did'),

p('Evaluated across four analysed drives, one of them a deliberately irregular trajectory rather than a clean circuit:'),

gap(60),
table(
  ['Statistic', 'Value', 'Reading'],
  [
    ['Median while moving', '0.035 rad/s', 'The normal disagreement between the two pairs.'],
    ['95th percentile', '0.111 to 0.124 rad/s', 'Across the four drives.'],
    ['Worst instantaneous value', '0.354 rad/s', 'A single sample, on the irregular drive.'],
    ['Episode threshold', '0.5 rad/s', 'Never crossed by any sample in any of the four drives.'],
  ],
  [0.3, 0.26, 0.44],
),

gap(),
p('Two caveats to volunteer. The 0.5 rad/s threshold is the **default of the analysis tool**, not a value derived from this drivetrain, and it was fixed before the drives were analysed rather than chosen afterwards. It sits about four times the observed 95th percentile, so it detects gross events and would not resolve a slow systematic drift. And the whole measure is **blind to a slip mode in which all four wheels slip together**, because then both pairs are equally wrong and the difference stays small. That blindness is exactly the gap the photogrammetry result in Part 5 walks into.'),

h2('3.5  The 20,000-case test, and what it does and does not prove'),

p('The implemented forward-kinematic transformation was checked against independently generated reference twists across twenty thousand simulated cases. The round trip reproduces them to a worst case of **2.22 x 10^-16**, which is machine epsilon for double-precision arithmetic.'),

p('Similarly, position was recomputed offline from the raw encoder record for a complete drive and compared against the estimate the robot published live. They diverge by at most **0.0054 m** at any point and by **0.0000 m** at the end.'),

gap(60),
table(
  ['What these two checks establish', 'What they do NOT establish'],
  [
    ['The transformation is coded correctly and contributes no numerical error of its own.',
     'Anything about the physical wheel-ground model. The equations could be perfectly implemented and still describe a robot that does not exist.'],
    ['The online and offline implementations are numerically consistent, which rules out a discrepancy between them as the source of the observed drift.',
     'An error shared by both. They integrate the same measurements through the same model, so a wrong wheel radius or a wrong encoder constant would pass this test untouched.'],
  ],
  [0.5, 0.5],
),

gap(),
warn('THE QUESTION YOU WILL BE ASKED', [
  '"Your kinematics are exact to 10^-16 but your robot drifts by centimetres. Explain."',
  'Answer: those measure two completely different things. 10^-16 says the arithmetic is right. The drift is in the **physics**: the wheel radius is not exactly 0.0762 m under load, the rollers slip, the floor is not uniform. A correct model of a slightly different robot. Separating the two is exactly why the report checks them separately, and why the floor measurements exist at all.',
]),

];
