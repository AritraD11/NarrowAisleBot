const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 8  SLAM: the theory, then every constraint you hit'),

h2('8.1  The chicken-and-egg problem'),

p('SLAM stands for Simultaneous Localisation And Mapping. The robot has to recover two unknowns from one stream of lidar measurements, and each one depends on the other:'),

bullet('To build a good **map**, you need to know where you were when each scan was taken, so you can project the scans into a common frame.'),
bullet('To know **where you are**, you need a good map to compare the current scan against.'),

gap(60),
analogy([
  'You wake up in an unfamiliar building with no phone and no map. You want to draw a floor plan **and** mark where you currently are on it. Every step you take, you note what you can see and roughly how far you moved. The plan and your position on it grow together, and an error in either corrupts the other.',
  'That is SLAM, and the reason it is hard is that there is no external truth to check against, only internal consistency.',
]),

h2('8.2  The two halves: front end and back end'),

p('Every practical SLAM system splits the problem in two, and the distinction is the whole of Chapter 1\'s most important negative result, so learn it properly.'),

gap(60),
table(
  ['', 'Front end (scan matching)', 'Back end (pose-graph optimisation)'],
  [
    ['**Job**', 'Given two nearby scans, or a scan and the map, estimate the rigid transformation between them.', 'Given many local estimates plus occasional loop closures, find the globally consistent set of poses that best explains all of them at once.'],
    ['**Scope**', '**Local.** It only ever compares nearby poses.', '**Global.** It optimises the entire trajectory jointly.'],
    ['**Error behaviour**', 'Errors accumulate. Drift is permanent, because each estimate only corrects relative to the previous pose.', 'Drift is **correctable**. Recognising a place you have been before injects one new constraint that the optimiser spreads over the whole trajectory.'],
    ['**Analogy**', 'Measuring each room against the one next door. Each measurement is good; by the twentieth room the floor plan is bent.', 'Discovering two rooms you thought were far apart share a wall, and redrawing everything so all the measurements fit.'],
  ],
  [0.14, 0.42, 0.44],
),

h2('8.3  How the occupancy map is stored, and why in log-odds'),

p('The map is a grid of square cells, 0.05 m on a side here. Each cell holds a probability that it is occupied.'),

p('But the probability is not stored directly. It is stored as **log-odds**:'),

eq('l  =  log ( p / (1 - p) )'),

p('Two reasons, and both are practical:'),

num('**Updates become additive.** In probability form, combining a new observation with an old belief requires a multiplication and a renormalisation. In log-odds form you simply **add** a fixed amount when a beam terminates in a cell (evidence of occupied) and subtract a fixed amount when a beam passes through it (evidence of free). Addition is cheap and it never needs renormalising.'),
num('**Numerical stability.** A cell observed as free a thousand times would have a probability like 0.0000001, which floating-point arithmetic handles badly. In log-odds it is just a large negative number, comfortably represented.'),

gap(60),
analogy([
  'Keeping score in a debate by **adding and subtracting points** rather than by recomputing a percentage after every argument. Much easier to run, and extreme confidence in either direction does not break the scoreboard.',
]),
gap(),

p('This is visible directly in the saved map file. The convention in the saved image is 0 for occupied, 254 for free and 205 for unknown. Those are the log-odds value saturated toward its extremes where observations accumulated, and left at the midpoint where too few observations exist to be confident either way.'),

gap(60),
good('THE SENTENCE THAT CONNECTS THEORY TO THE RESULT', [
  '"81 per cent unknown" in a map is not a separate metric from that equation. It literally means: these cells never accumulated enough log-odds evidence to move off the midpoint.',
  'Say that and the coverage failure in 8.5 stops sounding like a vague shortcoming and starts sounding like a measured quantity.',
]),

h2('8.4  Why slam_toolbox and not the alternatives'),

p('Have this comparison ready. "Why did you pick that package?" answered with "it is the ROS 2 default" is a weak answer; the reasoning below is a strong one.'),

gap(60),
table(
  ['Alternative', 'What it does', 'Why not here'],
  [
    ['**GMapping / particle filter SLAM**', 'Carries a population of pose hypotheses, each with **its own copy of the map**.', 'Memory and compute scale with particle count times map size. That is a real cost on a Pi 5 with no GPU. Dedicated hardware accelerators exist in the literature precisely because this approach is too slow on embedded hardware. Comparisons on low-cost rotating scanners of this exact class also report it noisier than scan-matching approaches.'],
    ['**Hector SLAM**', 'Scan matching at a high scan rate, deliberately **without** using odometry as a prior.', 'A legitimate alternative, and its no-odometry philosophy was the right call while this project\'s odometry was unreliable. But it has **no pose-graph back end and no loop closure**: drift is minimised going forward and never corrected once accumulated.'],
    ['**Cartographer**', 'Submaps plus branch-and-bound global scan matching.', 'More sophisticated and a reasonable **future** upgrade if map scale grows well beyond a single aisle. For the scale here it is more machinery than the problem needs.'],
    ['**slam_toolbox (chosen)**', 'Correlative scan-matching front end plus a Ceres-based pose-graph back end.', 'Carries **one** map, not N. Gets Hector\'s scan-matching-only option **and** an optimisation back end. Purpose-built for this deployment class; the package\'s own motivating examples are retail and warehouse floors.'],
  ],
  [0.22, 0.3, 0.48],
),

h2('8.5  Constraint 1: the room, and why it is the binding one'),

p('This is the most important constraint in the whole project. Get the argument right and the panel will accept it; get it vague and it sounds like an excuse.'),

h3('The four acceptance criteria, fixed before the mapping work began'),

gap(60),
table(
  ['Criterion', 'Threshold', 'Result on the three commissioning maps', 'Verdict'],
  [
    ['Map is not folded', 'binary', 'None of the three is folded', '**Pass**'],
    ['Return to starting mark', 'within 0.15 m', 'Passes comfortably on each; best measured at **6.4 mm**', '**Pass**'],
    ['Doubled walls', 'under 1 % of occupied cells', '0.7, 0.8 and **2.9** per cent', '**Two of three**'],
    ['Unclassified cells', 'under 50 % of mapped area', '**73.0, 78.3 and 84.6** per cent', '**Fail, on all three**'],
  ],
  [0.24, 0.18, 0.34, 0.24],
),

gap(),
p('These are engineering acceptance thresholds set by this project, not values from the literature. Only the 0.15 m return figure has a physical basis: it is the order of clearance the target aisle geometry allows. The other three were chosen as the condition a map would have to reach before attempting localisation against it was worthwhile. State that; it shows the bar was fixed in advance and is not being moved to suit the result.'),

h3('The mechanism behind the coverage failure'),

p('Coverage accumulates through **translation past surfaces**, at a rate set by how far the robot can drive while observing new geometry. The laboratory available permits a traversable circuit of only a few metres, much of it bounded by furniture rather than by continuous wall.'),

gap(60),
good('THE ONE-SENTENCE ARGUMENT', [
  '"The robot classifies what it drives past. A drive confined to a few metres cannot accumulate the observation the coverage criterion requires, however well the platform performs, because the criterion is a statement about how much of the mapped area has been seen."',
  'This is why the report calls it a statement about the **space**, not about the mapping layer. Everything else about the maps passes.',
]),

h3('The qualification the report volunteers, and you should too'),

p('The unclassified percentage is computed over **every cell in the published occupancy grid**, which is the bounding extent the mapper happened to allocate, not the traversable floor area. Cells the robot could never reach or see are counted in the denominator.'),

bullet('So the figure is sensitive to how large a window the mapper allocates, and it **overstates** the fraction of reachable space left unobserved.'),
bullet('It is used anyway because it is the criterion that was written down before the mapping work began, and because the same definition applies to every run compared, which makes the run-to-run comparison valid even where the absolute number is soft.'),
bullet('A coverage criterion computed over a fixed region of interest corresponding to the traversable area would be the better measure, and the report says it is owed.'),

gap(60),
warn('A LIKELY QUESTION', [
  '"So your headline failure metric is partly an artefact of your own denominator?"',
  'Answer: yes, partly, and the report says so before you ask. But the run-to-run comparison is still valid because the definition is identical across runs, and the direction of the bias is known: it makes the number look worse, not better. The right measure is over a fixed region of interest and it is listed as owed.',
]),

h3('What the constraint propagates into'),

p('This is the part that turns one limitation into four, and it is why the report treats it as the binding constraint rather than one item on a list.'),

gap(60),
code([
  '  small test area',
  '        |',
  '        v',
  '  coverage criterion fails',
  '        |',
  '        v',
  '  no accepted commissioning map',
  '        |',
  '        +--> localisation against a saved map is never exercised',
  '        |',
  '        +--> the named-location library has no coordinates to store',
  '        |',
  '        +--> autonomous navigation stays inside a live mapping session',
]),

gap(60),
p('Four entries in the status figure, and one cause. **No further work on the platform moves any of them.** A test space offering a continuous traversable loop lifts all four together.'),

p('The proposed target is fifteen to twenty metres of path, and the report is careful to say this is proposed **on the grounds that it is several times the few metres currently available, not derived from a measured coverage-accumulation rate**. Establishing that rate, and with it the path length a 50 per cent criterion actually demands, is itself one of the first measurements the new space would support. Do not over-claim this number.'),

h2('8.6  Constraint 2: rotating in place contributes almost no coverage'),

p('This is the most operationally consequential perception result in the report, and it changed a procedure.'),

gap(60),
table(
  ['Drive pattern', 'Duration', 'Occupied cells gained', 'Equivalent length'],
  [
    ['Pure rotation in place, 714 degrees', '642 s', '**43**', '2.1 m'],
    ['Arc, rotation combined with translation', '111 s', '**1545**', '77.2 m'],
    ['Full perimeter drive', '621 s', '(reference)', '88.1 m'],
  ],
  [0.36, 0.16, 0.22, 0.26],
),

gap(),
p('The arc produced **88 per cent of what a full perimeter drive accumulates, in 18 per cent of its duration.** Rotation in place produced essentially nothing: ten and a half minutes of driving for 43 cells.'),

h3('Why this mattered so much'),

p('The commissioning procedure in use had specified **rotating in place at each corner to survey the space**. That procedure discards its own corner observations. The robot was being asked to spend most of its time doing the one thing that adds nothing.'),

h3('The mechanism, and the honest scope'),

p('The thresholds governing when a scan is integrated and when a pose-graph node is inserted are both **motion-dependent**. Specifically, the configuration requires a minimum travel distance and a minimum travel heading before a new node is added. Pure rotation trips the heading threshold but the resulting node sees almost the same geometry from almost the same place, so it commits very little new occupancy.'),

gap(60),
warn('SCOPE IT CORRECTLY', [
  '"The effect is a property of that configuration rather than of lidar in general, since the thresholds governing when a scan is integrated and when a pose-graph node is inserted are both motion-dependent, and neither was varied here."',
  'Then immediately give the reason it still matters: "It is nonetheless the configuration the robot maps in, so the procedural consequence stands."',
  'That pairing, a narrow technical claim plus a real operational consequence, is exactly the register the whole report is written in.',
]),

h3('The fix'),

p('Turns are taken as **rounded arcs while rolling**, not as stationary pivots. Correcting the procedure required no hardware modification, no code change and no re-tuning. The report calls it the highest-value procedural change identified during the work, and it is: 88 per cent of the coverage for 18 per cent of the time, for free.'),

h2('8.7  Constraint 3: scan matching made the pose estimate worse'),

p('This is the headline negative result of Chapter 1. Tell it as a proper experiment.'),

h3('The measurement'),

gap(60),
table(
  ['Route', 'Range cap', 'Wheel odometry alone', 'With the scan-matching front end'],
  [
    ['38 s square, 1.42 m of path', '10 m', '2.58 cm', '**6.2 cm**'],
    ['1047 s drive, 21.85 m of wheel path', '10 m', '0.229 m, 10.53 deg', '**0.477 m, 16.18 deg**'],
    ['82.5 s circle, 3.193 m of path', '5 m', '16.2 mm, 0.51 %', '**206.7 mm, 6.47 %**'],
  ],
  [0.34, 0.12, 0.24, 0.3],
),

gap(),
p('The same wheel data and the same scans on each row, differing only in whether the front end was applied. On every route the front end **increased** the endpoint error.'),

h3('Ruling out the obvious objections, one at a time'),

num('**"Your back end never ran."** Nineteen loop closures fired during the 21.85 m drive. It ran.'),
num('**"Your range cap was too generous, so the matcher was fed noise."** The third row was run last, specifically for this. The cap was reduced from 10 m to 5 m and **verified against the live node** before the drive. The cap did not rescue the matcher.'),
num('**"The wheel odometry was unusually good on that run."** The third row carries its own control. Both estimates come from the same 3.193 m of driving, the same wheels and the same scans, with the robot physically returned to its mark. The matching-on drive\'s **own** wheel odometry closed at 16.2 mm, which is healthy, and the matched estimate on that same data closed at 206.7 mm.'),
num('**"You decided afterwards that it failed."** Four revert criteria had been written down before the drive and three fired. Of five keep criteria, the only one met was the one predicted to be neutral.'),

h3('The mechanism, which is the substantive finding'),

p('It is not enough to say it got worse. The report says **why**, and that is what makes it a result rather than a complaint.'),

gap(60),
bad('THE DIAGNOSIS', [
  'All seventeen corrections in the circle run fired at a **mean odometry spacing of 0.183 m**, with about a centimetre of spread across the whole drive. And the smallest correction in the run was **106.7 mm** against a deployed search half-width of 150 mm.',
  '"A front end that corrects at a fixed odometric interval is responding to a **schedule** rather than to disagreement between scans."',
  'The corrections track the creation of pose-graph nodes, which happen every 0.2 m of travel by configuration. They do not track whether the scans actually disagree. That also explains the zero loop closures on a route that returns to its own start: a closure would arrive off-cadence, and none did.',
]),

gap(60),
analogy([
  'A quality inspector who stamps "corrected" on every twentieth item regardless of whether anything was wrong with it. The stamps are regular, confident and entirely uninformative. Worse, each stamp moves the item, so the production line ends up further from correct than if nobody had inspected at all.',
]),
gap(),

h3('And the bounds on the finding, which you must give'),

bullet('It is bounded to **this scanner**, **this front-end configuration**, and three routes.'),
bullet('**Two of the three routes are tight circuits**, and the project\'s own notes flag circle geometry as degenerate for a matcher, because a circle shows the same walls from continuously rotating vantage points. So the third row cannot separate a matcher that fails on this robot from one that fails on circles.'),
bullet('A one-variable comparison on the 12.04 m perimeter route, against an existing matching-off baseline on identical geometry, is **still owed**.'),
bullet('Stating the result as a property of scan matching in general would go past the evidence.'),

gap(60),
good('THE DECISION THAT FOLLOWED', [
  'Scan matching is switched off. It is the one entry in the status figure that is off **by choice rather than by constraint**, and the choice rests on a measurement rather than on a preference.',
]),

h2('8.8  Constraint 4: a quarter of every scan is missing'),

p('The 90-degree self-occlusion wedge from Part 7 is a mapping constraint as well as a perception one, and it interacts badly with everything in this chapter.'),

bullet('**107 of 430 beams are masked as invalid**, permanently, in a fixed body-relative direction. A quarter of every scan is absent.'),
bullet('A genuine revisit to a known place therefore **legitimately scores lower** than it would on a full 360-degree scan, because a quarter of the evidence is simply not there.'),
bullet('That is why the loop-closure match-quality gates had to be relaxed from their stock values (coarse 0.35 to 0.25, fine 0.45 to 0.35). Stock thresholds assume a feature-rich environment and a full scan, and would reject real loop closures as if they were bad matches.'),

gap(60),
warn('AND THE COST OF RELAXING THEM, STATED HONESTLY', [
  'Relaxing the gates trades **a higher risk of a wrong closure for any closure at all**. That is the right trade when the measured state is zero closures and half a metre of drift, and it is the wrong trade the moment the map starts folding. The configuration carries a written instruction that these two gates are the first thing to raise back if a map ever visibly folds or tears.',
]),

h2('8.9  Constraint 5: the environment is ambiguous'),

p('The test space is a junction with several radiating aisles that look alike. A scan matcher comparing a new scan against the map does not just face noisy constraints there; it faces **genuinely ambiguous** ones, because several different poses explain the scan almost equally well.'),

gap(60),
analogy([
  'Finding your seat in a cinema by looking at the row you are in. Every row looks the same. Your view from row 12 is nearly identical to your view from row 13, so no amount of looking harder will tell you which one you are in. That is aliasing, and it is a property of the room, not of your eyesight.',
]),
gap(),

p('This is also why the earlier "flower petal" map shape appeared: driving down the centreline of each radiating aisle gave thin, poorly-defined edges rather than solid walls, and manual driving was changed to hug the walls instead.'),

h2('8.10  Constraint 6: the doubled-wall versus folded-map trade-off'),

p('A nice illustration that the criteria are not independent.'),

p('The run with the **best coverage** had the **worst doubled-wall figure** (2.9 per cent), because it was driven with the loosest lidar quality gate: more returns admitted means more area covered and more chance of a wall being drawn twice slightly offset.'),

p('Tightening that gate did reduce doubled walls, to 1.1 and 0.9 per cent. But it **tore the free space into disconnected regions** and the map graded folded.'),

gap(60),
good('THE JUDGEMENT, AND THE REASONING', [
  'The looser gate was retained, "on the grounds that a connected map with thicker walls is more useful than a clean one that has come apart."',
  'A planner can route through a slightly thick wall boundary. It cannot route across a gap between two disconnected free-space regions. Connectivity is the property navigation actually needs; wall thickness is cosmetic by comparison.',
]),

h2('8.11  Constraint 7: compute'),

p('slam_toolbox was killed outright by the Pi running out of CPU on at least one occasion. Two configuration consequences follow, and both are worth knowing because they are examples of paying for headroom deliberately:'),

bullet('**Interactive mode is turned off.** It lets you drag pose-graph nodes by hand in the visualiser, which this project never does, and it keeps extra state alive for the whole session. An unused feature that costs memory on a machine that has run out of it is a cost with no benefit.'),
bullet('**Map resolution stays at 0.05 m.** A 0.03 m grid would suit a narrow-aisle chassis better, and it is listed as the next single-variable test, but it costs CPU roughly as the square of the resolution change and the CPU is already the ranked blocker.'),

h2('8.12  The configuration decisions, and the reason for each'),

p('If asked "how did you tune SLAM?", the answer is not "by trial and error". Every value that was moved off stock was moved against a specific measured number. Have two or three of these ready.'),

gap(60),
table(
  ['Parameter', 'Stock', 'Here', 'The measured reason'],
  [
    ['`use_scan_matching`', 'true', '**false**', 'The three-route comparison in 8.7. Switched off on evidence.'],
    ['`max_laser_range`', '12.0', '**5.0**', 'The scatter measurement in Part 7: beyond 2.5 m the two captures do not even agree with each other, so those returns are noise carrying a number.'],
    ['`loop_match_minimum_chain_size`', '10', '**8**, earlier 5', 'At a 0.2 m travel threshold, 10 nodes means about 2 m of driving before loop closure is even **eligible** to fire. In a workspace a few metres across, most real revisits were structurally ineligible.'],
    ['`loop_search_maximum_distance`', '3.0 m', '**2.0 to 5.0 m**', 'A search radius must comfortably exceed the drift it is meant to correct, and 0.5 m of drift was measured. The 5.0 value was set for that reason; the Stage G file runs 2.0 with matching off.'],
    ['`loop_match_minimum_response` coarse / fine', '0.35 / 0.45', '**0.25 / 0.35**', 'A quarter of every scan is permanently masked, so a genuine revisit legitimately scores lower. Section 8.8.'],
    ['`correlation_search_space_dimension`', '0.5 m', '**0.3 m** (Stage G), 0.7 earlier', 'The odometry prior is imperfect (lateral slip corrected but not eliminated), so the matcher needs room to find the true pose beyond where the prior says it should be. Frozen at 0.3 while matching is off, so the comparison stays clean when it is turned back on.'],
    ['`distance` / `angle_variance_penalty`', '0.5 / 1.0', '**0.7 / 1.2**', 'Raised means trusting the odometry prior **less**. Set when odometry was known to over-report strafe by 25 per cent. A later test of this lever made the correction worse, so it was frozen rather than tuned further.'],
    ['`enable_interactive_mode`', 'true', '**false**', 'CPU and memory. Section 8.11.'],
  ],
  [0.26, 0.1, 0.16, 0.48],
),

gap(),
note('THE DISCIPLINE BEHIND THIS TABLE', [
  'One change at a time, wherever possible, because an earlier session changed six parameters at once and paid for it across three subsequent sessions. Where two were changed together, the file states why they are separable in the analysis: one changes **what** is drawn into the grid, the other changes **where** it is drawn.',
  'And a second rule, learned twice the hard way: a configuration committed to the repository is not a configuration running on the robot. Both failures in this project came from a file landing under a name nothing loads. The deploy is now hash-checked against the live file.',
]),

h2('8.13  The five-line summary of the SLAM position'),

num('Maps are produced repeatedly and reliably, and within the regions that accumulate enough observation, the recovered wall geometry is consistent across all three runs and with the layout of the room.'),
num('Three of the four acceptance criteria pass or nearly pass. The fourth, coverage, fails on all three runs and is a statement about the size of the room rather than about the mapping layer.'),
num('Rotating in place adds almost nothing. Coverage accumulates through translation, and the commissioning procedure was corrected accordingly.'),
num('Scan matching was measured rather than assumed and made the pose estimate worse on all three routes it was tested on, with a diagnosed mechanism. It is switched off.'),
num('A quarter of every scan is permanently missing behind the mast, which makes genuine loop closures score lower and forced the match gates to be relaxed, with a known and stated risk.'),

];
