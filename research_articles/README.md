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

## How to add a paper

1. Search for it properly (Scite or equivalent) — don't cite from memory.
2. Check `editorialNotices` for retractions/corrections before adding.
3. Add a row to the relevant table above: full citation, DOI, and a one-sentence note on what decision it informed.
4. Reference it by author/year in whichever doc it backs.
