const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code, qa } = S;

module.exports = [

h1('Part 13  The question bank'),

p('Three tiers. Tier 1 will almost certainly be asked. Tier 2 will be asked if the examiner engages with the detail. Tier 3 is for the examiner who knows this field well. Then the four hostile questions, which are the ones that decide how the session feels.'),

h2('13.1  Tier one: expect these'),

...qa('What is the novelty of your work?', [
  'Be precise, because overclaiming here is fatal. **The geometry is not the novelty; it is inherited from prior work in this laboratory.** The novelty is taking it from a demonstrated principle on a small prototype to a characterised, full-scale, 45.54 kg autonomous platform, and measuring what the transition costs.',
  'And then the four measured results: velocity control to 0.066 to 0.074 rad/s RMS under chassis weight with no channel saturating; kinematics and odometry numerically consistent to machine precision across twenty thousand cases; endpoint closure below 1 per cent of path to about 10 m; and scan matching measured to increase pose error rather than reduce it.',
]),

...qa('Why mecanum wheels?', [
  'Because the aisle problem is a lateral-correction problem. A differential-drive platform cannot correct a lateral offset without a manoeuvre, and the manoeuvre consumes longitudinal space the corridor does not have. A mecanum platform corrects a lateral offset by translating sideways, which in the ideal case requires no fore-aft travel at all.',
  'Then volunteer the cost, which makes the answer credible: slip is built in by design, efficiency is lower, and performance is floor-dependent. This project measured that last one: the same commanded drive gave ground-load increases of 24, 14 and 3 per cent on different patches of the same floor.',
]),

...qa('Why asymmetric? What does it actually change?', [
  'On a conventional mecanum platform the wheel rectangle sets the vehicle width, so the machine is wide because of its wheels rather than because of its payload. Moving one diagonal pair inward decouples the two.',
  '**What changes mathematically is only the yaw column of the transformation.** The translation terms are identical. The two diagonal pairs get lever arms of 0.5607 m and 0.4907 m, 14 per cent apart, so each wheel carries its own yaw coefficient instead of one shared one.',
  'And the risk: substituting a single shared coefficient anywhere in the software reduces the machine, in that code path alone, to an ordinary symmetric platform, and nothing in the telemetry would show it.',
]),

...qa('Explain your control loop.', [
  'Four independent loops, one per wheel, at 100 Hz on an ESP32. Each has a **two-term feedforward** that supplies most of the drive from the commanded velocity alone, plus a PID that corrects only the residual.',
  'The feedforward is `Kff * omega + Kstat * sign(omega)`: a viscous slope around 38 drive counts per rad/s and a breakaway term of 8 counts, fitted against three independent open-loop campaigns. Every measured point lands inside 8 per cent.',
  'The gains are 45, 250 and 0.5. The integral gain follows from direct synthesis: the plant DC gain is 1 over 38, a closed-loop time constant of 0.15 s was chosen, and Ki = 1/(K times lambda) gives 253, deployed as 250.',
  'The separation is the point: because the feedforward carries the bulk of the command, the integral is correcting a small residual rather than supplying drive from zero, which is why a gain of 250 is appropriate here and would be reckless on a bare loop.',
]),

...qa('What do P, I and D each do?', [
  '**P** responds to the error right now, in proportion to it. Like a spring: further from target means harder correction. On its own it leaves a permanent steady-state error, because the term only produces output when there is an error to produce it from.',
  '**I** accumulates the error over time, so even a small persistent error eventually produces a large correction. It is what eliminates the steady-state error P leaves. Its danger is windup.',
  '**D** responds to how fast the measurement is changing and opposes it. Like a shock absorber: it does not care where you are, only how fast you are moving. It damps the overshoot P produces.',
  'Concretely on this robot: a 0.1 rad/s error gives 4.5 counts from P immediately, and moves the output by 25 counts per second through I.',
]),

...qa('Why is Ki so large? 250 sounds enormous.', [
  'Two answers. First, it is not a free parameter: it follows from `Ki = 1/(K * lambda)` with a measured plant gain and a deliberately conservative 0.15 s closed-loop time constant.',
  'Second, and more important: the previous value of 30 was the **actual bug**. At Ki = 30 a 0.1 rad/s error moved the output 3 counts per second, so closing a realistic 10-count feedforward gap took over three seconds. The logs show an air run settling in up to 3.79 s. At 250 the same gap closes in 0.4 s.',
  'It is only safe because of the feedforward. On a bare loop it would be reckless.',
]),

...qa('How do you prevent integral windup?', [
  'By clamping the integral against **the drive authority genuinely left over**, recomputed every tick, rather than against a fixed bound. By the time the integral is computed, the feedforward and the P and D terms are all known, so the exact remaining headroom is known too.',
  'The old scheme clamped the raw integral state at plus or minus 200 with Ki = 30, which permits an integral term of 6000 counts against an output range of 255. The clamp existed but could never bind.',
  'The new scheme makes windup **structurally impossible** rather than merely bounded, and recovery from saturation is immediate rather than waiting for accumulated error to bleed off.',
]),

...qa('What is SLAM and which algorithm do you use?', [
  'Simultaneously recovering the robot\'s trajectory and a map of the environment from a stream of lidar measurements, where each depends on the other.',
  'Every practical system has a **front end** that estimates the transformation between nearby scans (local, so its errors accumulate) and a **back end** that jointly optimises the whole trajectory against all constraints including loop closures (global, so it can actually remove drift).',
  'The choice is slam_toolbox: graph-based, one map rather than one per particle, which matters on a Pi 5 with no GPU. Particle-filter SLAM scales with particle count times map size. Hector SLAM has no pose-graph back end so drift is never corrected. Cartographer is more machinery than this scale needs.',
]),

...qa('Why did you turn scan matching off? Is that not the whole point of lidar SLAM?', [
  'It was measured rather than assumed, and it increased pose error on all three routes tested. The tightest row: the same 3.193 m of driving, the same wheels and the same scans, robot physically returned to its mark. Wheel odometry alone closed at 16.2 mm. The matched estimate closed at 206.7 mm.',
  'And the mechanism is diagnosed, which is what makes it a result: all seventeen corrections fired at a mean odometry spacing of 0.183 m with about a centimetre of spread, and the smallest was 106.7 mm against a 150 mm search half-width. **A front end that corrects at a fixed odometric interval is responding to a schedule rather than to disagreement between scans.**',
  'Then bound it, unprompted: this scanner, this configuration, three routes of which two are tight circuits, which are degenerate geometry for a matcher. A one-variable comparison on the perimeter route is still owed. Stating it as a property of scan matching in general would go past the evidence.',
]),

...qa('Why does your map fail its own coverage criterion?', [
  'Because coverage accumulates through **translation past surfaces**, and the available circuit is a few metres, much of it bounded by furniture rather than continuous wall. The robot classifies what it drives past.',
  'Everything else about those maps passes: none of the three is folded, return to mark passes comfortably with a best of 6.4 mm, and the recovered wall geometry is consistent across all three runs. Only coverage fails, at 73.0, 78.3 and 84.6 per cent unclassified against a 50 per cent threshold.',
  'Then volunteer the qualification: the percentage is over the whole allocated grid rather than the traversable area, so it overstates the fraction of reachable space unobserved. It is used because it was fixed before the work began and because the same definition applies to every run compared.',
]),

...qa('Why is there no IMU?', [
  'Objective 2 asks **which sensing** a pose estimate requires. Fitting an IMU at the start would have removed the ability to answer that, because there would be no unfused baseline to compare against.',
  'The unfused platform is that baseline, and it is now characterised. The photogrammetry measured 3.85 and 4.49 degrees of heading error that every instrument on the robot missed, because all of them derive from the same wheel measurements.',
  'A rate gyroscope measures angular rate independently of the wheels, so it would make that class of error observable and would separate an encoder scale error from a rigid all-wheel slip mode. That is a falsifiable test with the number already written down.',
  'And the disclaimer, which makes the argument credible rather than defensive: **it is not claimed that the platform is better off without one.** Fusion would reduce heading error, it is the right next purchase, and the claim is only about order of work.',
]),

h2('13.2  Tier two: if the examiner engages'),

...qa('Your kinematics are exact to 10^-16 but your robot drifts by centimetres. Reconcile that.', [
  'They measure different things. The 10^-16 says the **arithmetic** is right: the code contributes no numerical error of its own. The drift is in the **physics**: the wheel radius is not exactly 0.0762 m under load, the rollers slip, and the floor is not uniform. A correct model of a slightly different robot.',
  'That is precisely why the report checks them separately, and why the floor measurements exist at all. And the offline re-integration check has the same shape: it rules out a discrepancy between the online and offline implementations, and explicitly does not rule out an error they share.',
]),

...qa('Does the asymmetry give you a slip sensor?', [
  'Be careful here, because the overclaim is easy and the correction is embarrassing. **No.** The two yaw estimates come from disjoint pairs of wheels, and a symmetric platform has disjoint pairs too, so it carries a residual of exactly the same algebraic form.',
  'What the differing lever arms change is the **weighting**. On a symmetric platform the common-mode component of the error cancels exactly; here it survives, scaled by (r/2)(1/Ko - 1/Ki) = **0.0097**.',
  'So: the asymmetry does not create the observable. It makes the residual sensitive to a class of error a symmetric layout cancels, at roughly one per cent of that error\'s magnitude. Whether that is useful for diagnostics is a question for measurement.',
]),

...qa('Your Kp derivation gives 22 but you shipped 45. Explain.', [
  'This is the honest one and you should welcome it. The derivation needed the plant time constant, which had never been measured because every bench run to that point logged steady-state points and no transients. 0.18 s was assumed on plausibility grounds, giving Kp = 45.',
  'Plant identification later measured it at about 0.09 s, half that, which by the same formula calls for about 22. Two recomputed candidates were swept against the shipped value across sixteen combinations of setpoint and motor. **Both produced more overshoot, and 45 won 16 of 16 rows.**',
  'The reasoned explanation: `Kp = tau * Ki` comes from pole-zero cancellation on the **bare plant**. This controller does not command a bare plant, because the feedforward supplies most of the drive the instant the setpoint changes. So Kp\'s real job here is damping the transient around that feedforward jump, not cancelling a pole the feedforward has already pre-compensated. Lowering it weakens exactly that damping.',
  'Caveat, volunteered: that explanation has not been tested against a Kp sweep with feedforward disabled, so it is reasoned from the data rather than itself measured. The objective closes as **confirmed**, not as changed.',
]),

...qa('Why 90 degrees of self-occlusion? Could you not just move the lidar?', [
  'The mast and payload sit in the scan plane, and the wedge was measured at five independent headings rather than assumed from the geometry: 107 of 430 beams, consistently, centred on directly behind the robot.',
  'Moving the lidar above the payload is the obvious fix and costs mast height and stability. A multi-plane sensor is the other. Masking costs nothing and the wedge is measurable, which is why it was chosen.',
  'And the general point the report makes: this is a consequence of carrying a payload above a single-plane scanner, and the trade-off between sensor placement, sector masking and accepted coverage loss does not appear to be characterised quantitatively in the literature.',
]),

...qa('Why did you replace DWB with MPPI? Did you tune DWB first?', [
  'No, and say so. The reason is structural rather than a tuning comparison. DWB\'s rotate-to-goal critic invalidates every candidate carrying translational motion once the robot is near the goal but not aligned, and because that configuration sampled velocities on a full cross-product grid, almost everything was rejected, giving "no valid trajectories" on rotation-only goals.',
  '**DWB\'s critics can individually reject a trajectory, reducing the candidate set to zero. MPPI\'s critics only ever add cost.** A weighted sum over many sampled trajectories cannot reach zero candidates the way a sequence of hard admissibility filters can. So the failure mode is structurally impossible in the replacement rather than tuned away.',
  'Honest scope: this is a property of that configuration rather than of the dynamic window approach as such. The goal tolerance, velocity sample set and simulation horizon were none of them varied before the controller was replaced.',
]),

...qa('MPPI comes from a GPU paper. How does it run on a Pi?', [
  'That was treated as a question to answer with a CPU measurement rather than assumed either way. Measured: 500 sampled trajectories at 20 Hz with full-footprint collision checking held the control loop rate with no missed-rate warnings. The GPU origin did not turn out to be the binding constraint on this platform.',
  'What **is** binding: three components run below their requested update rates, the global planner at 1.25 Hz against 5 Hz requested and the local controller at 7.5 to 13.7 Hz against 20 Hz. That is a property of the computer, not of the software.',
]),

...qa('Why is your inflation radius small? Is that not unsafe?', [
  'Because inflation is a **path preference**, not a collision statement. Setting it large in a narrow aisle makes a corridor the robot physically fits through appear impassable, because inflation from both walls meets in the middle and the planner sees no free corridor.',
  'Safety comes from the exact footprint check and from the collision monitor, which forward-simulates the commanded velocity against the true footprint polygon in real time and can veto a command the planner already approved.',
]),

...qa('What is log-odds and why use it?', [
  'A cell\'s occupancy is stored as the logarithm of the odds rather than as a probability. Two reasons, both practical. Updates become **additive**: add a fixed amount when a beam terminates in a cell, subtract when a beam passes through, with no multiplication and no renormalisation. And it is numerically stable at the extremes, where a probability like 0.0000001 would be handled badly.',
  'It also explains the map file directly: 0 for occupied, 254 for free, 205 for unknown are the log-odds value saturated toward its extremes or left at the midpoint. "84.6 per cent unclassified" literally means those cells never accumulated enough evidence to move off the midpoint.',
]),

...qa('Your two front encoders differ from the rear. Does that not need correction factors everywhere?', [
  'No, and this is a nice answer. `ENCODER_CPR` is a per-motor array and each motor\'s raw count is divided by its own constant, which converts edges into revolutions. The factor of two cancels exactly. Everything downstream sees only rad/s and never learns which encoder produced it. There is no scaling term anywhere else in the firmware.',
  'What genuinely differs is **resolution only**: one count is 3.37 x 10^-5 rad of wheel rotation on the front and 6.75 x 10^-5 on the rear, which at 100 Hz is a velocity quantum of 0.0034 and 0.0067 rad/s. Both sit far below the noise floor, so neither limits the loop. The extra front resolution matters for odometry, where counts accumulate over minutes.',
  'And the reason it was worth getting right: a single shared constant made the fronts report double their true speed, the controller believed them, and the fronts settled at half the commanded velocity. A permanent, silent, speed-dependent yaw bias with clean tracking plots.',
]),

h2('13.3  Tier three: the deep ones'),

...qa('Why does your endpoint error grow faster with rotation than with distance?', [
  'Because rotational manoeuvres involve more lateral roller motion, and lateral roller motion is exactly what the wheel encoder cannot see. The encoder measures how far the wheel turned about its own axle; the roller sliding sideways underneath it contributes nothing to that count while contributing everything to the position error.',
  'The evidence: three logged drives at 0.23, 0.29 and 0.91 per cent, and the 0.91 is the route with the most rotation rather than simply the longest. Separating length from rotation needs routes that vary the two independently, which is a direct use for a larger test space and is listed as owed.',
]),

...qa('Three of your estimators agree with each other. Is that not evidence they are right?', [
  'It is evidence of nothing, and that is the point of the photogrammetry result. Wheel odometry, the published estimate and the SLAM pose all reported 3.85 and 4.49 degrees of heading change; the floor, read against the tile grout, put the robot within 0.03 degrees of where it started.',
  '**Three estimates agreeing with one another while all three disagree with the floor is the signature of an error they share, not one that separates them.** They all derive from the same wheel measurements, so they all inherit the same wheel-level error and all report it confidently.',
]),

...qa('Your scatter measurement does not fit a linear or a quadratic model. Is that not a failed measurement?', [
  'No, it is the result. Below 1.5 m both captures are solid at 12 to 14 mm. In the 1.5 to 2.0 m band one capture gives 22.3 mm and a second, from a differently obstructed parking spot, gives 31.9 mm, which fails the 25 mm half-cell criterion the occupancy resolution implies. Beyond 2.5 m both return 55 to 200 mm and do not agree with each other.',
  'Neither model reproduces that, since both predict a single smooth curve. **The behaviour is scene-dependent and is not explained by range alone in these captures, which is itself the result: a range cap derived in one position is a fact about that position until it reproduces elsewhere.**',
]),

...qa('Why relax the loop-closure thresholds? Is that not just making the test easier?', [
  'It is making the test appropriate to the sensor. A quarter of every scan is permanently masked behind the mast, so a genuine revisit legitimately scores lower than stock thresholds expect, because a quarter of the evidence is simply absent. Stock values assume a feature-rich environment and a full 360-degree scan; this robot has neither.',
  'And the cost is stated rather than hidden: relaxing them trades a higher risk of a **wrong** closure for any closure at all. The right trade when the measured state is zero closures and half a metre of drift, and the wrong one the moment a map folds. The configuration carries a written instruction that these two are the first thing to raise back if that happens.',
]),

...qa('How would you quantify the benefit of the asymmetry?', [
  'A matched symmetric baseline: same mass, same wheels, same motors, same controller parameters, same routes, same analysis tools. In simulation first, and on hardware if the wheelbase can be reconfigured without a new chassis.',
  'That is what closes Objective 3, and until it exists the honest statement is the one in the report: **no asymmetry-specific penalty has been detected in any experiment performed, and an absence of penalty across a year of measurement is not the same thing as a measured cost of zero.**',
]),

h2('13.4  The four questions that can go badly'),

...qa('So it does not actually work yet?', [
  'Do not get defensive, and do not overclaim. Separate the layers.',
  '"Below the map, it works and it is measured: the motors track to a known error loaded and unloaded, the encoder path is clean, the feedforward is fitted rather than guessed, the kinematic and odometry implementations are verified against an independent reference, the planner plans, the local controller reaches goals, and the operator interface is geometrically correct."',
  '"At and above the map, three layers are not established, and in each case the reason is specific. Mapping produces consistent and repeatable geometry but cannot meet a coverage criterion in a room this size. Localisation against a saved map has never been run, because there is no accepted map to run it against. And a scan-matching front end, measured rather than assumed, made the pose estimate worse, so it is switched off."',
  '"Two of those three resolve to the size of the available test area, which is an environmental limit rather than anything on the platform."',
]),

...qa('Is the asymmetry not just a manufacturing defect you rationalised afterwards?', [
  'Answer factually rather than indignantly. It is a **designed** layout from a prior laboratory study with published kinematics, built to a drawing, and the offset is a deliberate 70 mm rather than a tolerance.',
  'The geometric motive is concrete: on a conventional layout the wheel rectangle sets the vehicle width, so the machine is wide because of its wheels rather than its payload. This decouples the two.',
  'And then concede the open part, which is what makes the answer credible: "the benefit is geometric and real; the **cost** is unquantified, because no matched symmetric baseline has been built. That is Objective 3, and it is open."',
]),

...qa('Why not just buy a commercial autonomous mobile robot?', [
  'Because no commercial platform is dimensioned for this. Commercial AMRs are built for wide, well-structured routes, and the aisle is exactly the part of the building they work around rather than in.',
  'And because the research question is not "can a robot move boxes". It is: does an asymmetric non-collinear mecanum geometry survive the transition to full scale, what does it cost, and what sensing does a pose estimate at corridor-width clearances actually require? None of those can be answered with a sealed commercial product, because the questions are about the parts a commercial product does not expose.',
]),

...qa('Three strands in one year sounds unfocused. Why not do one properly?', [
  'The honest answer is the one the report gives, and it is about shared engineering rather than shared subject matter.',
  '"They share instrumentation. Multi-sensor integration, calibration against a physical reference, real-time acquisition, and control that fails safe recur in all three, and an error made in one has repeatedly become a method in the next."',
  'Give the two concrete examples: the monitoring system established the practice of verifying a configuration against the running system rather than against a file, which was then applied to the platform; and the platform work established that a control law must be observed responding to a change rather than inferred from a steady-state snapshot, which was then applied back to the monitoring system and is exactly what Chapter 2 still admits it owes.',
  'Then add the structural point: "each strand is developed until it stands on its own, because a strand whose behaviour has not been characterised in isolation contributes nothing measurable to anything built above it."',
]),

];
