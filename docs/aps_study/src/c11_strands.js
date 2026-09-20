const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('Part 11  Strand two: environmental monitoring'),

h2('11.1  The argument for building it'),

p('Two considerations motivated the strand, and both are about the difference between measuring and acting.'),

num('**Environmental variables relevant to storage conditions and worker exposure are measurable, but are not necessarily incorporated into the control of air-treatment systems.** The sensing exists; the loop does not.'),
num('**Timer-based operation of treatment equipment provides no feedback from the condition of the air being treated.** Open-loop operation cannot adapt treatment to changing conditions and cannot indicate whether treatment is required at all.'),

p('The narrower form of the argument is the one to use in a viva, because it is concrete:'),

gap(60),
analogy([
  'A room heater on a mechanical timer. It runs from six to eight every evening whether the room is cold or not, and it has no idea whether its own element has burnt out. You would only find out by noticing the room is cold.',
  'A treatment duct on a timer is the same object. **It cannot raise airflow when the air is contaminated, and it cannot report the failure of its own lamp.**',
]),
gap(),

p('And why local rather than cloud: cloud-hosted monitoring makes continuity of monitoring depend on external connectivity. For a facility where the monitored condition matters **most during a disruption**, that dependency is misplaced. A locally hosted data platform removes it.'),

h2('11.2  The node, and why each part is there'),

gap(60),
table(
  ['Part', 'What it does', 'Why this one'],
  [
    ['Arduino UNO R4 WiFi', 'The sensing node.', 'Enough for five sensors on one bus and two actuators, with an integrated radio. No real-time requirement here, so the ESP32-class argument from the robot does not apply.'],
    ['Sensirion SCD40', 'CO2, temperature and humidity.', '**Three quantities, one device, one calibration.** A photoacoustic CO2 sensor rather than a cheap metal-oxide proxy, so the reading is a concentration rather than an index. 400 to 5000 ppm.'],
    ['MPM10-AS optical counter', 'PM2.5 and PM10 particulate mass.', 'Optical counting gives a mass concentration at two size fractions, which is what both product quality and worker exposure standards are written against.'],
    ['MQ-135 metal-oxide module', 'A general reducing-gas index, 0 to 500.', 'Cheap and sensitive, but **non-selective**: it responds to a mixture of reducing gases rather than to any one species. That is exactly why the report calls its output an index and not a concentration.'],
    ['GUVA-S12SD photodiode', 'Ultraviolet irradiance, 240 to 370 nm.', 'The only way to confirm the lamp is actually emitting. This is the sensor that turns the unit from a timer into a closed loop, and it is the one with an outstanding calibration.'],
    ['LCD1602, eight rotating screens', 'Local status display.', 'So a node can be checked in the laboratory **without attaching a computer to it**. A surprisingly practical thing to have.'],
    ['Opto-isolated relay', 'Switches the lamp mains.', 'Opto-isolation means **no electrical path** between the mains side and the logic. Non-negotiable when a microcontroller shares an enclosure with switched mains.'],
    ['120 mm four-wire fan', 'Airflow, driven by a duty-cycle command with the tachometer read back.', 'The tachometer is the point. It makes this **the one actuator in the system whose response can be confirmed rather than assumed.**'],
    ['Two isolated 12 V supplies, one common ground', 'Power.', 'Not elegance: see 11.4. It exists to prevent a measured failure.'],
  ],
  [0.22, 0.28, 0.5],
),

h2('11.3  Three channels at once, not a failover chain'),

gap(60),
table(
  ['Channel', 'What it carries', 'Where it ends up'],
  [
    ['**Wi-Fi**', 'A full message every 5 s.', 'A broker on the server, then a flow engine, then the time-series database.'],
    ['**Long-range radio**', 'At most 240 bytes every 30 s.', 'A second microcontroller acting as a gateway; a dedicated service reads that gateway over serial and writes to the **same database with the same schema**, distinguished only by a source tag.'],
    ['**Cellular**', 'A short message on any threshold breach, on the corresponding clear, and a summary every 30 minutes.', '**A person.** Nothing on the server records it.'],
  ],
  [0.16, 0.38, 0.46],
),

gap(),
good('THE DESIGN ARGUMENT, AND IT IS A GOOD ONE', [
  '"A failover design must **detect** failure before it can switch, and detection is the first thing to fail in a dead network. Running independent channels concurrently avoids that dependency at a bandwidth cost that a low-rate telemetry system can absorb."',
  'Most facility monitoring systems arrange their radios as a chain: try Wi-Fi, fall back to radio, fall back to cellular. This one does not, on that reasoning.',
]),
gap(),

p('And the honest reading of the architecture: **only two of the three reach the database.** A reader who assumes all three converge on the broker would draw the wrong conclusion about what a server outage costs.'),

p('The cellular channel is also the only one bidirectional at the human end. The node accepts the same command vocabulary on every channel, including text messages from a handset, so an operator with no network access can still ask a node for a snapshot or switch its lamp. Dashboard commands travel one of two ways, selected at runtime by a variable read from the browser address rather than by a firmware change, which is what lets a zone move in and out of coverage without anything being reflashed.'),

h2('11.4  Three design decisions that were responses to observed failures'),

p('Say this phrase exactly: these were **responses to observed failures, not anticipatory choices.** That is a stronger claim than good design, because each one is a fault that was diagnosed and engineered out.'),

num('**Driving the long-range radio directly from the host computer\'s pins was attempted and abandoned.** The command protocol requires deterministic timing that a non-real-time operating system does not provide, and scheduler jitter produced dropped packets that were **indistinguishable from radio link failures**. Interposing a dedicated microcontroller moved the timing-critical work to where timing is deterministic. Note the parallel with the ESP32 argument on the robot: the same principle, arrived at independently, in a different strand.'),
num('**The cellular modem draws approximately 2 A in transmit bursts.** Sharing a supply rail with the microcontroller produced brownout resets. Two supplies with a single common ground point eliminated them.'),
num('**The three channels run concurrently rather than as a chain**, for the detection reason above.'),

gap(60),
bad('TWO THINGS STATED RATHER THAN IMPLIED', [
  '**Separation between the two co-located deployments is by network identifier**, which the transceiver filters at the protocol layer, so the two operate without physical frequency separation. That is a documented vendor feature rather than a contribution of this work, and it is an **addressing filter, not a security mechanism**: the control path carries no message authentication, so any transmitter within range configured to the right identifier can actuate a lamp. Acceptable on an isolated laboratory network. Not acceptable anywhere else.',
  '**The two deployments were configured on different frequencies, and neither matches the delicensed band available in India.** The link works and the deployment is a bench one, so this has obstructed nothing, but it would have to be settled before the system went near a real facility.',
]),

h2('11.5  The control law'),

p('Actuation is driven from the gas index, with hysteresis and a dead band.'),

gap(60),
table(
  ['Element', 'Rule', 'Why'],
  [
    ['Lamp', 'On above an index of **200**, off below **150**.', 'The two thresholds are separated by a band in which nothing changes, so the relay cannot chatter around a single setpoint.'],
    ['Fan', 'Not switched but **ramped**, from half command at the lamp-on threshold to full command at an index of 500.', 'Proportional response rather than on-off. Worse air means more airflow, continuously.'],
    ['Fan floor', 'Never below half duty while the lamp is energised.', 'Irradiating stationary air accomplishes little. The lamp and the airflow are two halves of one treatment.'],
    ['Alerts', 'Fire simultaneously on all three channels; the state is **latched**.', 'A sustained breach does not generate a message on every cycle.'],
    ['Particulate handling', 'Evaluated only when the reading is valid; a sensor that fails to respond is transmitted as a **negative marker** rather than as zero.', 'A failed sensor never raises a false alarm, and a broken particulate sensor stays distinguishable from genuinely clean air. Zero would look like perfect air.'],
  ],
  [0.18, 0.4, 0.42],
),

gap(),
bad('THE DEFECT IN THE ALERT PATH, AND IT IS A REAL ONE', [
  '**The alert path does not have the dead band the control path does.** It compares a noisy signal against a bare threshold, so a reading sitting near a limit flaps, and each transition sends a message.',
  'Figure 18 happens to catch the system 40 ppm above the carbon dioxide threshold, which is well inside that flapping range. Point at it yourself rather than hoping nobody notices.',
]),

h2('11.6  What the source-level audit found, and what it fixed'),

p('A firmware audit was carried out during the reporting period and its findings have since been implemented. Four items, and the first is the important one.'),

num('**Lamp-failure detection now runs from the irradiance measurement the unit was already taking.** Once the relay has been closed for longer than the lamp strike time, irradiance above a threshold is required, and its absence raises an alert. **That is the capability that separates the unit from a timer.** Before the fix, the sensor was fitted, it read, its value reached the display and both telemetry payloads, and it appeared in no control path and no alert path, which meant the loop described in project documents as taking two inputs in fact took one.'),
num('**The operator off-command persists** rather than being reverted by the automatic law on its next pass. The on-commands always did clear automatic mode; the off-command did not. The off command is the one an operator issues to **halt** automatic actuation, which makes this a safety defect rather than an inconvenience.'),
num('**The cellular inbox poll no longer blocks the main loop**, which removed the publish jitter and the command latency together.'),
num('**The gas channel is driven from the stored calibration** rather than from a rescaled analogue count. A calibration routine had been running at first boot, computing a value, storing it, and the control law had never read it.'),

h2('11.7  What is deployed, and what it does not establish'),

gap(60),
table(
  ['Established', 'Not established'],
  [
    ['Four zones across two radio-isolated installations sharing one database. All three channels, both control paths and the dashboards in service. Automatic recovery after a power interruption without intervention.',
     'That the system has been shown **responding to a change**. The capture shows one consistent operating state at one instant.'],
    ['The deployed logic produces the configured actuator and alert states for the inputs present at an instant.',
     'A time-resolved recording, with the measurement, the threshold crossing, the actuator command and the response on one time axis. Straightforward to take on the running system and owed.'],
    ['An engineering result: a complete system taken from nothing to a deployment running unattended.',
     'A **measured** result. The report is careful about the difference and so should you be.'],
    ['Transferability is designed for: zones are templated, the database takes one schema regardless of transport, and adding an installation means adding a node and a zone identifier.',
     'Transferability is **demonstrated**. The system has so far been deployed in one application, and transferability is a design expectation rather than a demonstrated result.'],
  ],
  [0.5, 0.5],
),

gap(),
warn('WHAT REMAINS IS INSTRUMENTATION, NOT SOFTWARE', [
  'Two channels need a physical reference before their readings can be quoted as quantities: **the gas channel against a reference gas**, and **the ultraviolet channel against a reference radiometer at a fixed geometry**.',
  'The responsivity coefficient that converts photodiode voltage to irradiance is a property of the installed part and **cannot be recovered from firmware**. That is why this is an instrument problem rather than a development-time problem, and it is a good distinction to be able to draw.',
]),

h1('Part 12  Strand three: contactless fatigue assessment'),

h2('12.1  Open by saying what it is not'),

p('The single best move on this chapter is to state its status before anyone asks. It is a hypothesis, a completed literature survey and a research proposal built on both. **No hardware has been built, no data has been collected, and nothing has been measured.**'),

p('Then give the reason it is in the report anyway: because the argument is already specific enough to state, to criticise and to **test**, and because the first year of a doctorate is the right time to establish whether a direction is worth pursuing at all.'),

h2('12.2  The setting'),

gap(60),
table(
  ['Fact', 'Figure'],
  [
    ['People employed in India\'s logistics and warehousing sector', 'over **22 million**'],
    ['Recorded workplace incidents per year', 'more than **26,800**'],
    ['Share of that workforce in the unorganised sector, where occupational health protocols are minimal or absent', 'nearly **70 per cent**'],
    ['Typical shift', '**ten to twelve hours**, sustained walking and lifting'],
    ['Ambient temperature', 'routinely exceeds **40 degrees C**'],
  ],
  [0.7, 0.3],
),

gap(),
p('Occupational heat stress in Indian workplaces has been measured directly, with documented exceedances of established thresholds and associated health and productivity consequences, across steel, construction and multi-sector settings.'),

h2('12.3  Why every existing method fails, and why the reasons are not equivalent'),

p('This distinction is the whole argument for the strand. Get it right.'),

gap(60),
table(
  ['Method class', 'What it is', 'Why it fails here', 'Tractable?'],
  [
    ['**Subjective instruments**', 'Sleepiness and perceived-exertion scales, vigilance tests. The accepted references.', 'They **interrupt the work they are measuring**, which rules them out as a continuous signal. And they are unreliable at source.', '**No.** No instrument corrects an unreliable source.'],
    ['**Contact-based physiological monitoring**', 'Surface electromyography with inertial measurement. Reports 87.9 per cent accuracy on induced fatigue under leave-one-subject-out validation across 35 participants.', 'Requires skin-contact electrodes and per-subject placement. Cannot be maintained across a ten-hour shift above 40 degrees.', '**Yes.** This is a limitation of the **instrument**, not of the measurement principle.'],
    ['**Driver drowsiness systems**', 'The most mature deployed fatigue systems. Thermal facial imaging alone reaches 82 per cent against observer-rated drowsiness in a simulator.', 'They assume a **seated, stationary, forward-facing, cooperative** subject at a fixed distance. A worker walking an aisle under load satisfies none of those.', 'Partly, and that is what this strand attempts.'],
  ],
  [0.2, 0.3, 0.32, 0.18],
),

gap(),
good('THE SENTENCE', [
  '"It is that second class of failure, and only that class, which this strand addresses."',
]),

h2('12.4  The hypothesis, stated so it can be wrong'),

p('**The hypothesis:** physical fatigue shows itself as a **correlated signature across several physiological domains at once**: gait regularity deteriorating, heart and respiration rates rising, and facial skin temperature climbing.'),

p('**What follows if it holds:** a system watching all of those at the same time should beat any system watching one of them, and it should beat it hardest under exactly the conditions where single modalities struggle, which are occlusion, heat and an uncontrolled floor.'),

p('**The gap:** the fusion of contactless modalities for whole-body physical fatigue assessment in an uncontrolled industrial environment. No study meeting the criteria used in this review was identified.'),

gap(60),
warn('BOUND THE GAP CLAIM, BECAUSE IT IS THE EASIEST THING TO ATTACK', [
  'The review covered the publication record indexed through Crossref and the scite database, searched between June and September 2026, on combinations of fatigue, gait, thermal imaging, millimetre-wave radar and lidar with industrial, occupational and warehouse qualifiers, and admitted peer-reviewed work only.',
  '**It is a bounded search rather than an exhaustive one, and the claim should be read as a gap in a search rather than a gap in the field.** Say that yourself. A panel member who has read one paper you missed will otherwise use it to discredit the whole chapter.',
]),

h2('12.5  The four modalities, and what each is for'),

gap(60),
table(
  ['Modality', 'What it recovers', 'Why it is in the set', 'Reported accuracy in the literature'],
  [
    ['Camera with on-device pose estimation', 'Two-dimensional gait: stride, cadence, trunk sway, left-right asymmetry.', 'Cheapest and richest. Gait is the primary hypothesised signal.', 'Mean absolute error of 0.02 s on temporal parameters and 4.0, 5.6 and 7.4 degrees on sagittal hip, knee and ankle angles, against marker-based motion capture.'],
    ['Solid-state lidar', 'The same geometry in three dimensions, adding step width and centre-of-mass motion.', '**Insensitive to illumination**, which a warehouse aisle is not.', 'A point-cloud gait benchmark establishes the signal carries enough information to identify individuals, which this strand must constrain rather than exploit.'],
    ['60 GHz millimetre-wave radar', 'Heart rate, respiration and their variability, **through clothing**.', 'Neither of the other two can see a heartbeat.', 'Correlating with a reference sensor at 94 per cent on respiration and 80 per cent on heart rate, **established for near-stationary subjects** and degrading with body motion, which the surveyed literature treats as an open problem.'],
    ['Long-wave infrared camera', 'Facial skin temperature and the forehead-to-cheek gradient.', 'Responds to thermal strain, which in a 40-degree facility is likely to carry more information than it would in a temperate one.', 'Used to detect exercise-induced fatigue directly, subject to the absolute accuracy limits of low-cost sensors.'],
  ],
  [0.2, 0.22, 0.24, 0.34],
),

h2('12.6  The two design decisions that carry the risk'),

num('**Capture is fixed and single-subject.** Rather than tracking several people continuously across a floor, the node sits at **one point everybody passes**, an aisle end or a doorway, mounted two and a half to three and a half metres up and angled down, working at one to five metres. Each crossing yields one clean measurement of one person.'),

p('That trades coverage for tractability, and it is the trade the strand makes deliberately. Continuous multi-person tracking is a harder problem than the one being asked about, and solving it is **not a prerequisite** for answering whether fatigue is legible at all.'),

num('**Every feature is referred to the worker\'s own baseline**, recorded at the start of their shift, before it reaches the model.'),

gap(60),
analogy([
  'Judging whether someone is ill by comparing their temperature today against **their own** temperature yesterday, rather than against a population average. People differ enormously; the same person over one shift differs much less. The within-subject change is the quantity the question is actually about.',
]),
gap(),

p('The fusion itself is a convolutional branch per stream followed by a recurrent stage over the sequence, with attention across the modalities so the model can lean on whichever streams are usable when one is occluded. It produces a single number per crossing, computed on the node, and no raw video leaves it.'),

h2('12.7  The constraint the design respects rather than exploits'),

gap(60),
bad('THE PRIVACY PROBLEM, MET HEAD ON', [
  'Gait carries enough information to **identify a person**, and the point-cloud benchmark cited in the review exists to demonstrate exactly that.',
  '"A system installed to estimate fatigue must not become a system that recognises individuals, so the pipeline has to discard identity **by construction rather than by policy**. That is easier to design for at the start than to retrofit, and it constrains which features may be retained and what may be stored."',
  'There is a second, regulatory half: India\'s data protection legislation of 2023 has created real uncertainty about workplace monitoring, and an architecture that extracts a derived score on the device and never transmits raw video is **a different legal object** from one that streams a camera feed to a server.',
]),

h2('12.8  How it would be validated, and the bar set in advance'),

num('**Gait from the camera and the lidar checked against marker-based motion capture.** An external physical reference, not another estimate.'),
num('**A subset of volunteers wears surface electromyography on the calf muscles and inertial bands at the same time as the contactless capture**, so the proposed method is compared directly against the established contact method it proposes to replace, on the same subjects during the same task.'),
num('**Field deployment** in an operational, non-air-conditioned warehouse across thirty to fifty workers and several shifts, scored against the vigilance and sleepiness instruments.'),
num('**The comparison that decides it:** the fused score must beat four single-modality baselines, camera alone, lidar alone, radar alone and thermal alone, together with an ablation over the four.'),

gap(60),
good('WHY THE BAR IS SET NOW', [
  '"Setting that bar before any data is collected is deliberate, because it is exactly the comparison that becomes easy to avoid once a pipeline exists and produces plausible-looking numbers. A fused score that cannot beat the best single modality has bought nothing for four sensors and an edge processor."',
]),

h2('12.9  The sequence, and the one practical constraint'),

p('The order matters more than the schedule:'),

bullet('**First, the capture node.** Until one exists there is no data of any kind.'),
bullet('**Second, per-modality laboratory validation.** This is the step **most likely to end the strand**, which is a reason to reach it early rather than late. If two of the four modalities carry no usable fatigue signal on walking subjects, the design changes before anything is built around them.'),
bullet('**Last, fusion, field deployment and the baseline comparison**, because they are the only steps that need every preceding one to have worked.'),

gap(60),
warn('THE CONSTRAINT THAT SITS ACROSS ALL OF IT', [
  'Simultaneously processing four high-bandwidth streams on a single edge platform **generates heat**, and a non-air-conditioned Indian warehouse above 40 degrees is precisely where that platform will throttle.',
  'That is a design constraint on the node rather than a footnote, and it is one of the reasons the hardware objective has to be completed and tested in situ before the algorithmic one means anything.',
]),

gap(),
good('THE CLOSING LINE FOR THIS CHAPTER', [
  '"A negative result is a useful contribution while there is still time to act on it, and stops being one once there is not."',
  'That is the whole justification for carrying an unbuilt strand in a first-year report, and it is a good one.',
]),

];
