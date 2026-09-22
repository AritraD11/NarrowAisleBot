const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 5  Where the gain values came from'),

p('"Why 45, 250 and 0.5?" is the single most likely technical question in the viva, because it is the one place where a candidate either has a derivation or has been turning knobs. This project has a derivation, and it also has an honest story about the one gain where the derivation failed. Both are worth telling.'),

h2('5.1  The method: direct synthesis, not trial and error'),

p('The feedforward fit does something useful beyond supplying drive: it hands over the plant\'s **DC gain** directly. The plant is the motor plus gearbox plus wheel, treated as a black box.'),

eq('K  =  1 / Kff  =  1 / 38  =  0.0263 rad/s per drive count'),

p('Read that as: one extra drive count buys 0.0263 rad/s of steady-state speed.'),

p('For a first-order plant, direct-synthesis tuning (also called lambda tuning) gives both gains in closed form:'),

gap(60),
eq('Ki  =  1 / ( K * lambda )'),
eq('Kp  =  tau * Ki'),
gap(60),

p('where **lambda** is the closed-loop time constant you _choose_ (how fast you want the loop to respond) and **tau** is the plant\'s own mechanical time constant (how fast the motor physically can respond).'),

gap(60),
good('THE USEFUL PROPERTY, AND THE REASON THIS WORKED', [
  '**Ki does not contain tau.** It follows from K and lambda alone, and both of those were known: K from the feedforward fit, lambda by choice. So the integral gain could be computed correctly long before anybody had measured the motor\'s time constant.',
  'Kp is the one that needs tau, and tau was the number nobody had. That is the whole shape of the story in 5.3.',
]),

h2('5.2  Computing Ki'),

p('The choice of lambda is the engineering judgement. It was set to **0.15 s**, which is fifteen control periods at 100 Hz. That is deliberately conservative: you want the closed loop comfortably slower than the sampling rate, or the controller is trying to react to things it cannot see properly.'),

eq('Ki  =  1 / ( 0.0263 x 0.15 )  =  253'),

p('The deployed value is **250**, rounded. Nothing more than that: 253 is not more accurate than 250 given an 8 per cent fit band.'),

gap(60),
note('IF ASKED "WHY 0.15 AND NOT SOMETHING ELSE?"', [
  'Smaller lambda means a faster closed loop, and a larger Ki. Faster sounds better until the loop starts chasing noise and fighting the unmodelled lag. Fifteen control periods is a standard conservative choice and it leaves margin for the plant being different under load, which it is: on the ground K drops, which by the same formula means Ki should rise. That re-derivation on the floor is listed as outstanding work.',
]),

h2('5.3  Kp, and the part of the argument that did not survive'),

p('Tell this story properly. It is the strongest methodological moment in the control chapter, and trying to hide it would be both dishonest and worse for your marks.'),

h3('Step one: the assumption'),

p('`Kp = tau x Ki` needs tau, the plant\'s mechanical time constant. It had never been measured on this machine, because **every bench run to that point had logged steady-state points and no transients**. You cannot get a time constant from steady-state data; a time constant is entirely a property of the transient.'),

p('So a value was assumed: **tau = 0.18 s**, on the grounds that it is plausible for a 100 W motor behind a 47:1 planetary gearbox. That gives:'),

eq('Kp  =  0.18 x 250  =  45'),

p('And the report says plainly that this is the one quantity in the loop that is an estimate rather than a fit.'),

h3('Step two: the measurement'),

p('Later, plant identification was run properly: six open-loop drive steps per motor at plus and minus 70, 110 and 160 counts, wheels in the air, 1251 samples logged at 50 Hz.'),

gap(60),
table(
  ['Motor', 'K measured (rad/s per count)', 'tau, all six steps', 'tau, excluding the smallest step'],
  [
    ['FR', '0.02442', '0.089 s', '0.089 s'],
    ['FL', '0.02306', '0.089 s', '0.089 s'],
    ['RR', '0.02428', '0.103 s', '0.092 s'],
    ['RL', '0.02386', '0.103 s', '0.092 s'],
  ],
  [0.16, 0.3, 0.26, 0.28],
),

gap(),
p('**tau is about 0.09 s, half what had been assumed.** By the same formula, that calls for:'),

eq('Kp  =  0.09 x 250  =  about 22'),

gap(60),
warn('ONE MEASUREMENT WAS EXCLUDED, AND THE REASON IS STATED', [
  'RR and RL both show tau = 0.154 s at their smallest step (drive count 70), an outlier that neither front motor reproduces at the same step. Drive count 70 sits closest to the breakaway threshold, where a first-order-lag fit is least trustworthy.',
  'Dropping that one step per motor collapses the front-to-rear split from 0.103 s to 0.092 s and leaves all four motors at 0.089 to 0.092 s, which is the physically simpler result: **one drivetrain, one tau**, not a real front-to-rear mechanical difference.',
  'The excluded point was kept in the data file rather than discarded, so the next person to run the test can decide for themselves whether they agree. Say that if challenged on the exclusion; it is the right answer.',
]),

h3('Step three: the prediction, registered in advance'),

p('Before flashing anything, a prediction was written down: both candidate values, 22 and 26, should settle faster than the shipped 45, with overshoot flat or reduced and no new saturation, since a Kp moved toward the true tau is supposed to help rather than trade against something.'),

h3('Step four: the prediction was wrong, and cleanly so'),

p('Three gain sets were swept against each other, four setpoints (1.00, 2.00, 3.00, 4.50 rad/s) times four motors times three gain sets, 48 rows.'),

gap(60),
table(
  ['Gain set', 'Mean overshoot (rad/s)', 'Against the baseline'],
  [
    ['**Kp = 45 (shipped)**', '**0.107**', 'baseline'],
    ['Kp = 22', '0.164', '+54 per cent worse'],
    ['Kp = 26', '0.153', '+43 per cent worse'],
  ],
  [0.35, 0.3, 0.35],
),

gap(),
p('**Kp = 45 posted the lowest overshoot in 16 of 16 rows.** Not a majority: all of them. Steady-state error moved the other way (45: 0.009, 22: 0.005, 26: 0.006 rad/s mean), but every one of those numbers sits below the 0.003 to 0.007 rad/s encoder velocity quantum, so that difference is noise floor, not signal.'),

h3('Step five: why the theory failed here'),

p('This is the explanation to have ready, and it is reasoned from the data rather than separately measured, which you should say.'),

p('The formula `Kp = tau x Ki` comes from pole-zero cancellation on the **bare plant**: the controller\'s zero is placed exactly on top of the plant\'s pole so they cancel.'),

gap(60),
good('BUT THIS CONTROLLER DOES NOT COMMAND A BARE PLANT', [
  'The two-term feedforward supplies most of the drive the instant a setpoint changes. So the closed-loop Kp term\'s real job here is **damping the transient around that feedforward jump**, not cancelling a pole the feedforward has already largely pre-compensated.',
  'Lowering Kp weakens exactly that damping. The sweep shows the result directly: more overshoot, not less.',
  'Honest caveat to volunteer: this explanation has not been tested against a Kp sweep with the feedforward disabled, so it is reasoned from the data in front of it, not itself a measured result.',
]),

h3('Step six: the decision'),

p('**Kp stays at 45. Nothing was flashed.** The objective closes as _confirmed_, not as _changed_. Both are legitimate outcomes of the same measurement, and this project\'s standing rule is to report whichever one the data actually gives.'),

gap(60),
note('THE SENTENCE FROM THE REPORT, WORTH QUOTING VERBATIM', [
  '"This is the least satisfying part of the tuning and it is recorded as such: the deployed gain is right, but the argument that originally justified it turned out to rest on a number that was wrong by a factor of two."',
  'Delivering that line yourself, before anyone asks, is worth more than any polished answer you could give afterwards.',
]),

h2('5.4  A bug found in the measuring tool, in the same session'),

p('Worth knowing because it shows the difference between a result and an artefact.'),

p('Every row in the sweep printed `settle(s): none`, for all three gain sets, at every setpoint. That looks like a finding. It was not.'),

p('**Root cause:** the settling-time function\'s pass condition was "never leaves the band again", checked against the _entire remaining run_ rather than the window belonging to that step. So a later setpoint, or the run\'s own final return to zero, always eventually pulled the signal back out of band. The check was **structurally guaranteed to fail** regardless of the gains.'),

p('Fixed by windowing the series to each step\'s own end time before the check. Overshoot and steady-state error were computed correctly throughout and are unaffected; only the settle-time column was silent. The overshoot result above is unambiguous on its own, which is why the sweep did not need re-running.'),

gap(60),
good('THE GENERAL LESSON, AND IT APPLIES TO SLAM TOO', [
  'A measurement that always returns the same answer regardless of the input is not a measurement. It is a broken instrument. This project hit the same class of problem three separate times: this settling-time check, the dashboard syntax error that took a whole page offline while every server-side signal said "fine", and a scan-matching front end whose corrections fired on a fixed schedule rather than in response to the scans.',
]),

h2('5.5  Air values versus ground values, and the headroom problem'),

p('Every gain above is an **air value**: measured with the wheels off the ground. The report is explicit that ground calibration is outstanding, and there is one consequence that is genuinely a safety-of-operation issue rather than a refinement.'),

h3('The velocity ceiling arithmetic'),

p('The wheel speed ceiling is 5.20 rad/s. Work out what the worst motor needs at that speed:'),

eq('38.4 x 5.20  +  8  =  208 drive counts'),

p('Out of 255 available. That leaves 47 counts, about **18 per cent of the range, as authority for the feedback terms**. That is the margin the P, I and D terms have to work within.'),

gap(60),
bad('NOW APPLY THE MEASURED GROUND LOAD', [
  'Ground load raises the feedforward demand by a measured mean of **24 per cent**. Apply that to 208 counts and the feedforward alone wants about 258, which is more than the output range. The controller would have **nothing left to regulate with**: it would sit saturated at full drive, the integral would be clamped at its limit, and the loop would effectively be open.',
  'The documented fix is to lower the ceiling to roughly **4.2 rad/s** before serious floor work, and to re-measure the feedforward under load. Note that this is not the operating limit the robot actually drives at (0.12 m/s linear, 0.30 rad/s yaw, which is far below the ceiling), so the machine has not been run in this condition. But the ceiling is the number that would let it happen, and it is listed as outstanding.',
]),

h3('The largest demand actually observed'),

p('For balance, quote the measured figure alongside the worst case: the largest drive demand observed at the operating velocity limit was **131 of 255**, leaving about 49 per cent of the commanded range unused under the tested condition.'),

p('And immediately qualify it, the way the report does: that is headroom **in the command**, not a measurement of torque or traction reserve. It bounds what the controller was asked for, not what the drivetrain could deliver.'),

h2('5.6  The result the controller actually achieves'),

gap(60),
table(
  ['Condition', 'Per-wheel RMS error', 'Samples', 'Saturation'],
  [
    ['Wheels free of the ground', '0.040 to 0.047 rad/s', '26,468 over three bench runs', '0.0 per cent'],
    ['Under full chassis weight', '0.066 to 0.074 rad/s', '35,248 over three floor runs', '0.0 per cent'],
  ],
  [0.3, 0.26, 0.28, 0.16],
),

gap(),
p('The two conditions are reported separately because the figures differ by about half. The loaded figure is the one that matters operationally. The unloaded figure is reported because it **separates the controller from the wheel-ground interaction**, which is the only way to say whether a given error belongs to the loop or to the floor.'),

p('One step response, for the concrete picture: on the largest commanded step in a bench run, the wheel reaches within 5 per cent of the commanded -2.207 rad/s in **0.20 s**, overshoots by **3.5 per cent**, and then holds the level to a mean offset of **0.003 rad/s**.'),

gap(60),
good('HOW TO SUMMARISE THE WHOLE CONTROL LAYER IN ONE BREATH', [
  '"Four independent loops at 100 Hz. A two-term feedforward, fitted against three campaigns rather than tuned, supplies most of the drive. The integral gain follows from direct synthesis and closes the residual in about 0.4 s. The proportional gain is confirmed rather than derived, because the derivation rested on a time constant that turned out to be wrong by a factor of two, and a closed-loop sweep kept the shipped value on evidence. The result tracks to 0.066 to 0.074 rad/s under chassis weight with no channel ever saturating."',
]),

];
