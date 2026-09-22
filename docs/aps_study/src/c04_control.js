const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 4  Wheel control: feedforward and PID, from first principles'),

p('This is the longest part of this document, because it is the layer everything else is built on, and because it is the layer a panel can interrogate most deeply. The whole chapter answers one question: **when the software says "turn at 2.0 rad/s", how does the wheel actually end up turning at 2.0 rad/s?**'),

h2('4.1  The problem: a command is not an obedience'),

p('The ESP32 does not speak to the motor in rad/s. It speaks in a **drive count**, a number from 0 to 255 that sets how hard the driver pushes current through the motor. (It is a PWM duty cycle: 255 means the supply is connected to the motor all the time, 128 means about half the time, and the motor\'s own inductance smooths that into an average.)'),

p('So the controller\'s entire job is a translation problem: given a wanted speed in rad/s, choose a number between -255 and +255.'),

p('And that translation is not fixed. It changes with:'),

bullet('**Load.** The same drive count produces a different speed with the wheels in the air than with 45.54 kg pressing them onto the floor. This project measured the difference: about 24 per cent more drive needed on the ground, on average.'),
bullet('**Speed itself.** Getting a stationary wheel to start moving needs more push per unit of speed than keeping a moving wheel going. That is static friction.'),
bullet('**Which motor.** Four nominally identical motors are not identical. Measured spread here: 3 per cent.'),
bullet('**Battery voltage, temperature, the patch of floor, and the direction of travel.**'),

gap(60),
analogy([
  'Driving a car up a hill you have never driven before. You want to hold 40 km/h. The accelerator pedal is your drive count; the speedometer is your encoder. You have two ways to do this.',
  '**Open loop:** press the pedal to where 40 km/h usually is, and never look at the speedometer. Fast to react, but wrong the moment the hill gets steeper.',
  '**Closed loop:** watch the speedometer and adjust. Always correct eventually, but always a little late, because you only move the pedal after you have already seen the error.',
  'A good driver does **both**: pedal roughly where experience says, then trim against the speedometer. That is exactly what this controller does, and the two halves have names: **feedforward** and **PID**.',
]),

h2('4.2  The structure: feedforward first, then three corrections'),

p('The loop runs at 100 Hz on the ESP32, one completely independent loop for each of the four wheels. Every 10 ms, for each wheel, the firmware does this:'),

gap(60),
code([
  '  pwm  =  FEEDFORWARD (from the commanded speed alone)',
  '       +  P  x  error',
  '       +  I  x  (accumulated error)',
  '       +  D  x  (rate of change of measurement)',
]),
gap(60),

p('The crucial sentence, and it is the one to memorise for the viva:'),

gap(60),
good('WHY THE STRUCTURE MATTERS', [
  '"The feedforward supplies most of the drive from the commanded velocity alone, and the three feedback terms correct only what the feedforward gets wrong. That separation is what permits the integral gain to be as large as it is without the loop becoming oscillatory."',
  'On a bare PID with no feedforward, the integral term has to build up the **entire** drive from zero every time. That takes time and a large integral gain would make it violently unstable. Here, the integral is trimming a small residual, so a gain that would be reckless on a bare loop is appropriate.',
]),
gap(),

p('Why four independent loops rather than one controller for the whole robot: because each wheel has its own friction, its own encoder, its own load and its own driver channel. A single controller would have to average them, and averaging is exactly what you must not do on a mecanum base, where an error on one wheel becomes an unwanted body motion rather than a slower body motion.'),

h2('4.3  Feedforward: the experienced driver'),

p('Feedforward means: from the speed you _want_, predict the drive count you will _need_, before measuring anything. It is the pedal position from experience.'),

h3('Why a single straight line does not work'),

p('The obvious model is `pwm = Kff x omega`: double the wanted speed, double the drive. Fit one number and you are done.'),

p('The raw data says that is wrong, and it says so **before any fit is attempted**. The ratio of drive command to resulting wheel speed _rises as speed falls_. At 1.50 rad/s the ratio is higher than at 2.77 rad/s. A straight line through the origin cannot reproduce that, because a straight line through the origin has a constant ratio by definition.'),

gap(60),
analogy([
  'Pushing a heavy crate across a floor. Getting it to **start** moving takes a big shove. Once it is sliding, keeping it going takes much less. The extra effort at the start is static friction, sometimes called breakaway or Coulomb friction, and it does not scale with speed: it is a fixed lump you have to pay to get moving at all.',
  'A model that only says "effort is proportional to speed" charges nothing for starting, so it always under-drives at low speed.',
]),
gap(),

h3('The two-term model actually used'),

eq('pwm_ff  =  Kff * omega   +   Kstat * sign(omega)'),

bullet('**Kff** is the viscous, speed-proportional term. It covers everything that gets harder the faster you go: back-EMF in the motor, viscous drag in the gearbox.'),
bullet('**Kstat** is the static, breakaway term. It is a fixed lump, and it carries the **sign** of the command so it pushes in whichever direction you asked for.'),

p('The fitted values, per motor:'),

gap(60),
table(
  ['Motor', 'Kff (counts per rad/s)', 'Kstat (counts)', 'Relative speed at matched drive'],
  [
    ['FR (front right)', '**37.3**', '8.0', '1.018'],
    ['FL (front left)', '**38.4**', '8.0', '0.990'],
    ['RR (rear right)', '**38.3**', '8.0', '0.992'],
    ['RL (rear left)', '**38.0**', '8.0', '1.000'],
  ],
  [0.3, 0.26, 0.2, 0.24],
),

gap(),
p('A 3 per cent spread across the four. Read that as a good sign: four nominally identical gearmotors behaving nearly identically means the drivetrain is healthy and the measurement is trustworthy. An earlier firmware shipped a 19 per cent spread, and that turned out to be an artefact of the faulty feedback path before the front-rear encoder cross-connection was found, not a real property of the motors.'),

p('`Kstat` is one number for all four because nothing in the available data distinguishes them. The test that would give per-motor breakaway values is a staircase test (step the drive up from rest in increments of 2 until each wheel breaks away) and it has not been run. Say that if asked; it is the honest state.'),

h3('How the fit was made: three campaigns, not one'),

p('This is a methodology point worth making, because fitting to a single dataset is exactly how you fool yourself.'),

gap(60),
table(
  ['Source', 'What it was', 'Confidence'],
  [
    ['Campaign A', 'A manual drive logged at steady state. All four motors converge to a 1.83 to 1.94 rad/s band at drive count 80. Mean 1.885 rad/s.', '**Highest.** Reported while running, so it is true steady state.'],
    ['Campaign B', 'An automated test sweeping demand in 1.5 s windows at drive count 110. Overall mean 2.621 rad/s.', 'Good for the **relative** comparison between motors (identical window for all four). Only approximate in absolute terms, because the window starts from rest and therefore includes spin-up, so it under-reads true steady state.'],
    ['Campaign C', 'A back-calculation from an earlier closed-loop run at 0.6 to 2.2 rad/s.', '**Lowest** (this was the campaign with the encoder faults). But it carries one piece of information nothing else does: the drive-per-speed ratio is higher at low speed, which is the evidence for the static term.'],
  ],
  [0.12, 0.52, 0.36],
),

gap(),
p('Fitting Kff around 38 and Kstat around 8 against all three:'),

gap(60),
table(
  ['Wanted speed (rad/s)', 'Model predicts', 'Actually measured', 'Error'],
  [
    ['1.50', '65.0', '70.4', '-8 %'],
    ['**1.885**', '**79.6**', '**80**', '**-0.5 %**'],
    ['**2.621**', '**107.6**', '**110**', '**-2 %**'],
    ['2.77', '113.3', '120', '-6 %'],
  ],
  [0.28, 0.22, 0.25, 0.25],
),

gap(),
p('Every measured point inside 8 per cent, and the two high-confidence points inside 2.2 per cent. The residual error is exactly what a correctly tuned integral term is for, and at the deployed integral gain that 8 per cent gap closes in about 0.3 s.'),

gap(60),
warn('THE HONEST LIMITATION, AND VOLUNTEER IT', [
  'The **split** between Kff and Kstat is not well determined by this data. Every measurement sits between 1.8 and 2.8 rad/s, and over that narrow span many pairs fit almost equally well. A fit with Kff = 34.5 and Kstat = 15 is barely distinguishable from Kff = 38 and Kstat = 8.',
  'What **is** well determined is the value of the whole expression across the measured range, and that is what the controller actually consumes. Separating the two properly needs the staircase test, which has not been run.',
  'Also: above about 3 rad/s the model extrapolates, and it will over-predict near the top of the range because the motor approaches its rated 60 rpm and stops behaving linearly. Over-prediction is the **safe** direction: the output saturates and the integral unwinds it, rather than the wheel coming up short.',
]),

h3('The fade-in, a small detail with a real reason'),

p('If the static term were applied as a step at any non-zero command, then asking for 0.001 rad/s would produce an instant 8-count jump at the output. Instead, `Kstat` is faded in linearly across 0.05 to 0.20 rad/s:'),

code([
  'static inline float feedforward(int idx, float w) {',
  '    float aw = fabsf(w);',
  '    float ff = Kff[idx] * w;',
  '    if (aw > KSTAT_FADE_LO) {',
  '        float fade = (aw - KSTAT_FADE_LO) / (KSTAT_FADE_HI - KSTAT_FADE_LO);',
  '        if (fade > 1.0f) fade = 1.0f;',
  '        ff += Kstat[idx] * fade * (w > 0 ? 1.0f : -1.0f);',
  '    }',
  '    return ff;',
  '}',
]),

gap(60),
p('So a very small commanded velocity does not produce a discontinuity in the drive. In a narrow aisle, where the robot is often making tiny corrective moves, that discontinuity would show up as a jerk.'),

h2('4.4  P, the proportional term: the spring'),

p('`P` looks at the error right now (wanted speed minus measured speed) and pushes in proportion to it.'),

eq('p_term  =  Kp * error        with Kp = 45'),

gap(60),
analogy([
  '**A spring.** Pull it 1 cm and it pulls back a little. Pull it 10 cm and it pulls back ten times as hard. The further you are from where you should be, the harder the correction.',
  'Everyone understands the appeal, and everyone runs into its two limitations.',
]),
gap(),

h3('What Kp = 45 means in real units'),

p('Suppose the wheel is running 0.1 rad/s slower than commanded. Then:'),

eq('p_term  =  45 x 0.1  =  4.5 drive counts of extra push'),

p('That is the instant, proportional response. It is applied within the same 10 ms tick that the error appeared.'),

h3('The two problems with P alone'),

num('**P alone leaves a permanent error.** This is the one people find surprising, so understand it properly. The P term produces output _only when there is an error_. If the error were ever zero, the P term would be zero, so there would be no push at all, so friction would slow the wheel and the error would come back. The loop settles at whatever small error produces exactly enough push to balance the losses. That permanent leftover is called steady-state error or **droop**. On this robot the feedforward mostly hides it, which is another reason the feedforward earns its place.'),
num('**P alone overshoots and can oscillate.** Raise Kp to kill the droop and the correction becomes so aggressive that the wheel shoots past the target, then gets pushed back hard, then shoots past the other way. A spring with no damping rings.'),

h2('4.5  I, the integral term: the stubborn assistant'),

p('`I` adds up the error over time and pushes based on the total. Even a tiny error, if it persists, eventually accumulates into a large correction.'),

eq('integral += error * dt          (dt = 0.01 s)'),
eq('i_term  =  Ki * integral        with Ki = 250'),

gap(60),
analogy([
  '**A stubborn assistant with a notebook.** Every 10 ms she writes down how far short you are. She does not care that today\'s shortfall is small; she cares that you have been short for a while. The longer the error lasts, the more insistently she pushes.',
  'Her job is the one P cannot do: **eliminate the permanent error**, because the only state in which her notebook stops growing is the state where the error is genuinely zero.',
]),
gap(),

h3('Why Ki = 250, and why the previous value of 30 was the real bug'),

p('This is the single biggest change in the deployed firmware and the best worked example in the project. Do the arithmetic out loud in the viva; it is simple and it is convincing.'),

p('**At the old Ki = 30.** A tracking error of 0.1 rad/s moves the integral term by:'),

eq('30 x 0.1  =  3 drive counts per second'),

p('Now ask how long it takes to close a realistic feedforward gap of 10 drive counts. Three counts per second means **over three seconds**. And that is exactly what the logs showed: an air run in May settled in up to **3.79 s**. Three and a half seconds is an eternity inside a manoeuvre. What was actually settling the loop was mostly the proportional term, with the integral quietly and far too slowly absorbing the under-calibration.'),

p('**At the new Ki = 250.** The same 0.1 rad/s error moves the output by:'),

eq('250 x 0.1  =  25 drive counts per second'),

p('The same 10-count gap closes in **0.4 s**. Roughly a factor of eight faster, and it turns the integral from a term that was theoretically present into one that actually does work inside the time a manoeuvre takes.'),

gap(60),
good('THE ANSWER TO "WASN\'T THAT RECKLESS?"', [
  '"Raising a gain by a factor of eight at once is a large change, and it was only safe because of the feedforward. When the feedforward carries the bulk of the command, the integral is correcting a small residual rather than supplying drive from zero, so a gain that would be reckless on a bare loop is appropriate here."',
]),

h3('Integral windup, and the anti-windup that actually binds'),

p('Windup is the classic failure of an integral term, and this project has a good version of the story.'),

gap(60),
analogy([
  'The assistant keeps writing in her notebook even when you are physically unable to go faster. Imagine the wheel is jammed against a wall. The error never goes away, so the notebook fills with an enormous total. Then the wall is removed. The assistant now demands a correction proportional to that huge accumulated total, and the wheel leaps forward violently before the notebook can be unwound.',
]),
gap(),

p('**The old anti-windup did not work, and understanding why is instructive.** The previous firmware clamped the raw integral _state_ at plus or minus 200, with Ki = 30. Multiply them out:'),

eq('200 x 30  =  6000 drive counts of integral term, against an output range of 255'),

p('The clamp existed but could never bind. It permitted an integral term twenty-three times the entire output range. It was a safety feature that was, in practice, absent.'),

p('**The new anti-windup clamps against the authority genuinely left over.** By the time the integral is computed, the feedforward, the P term and the D term are all known, so the exact remaining headroom is known too. The integral is never allowed to accumulate past it:'),

code([
  'float base = m.ff_output + p_term + d_term;',
  '',
  'if (Ki > 1e-6f) {',
  '    m.integral += m.error * PID_DT;',
  '',
  '    float i_hi = ( (float)PWM_MAX - base) / Ki;',
  '    float i_lo = (-(float)PWM_MAX - base) / Ki;',
  '    if (i_lo > i_hi) { float t = i_lo; i_lo = i_hi; i_hi = t; }',
  '',
  '    m.integral = constrain(m.integral, i_lo, i_hi);',
  '    m.integral = constrain(m.integral, -INTEGRAL_ABS_MAX, INTEGRAL_ABS_MAX);',
  '    i_term = Ki * m.integral;',
  '}',
]),

gap(60),
good('THE TWO PROPERTIES THIS BUYS', [
  '**Windup is structurally impossible**, not merely bounded. The integral cannot reach a value that would demand more output than exists.',
  '**Recovery from saturation is immediate**, rather than waiting for the accumulated error to bleed back off. The moment the wheel can move again, the clamp releases and the term is already in range.',
]),

h2('4.6  D, the derivative term: the shock absorber'),

p('`D` looks at how fast the measured speed is _changing_ and pushes against it. It is a brake on rapid movement, regardless of which side of the target you are on.'),

eq('d_term  =  Kd * ( -d(measurement)/dt )        with Kd = 0.5'),

gap(60),
analogy([
  '**A shock absorber on a car.** The spring (P) decides where the car should sit. The shock absorber does not care about position at all; it resists **motion**. Without it a car with good springs bounces for ten seconds after every bump. With it, the bounce dies out in one.',
  'Here, the derivative term resists the wheel accelerating or decelerating fast, which is what damps the overshoot that P alone would produce.',
]),
gap(),

h3('Why Kd is small, and deliberately so'),

p('Against a genuinely first-order plant, a matched proportional-integral pair needs no derivative action at all. Everything this term is doing is damping lag that the first-order model does not contain: driver delay, compliance in the gearbox, and the velocity filter itself.'),

p('Work out what it is actually worth. At a typical step acceleration of about 30 rad/s squared:'),

eq('0.5 x 30  =  about 15 drive counts of damping'),

p('The previous firmware used Kd = 3.0, which would have applied **90 counts** at the same acceleration, actively fighting the acceleration the controller had just asked for. Reducing it by a factor of six is a real fix, not a cosmetic one.'),

h3('The two details that matter more than the value'),

p('**Detail one: the derivative acts on the measurement, not on the error.** This is important and is a common exam question.'),

p('The host computer sends stepped setpoints at 20 Hz. If you differentiate the _error_, then every setpoint step produces a derivative spike proportional to the size of the step, because the error jumps instantaneously even though nothing physical has happened yet. That spike is called **derivative kick**, and on this robot it would appear as a jolt at the start of every commanded move.'),

p('Differentiating the _measurement_ instead gives identical damping with no kick, because the measurement cannot jump: it is a physical wheel. The minus sign in the code preserves the correct sense:'),

code([
  'float raw_d = -(m.actual_velocity - m.prev_velocity) / PID_DT;',
]),

gap(60),
p('**Detail two: it is filtered, and more heavily than the velocity signal.** Differentiating amplifies noise: a small wobble in the measurement becomes a large wobble in its rate of change. So the derivative is passed through its own low-pass filter, heavier than the one on the velocity signal itself.'),

gap(60),
analogy([
  'Estimating how fast a queue is moving by watching only the last two people. If one person shuffles, your estimate swings wildly. Averaging over a few seconds gives a number you can act on. That averaging is the filter, and the derivative needs more of it than the raw speed does.',
]),

h2('4.7  Putting the three together, at one tick'),

p('Here is the whole tick, as the deployed firmware runs it, with the reasoning in place.'),

gap(60),
table(
  ['Step', 'What happens', 'Why'],
  [
    ['**0. At rest**', 'If the slewed target is below 0.01 rad/s, everything is held at zero: error, integral, derivative, output.', 'Coasting to a stop is kinder to the drivers and safer than active braking. The slew limiter has already walked the setpoint down before this point.'],
    ['**1. Feedforward**', '`ff = Kff * target + Kstat * sign(target)` (faded).', 'Supplies the bulk of the drive immediately, in the same tick the command arrives.'],
    ['**2. Error**', '`error = slewed_target - actual_velocity`.', 'Note it is the **slewed** target, not the raw command. The loop chases a reachable target, not an instantaneous jump.'],
    ['**3. P term**', '`45 * error`.', 'Proportional correction now.'],
    ['**4. D term**', '`0.5 * filtered(-d(measurement)/dt)`.', 'Damping, no kick, filtered.'],
    ['**5. I term**', 'Accumulate, then clamp against the headroom left after FF + P + D, then multiply by 250.', 'Kills steady-state error. Cannot wind up.'],
    ['**6. Output**', '`pwm = round(ff + p + d + i)`, clipped to plus or minus 255.', 'One number, sent to the driver.'],
  ],
  [0.14, 0.42, 0.44],
),

h2('4.8  The three arrangements that do more than the gains do'),

p('If you only have time to say one thing about tuning, say this: on this robot, three structural choices mattered more than the gain values.'),

h3('One: the slew limiter, 12 rad/s squared'),

p('Before the loop ever sees a command, the commanded velocity is walked toward the new target at no more than 12 rad/s per second:'),

code([
  'float step = max_wheel_accel * PID_DT;      // 12 * 0.01 = 0.12 rad/s per tick',
  'float diff = target - m.slewed_target;',
  'if      (diff >  step) m.slewed_target += step;',
  'else if (diff < -step) m.slewed_target -= step;',
  'else                   m.slewed_target  = target;',
]),

gap(60),
p('**Why.** A step command from the host would otherwise ask for an acceleration the hardware physically will not produce. Asking for the impossible is precisely the condition that drives an integrator into saturation in the first place. Limiting the setpoint is a cheaper and more reliable fix than trying to handle the saturation afterwards.'),

p('There is a second, subtler reason recorded in the firmware comment: the whole four-wheel set is snapshotted atomically against the serial parser running on the other CPU core. Without that, a command arriving mid-loop could be applied to two wheels this tick and two the next, which on a mecanum base is a momentary commanded twist that nobody asked for.'),

h3('Two: the minimum drive output, lowered from 15 to 5'),

p('Below a certain drive count the motor does not move, it just hums. The old firmware suppressed that by refusing to output anything below 15 counts.'),

gap(60),
bad('WHY THAT WAS A MISTAKE', [
  'It cut a **dead zone straight through the middle of the range in which the controller does its fine regulation**. When the feedforward has got the wheel nearly right, the correction the PID needs is small, often under 15 counts. The controller would ask for 8 counts, get 0, wait, ask for 20, get 20, overshoot, ask for 8, get 0, and so on. That is a **limit cycle**: the wheel hunts back and forth at low speed and never settles.',
  'With breakaway friction now handled properly by the static feedforward term, the threshold can sit at the level where the motor is genuinely silent, which is 5.',
]),

h3('Three: the dynamic integral clamp'),

p('Covered in 4.5. Repeated here because it belongs in this list: clamping against the leftover authority rather than a fixed bound is what made the anti-windup real.'),

h2('4.9  The velocity filter'),

p('The measured velocity is smoothed with a simple exponential filter, `VEL_FILTER_ALPHA = 0.4`. That means each new reading contributes 40 per cent and the running estimate keeps 60 per cent.'),

p('**Why it can stay this light.** The encoder quantisation is far below the noise floor: 0.0034 rad/s on the front wheels and 0.0067 rad/s on the rear, at 100 Hz. Neither limits the loop. If the encoders were coarse, the filter would have to be heavier, which would add lag, which the derivative term would then have to fight. Good sensing buys you a light filter, and a light filter buys you a responsive loop.'),

h2('4.10  The safety trips, and the one that only exists for a specific fault'),

p('Three trips watch every wheel. If any fires, a latched emergency stop halts all four motors.'),

gap(60),
table(
  ['Trip', 'What it watches for', 'Why it exists'],
  [
    ['**Overspeed**', 'Measured speed above 1.30 times the speed ceiling, held for a set time.', 'A runaway drive or a command that slipped past the clamp.'],
    ['**Stall**', 'Drive commanded but the wheel is not turning.', 'A jam, a seized gearbox, a wheel lifted off the floor and then caught.'],
    ['**Runaway**', 'A saturated command pushing one way while the wheel turns the other **and is not slowing down**.', 'The sign-inversion fault, below.'],
  ],
  [0.16, 0.42, 0.42],
),

gap(),
h3('The sign-inversion fault, and why nothing else would catch it'),

p('Each motor has two sign conventions that must agree: the direction the drive signal pushes, and the direction the encoder counts. If they disagree on one motor, the loop sees **positive feedback**: the motor spins the wrong way, the controller reads that as a larger error, pushes harder, and the wheel ends up pinned at full drive in the wrong direction.'),

p('The reason a dedicated trip is needed: **a motor rated at 60 rpm cannot physically overspeed its way past the overspeed threshold**, so the overspeed trip will never fire on this fault. The wheel just sits at full drive going the wrong way until a gearbox tooth or a driver transistor gives out.'),

gap(60),
warn('THE DETECTION SUBTLETY, WHICH IS A GOOD THING TO KNOW', [
  '"Drive one way, wheel the other" is also exactly what an ordinary hard deceleration looks like. You brake by driving against the current motion. So a naive detector would trip on every fast reversal.',
  'The distinguishing feature is that under braking the wheel is **slowing down**, and under runaway it is not. Hence the deceleration check: the trip compares the current speed against a checkpoint taken one window earlier, and only fires if the wheel is not losing speed. Without that check the robot would be un-drivable.',
]),

];
