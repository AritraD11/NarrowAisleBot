const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 9  Navigation: planning, control, and every constraint'),

h2('9.1  The one idea that makes obstacle avoidance work'),

p('A path planner searching a grid naturally treats the robot as a **point**: it finds a sequence of free cells from A to B. But a real robot is a rigid body with extent. A path that threads a point through a gap narrower than the robot is not a path, it is a collision.'),

p('There are two ways to reconcile that, and knowing which is in play matters for every parameter below.'),

gap(60),
table(
  ['Approach', 'How it works', 'Cost'],
  [
    ['**Footprint (exact)**', 'Declare the robot\'s outline as a polygon. For every candidate pose, test whether that polygon, rotated and translated, overlaps any occupied cell.', 'Exact, but expensive: a full polygon-versus-grid test per candidate pose.'],
    ['**Inflation (approximate)**', 'Instead of growing the robot, grow the **obstacles**. Expand every occupied cell outward, then plan with a point robot on the inflated grid.', 'Cheap. The expansion is computed once per costmap update, and planning is then a plain grid search.'],
  ],
  [0.22, 0.44, 0.34],
),

gap(),
p('The stack uses **both, at different stages**: inflation for fast global planning, exact footprint collision checking for local trajectory validation.'),

h2('9.2  Inflation, precisely, and the trap it sets for a narrow-aisle robot'),

p('Two radii characterise any footprint polygon:'),

bullet('**Inscribed radius**: the largest circle that fits **inside** the footprint. For a rectangle of width w, that is w/2.'),
bullet('**Circumscribed radius**: the smallest circle that **contains** the footprint. For a rectangle l by w, that is half the square root of (l squared plus w squared).'),

p('The costmap then assigns every cell a cost from 0 to 254 according to its distance from the nearest obstacle:'),

gap(60),
table(
  ['Distance from obstacle', 'Cost', 'What it means'],
  [
    ['Zero (the obstacle cell itself)', '254, LETHAL', 'Occupied.'],
    ['Up to the inscribed radius', '253, INSCRIBED', '**Any** robot pose whose centre is this close is in collision **regardless of heading**, because the inscribed circle is inside the footprint at every rotation. Planning must treat these as blocked.'],
    ['Between inscribed and circumscribed', 'decaying exponentially', 'Collision **depends on heading**. A point-robot planner cannot resolve this, which is exactly why the local controller re-checks the true polygon.'],
    ['Beyond the inflation radius', '0, FREE', 'No statement about collision at all.'],
  ],
  [0.28, 0.16, 0.56],
),

gap(),
good('THE SEMANTIC POINT WORTH INTERNALISING', [
  'Beyond the circumscribed radius, the decaying cost is **not a collision statement**. It is a **preference**. It biases paths toward the middle of free space without forbidding proximity.',
  'Confusing preference with safety is the single most common costmap mistake, and it causes the trap below.',
]),

gap(60),
bad('THE NARROW-AISLE TRAP, AND IT IS REAL', [
  'Setting the inflation radius too large makes an aisle that the robot **physically fits through** appear impassable, because the inflation from both walls meets in the middle and the planner sees no free corridor at all.',
  'So the inflation radius must be tuned against the **narrowest aisle the robot must traverse**, not set generously "for safety".',
  '**Safety comes from the footprint check. Inflation is about path preference.** That distinction matters disproportionately on this platform and it is worth saying in exactly those words.',
]),

h2('9.3  Layered costmaps'),

p('The costmap is composed from ordered layers, each of which may write to the master grid.'),

gap(60),
table(
  ['Layer', 'What it contributes'],
  [
    ['**Static**', 'The SLAM or map-server occupancy grid. Long-lived structure.'],
    ['**Obstacle**', 'Live lidar returns, and it does **two distinct things** per scan. **Marking:** a beam that terminates at some range marks that cell occupied. **Clearing:** raytracing along the beam from the sensor out to that range, clearing every cell passed through. Clearing is what lets a moved obstacle disappear rather than smearing across the map forever.'],
    ['**Inflation**', 'Applies the cost function above to whatever the layers beneath wrote.'],
  ],
  [0.16, 0.84],
),

gap(),
p('**Why layers rather than one fused grid.** Each layer owns its own semantics and update rule, and layers can be added without touching the others. That extensibility is directly relevant here: a future "no-go zone near the loading area" is a new layer, not a rewrite.'),

p('It is also the mechanism that made the self-occlusion bug so damaging. The obstacle layer marks what it is given. If the mast\'s own returns reach it, they are marked, they move with the robot, and inflation expands them. Fixing it at the layer would be the wrong place; it is fixed upstream in the scan relay, because a beam with no information should never reach a layer that will interpret it.'),

h2('9.4  Global planning'),

p('The global planner searches the costmap for a route from the current pose to the goal, using A* (or Dijkstra with a zero heuristic).'),

p('A* minimises cost-so-far plus an admissible estimate of cost-to-go. With a zero heuristic it degenerates to Dijkstra: still optimal, but expanding far more nodes. The heuristic costs nothing and prunes heavily, so A* is the right default.'),

h3('The parameter that decides whether exploration is possible at all'),

p('`allow_unknown`. With it set false, the planner refuses to route through cells the map marks unknown. On a fully pre-mapped floor that is the safe choice.'),

gap(60),
warn('BUT ON THIS ROBOT', [
  'While SLAM is building the map live, most of the world is still unknown: the commissioning maps were **73 to 85 per cent unknown**. With `allow_unknown: false` the planner can essentially never find a path to anywhere interesting.',
  'So it must be **true**, with the local costmap and the footprint check providing the actual safety. This is a good example of a parameter whose correct value is set by a measured property of your environment, not by a general preference for caution.',
]),

h2('9.5  Local control: why DWB failed and MPPI replaced it'),

p('The global path is geometric: a line through free space, computed on a possibly stale map, ignoring the robot\'s dynamics. The local controller converts it into velocity commands at about 20 Hz, reacting to things the global map does not know about.'),

h3('The first choice: the dynamic window approach'),

p('DWB searches directly in **velocity space** rather than position space. Three ideas:'),

num('**Search over velocities**, not positions. Each candidate velocity, held for a short horizon, implies a trajectory.'),
num('**Restrict to the dynamic window**: only velocities reachable from the current velocity within one control period, given the acceleration limits. This is what makes it dynamically feasible rather than a kinematic fantasy.'),
num('**Admissibility**: discard any velocity from which the robot could not stop before hitting the nearest obstacle on that trajectory.'),

p('Surviving candidates are scored by a weighted sum of **critics**: plugins scoring goal progress, path alignment, obstacle proximity via the true footprint, and oscillation. Highest score wins.'),

p('It was adopted first on the reasoning that it is computationally lighter, which on a Pi 5 with no GPU was a defensible starting point.'),

h3('Why it failed, diagnosed from source rather than from symptoms'),

gap(60),
bad('THE FAILURE MODE', [
  'The deployed configuration **stalled on rotation-only goals**. The robot would arrive near a goal, still need to rotate to the final heading, and the controller would report "no valid trajectories".',
  'Root cause: DWB\'s rotate-to-goal critic **invalidates every candidate carrying translational motion** once the robot is near the goal but not yet aligned. And because that configuration sampled velocities on a full cross-product grid, only a small fraction of candidates were pure rotation, so almost everything was thrown out.',
]),
gap(),

p('**Scope it honestly, because the report does.** This is a property of the **configuration** rather than of the dynamic window approach as such. The critic\'s behaviour depends on the goal tolerance, the velocity sample set and the simulation horizon, and none of those was varied before the controller was replaced. If asked "did you try tuning it first?", the answer is no, and the reason to give is the structural one below.'),

h3('The structural difference that decided it'),

gap(60),
good('THE ARGUMENT WORTH MEMORISING', [
  'DWB\'s critics can individually **reject** a trajectory, reducing the candidate set to zero. MPPI\'s critics only ever **add cost** to a trajectory.',
  'A weighted sum over many sampled trajectories **cannot reach zero candidates** the way a sequence of hard admissibility filters can. So that particular failure mode is structurally impossible in the replacement, rather than merely tuned away.',
]),
gap(),

h3('MPPI, and what it is'),

p('Model Predictive Path Integral control is a sampling-based stochastic optimal control method. In plain words:'),

num('Sample many noisy control sequences (500 of them here).'),
num('Roll each one forward through a model of the robot over a short horizon, producing a predicted trajectory.'),
num('Score each trajectory with a cost function.'),
num('Form the next command as an **importance-weighted average** of all the samples, weighted by the exponential of the negative cost, rather than by picking a single best.'),

gap(60),
analogy([
  'Asking 500 people to guess the route, then taking a weighted average of their answers with the good guesses weighted far more heavily, rather than picking the single best guess and discarding the rest.',
  'The averaging is why it degrades gracefully. If the best option disappears, the answer shifts smoothly toward the next-best group. A winner-take-all scheme, in the same situation, can find itself with no winner at all.',
]),
gap(),

p('**Why it suits a mecanum base specifically:** it samples the full continuous forward, lateral and yaw space. DWB discretises the lateral axis coarsely, which for a genuinely omnidirectional platform throws away most of what the platform can do.'),

p('**And the concern that turned out not to bind:** the method comes from a paper whose own experiments ran on a GPU, and this robot is a Pi 5 with none. That was treated as a question to answer with a CPU measurement rather than assumed either way. Measured: 500 sampled trajectories at 20 Hz with full-footprint collision checking held the control loop rate with no missed-rate warnings. So the GPU origin did not turn out to be the binding constraint.'),

h2('9.6  Two stock critics deliberately disabled, and the bug class behind it'),

p('This is a small thing that demonstrates real care, and it is worth raising yourself.'),

p('Two stock MPPI critics are **not** enabled: the path-angle critic and the prefer-forward critic. Both assume the robot\'s +X axis is its forward direction, which is the ROS convention.'),

gap(60),
bad('THIS ROBOT\'S BASE FRAME IS DELIBERATELY NOT THAT', [
  'On this platform +X is the **right side** and +Y is **forward**. So the path-angle critic, which computes the angle of travel assuming +X is the nose, would **reward travelling sideways and rotate the chassis toward it**. The prefer-forward critic penalises negative forward velocity, which is meaningless once that axis means strafe, and it encodes a differential-drive reluctance to reverse that a mecanum base simply does not have.',
  'Both were checked against source and **dropped rather than reparametrised**, because no parameter renames which axis is forward.',
]),
gap(),

p('**The bug class.** Axis-convention mismatches have recurred five separate times on this project. The worst instance: the first autonomous goal ever sent produced motion at **88.4 degrees to the commanded direction**, measured from the action\'s own feedback poses. Two individually correct, individually validated axis conventions met at one topic and nothing had ever reconciled them. The planner, wanting forward motion, published on the lateral channel, and the teleoperation node executed a sideways strafe. Because the error was a constant 90-degree rotation sitting inside a closed loop, the planner\'s own cross-track corrections came out rotated too, so the drive did not fail as a single wrong turn, it failed by **never converging**.'),

p('The fix was an explicit axis adapter node sitting between the navigation output and the wheel layer, plus a written axis-convention document so the derivation does not have to happen a sixth time.'),

h2('9.7  The command pipeline, and why a multiplexer sits at the end'),

p('Commands from three sources converge before reaching the wheels:'),

gap(60),
code([
  '  planner  -->  controller  -->  velocity smoother  -->  collision monitor',
  '                                                              |',
  '                                                       axis adapter',
  '                                                              |',
  '                                                              v',
  '  phone joystick / dashboard  ------------------------>  twist_mux',
  '                                                              |',
  '                                                              v',
  '                                            asymmetric inverse kinematics',
  '                                                              |',
  '                                                              v',
  '                                                   ESP32, four PID loops',
]),

gap(60),
bullet('**The multiplexer gives manual override priority.** Manual outranks the planner at the single point where the two meet. One place, one rule.'),
bullet('**The collision monitor is the hard safety layer.** It forward-simulates the commanded velocity against the true footprint polygon in real time and can veto or slow a command the planner already approved, independently of whether the costmap is stale. The project\'s own note calls it "the one thing on this robot that must not be subtly wrong."'),
bullet('**The asymmetric inverse kinematics are evaluated exactly once**, in the teleoperation node on the host. Whichever source holds control, the same transformation runs. That is what stops the early Wi-Fi joystick bug (one shared yaw coefficient instead of two) from ever recurring.'),

h2('9.8  What autonomous navigation actually achieved'),

gap(60),
table(
  ['Trial', 'Result'],
  [
    ['First complete autonomous round trip, August', 'Drove out, reversed its heading, returned. Held direction to within **5.5 and 3.7 degrees** on the two legs, stopped **4.6 cm** short of the commanded stop point.'],
    ['Dashboard tap-to-goal trials', 'Goals selected by tapping the map. Reached in **21 s** and **26 s**.'],
    ['Trial count', '**Three goals across three trials, all three reached.**'],
    ['Interface verification', 'The tapped-pixel to world-coordinate transform agrees with its analytic value to within **one part in a million** at three display pixel densities, which over the test map is well under a millimetre.'],
  ],
  [0.28, 0.72],
),

gap(),
warn('THE QUALIFIERS THAT MUST TRAVEL WITH THOSE NUMBERS', [
  '**Inside a live mapping session, not against a saved map.** That is because there is no accepted commissioning map to run against, which is the room constraint from Part 8 again.',
  '**Three trials is a small number.** Establishing a success rate, a stopping-error distribution and behaviour against obstacles needs a larger trial count in a space that permits varied routes.',
  '**The interface check is a check that the transformation is coded correctly**, not a statement about pointing accuracy. Pointing accuracy is set by the size of a fingertip against the map scale and was not measured.',
]),

h2('9.9  Localisation against a saved map: configured, never run'),

p('Monte Carlo localisation (AMCL) is the intended mode once an accepted map exists. It is worth understanding because the panel may ask what the robot would do in a real warehouse, where the map is made once and reused.'),

h3('How a particle filter localises'),

gap(60),
analogy([
  'Drop a thousand pins on a floor plan, each one a guess at "maybe I am here, facing this way". Then, every cycle:',
  '**Move them.** Shift every pin by however much the robot thinks it moved, plus a bit of random noise, because the motion estimate is not exact.',
  '**Score them.** For each pin, ask: if I really were here, what would the lidar see? Compare that against what the lidar actually sees. Pins whose predicted view matches reality score high.',
  '**Resample.** Redraw the thousand pins in proportion to their scores. Bad guesses die out, good guesses multiply, and the cloud concentrates on the poses the scan actually supports.',
]),
gap(),

p('The parameters that matter here: the four motion-noise terms scale how much the filter distrusts the odometry it is given (rotation from rotation, rotation from translation, and the two reverses). The robot model is set to omnidirectional, which is correct for mecanum, where lateral motion carries its own noise character distinct from forward motion. And the initial pose already accounts for the non-standard base frame: a robot facing forward along map +X has a base-frame yaw of -90 degrees here, not 0. Get that wrong and the very first scan match starts from a hypothesis rotated 90 degrees from reality.'),

gap(60),
bad('THE HONEST STATE', [
  'It is **configured but never hardware-tested**, because no accepted map has ever been saved for it to load. It has never been exercised against real particle convergence, real drift under motion, or real recovery behaviour.',
  'Also worth knowing, because it is a good question: **AMCL and SLAM must never run at the same time.** Both publish the same coordinate transform, so running both means two nodes fighting over one transform and the resulting pose estimate is meaningless. Pick one per run.',
]),

h2('9.10  Frontier exploration: not used, and that is a decision'),

p('The standard way to make mapping autonomous is frontier exploration: find the boundaries between known-free and unknown space, drive to one, repeat. A panel may ask why the mapping is driven manually.'),

p('The answer is not "we did not get to it". It is that manual driving lets a human apply two pieces of domain knowledge that frontier selection cannot:'),

num('**Hug the walls rather than the aisle centreline.** Centreline driving produced thin, poorly-defined map edges instead of solid walls.'),
num('**Translate rather than rotate wherever possible.** Pure rotation gives the mapper almost nothing, as Part 8 measured.'),

p('Automating frontier selection would have to re-encode both of those hard-won findings as an algorithm before it could safely replace a person driving. It is worth revisiting once a good map exists and repeated remapping of known territory becomes the actual cost driver. Not before.'),

h2('9.11  The navigation constraints, collected'),

gap(60),
table(
  ['Constraint', 'Status and justification'],
  [
    ['**No saved map to navigate against**', 'The room constraint. Navigation therefore runs inside a live mapping session. Not a navigation defect; the same single cause as four other open entries.'],
    ['**Small trial count**', 'Three goals, three trials. A success rate and a stopping-error distribution need varied routes, which need space.'],
    ['**Three components run below their requested rate**', 'Global planner at 1.25 Hz against 5 Hz requested; local controller at 7.5 to 13.7 Hz against 20 Hz; the safety chain likewise. A property of the host computer, not of the software. A faster host raises all three.'],
    ['**DWB abandoned without exhausting its tuning**', 'Stated honestly. The replacement was chosen on a structural argument (critics that add cost cannot produce zero candidates) rather than on a tuning comparison.'],
    ['**Inflation radius must be small**', 'Forced by the aisle width. Safety therefore rests on the footprint check and the collision monitor rather than on a generous inflation band.'],
    ['**Non-standard axis convention**', 'Deliberate, documented, and the cause of five separate recurrences of one bug class. Handled by an explicit adapter node and by disabling two stock critics that cannot be reparametrised.'],
    ['**Unmodelled slowness on one long drive**', 'A nominal 1 m strafe took 87.4 s, with repeated progress-checker events and control-loop rate warnings coinciding with costmap clear-and-replan cycles. Plausibly CPU contention, plausibly a moving target from the global planner republishing a shifted path as the live map grew. **Not distinguished. Left open and stated as open.**'],
  ],
  [0.3, 0.7],
),

];
