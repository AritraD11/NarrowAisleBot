# Research Articles

Papers backing the SLAM/AMR decisions for NarrowAisleBot, found and verified via literature search (Scite — every entry below was retrieved from the actual publication record, not assumed from memory). This folder is the citation trail for `docs/SLAM_Theory.md` and for every SLAM-architecture decision made from Part XVII of `docs/Research_Journal.md` onward.

Add a paper here whenever it materially informs a decision — algorithm choice, a parameter, a threshold, a design tradeoff. Cite it in the relevant doc by author/year, and list it here with the DOI and why it mattered.

## Index

### SLAM systems (algorithm choice)

| Citation | DOI | Why it's here |
|---|---|---|
| Macenski, S., & Jambrečić, I. (2021). SLAM Toolbox: SLAM for the dynamic world. *Journal of Open Source Software*, 6(61), 2783. | [10.21105/joss.02783](https://doi.org/10.21105/joss.02783) | The paper for `slam_toolbox` itself — what this robot already runs. Confirms it replaced GMapping as ROS 2's default SLAM package, built for exactly the retail/warehouse-scale, dynamic-environment case this robot operates in. |
| Grisetti, G., Stachniss, C., & Burgard, W. (2007). Improved Techniques for Grid Mapping With Rao-Blackwellized Particle Filters. *IEEE Transactions on Robotics*, 23(1), 34–46. | [10.1109/tro.2006.889486](https://doi.org/10.1109/tro.2006.889486) | The GMapping paper — the particle-filter alternative to scan-matching/graph-based SLAM. 2423 citing publications; the canonical RBPF-SLAM reference. |
| Kohlbrecher, S., von Stryk, O., Meyer, J., & Klingauf, U. (2011). A flexible and scalable SLAM system with full 3D motion estimation. *SSRR 2011*, 155–160. | [10.1109/ssrr.2011.6106777](https://doi.org/10.1109/ssrr.2011.6106777) | Hector SLAM — pure scan-matching, deliberately built to work *without* relying on odometry. Directly relevant given this project's own odom-TF failure history (§16.9–§16.10). |
| Heß, W., Kohler, D., Rapp, H., & Andor, D. (2016). Real-time loop closure in 2D LIDAR SLAM. *ICRA 2016*, 1271–1278. | [10.1109/icra.2016.7487258](https://doi.org/10.1109/icra.2016.7487258) | Google Cartographer — submap + branch-and-bound scan matching. The heavier-weight alternative; useful as an upper bound on what "more sophisticated" costs computationally. |
| Konolige, K., Grisetti, G., Kümmerle, R., Burgard, W., Limketkai, B., & Vincent, R. (2010). Efficient Sparse Pose Adjustment for 2D mapping. *IROS 2010*, 22–29. | [10.1109/iros.2010.5649043](https://doi.org/10.1109/iros.2010.5649043) | Karto SLAM's SPA back-end — the algorithmic lineage `slam_toolbox`'s pose-graph optimizer descends from. |

### Empirical comparisons on similar hardware

| Citation | DOI | Why it's here |
|---|---|---|
| Laksono, P. S., & Kusuma, T. M. (2022). Performance Analysis of Hector SLAM and GMapping for Navigation for Mobile Robot Navigation. *Jurnal Ilmiah Teknologi dan Rekayasa*, 27(2), 144–153. | [10.35760/tr.2022.v27i2.6063](https://doi.org/10.35760/tr.2022.v27i2.6063) | Direct empirical comparison of Hector SLAM vs. GMapping on an **RPLidar-A1** — the same class of low-cost rotating 2D LiDAR as this robot's YDLIDAR X4 Pro. Found GMapping+laser_scan_matcher noisier and less accurate than Hector SLAM on this hardware tier. |
| Sugiura, K., & Matsutani, H. (2021). An FPGA Acceleration and Optimization Techniques for 2D LiDAR SLAM Algorithm. *IEICE Transactions on Information and Systems*, E104.D(6), 789–800. | [10.1587/transinf.2020edp7174](https://doi.org/10.1587/transinf.2020edp7174) | Quantifies why RBPF/particle-filter SLAM (GMapping) is computationally heavier on resource-limited embedded hardware — memory grows with particle count × map size. Directly relevant to running on a Pi 5 rather than a desktop-class machine. |
| Sugiura, K., & Matsutani, H. (2022). A Universal LiDAR SLAM Accelerator System on Low-Cost FPGA. *IEEE Access*, 10, 26931–26947. | [10.1109/access.2022.3157822](https://doi.org/10.1109/access.2022.3157822) | Companion paper; benchmarks scan matching and loop-closure cost across scan-matching, particle-filter, and graph-based SLAM on constrained hardware. |

### The math (scan matching, pose-graph optimization, occupancy grids)

| Citation | DOI | Why it's here |
|---|---|---|
| Censi, A. (2008). An ICP variant using a point-to-line metric. *ICRA 2008*, 19–25. | [10.1109/robot.2008.4543181](https://doi.org/10.1109/robot.2008.4543181) | PLICP — the point-to-line ICP metric closest to what correlative scan matchers (including `slam_toolbox`'s front-end) actually compute. Closed-form, quadratic convergence. 643 citing publications. |
| Grisetti, G., Kümmerle, R., & Stachniss, C. (2010). A Tutorial on Graph-Based SLAM. *IEEE Intelligent Transportation Systems Magazine*, 2(4), 31–43. | [10.1109/mits.2010.939925](https://doi.org/10.1109/mits.2010.939925) | The pose-graph optimization math end to end — nonlinear least-squares formulation, information-matrix weighting, the normal equations solved by Gauss-Newton/Levenberg-Marquardt. 1353 citing publications; this is the reference `docs/SLAM_Theory.md`'s back-end derivation follows. |
| Moravec, H., & Elfes, A. (1985). High resolution maps from wide angle sonar. *ICRA 1985*, 116–121. | [10.1109/robot.1985.1087316](https://doi.org/10.1109/robot.1985.1087316) | The original occupancy grid mapping paper — the Bayesian log-odds update every occupancy-grid SLAM system, including `slam_toolbox`, still uses. 1632 citing publications. |

### Navigation, costmaps, and local control (Part XVII autonomy phase)

| Citation | DOI | Why it's here |
|---|---|---|
| Macenski, S., Martín, F., White, R., & Ginés Clavero, J. (2020). The Marathon 2: A Navigation System. *IROS 2020*. | [10.48550/arxiv.2003.00368](https://doi.org/10.48550/arxiv.2003.00368) | The Nav2 paper — the navigation stack this robot's autonomy is built on. Behavior-tree task orchestration, lifecycle-managed nodes, and support for holonomic robots with collision checking in SE(2); motivating deployment cases are warehouse/retail floors, the same class as this robot. |
| Lu, D. V., Hershberger, D., & Smart, W. D. (2014). Layered costmaps for context-sensitive navigation. *IROS 2014*, 709–715. | [10.1109/iros.2014.6942636](https://doi.org/10.1109/iros.2014.6942636) | The layered-costmap architecture `nav2_costmap_2d` implements directly — static/obstacle/inflation layers as ordered, separately-owned contributions to one grid rather than a single fused map. 299 citing publications. Grounds `Navigation_Theory.md` §1.2. |
| Fox, D., Burgard, W., & Thrun, S. (1997). The dynamic window approach to collision avoidance. *IEEE Robotics & Automation Magazine*, 4(1), 23–33. | [10.1109/100.580977](https://doi.org/10.1109/100.580977) | The DWA paper — ancestor of Nav2's `dwb_core`, the local controller this project starts with. Searching velocity space restricted to a dynamically-reachable window, with an admissibility condition guaranteeing the robot can stop before contact. 3677 citing publications. |
| Li, X., Liu, F., & Liu, J. (2017). Obstacle avoidance for mobile robot based on improved dynamic window approach. *Turkish Journal of Electrical Engineering & Computer Sciences*, 25, 666–676. | [10.3906/elk-1504-194](https://doi.org/10.3906/elk-1504-194) | Diagnoses DWA's two limitations that matter for narrow-aisle operation: local minima (U-shaped obstacles/dead ends, since DWA ignores free-space connectivity) and not accounting for robot size when judging gap traversability. Why the global planner + recovery behaviors are load-bearing, not optional. |
| Williams, G., Drews, P., Goldfain, B., Rehg, J. M., & Theodorou, E. A. (2016). Aggressive driving with model predictive path integral control. *ICRA 2016*, 1433–1440. | [10.1109/icra.2016.7487277](https://doi.org/10.1109/icra.2016.7487277) | The original MPPI paper — sampling-based stochastic optimal control via importance-weighted trajectory rollouts. The candidate upgrade from DWB for genuinely omnidirectional local control. Note the experiments run on a GPU, which is the relevant caveat for a Pi 5. |
| Williams, G., Drews, P., Goldfain, B., Rehg, J. M., & Theodorou, E. A. (2018). Information-Theoretic Model Predictive Control: Theory and Applications to Autonomous Driving. *IEEE Transactions on Robotics*, 34(6), 1603–1622. | [10.1109/tro.2018.2865891](https://doi.org/10.1109/tro.2018.2865891) | The full derivation behind MPPI — free energy / KL-divergence formulation giving the soft-min importance-weighting update, versus DWA's hard arg-max over a discretized velocity grid. The reference `Navigation_Theory.md` §3.2 follows. |

## How to add a paper

1. Search for it properly (Scite or equivalent) — don't cite from memory.
2. Check `editorialNotices` for retractions/corrections before adding.
3. Add a row to the relevant table above: full citation, DOI, and a one-sentence note on what decision it informed.
4. Reference it by author/year in whichever doc it backs.
