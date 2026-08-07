# Past Iterations

Superseded tools and files, kept for reference rather than deleted. Nothing
here is wired into the active pipeline — if you're looking for the tool
that's actually in use today, check the note next to each entry below for
what replaced it.

| File | Superseded by | Why |
|---|---|---|
| `aislebot_pid_analysis_v2.py` | `src/mecanum_robot/mecanum_robot/run_report.py` + `docs/tools/telemetry_analyzer.html` | Was a Google Colab notebook (`from google.colab import files`) requiring a manual upload after every run. `run_report.py` computes the identical metrics automatically on the Pi the moment a mapping run stops (`phone_dashboard.py`'s `stop_mapping()`), and `telemetry_analyzer.html` is the no-install browser equivalent when you want to look at a run interactively — both documented in `docs/Research_Journal.md` Part XVI §16.14. |

Add an entry here whenever something gets replaced instead of deleting it —
the value is being able to go back and compare against an older approach
without digging through git history.
