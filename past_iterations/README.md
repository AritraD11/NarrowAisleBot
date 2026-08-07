# Past Iterations

Superseded tools and files, kept for reference rather than deleted. Nothing
here is wired into the active pipeline — if you're looking for the tool
that's actually in use today, check the note next to each entry below for
what replaced it.

| File | Superseded by | Why |
|---|---|---|
| `aislebot_pid_analysis_v2.py` | `src/mecanum_robot/mecanum_robot/run_report.py` + `docs/tools/telemetry_analyzer.html` | Was a Google Colab notebook (`from google.colab import files`) requiring a manual upload after every run. `run_report.py` computes the identical metrics automatically on the Pi the moment a mapping run stops (`phone_dashboard.py`'s `stop_mapping()`), and `telemetry_analyzer.html` is the no-install browser equivalent when you want to look at a run interactively — both documented in `docs/Research_Journal.md` Part XVI §16.14. |
| `firmware/aislebot_esp32_v2.ino` | `aislebot_esp32.ino` (v3.0) | The pre-recalibration ESP32 firmware: single-scalar Kstat feedforward, `Ki`≈30, no dynamic anti-windup, WiFi joystick still present. Superseded 4 Aug 2026 by the v3.0 rewrite — two-term feedforward, `Ki` 30→250, dynamic anti-windup, 100 Hz loop, WiFi removed (derivation in `docs/PID_Calibration.md`, logged in `docs/Research_Journal.md` §16.1). Extracted from git history at commit `407516b^` — the last commit before the v3.0 rewrite. |
| `firmware/aislebot_arm_v7.ino` | `aislebot_arm.ino` (v8) | Pre-UV-lighting Mega arm firmware — lift/lower/open/close only, no staged `<U1>`/`<U0>`/`<U?>` UV-C tube control. Superseded 23 June 2026 when the UV-C lighting subsystem was added (`docs/Research_Journal.md` Part IX). Extracted from git history at commit `7753299^`. |
| `launch/hardware.launch.py` | `src/mecanum_robot/launch/aislebot_full.launch.py` | An older per-node launch file, deleted outright 8 July 2026 rather than kept in the tree ("deprecated... to avoid breaking existing links" — original deletion commit message). Recovered from git history at commit `782afce^` since it had been fully removed, not renamed. |
| `ros2_nodes/phone_dashboard_v2.2_record_run.py` | `src/mecanum_robot/mecanum_robot/phone_dashboard.py` (v2.3) | The dashboard before the Map button: RECORD RUN was a standalone manual toggle (`record_start`/`record_stop`), with no way to trigger `mapping_full.launch.py` from the UI at all. Superseded 7 Aug 2026 (`docs/Research_Journal.md` §16.13). Extracted at commit `afe89e4^`. |
| `ros2_nodes/esp32_bridge_pre-selfheal.py` | `src/mecanum_robot/mecanum_robot/esp32_bridge.py` | `<L1>` (enable telemetry) was sent exactly once, inside `connect_serial()` — if the ESP32 reset on its own without the Pi's serial layer noticing a disconnect, telemetry went silent for good. Superseded 6 Aug 2026 by a 5-second `resend_telemetry_enable` timer that self-heals (`docs/Research_Journal.md` §16.10). Extracted at commit `61b8475^`. |

Add an entry here whenever something gets replaced instead of deleting it —
the value is being able to go back and compare against an older approach
without digging through git history.
