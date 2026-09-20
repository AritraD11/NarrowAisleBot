const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code, figure } = S;

// One section per report figure: what is plotted, what it shows, the sentence
// to say out loud, and the question it invites.
function fig(n, title, opts) {
  const out = [h2(`Figure ${n}.  ${title}`)];
  out.push(...figure('fig' + String(n).padStart(2, '0'), opts.caption));
  if (opts.plotted) {
    out.push(h3('What is plotted'));
    (Array.isArray(opts.plotted) ? opts.plotted : [opts.plotted]).forEach((t) => out.push(p(t)));
  }
  if (opts.shows) {
    out.push(h3('What it shows'));
    (Array.isArray(opts.shows) ? opts.shows : [opts.shows]).forEach((t) => out.push(p(t)));
  }
  if (opts.say) {
    out.push(gap(40));
    out.push(good('SAY THIS', opts.say));
  }
  if (opts.ask) {
    out.push(gap(40));
    out.push(warn('EXPECT TO BE ASKED', opts.ask));
  }
  return out;
}

module.exports = [

h1('Part 10  Every figure, explained'),

p('Twenty-one figures. For each one: what is actually plotted, what it demonstrates, the sentence to deliver while it is on screen, and the question it invites. If you can do this for all twenty-one you can survive any figure the panel points at.'),

...fig(1, 'The prior work: chassis variants and the kinematic model', {
  caption: 'Reproduced from the prior laboratory study. This is the geometry the platform inherits.',
  plotted: 'Three panels from the earlier paper. Panels (a) and (b) are the two chassis variants that paper proposes: in (a) the lateral wheels sit close together, in (b) they are distributed along the length. Panel (c) is that paper\'s kinematic schematic, with the wheel origins at longitudinal distances l1 and l2 from the body centre and a half track of d.',
  shows: 'That the asymmetric non-collinear geometry is inherited, not invented here. **Variant (a) is the arrangement built.** The symbols l1, l2 and d in panel (c) are the same symbols used throughout the report.',
  say: ['"This slide is somebody else\'s result. The prior work derived the kinematics and demonstrated the principle on a small prototype. What it did not establish is whether the geometry survives the transition to a full-scale machine, and that is where my year begins."'],
  ask: ['"What exactly is your contribution then?" Answer: the transition to 45.54 kg, closed-loop control at every wheel, and the measurement campaign. A prototype shows the transformation is correct. It says nothing about whether four geared motors will hold a commanded velocity on a machine this size, whether the resulting pose estimate is good enough to navigate on, or whether a perception stack can be built on top.'],
}),

...fig(2, 'Symmetric and non-collinear wheel layouts', {
  caption: 'Drawn at the dimensions of the machine built here.',
  plotted: 'Two side-by-side plan views. On the left, the symmetric layout with all four wheels on one rectangle and one shared yaw lever arm. On the right, the non-collinear layout with one diagonal pair moved inward and two lever arms. Underneath each, the inverse kinematics that follow.',
  shows: ['In the symmetric case one coefficient, K = l + d = 0.5607 m, serves every wheel. In the non-collinear case there are two: Ko = 0.5607 m and Ki = 0.4907 m, a **14 per cent** difference.',
    'And, critically, the translation terms are byte-for-byte identical between the two. Only the yaw column changes.'],
  say: ['"Only the yaw column changes. That is the whole of the difference, and it is also the whole of the risk, because a wheel driven with the wrong lever arm produces a yaw rate wrong by 14 per cent and nothing else in the transformation gives any sign of it."'],
  ask: ['"So is the asymmetry an advantage or just a complication?" Answer honestly: the geometric advantage is real (vehicle width decouples from the wheel rectangle) and it is **not yet quantified**, because no matched symmetric baseline has been built. Objective 3 is open for exactly that reason. What can be said is that no asymmetry-specific penalty has been detected in any experiment performed.'],
}),

...fig(3, 'The machine as built', {
  caption: '1.00 m long, 0.36 m wide across the wheels.',
  plotted: 'A photograph of the platform on the laboratory floor.',
  shows: ['The four mecanum wheels sitting non-collinearly rather than at the corners of a rectangle: the pair nearer the camera is visibly offset along the length from the pair behind. The vertical mast carrying the three ultraviolet tubes and the stepper axis of the cargo arm. The lidar, the black unit above the battery.'],
  say: ['Point at the wheels first, because the offset is genuinely visible and that makes the geometry concrete before any equation. Then point at the mast: "the mast and its payload sit within the plane of the lidar, and they are the cause of the 90-degree self-occlusion sector measured later."'],
  ask: ['"Why is the lidar so low, under the mast?" Answer: it is mounted above the battery for cable routing and for a clear forward view, and the consequence is measured rather than guessed. Raising it above the payload is the obvious fix and would cost mast height and stability. The masking approach was chosen because it costs nothing and the wedge is measurable.'],
}),

...fig(4, 'The physical platform and the commissioning measurements', {
  caption: 'Photographed during hardware trials, 11 August 2026.',
  plotted: 'Four panels. (a) A top-down view with the body axis convention marked by hand and the lidar at its mounting position. (b) The corresponding view in the visualiser. (c) and (d) The start and end frames of the forward-drive test used to establish the lidar angular convention.',
  shows: ['That the axis convention was established **empirically**, by driving against a placed block and recording the result, rather than assumed from the data sheet.'],
  say: ['"Establishing which way the scanner counts its angles took a drive against a placed block, recorded start to end, because nothing on the sensor says which way it is looking. A fault of that kind is trivial to correct once identified and costly for as long as it is not."'],
  ask: ['"Is that not in the manual?" Answer: the manual describes a class of part. This is about the installed unit in its installed orientation, and the mirror-convention bug it uncovered had already been silently corrupting the map. The general rule this project works to is to verify against the running system rather than against a document.'],
}),

...fig(5, 'Deployed electronics, end to end', {
  caption: 'Three layers, each on its own rail colour: power distribution, compute and command, drive with odometry feedback.',
  plotted: 'A full system schematic. Power from the battery up to the 24 V drive rail and down to the 5 V logic rail; compute and command; drive with its odometry return through the level translator.',
  shows: ['The complete signal and power topology, and in particular that the level translator sits only on the encoder returns, not on the command path.'],
  say: ['Do not walk this figure block by block. Trace **one** path and stop: battery to the drive rail, the ESP32 command out to a driver, the encoder return back through the level shifter. Then say the one thing the figure is really for: "the encoder rows carry their wire colours, because the front and rear motors do not share a convention, and that difference has already put a channel on the wrong pin once during commissioning."'],
  ask: ['"Why is the translator only on one side?" This is the good question and you should welcome it. Answer: the drivers threshold at 1.5 V and accept 3.3 V directly, so no translation is needed there. Fewer components in the command path is worth having, because a fault in the command path moves the machine while a fault in the feedback path only misreports it.'],
}),

...fig(6, 'Asymmetric wheelbase geometry', {
  caption: 'Dimensioned plan view, taken from the mechanical assembly.',
  plotted: 'The chassis in plan, with the outer diagonal pair at 403 mm from the body centre along the longitudinal axis, the inner pair at 333 mm, and the half track width marked.',
  shows: ['The 70 mm offset that is the entire geometric novelty, and both width figures: 360 mm by tape and 375.4 mm derived from the assembly.'],
  say: ['"Two width figures appear in this report and they measure the same span by different means. The 360 mm is the tape measurement of the built machine and is what every experimental result and the collision footprint are referenced to. The 375.4 mm is derived from the assembly. They differ by 15.4 mm, and in a corridor with centimetres of clearance that is not a rounding detail, which is why the report says which one it used."'],
  ask: ['"Which one is right?" Neither is wrong; they measure differently. The tape figure is the one the robot is operated against, because a collision footprint has to match the physical object, not the drawing.'],
}),

...fig(7, 'The per-wheel velocity loop', {
  caption: 'As the deployed firmware runs it, one loop for each of the four wheels at 100 Hz.',
  plotted: 'A block diagram of one control loop. Green marks the three blocks this firmware version added, orange the command path out to the wheel, purple the controller and the measurement path back from the encoder. Two notes at the left carry details a block diagram cannot show.',
  shows: ['That this is not a plain PID. The two-term feedforward sits in the forward path and supplies most of the drive; the three feedback terms sit in a correction path.'],
  say: ['"The feedforward supplies most of the drive from the commanded velocity alone, and the three feedback terms correct only what the feedforward gets wrong. That separation is what permits the integral gain to be as large as it is without the loop becoming oscillatory."'],
  ask: ['"What are the two notes at the left?" They are the things a block diagram cannot express: that the derivative acts on the measurement rather than the error, so a stepped setpoint produces no derivative kick, and that the integral clamp is recomputed every tick against the authority actually left over.'],
}),

...fig(8, 'The feedforward model', {
  caption: 'The two-term model fitted against measured open-loop data.',
  plotted: 'Left panel: steady-state drive count against commanded wheel speed, with the measured points from three campaigns, the fitted two-term model, and a single-slope model for comparison. Right panel: the residuals, with the two high-confidence points marked.',
  shows: ['That a single slope through the origin systematically **under-drives** the wheels at low speed, and that adding a static term fixes it. Every measured point lands inside 8 per cent, and the two high-confidence points inside 2.2 per cent.'],
  say: ['"The inadequacy of a single-slope model is evident in the raw data, before any fit is attempted: the ratio of drive command to resulting wheel speed rises as speed falls, which is the signature of a breakaway friction term that a straight line through the origin cannot reproduce."'],
  ask: ['"How well separated are your two coefficients?" Volunteer the limitation before it is asked. Every measurement sits between 1.8 and 2.8 rad/s, and over that narrow span many pairs fit almost equally well: Kff 34.5 with Kstat 15 is barely distinguishable from Kff 38 with Kstat 8. What is well determined is the value of the whole expression across the measured range, which is what the controller consumes. Separating them properly needs a staircase test that has not been run.'],
}),

...fig(9, 'Closed-loop tracking', {
  caption: 'Wheel velocity against command, with the wheels free of the ground.',
  plotted: ['Panel (a): the front-right wheel over the full 90.8 s run, commanded and measured, with a shaded band marking the region expanded below. Panel (b): the largest commanded step in the run, expanded, plotted against time relative to the step edge, one marker per 20 Hz log sample. Panel (c): tracking error for all four wheels across the whole run.'],
  shows: ['(b) is the quantitative core: the wheel reaches within 5 per cent of the commanded -2.207 rad/s in **0.20 s**, overshoots by **3.5 per cent**, and then holds the level to a mean offset of **0.003 rad/s**.',
    '(c) is the qualitative core: the error excursions coincide with **commanded step edges**, not with steady state. A loop that was badly tuned would show error during the steady sections too.'],
  say: ['"The step transient occupies three to four log samples, which is why it appears in panel (a) as a vertical edge. Panel (b) is the same event expanded so you can see it is a clean first-order response with a small overshoot, not a ringing one."'],
  ask: ['"Your logging is at 20 Hz but your loop runs at 100 Hz. Are you seeing the real transient?" Honest answer: the transient occupies three to four log samples, so it is sampled but coarsely. The overshoot and steady-state figures are reliable; a settling-time figure to the millisecond would need faster logging.'],
}),

...fig(10, 'Ground load', {
  caption: 'Steady-state drive demand per unit wheel speed, unloaded against loaded.',
  plotted: 'Left panel: the same controller, unloaded and loaded, per motor. Right panel: the measured percentage increase per motor against the band predicted before the run.',
  shows: ['Measured increases of **22.5, 23.6, 30.3 and 21.0 per cent**, a mean of 24, against a band of 10 to 30 per cent written down in advance. Three motors fall inside. The rear-right reaches 30.3, which is **0.3 points above its upper bound**, and is reported as an exceedance rather than rounded into agreement.'],
  say: ['"The ground-load result is stated as a prediction and a test rather than as an observation, because the predicted band was written down before the run. That is one of this project\'s two standing conventions; the other is that configuration is verified by querying the running system rather than by reading a file."'],
  ask: ['"Is 24 per cent a reliable number?" No, and say so. Two later runs the same afternoon, at the same commanded levels but over different patches of floor, gave means of 14 and 3 per cent. The increase is real; its size is not established to better than the width of the band it was predicted against. The likeliest reason is the surface rather than the load, and a staircase test holding position and sweeping demand is what would settle it. It has not been run on the floor.'],
}),

...fig(11, 'Endpoint closure', {
  caption: 'Wheel-odometry trajectories for three logged drives, each driven manually and returned to its starting mark.',
  plotted: 'Three plan-view trajectories, plotted from the recorded pose, with the start and end marks shown on each.',
  shows: ['Closure of 19 mm over 8.00 m, 28 mm over 9.61 m and 96 mm over 10.61 m: **0.23, 0.29 and 0.91 per cent** of path travelled.'],
  say: ['"The longest of the three, which includes the most rotation, closes at 0.91 per cent. Error grows with the amount of rotation a route contains as well as with its length, which is consistent with the increased lateral roller motion expected during rotational manoeuvres."'],
  ask: ['"Can you generalise that to a warehouse aisle?" No, and the report says so explicitly. On an 18 m route the same estimator closed 0.229 m, 1.27 per cent, and on a second long route 0.257 m over 18.14 m, 1.42 per cent. The defensible statement is bounded: below 1 per cent out to about 10 m, 1.1 to 1.5 per cent on the longest routes driven. Separating length from rotation needs routes that vary the two independently, which needs a larger space.'],
}),

...fig(12, 'Self-occlusion', {
  caption: 'The occluded sector, re-measured at five independent headings.',
  plotted: 'A polar diagram in the corrected body frame, showing the wedge that returns a close reading at every heading, and a panel distinguishing the two failure modes that unmasked returns would cause.',
  shows: ['A wedge of approximately **90 degrees** centred on directly behind the robot, covering **107 of the 430 beams** returned per revolution.'],
  say: ['"Real features move in the laser frame as the robot rotates. Self-occlusion does not. That invariance is the discriminator, and it needs no props, no reference objects and no physical construction. One contiguous bearing block returned a close reading in all five independent headings at consistent percentages; every other sector that any single run flagged appeared in that run and nowhere else."'],
  ask: ['"Why mask rather than mark occupied?" Because a fixed-bearing occupied cell translates and rotates with the robot: a permanent obstacle welded to the chassis that can never be cleared, which inflation then expands until the planner concludes that entire direction is blocked. And you cannot mark it free either, because a clearing beam would erase real obstacles behind the mast. A beam carrying no information must be dropped, not reinterpreted.'],
}),

...fig(13, 'Rotation and mapping coverage', {
  caption: 'Map coverage accumulated under three drive patterns.',
  plotted: 'A bar chart of occupied-cell equivalent length for three drives: pure rotation in place, an arc combining rotation with translation, and a full perimeter drive.',
  shows: ['A deliberate 714-degree rotation over 642 s produced **43 occupied cells**, 2.1 m on this measure. A 111 s arc produced **1545 cells**, 77.2 m, which is **88 per cent of a full perimeter drive\'s coverage in 18 per cent of its duration**.'],
  say: ['"This is the most operationally consequential perception result obtained. The commissioning procedure in use had specified rotating in place at each corner to survey the space. That procedure discards its own corner observations. Coverage accumulates through translation, so turns must be taken as rounded arcs while rolling rather than as stationary pivots. Correcting it required no hardware modification."'],
  ask: ['"Why does the total exceed the perimeter of the room?" Because the quantity is an occupied-cell **equivalent length**: occupied-cell count times the 0.05 m cell size. It is a proxy for how much occupancy the map has committed to, not a physical wall length, and a single wall rendered several cells thick contributes several times its own length. Have that answer ready; the number does look odd.'],
}),

...fig(14, 'Commissioning maps', {
  caption: 'The three maps of 15 September, rendered from the saved occupancy grids.',
  plotted: 'Three occupancy grids side by side, with the driven path overlaid on each. Grey regions are cells that never accumulated enough observation to be classified.',
  shows: ['Within the classified regions, the recovered wall geometry is **consistent across all three runs** and with the layout of the room, and the robot returns to its starting mark in each case. The grey regions are the criterion that fails.',
    'The driven path is visible as a small loop near the origin in each panel, which is the coverage problem seen directly.'],
  say: ['"The driven path is that small loop. The robot cannot classify what it cannot drive past, and the available circuit is a few metres. Unclassified cells occupy 73.0, 78.3 and 84.6 per cent against a threshold of 50. That is a statement about the space rather than about the mapping layer, because everything else about these maps passes."'],
  ask: ['"Is your coverage metric fair?" Volunteer the answer: the percentage is computed over every cell in the published occupancy grid, which is the bounding extent the mapper allocated rather than the traversable floor area, so it **overstates** the fraction of reachable space left unobserved. It is used because it is the criterion written down before the mapping work began and because the same definition applies to every run compared. A criterion over a fixed region of interest would be better and is owed.'],
}),

...fig(15, 'System validation status', {
  caption: 'Each layer with the measurement that supports it, or the reason it has none.',
  plotted: 'A two-part status board. The upper half lists layers that are established, with the measurement against each. The lower half lists layers that are not, with the specific reason against each.',
  shows: ['That the evidence is **not all of one kind**. Closure against the floor is an external reference. The kinematics and odometry rows are checks against an independent implementation. The planner, controller and safety rows are operational demonstrations rather than measurements against a reference.',
    'And that three components work correctly but run **below their requested update rates** because of the processing available on the host.'],
  say: ['"For the five layers that are not yet established, the entry states the specific reason rather than recording a failure. And in three of those five the reason is the size of the available test area rather than anything on the platform. Four entries, one cause."'],
  ask: ['"Which of these would you fix first?" The test space, because it lifts four entries at once and no work on the robot moves any of them. Then the inertial sensor, because it has a measured target to be tested against.'],
}),

...fig(16, 'The appliance and the sensing node', {
  caption: 'Both units as built.',
  plotted: 'Panel (a): the integrated air-treatment unit, an aluminium duct on a stand with the germicidal lamp inside, the control enclosure mounted on top near one end, and the 120 mm fan set into the end face. Panel (b): both control boxes powered and linked, with the two helical antennas and the transparent panels visible.',
  shows: ['The physical arrangement, and that the electronics sit **outside** the treated air path: the only things inside the duct are the lamp and the airflow.',
    'The displays are reading live, which is how a node is checked in the laboratory without attaching a computer to it: irradiance and gas state on the left, uptime and firmware build on the right.'],
  say: ['"The enclosure was designed rather than bought. Acrylic, each face a separate panel held by printed corner standoffs, so any one face can come off without disturbing the others. And one correction worth recording, because earlier project documents have it wrong: the enclosure is not a cube. The photographs show a box visibly wider than it is deep."'],
}),

...fig(17, 'Monitoring and control architecture', {
  caption: 'End to end, from the devices on the edge node through three communication channels to the containerised stack.',
  plotted: 'A full architecture diagram. Blue is telemetry travelling outward from the node; orange is a command travelling back to it; red marks the one measurement channel that is fitted, reads, and does nothing.',
  shows: ['That the three channels are **not variants of one path**. Only the Wi-Fi telemetry passes through the message broker. The radio path never touches it, because the gateway speaks a framed serial protocol and its service writes to the database directly. And the cellular path is **not ingested at all**: it delivers a message to a person, and nothing on the server records it.'],
  say: ['"The figure is drawn so each channel can be followed separately, because the three arrive at three different places and only two of them reach the database. A reader who assumes all three converge on the broker would draw the wrong conclusion about what a server outage costs."'],
  ask: ['"Why concurrent rather than failover?" Because a failover design must **detect** failure before it can switch, and detection is the first thing to fail in a dead network. Running independent channels concurrently avoids that dependency at a bandwidth cost a low-rate telemetry system can absorb.'],
}),

...fig(18, 'The operator dashboard in service', {
  caption: 'Photographed off the screen rather than captured from it.',
  plotted: 'Panel (a): the status view for one zone. Panel (b): the trend view, whose legends expose the stored tag structure.',
  shows: ['The deployed system in a single consistent operating state: the gas index below its actuation threshold with the lamp correspondingly off, and the carbon dioxide reading at the same instant above its alert threshold with an alert raised on all three channels.'],
  say: ['"That establishes the deployed logic produces the configured actuator and alert states for the inputs present at an instant. What it does not do is show the control path responding to a change. A time-resolved recording, with the measurement, the threshold crossing, the actuator command and the response on one time axis, is the next capture the control path needs, and it is straightforward to take on the running system."'],
  ask: ['"Why photograph the screen rather than screenshot it?" It is the primary record as captured, including the operator\'s own annotation, and the report keeps it alongside the regenerated counterpart rather than replacing it. The figure also happens to catch the system 40 ppm above the carbon dioxide threshold, which is well inside the range where the alert path flaps, which is a known defect stated in the text.'],
}),

...fig(19, 'The operating condition, and where each method stops', {
  caption: 'The conditions any instrument would have to work in, against the class of method now in use and why each fails.',
  plotted: 'Two columns. The left states the operating conditions of an Indian warehouse floor. The right pairs each established class of fatigue measurement with the specific reason it does not survive those conditions.',
  shows: ['That the three reasons are **not equivalent**, which is the whole argument for the strand. Subjective report is unreliable at its source, and no instrument corrects that. Contact methods are reliable in themselves and cannot be maintained in contact across a ten-hour shift above 40 degrees.'],
  say: ['"The contact methods fail for a limitation of the **instrument** rather than of the measurement principle, and that is therefore a tractable failure. It is that second class of failure, and only that class, which this strand addresses."'],
  ask: ['"Why not just improve the wearables?" Fair question, and the honest answer is that the objections are practical rather than evidential: discomfort over an eight-hour shift, electrode contact degrading with perspiration, compliance depending on the worker choosing to wear it, and a daily charging burden across hundreds of people. None is fatal alone. Together they are why the strand asks whether the measurement can be made without contact at all.'],
}),

...fig(20, 'The proposed pipeline, capture to score', {
  caption: 'One crossing of the monitored zone, from capture to a single score.',
  plotted: 'Four contactless streams reduced on the node itself, each supplying a distinct fatigue indicator, feeding a fused estimate. A dashed rule marks the limit of what the proposal fixes.',
  shows: ['The sensor set, the mounting, and the two design decisions that carry most of the risk. Everything to the right of the dashed rule is design rather than specification.'],
  say: ['"The fused estimate is computed without any raw video or point cloud leaving the sensor bracket, which is what makes the privacy position a property of the architecture rather than an undertaking. India\'s data protection legislation of 2023 makes a device that extracts a derived score a different legal object from one that streams a camera feed to a server."'],
  ask: ['"Could this become surveillance?" Meet it head on. Gait carries enough information to identify a person; the point-cloud benchmark cited in the review exists to demonstrate exactly that. A system installed to estimate fatigue must not become one that recognises individuals, so the pipeline has to discard identity **by construction rather than by policy**. That constrains which features may be retained and what may be stored, and it is easier to design for at the start than to retrofit.'],
}),

...fig(21, 'The three objectives, and the reference each is measured against', {
  caption: 'Where Figure 20 gives the signal path, this gives the order of work.',
  plotted: 'Three objectives in sequence, each with the external reference it would be validated against in the right-hand column.',
  shows: ['That the strand is set up to be **falsified**. Gait from the camera and the lidar is checked against marker-based motion capture, which is an external physical reference rather than another estimate. A subset of volunteers wears surface electromyography at the same time as the contactless capture, so the proposed method is compared directly against the established method it proposes to replace, on the same subjects during the same task.'],
  say: ['"Reading down the right-hand column establishes the order: a modality that has not been checked against motion capture cannot sensibly be fused, and a fused score has nothing to be compared against until the contact reference has been recorded on the same subjects during the same task. The comparison that decides it is the last row: the fused score must beat all four single-modality baselines plus an ablation. A fused score that cannot beat the best single modality has bought nothing for four sensors and an edge processor."'],
  ask: ['"Why set that bar now, before any data?" Because it is exactly the comparison that becomes easy to avoid once a pipeline exists and produces plausible-looking numbers. Registering it in advance is the same discipline as writing the ground-load prediction down before the run.'],
}),

];
