# A nodding 2D LiDAR for NarrowAisleBot: what the paper gives us, and when

Harchowdhury, A., Kleeman, L., and Vachhani, L. (2018). "Coordinated Nodding
of a Two-Dimensional Lidar for Dense Three-Dimensional Range Measurements."
*IEEE Robotics and Automation Letters* 3(4), 4108–4115.
DOI: [10.1109/LRA.2018.2852781](https://doi.org/10.1109/LRA.2018.2852781)

Leena Vachhani is at SYSCON, IIT Bombay. The first author was with the
IITB-Monash Research Academy. This is work done partly in this building, which
matters for the APS: it is a citable local line of research to point at rather
than a paper pulled off arXiv.

## The short version

Put a cheap 2D scanner on a servo, nod it, and you get a 3D point cloud for
roughly the price of the 2D scanner. Everyone has had that idea. The paper's
actual contribution is narrower and better than that: it says **how fast to
nod**, and proves that one specific choice of speed stops the beams from
landing on top of each other.

Here is the mechanism. The scanner takes `N_L` samples per full revolution
(1024 on their Hokuyo). Let `N_s` be the number of laser samples that elapse
while the servo travels from one pitch extreme to the other and back. If
`N_s` and `N_L` share a common factor, the pattern closes on itself quickly
and the sensor spends the rest of its time re-measuring points it already
has. Make them coprime and no beam can revisit a previously registered
(azimuth, pitch) pair until `N_s · N_L · T_s` has elapsed, which is a very
long time.

Since 1024 is a power of two, **any odd `N_s` is automatically coprime with
it.** That is the whole trick, and it is a good one: a hard theoretical
guarantee bought with a parity check.

Coprimality gets you uniqueness, not coverage. Unique points can still leave
holes. So section V adds a second criterion: grid the angular scan window
into cells sized to the smallest object you care about detecting at a given
range, then pick the `N_s` that visits every cell soonest. They report bands
of good `N_s` values rather than one optimum, and settle on 2745 as a
worked example (around 10 seconds to touch every cell, with good revisit
time and hit frequency).

## The part I think is actually the hard part

Sections VI-B and VI-C, which are not the headline and should have been.

The scanner reports one timestamp per frame. The servo reports its position
at a different rate entirely (62 Hz for the servo against 10 Hz for the
scanner). During a single laser frame the mirror sweeps through hundreds of
bearings while the whole sensor is *also* pitching. Treat the pitch as
constant across the frame, which is the obvious thing to do, and you get
their Figure 8b: the object reconstructs as two overlapping copies of itself.
Not noise. A clean, confident, wrong answer.

Their fix is to interpolate the servo's orientation to each individual beam's
own moment, using SLERP between the two bracketing servo reports, and only
then project the beam. Figures 8c and 8d are the same object after that.

Then ego-motion makes it worse again. Drive toward a wall with fixed pitch
limits and the point cloud gets dense low and sparse high, because the
angular window subtends less height as you close in. They compensate by
re-deriving the pitch limits from the median range every 100 ms and running a
velocity controller on the nodding servo to keep coverage even. Measured
result: 44,957 repeated points instead of 66,373 over 4000 frames.

Two findings worth carrying away because they contradict intuition:

Slower nodding gave **more** repeated beam positions, not fewer. At
`N_s = 3000` (4.189 rad/s) the repeat rate was lower than at `N_s = 7000`
(1.795 rad/s). Going slow to "be careful" is the wrong instinct here.

Almost all the repeats came from the two ends of the servo's travel, where
its angular velocity is changing and the constant-speed assumption behind
`N_s` breaks. The linear middle of the sweep was clean. Their servo's 0.005
rad position resolution sets the floor on pitch resolution no matter what
else you do.

## What this means for NarrowAisleBot

Not this month. Let me be blunt about that before anything else.

The paper's contribution requires a servo, a bracket, a pitch axis, per-beam
timestamp interpolation, and a calibration procedure. NAB has none of those,
and the APS is on 23 September. Adding a moving part to the sensor head nine
days out would put the one subsystem that currently works at risk to chase a
capability nobody is asking for in this seminar.

It is still the right direction for year two, and here is the argument for
why, which is not the argument the paper makes.

NAB maps a warehouse aisle with a single horizontal slice at one height. In
an aisle, that is a genuinely bad assumption. Pallet overhang sits above the
scan plane and never gets mapped. Fork tines and pallet feet sit below it.
A load projecting off a rack at 1.4 m is invisible to a scanner at 0.275 m
and the robot will drive straight into it with a perfectly clean costmap.
That is a real, aisle-specific failure that 3D perception fixes and better
2D algorithms do not. The case for nodding is not "3D is nicer." It is that
the aisle has obstacles at heights the sensor structurally cannot see.

Second, the cost argument transfers exactly. A Velodyne is out of reach for
this project. A hobby servo and a printed bracket are not.

Where the transfer is *not* clean, and I would rather write this down now
than rediscover it:

Their Hokuyo scans ±120° and reports 1024 samples per notional revolution.
NAB's X4 Pro scans a full 360° and delivers a measured ~430 points per
revolution at a measured 11.35 Hz. So `N_L` is different, the geometry is
different, and the `N_s` bands in their Figure 6 do not carry over. The
coprimality argument does, since it is arithmetic, but every number in it
has to be recomputed for 430.

Worse, NAB cannot command its scan rate at all. `support_motor_dtr: false`
means the driver never touches the motor and the head free-runs
(`system/ydlidar_params.yaml` records this, along with the fact that the
`frequency: 6.0` parameter has been inert the whole time). The paper's method
assumes you can choose the ratio between two rates. NAB can currently choose
neither. Fixing that means either enabling motor control on a unit whose
motor start/stop behaviour is unknown, or accepting whatever ratio falls out
and checking afterwards whether it happens to be coprime. The second is
honest but gives up the design freedom that makes the method work.

And the pitch-interpolation problem needs per-beam timing that NAB would have
to get from `LaserScan.time_increment`, which the driver populates but which
nobody in this project has ever validated against anything.

## The one idea that transfers today at zero hardware cost

Their Figure 8b failure is a *timestamping* failure, not a nodding failure:
the sensor pose changed during a frame and the reconstruction assumed it had
not. NAB has the same failure in-plane. One sweep takes 88 ms at the measured
11.35 Hz, and the robot moves during it. At the 0.08 m/s Nav2 cap that is 7 mm
of translation smeared across the sweep, which is 0.14 of a costmap cell and
genuinely does not matter. Under rotation it is a different story, and the
project has never measured it.

I am not proposing we deskew the scan before the APS. The correction is
smaller than the noise we already know about (150–370 mm of scan-match
correction, 74.8–78% ray flicker), so it would be optimising the wrong term.
Fix the sensor first. But it is the right thing to measure once the LiDAR
quality work has actually moved the flicker number, and this paper is the
reference for how.

## Where it goes in the plan

Objective 1, year 2, under sensing. Cite it in the APS as future work with
the honest framing: NAB's current perception is a single horizontal slice,
that slice is structurally blind to overhang and to floor-level obstacles in
an aisle, and a coordinated nodding axis is the cheap route to fixing that
rather than a 3D sensor the project cannot buy. Note the IIT Bombay
connection. Do not claim any of it is implemented, because none of it is.
