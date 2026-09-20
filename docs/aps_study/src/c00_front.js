const S = require('./style');
const { p, h1, h2, h3, bullet, num, analogy, note, good, warn, bad, gap, table, eq, code } = S;

module.exports = [

h1('How to use this document'),

p('This is the study companion to the APS report. The report is written for a reader who already knows robotics vocabulary. This document is written for you, the night before, and it assumes nothing. Every idea is explained twice: once in plain words with a picture you can hold in your head, and once with the real numbers from this robot.'),

p('Three rules run through the whole thing, and they are the rules the panel will actually test you on.'),

num('**Never state a number without its evidence grade.** "We measured 0.91 per cent closure over 10.61 m" is a strong answer. "It is about one per cent" is a weak one. "We have not tested that" is a strong answer too, and it beats a guess every single time.'),
num('**Never drop the qualifier.** The report says closure stays below 1 per cent _out to about 10 m_. Say the whole sentence. The moment you shorten it to "below 1 per cent" you have claimed something you cannot defend, and a good examiner will find the 18 m route where it is 1.42 per cent.'),
num('**A failure explained well scores higher than a success stated flatly.** Three of the strongest results in this project are things that did not work: scan matching made the pose worse, the proportional-gain argument turned out to rest on a wrong number, and the commissioning map cannot pass its own coverage test. Each of those is a result. Present them as results.'),

gap(),
note('WHAT IS IN HERE', [
  'Part 1 sets up the problem. Part 2 walks every piece of hardware and says why it is on the robot. Part 3 is the kinematics. **Part 4 is the control chapter, the long one: feedforward, P, I, D, every value and where it came from.** Part 5 is odometry, Part 6 the lidar, **Part 7 is SLAM and every constraint you hit**, Part 8 is navigation and the same. Part 9 explains all 21 figures one by one. Parts 10 and 11 cover the other two strands. Part 12 is the question bank. Part 13 is the one-page cheat sheet to read in the corridor.',
]),

h2('The twenty numbers to know cold'),

p('If you are woken at three in the morning you should be able to say these. Not being able to state your own robot\'s mass or footprint is the single worst impression available in a viva.'),

gap(60),
table(
  ['Quantity', 'Value', 'Why it matters'],
  [
    ['Chassis footprint', '1.00 m x 0.36 m', 'Tape-measured on the built machine. The 0.36 m is what the collision footprint uses.'],
    ['Mass', '45.54 kg', 'This is the number that makes it a full-scale machine rather than a prototype.'],
    ['Outer wheel distance, l1', '0.403 m', 'Front-right and rear-left, the far diagonal pair.'],
    ['Inner wheel distance, l2', '0.333 m', 'Front-left and rear-right, the near diagonal pair.'],
    ['Asymmetry offset', '70 mm', 'l1 minus l2. The entire geometric novelty of the platform.'],
    ['Half track width, d', '0.15769 m', 'Same for all four wheels. Only the longitudinal distance differs.'],
    ['Wheel radius, r', '0.0762 m', '6 inch mecanum wheel, rollers at 45 degrees.'],
    ['Outer lever arm, Ko', '0.5607 m', 'l1 + d. Used by FR and RL in the yaw term.'],
    ['Inner lever arm, Ki', '0.4907 m', 'l2 + d. Used by FL and RR. 14 per cent shorter than Ko.'],
    ['Control loop rate', '100 Hz', 'On the ESP32, four independent loops, one per wheel.'],
    ['Kff (feedforward slope)', '37.3 / 38.4 / 38.3 / 38.0', 'Drive counts per rad/s, FR / FL / RR / RL. A 3 per cent spread.'],
    ['Kstat (breakaway term)', '8.0 counts, all four', 'Static friction. Faded in over 0.05 to 0.20 rad/s.'],
    ['Kp, Ki, Kd', '45, 250, 0.5', 'The deployed gains. Ki was 30 before; that is the headline change.'],
    ['Tracking error, unloaded', '0.040 to 0.047 rad/s RMS', 'Wheels in the air, 26,468 samples over three runs.'],
    ['Tracking error, loaded', '0.066 to 0.074 rad/s RMS', 'Full chassis weight on the floor, 35,248 samples.'],
    ['Endpoint closure', '0.23, 0.29, 0.91 % of path', 'Over 8.00 m, 9.61 m and 10.61 m, against a floor mark.'],
    ['Kinematics round-trip error', '2.22 x 10^-16', 'Worst case over 20,000 generated cases. Machine epsilon.'],
    ['Lidar beams per revolution', '430, at 11.35 Hz', 'Measured on the installed unit, not taken from the data sheet.'],
    ['Self-occlusion wedge', '90 degrees, 107 of 430 beams', 'The mast blocks a quarter of every scan, permanently.'],
    ['Scan matching, the key row', '16.2 mm vs 206.7 mm', 'Same wheels, same scans, matcher off vs on. It made things worse.'],
  ],
  [0.26, 0.24, 0.50],
),

gap(),
warn('THE FIVE SENTENCES THAT WILL SAVE YOU', [
  '1. "The asymmetry changes only the yaw column of the transformation. The translation terms are identical."',
  '2. "The feedforward supplies most of the drive; the PID only corrects what the feedforward gets wrong. That is why the integral gain can be as large as 250."',
  '3. "Coverage accumulates through translation, not rotation. The robot classifies what it drives past, and the room is only a few metres across."',
  '4. "Scan matching was measured against wheel odometry rather than assumed better, and it increased the error on all three routes tested."',
  '5. "The inertial sensor is absent by decision, not by omission. Without an unfused baseline there is no way to say what fusion bought."',
]),

];
