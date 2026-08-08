# SLAM Theory — Algorithm Choice and the Underlying Math

Written to close out Research_Journal.md Part XVI and open Part XVII (reliable mapping/visualization → SLAM → autonomous drive). Every claim below traces to a specific paper in `research_articles/` — this is the reasoning, not just the conclusion, because the point of doing this before touching parameters is to know *why* a choice is right, not just that it works.

**Scope.** This covers *why* `slam_toolbox` is the right algorithm for this platform and *what math* it's actually running underneath. It does not cover parameter tuning, dynamic modeling, or what "autonomous" needs beyond mapping — those are explicitly separate, later work (per the scope boundary set at the start of this session).

## 1. What SLAM actually has to solve

A mobile robot with a 2D LiDAR observes range/bearing measurements to nearby surfaces as it moves, and has to simultaneously recover two unknowns from that stream: its own trajectory, and a map of the environment — each depends on the other (a good map needs a good trajectory estimate to project scans into; a good trajectory estimate needs a good map to localize against). This is the chicken-and-egg problem SLAM literature always opens with (Ben-Ari & Mondada, 2017).

Every practical SLAM system splits this into two cooperating parts:

- **Front-end (scan matching):** given two LiDAR scans (or a scan and a map), estimate the rigid-body transformation between them. This is *local* — it only ever compares nearby poses/scans, so its errors accumulate (drift) over a long run.
- **Back-end (optimization):** given many local scan-matching estimates plus occasional *loop-closure* constraints (recognizing "I've been here before"), find the globally consistent set of poses that best explains all of them at once. This is what actually removes drift.

`slam_toolbox` (Macenski & Jambrečić, 2021) — what this robot already runs — implements both: a correlative scan-matching front-end descended from Karto SLAM, and a Ceres-based pose-graph optimization back-end descended from Sparse Pose Adjustment (Konolige et al., 2010). The rest of this document derives what those two halves are actually computing.

## 2. Front-end: scan matching

### 2.1 The general problem

Given a reference scan (points $M = \{m_j\}$, e.g. the existing map) and a current scan (points $P = \{p_k\}$), scan matching finds the rigid transformation $T = (R, t)$ — rotation $R \in SO(2)$, translation $t \in \mathbb{R}^2$ — that best aligns $T(P)$ with $M$. The classic algorithm, Iterative Closest Point (ICP), alternates:

1. **Correspondence:** for each $p_k$, find its match in $M$ under the current estimate of $T$.
2. **Minimization:** solve for the $T$ that minimizes total correspondence error.
3. Repeat until $T$ converges.

Step 1 is where variants diverge. Plain ICP matches each point to its single nearest neighbor — cheap, but a poor local model of the actual surface, so it converges slowly and can settle into the wrong local minimum.

### 2.2 The point-to-line metric (Censi, 2008)

Instead of matching a point to a point, PLICP matches each transformed point $T(p_k)$ to the **line** through its two nearest neighbors in $M$ — a first-order local approximation of the real surface the LiDAR is actually seeing (walls, shelving, etc. are locally straight). If that line has unit normal $n_k$ and passes through $q_k$, the error for that correspondence is the perpendicular distance:

$$e_k(T) = n_k \cdot \big(T(p_k) - q_k\big)$$

and the objective is the weighted sum over all correspondences:

$$T^* = \arg\min_T \sum_k w_k\, e_k(T)^2$$

Censi shows this has an exact closed-form minimizer (not requiring a per-iteration SVD the way point-to-point ICP does), and demonstrates quadratic convergence in a finite number of steps — more precise and fewer iterations than plain ICP, at the cost of being less tolerant of a bad initial guess (research_articles: Censi, 2008). This point-to-line structure is the same family of scan matcher `slam_toolbox`'s correlative front-end and Cartographer's branch-and-bound matcher (Heß et al., 2016) both build on.

### 2.3 Why the *initial guess* matters as much as the metric

Every scan-matching front-end — PLICP included — is a local optimizer: it needs a starting estimate close enough to the true alignment, or it converges to the wrong local minimum. That starting estimate normally comes from odometry (predict where the robot moved since the last scan, then refine with scan matching). **This project currently runs `slam_toolbox` scan-matching-only, deliberately not fusing wheel odometry as that prior** (`system/slam_nodom.yaml`) — a choice made when the odometry pipeline itself was unreliable (the odom-TF gaps documented across §16.9–§16.10). Hector SLAM (Kohlbrecher et al., 2011) takes this same "don't trust odometry" stance by design, using a high LiDAR scan rate instead of a motion prior — and Laksono & Kusuma (2022)'s direct comparison on an RPLidar-A1 (same hardware tier as this robot's YDLIDAR X4 Pro) found Hector SLAM measurably more accurate than GMapping-with-scan-matcher on exactly this class of sensor.

That reasoning was sound *at the time*. It's now worth revisiting: this session confirmed the odom-TF pipeline holds cleanly across reboots and real driving (§16.12, §16.15). A scan matcher with a good motion prior converges faster and more reliably than one with none — every point above is about **not trusting a bad prior**, not about odometry being inherently unhelpful. **Concrete recommendation for the next session:** benchmark `slam_toolbox` with odometry-as-prior enabled against the current scan-matching-only config, now that odometry is trustworthy, rather than assuming the old constraint still holds.

## 3. Occupancy grid mapping

Once poses are known (or being estimated), the *map* itself is built as an occupancy grid — the environment discretized into cells, each holding a probability of being occupied. This traces to Moravec & Elfes (1985), the original occupancy-grid paper, still the basis of every grid-based SLAM map today including `slam_toolbox`'s.

Each cell's occupancy is represented in **log-odds** form for numerical stability and because it makes repeated updates additive:

$$l_i = \log\frac{p(m_i)}{1-p(m_i)}$$

For a new observation $z_t$ at pose $x_t$, the cell's log-odds updates as:

$$l_{i,t} = l_{i,t-1} + \log\frac{p(m_i \mid z_t, x_t)}{1 - p(m_i \mid z_t, x_t)} - l_0$$

where $l_0$ is the prior (log-odds of $p=0.5$, i.e. "unknown," so $l_0=0$), and the middle term is the *inverse sensor model*'s contribution — a fixed log-odds value added when a LiDAR beam terminates in that cell (occupied evidence, e.g. $z_{hit}=\ln(0.7/0.3)$) or passes through it (free evidence, e.g. $z_{free}=\ln(0.4/0.6)$, values as used in Bai et al., 2026's continuous-mapping formulation, following the same convention). Converting back to probability: $p(m_i) = 1 - \frac{1}{1+e^{l_i}}$.

**This is directly visible in this project's own tooling, not just abstract theory.** `map_saver_cli`'s `.pgm` convention — 0 = occupied, 254 = free, 205 = unknown (`run_report.py`'s `classify_map_pixel`, mirrored from `telemetry_analyzer.html`) — is this exact log-odds value, saturated toward its extremes as consistent observations accumulate and left at the midpoint where too few observations exist to be confident either way. "81% unknown" in §16.15's map isn't a separate metric from this equation — it's literally "these cells never accumulated enough log-odds evidence to move off $l=0$."

## 4. Back-end: pose-graph optimization

Scan matching alone drifts — each estimate only ever corrects the *previous* pose, so small errors accumulate without bound over a long run. The back-end fixes this by treating the *entire trajectory* as one joint optimization problem, following Grisetti, Kümmerle & Stachniss (2010)'s tutorial formulation (the reference this section follows directly):

**The graph.** Nodes $x_1, \dots, x_n$ are robot poses (position + heading, $SE(2)$) at different points in time. Edges $(i,j)$ represent a relative-pose measurement $z_{ij}$ between two poses — either a consecutive scan-match (odometry-like edge) or a **loop closure**: a scan match between the current pose and a much earlier one, recognized when the robot revisits a previously-mapped area.

**The error per edge.** Given the current pose estimates, the *predicted* relative pose between $x_i$ and $x_j$ is $\hat{h}(x_i, x_j) = x_i^{-1} \oplus x_j$. The error is how far that prediction is from what was actually measured:

$$e_{ij}(x) = z_{ij} \ominus \hat{h}(x_i, x_j)$$

**The objective.** Each edge carries an information matrix $\Omega_{ij}$ (inverse covariance — how much to trust that particular measurement). The whole graph is optimized jointly:

$$x^* = \arg\min_x \sum_{(i,j)\in C} e_{ij}(x)^\top \Omega_{ij}\, e_{ij}(x)$$

This is nonlinear least squares. Linearizing around the current estimate $\breve{x}$ with Jacobian $J_{ij} = \frac{\partial e_{ij}}{\partial x}$:

$$e_{ij}(\breve{x} + \Delta x) \approx e_{ij}(\breve{x}) + J_{ij}\,\Delta x$$

gives the normal equations solved at each Gauss-Newton iteration:

$$H\,\Delta x = -b, \qquad H = \sum_{(i,j)} J_{ij}^\top \Omega_{ij} J_{ij}, \qquad b = \sum_{(i,j)} J_{ij}^\top \Omega_{ij}\, e_{ij}(\breve{x})$$

$H$ is sparse — each pose only connects to a handful of others — which is precisely why solving it efficiently was a research problem in its own right: Sparse Pose Adjustment (Konolige et al., 2010) is a fast structure-exploiting solver for this exact system, and it's the algorithmic ancestor of the Ceres-based solver `slam_toolbox` uses today. Update $x \leftarrow x \boxplus \Delta x$, re-linearize, repeat to convergence.

**What this buys, concretely:** without loop closure and graph optimization, drift is permanent — each new observation only ever corrects relative to the last pose, never against the whole history. With it, revisiting a known area injects one new edge that the optimizer distributes across the *entire* trajectory, correcting accumulated error everywhere at once. This is the mechanism the calibration procedure (full CW + CCW in-place rotation before driving, per this session's plan) is meant to seed: giving the graph a strong, loop-closed initial reference before committing to a longer path.

## 5. Why `slam_toolbox`, specifically, for this robot

Bringing §2–4 together against the alternatives actually surveyed (`research_articles/`):

- **vs. GMapping/RBPF** (Grisetti, Stachniss & Burgard, 2007): each particle in a Rao-Blackwellized particle filter carries its *own* copy of the map — memory and compute scale with particle count × map size, a real cost on a Pi 5's ARM cores with no GPU (quantified directly by Sugiura & Matsutani, 2021, 2022, who built FPGA accelerators specifically because RBPF-SLAM is too slow on embedded hardware otherwise). Laksono & Kusuma (2022)'s direct RPLidar-A1 comparison additionally found GMapping noisier and less accurate than scan-matching approaches on this sensor class. Graph-based `slam_toolbox` carries one map, not $N$.
- **vs. Hector SLAM** (Kohlbrecher et al., 2011): a legitimate, well-cited alternative, and its no-odometry philosophy was the right call *while* this project's odometry was unreliable. But it has no pose-graph back-end and no loop closure — drift is not correctable once accumulated, only ever minimized going forward. `slam_toolbox` gets Hector's scan-matching-only option *and* an optimization back-end for when odometry is trusted again.
- **vs. Cartographer** (Heß et al., 2016): more sophisticated — submaps plus branch-and-bound global scan matching — and a reasonable *future* upgrade if map scale grows well beyond a single narrow-aisle environment. For the scale this robot operates at, it's more machinery than the problem currently needs.
- **`slam_toolbox` itself** (Macenski & Jambrečić, 2021) is purpose-built for exactly this deployment class — the paper's own motivating examples are retail and warehouse floors — and is ROS 2's default SLAM package for that reason, not an arbitrary pick.

Net: the algorithm choice already made (§16.10's consolidation onto `slam_toolbox`) is the scientifically justified one, not just the path of least resistance. The one open, reasoned recommendation this review surfaces is §2.3's: re-evaluate the no-odometry-prior configuration now that the reason for it (unreliable odometry) no longer holds.

## References

See `research_articles/README.md` for the full citation list with DOIs and per-paper relevance notes.
