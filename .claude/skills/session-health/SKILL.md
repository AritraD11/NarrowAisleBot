---
name: session-health
description: Self-audit for drift, hallucination and context exhaustion during long NarrowAisleBot hardware sessions. Use when the operator asks "are you hallucinating", "should we start a new session", "are you sure", when a command you gave has just failed, when context has been compacted, or before writing anything into Research_Journal.md. Also run it unprompted when two or more tripwires in this file are tripping at once.
---

# Session health

This robot is real, it weighs ~45 kg, and it acts on what I say. A confident
wrong number here is not a bad answer, it is a machine driving into a wall
or an afternoon of the operator's time spent chasing a fault I invented.

This skill exists because every entry in the table below **actually
happened on this project**. It is not a generic list of LLM failure modes.

---

## 1. The one rule

> **Every factual claim about this robot carries its provenance.**
> Read from a file *this session* / `ros2 param get` *this session* / a
> hash the operator pasted / a timestamped log line.
> **No provenance means: "I don't know, let's check."**

"I read that file yesterday" is not provenance. "The summary says" is not
provenance. "That's how it's configured" is not provenance.

---

## 2. Tripwires, with the real instance each one comes from

| Tripwire | What actually happened |
|---|---|
| I quote a number I did not derive **this session** | Reported node spacing as 0.175 m. I had differenced `hypot(x, y)` — displacement from origin — on an out-and-back route, where it shrinks on the return leg. Real path-length spacing: 0.441 m. Wrong by 2.5x, and it was about to score an ablation. |
| I describe a file's contents instead of reading it | Nearly shipped `verify_axis_chain.py` still looking for `ZERO_POINT_YAW` in `mapping_full.launch.py` after I had moved it to `sensors.launch.py`. The guard would have passed while guarding nothing. |
| I give a build or deploy command without checking the existing build mode | Told the operator to run `colcon build --packages-select mecanum_robot mecanum_navigation --symlink-install`. `mecanum_navigation` had only ever been built without symlinks; colcon does not reconcile the modes. Both adapter nodes died with `PackageNotFoundError` while the build printed `Summary: 2 packages finished`. Cost a full hand-driven run. |
| I predict hardware state instead of asking for it | Said the DRIFT card would read "about 0.000 m" on a parked robot. With no mapping session there is no `map` frame at all, so it correctly read `NO POSE (map -> base_link)`. |
| I report the metric that flatters the result | Reported net drift 0.064 m as "better than baseline 0.114 m". Net is an artefact of where a route happens to end. **Peak was 20.3 cm** and 57% of the run sat past 5 cm. |
| I fit a story to a measurement that failed | Pixel-forensics runs where the gridline detector caught map cells, the footprint detector caught UI chrome, and the origin detector caught a text label. The correct output was "unmeasured", not a number. |

---

## 3. The three-strike rule for a new session

Cut the session and restart when **any** of these is true:

1. **A second context compaction fires.** After one compaction I am working
   from a summary I wrote. After two, I am working from a summary of a
   summary. Restart from `docs/Session_Handoff_<date>.md`.
2. **I contradict something the operator can see on their own screen.**
   Their screen is ground truth. Mine is a reconstruction.
3. **A command I gave failed, and my next command is a variation of the
   same guess.** This is the loudest alarm. It means I am pattern-matching
   on the shape of the error rather than reasoning about the cause. One
   diagnostic step is fine. A second guess without a diagnostic is not.

Strike 3 is the real one. The other two are early warnings.

---

## 4. Running the audit

When invoked, do this and report it plainly — no reassurance, no hedging:

1. **Compaction count.** Has this session been summarised? Say so first.
2. **Take the last 5 substantive factual claims I made** and tag each:
   `FILE-THIS-SESSION` / `LIVE-PARAM` / `OPERATOR-PASTED` / `LOG-LINE` /
   **`UNSOURCED`**. Any `UNSOURCED` claim gets retracted in the same
   message, not softened.
3. **Re-read, do not recall**, any file I am about to modify or cite.
4. **Check the tripwire table.** Name any that are tripping.
5. **Verdict**, one of exactly three:
   - `CONTINUE` — nothing tripping.
   - `CONTINUE WITH CORRECTIONS` — listed retractions, then carry on.
   - `RESTART` — write/refresh `docs/Session_Handoff_<date>.md` first,
     commit and push it, then hand the operator a resume prompt.

Do not soften a `RESTART` into a `CONTINUE` because the operator seems busy
or because work is mid-flight. A restart costs twenty minutes; a wrong
number driven into hardware costs an afternoon.

---

## 5. Hardware-specific hard checks

Before *any* claim that the robot is configured a certain way:

    ros2 param get <node> <param>      # live node, never the YAML

Before *any* claim that a file reached the robot:

    sha256sum <file>                   # per file, on arrival, not per batch

Before *any* claim that a topic is flowing:

    ros2 topic hz <topic>

Before *any* claim that a launch succeeded, ask for the tail of its log and
read it. `Summary: N packages finished` is not success. `Managed nodes are
active` is.
