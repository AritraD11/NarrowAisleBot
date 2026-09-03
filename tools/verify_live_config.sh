#!/usr/bin/env bash
# verify_live_config.sh — is the robot RUNNING what the repo SAYS?
#
# This exists because of §17.32, which is the most expensive lesson in this
# project's history: system/slam_nodom.yaml was committed on 19 Aug and
# never reached the Pi. Three days of drives, and every conclusion drawn
# from them, ran on slam_toolbox stock defaults while the journal described
# a tuned config. The reasoning was sound; it was applied to parameters that
# were never active.
#
#     A VALUE IN THE REPO IS NOT A VALUE ON THE ROBOT.
#
# Every check below asks a LIVE NODE, never a file. Run it after every
# deploy, before the first metre of driving. It is the G1 gate, automated.
#
#   ./tools/verify_live_config.sh              # expects Stage G
#
# Exit 0 = everything matches. Exit 1 = at least one mismatch; the drive
# you were about to do would have measured something other than what you
# think you deployed.
set -uo pipefail

PASS=0; FAIL=0; WARN=0
ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAIL=$((FAIL+1)); }
info() { printf '  ....  %s\n' "$1"; }

# get_param <node> <param> -> prints the bare value, or "" if unreachable
get_param() {
  timeout 10 ros2 param get "$1" "$2" 2>/dev/null \
    | sed -n 's/^[A-Za-z ]*value is: //p' | tail -1
}

warn() { printf '  \033[33mWARN\033[0m  %s\n' "$1"; WARN=$((WARN+1)); }

expect() {   # expect <node> <param> <wanted>
  local node="$1" p="$2" want="$3" got got_lc want_lc
  got="$(get_param "$node" "$p")"
  if [ -z "$got" ]; then
    bad "$node $p — NODE OR PARAM UNREACHABLE (is it running?)"
    return
  fi
  # ros2 param get prints Python-style booleans (True/False). Compare
  # case-insensitively so a correctly-deployed `false` is not failed
  # against a literal "false" — this bug caused three false FAILs on the
  # first-ever run of this script, 3 Sep 2026, and is recorded here so it
  # is not silently "fixed" a second time without anyone noticing why.
  got_lc="$(printf '%s' "$got"  | tr '[:upper:]' '[:lower:]')"
  want_lc="$(printf '%s' "$want" | tr '[:upper:]' '[:lower:]')"
  if [ "$got_lc" = "$want_lc" ]; then
    ok "$node $p = $got"
  else
    bad "$node $p = $got   (expected $want)"
  fi
}

echo "════════════════════════════════════════════════════════════════"
echo " STAGE G — live config verification    $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════════"

echo
echo "── 1. LiDAR driver ─────────────────────────────────────────────"
LIDAR_NODE=/ydlidar_ros2_driver_node
expect "$LIDAR_NODE" frequency 6.0
expect "$LIDAR_NODE" range_max  10.0

echo
echo "── 2. slam_toolbox ─────────────────────────────────────────────"
# THE TWO THAT DEFINE THIS STAGE. If either reads the old value, stop:
# the drive would score the previous configuration under a new name.
expect /slam_toolbox use_scan_matching false
expect /slam_toolbox max_laser_range   5.0
# Frozen on purpose — listed so a silent drift shows up here rather than in
# a map three sessions from now.
expect /slam_toolbox correlation_search_space_dimension 0.3
expect /slam_toolbox coarse_search_angle_offset         0.175
expect /slam_toolbox use_scan_barycenter                false
expect /slam_toolbox do_loop_closing                    true
expect /slam_toolbox resolution                         0.05

echo
echo "── 3. Nav2 (only if navigation is up) ──────────────────────────"
if timeout 8 ros2 node list 2>/dev/null | grep -q '^/controller_server$'; then
  expect /controller_server FollowPath.batch_size            300
  expect /controller_server goal_checker.xy_goal_tolerance   0.05
  expect /controller_server goal_checker.yaw_goal_tolerance  0.05
else
  info "controller_server not running — skipped (expected during a mapping drive)"
fi

echo
echo "── 4. The scan itself, measured not assumed ────────────────────"
# frequency: 6.0 is a REQUEST. support_motor_dtr is false, so the driver
# does not command the motor at all, and on the unit tested 3 Sep 2026 the
# hardware ignores the request outright and free-runs at its own native
# speed (measured 11.35 Hz, deviation ~8 ms on an ~88 ms period — STABLE,
# just not the requested rate). That is a hardware ceiling, not a broken
# measurement, so it is a WARN: it does not block the drive, but every
# prediction built on 833 pts/rev (the +67% density case) is void and
# StageG_Deploy.md needs correcting rather than re-argued.
echo "  measuring /scan for 10 s ..."
HZ_OUT="$(timeout 12 ros2 topic hz /scan 2>/dev/null | tail -4)"
RATE=""
if [ -n "$HZ_OUT" ]; then
  echo "$HZ_OUT" | sed 's/^/        /'
  RATE="$(echo "$HZ_OUT" | sed -n 's/.*average rate: \([0-9.]*\).*/\1/p' | tail -1)"
  DEV="$(echo "$HZ_OUT" | sed -n 's/.*std dev: \([0-9.]*\)s.*/\1/p' | tail -1)"
  if [ -n "$RATE" ]; then
    if awk -v r="$RATE" 'BEGIN{exit !(r>5.4 && r<6.6)}'; then
      ok "scan rate ${RATE} Hz — the 6.0 Hz request took effect"
    else
      REQ="$(get_param "$LIDAR_NODE" frequency)"
      STABLE="unknown"
      if [ -n "$DEV" ] && [ -n "$RATE" ]; then
        STABLE="$(awk -v d="$DEV" -v r="$RATE" 'BEGIN{p=1/r; print (d/p<0.15)?"stable":"RAGGED"}')"
      fi
      warn "scan rate ${RATE} Hz — hardware ignored the ${REQ:-6.0} Hz request (native free-run, $STABLE)"
      info "  support_motor_dtr is false, so this parameter has no effect on"
      info "  this unit. NOT a config bug — do not re-deploy to 'fix' this."
      info "  Density predictions in StageG_Deploy.md assumed 833 pts/rev;"
      info "  actual is ~$(awk -v r="$RATE" 'BEGIN{printf "%.0f", 5000/r}'). Correct the doc, do not re-drive to chase this."
    fi
  fi
else
  bad "/scan is not publishing at all"
fi

echo
echo "── 5. Beam count vs the 5000/f model, at the MEASURED rate ─────"
# Checked against whatever rate section 4 actually measured, not the
# requested 6.0 — the formula (Stack_Assessment §3A) is the thing under
# test here, not whether the frequency request took effect (section 4
# already answered that). README's ~1258 pts @ ~11.5 Hz figure implies a
# ~14.5 kHz sample rate against a configured 5 kHz; both cannot be true.
N="$(timeout 10 ros2 topic echo /scan --once --field ranges 2>/dev/null \
     | tr ',' '\n' | grep -c '[0-9]')"
if [ "${N:-0}" -gt 0 ] && [ -n "$RATE" ]; then
  EXPECT="$(awk -v r="$RATE" 'BEGIN{printf "%.0f", 5000/r}')"
  info "beams per scan: $N   (5000 / measured ${RATE} Hz predicts ~$EXPECT)"
  if awk -v n="$N" -v e="$EXPECT" 'BEGIN{d=(n-e)/e; if(d<0) d=-d; exit !(d<0.15)}'; then
    ok "beam count matches 5000/f AT THE MEASURED RATE — Stack_Assessment §3A"
    ok "  is right; README.md's ~1258 pts @ ~11.5 Hz figure is stale, fix it"
  else
    bad "beam count $N does not match 5000/f even at the measured rate —"
    info "  neither existing doc's model fits. Needs a fresh look, not a pick."
  fi
elif [ "${N:-0}" -gt 0 ]; then
  info "beams per scan: $N   (no rate measurement to compare against)"
else
  bad "could not read /scan ranges"
fi

echo
echo "── 6. Does loop closure survive use_scan_matching: false? ──────"
# HYPOTHESIS until this prints something. slam_toolbox gates the SEQUENTIAL
# matcher with this parameter; loop closure uses a separate matcher object.
# Read it, do not recall it.
SRC_HITS="$(grep -rl "SequentialScanMatcher\|LoopScanMatcher\|UseScanMatching" \
             /opt/ros/"${ROS_DISTRO:-jazzy}"/include/ 2>/dev/null | head -3)"
if [ -n "$SRC_HITS" ]; then
  info "headers found:"; echo "$SRC_HITS" | sed 's/^/        /'
  grep -rh "m_pSequentialScanMatcher\|m_pLoopScanMatcher" \
       /opt/ros/"${ROS_DISTRO:-jazzy}"/include/ 2>/dev/null \
       | sed 's/^[[:space:]]*//' | sort -u | head -8 | sed 's/^/        /'
  ok "source is readable — confirm the two matchers are separate objects"
else
  info "slam_toolbox headers not installed locally (binary install)."
  info "EMPIRICAL CHECK INSTEAD: watch for 'Loop closure' in the SLAM log"
  info "during the drive, or run tools/graph_residuals.py --watch and look"
  info "for moved!=0. Either proves closure is alive with matching off."
fi

echo
echo "════════════════════════════════════════════════════════════════"
printf ' %d passed, %d failed, %d warned\n' "$PASS" "$FAIL" "$WARN"
if [ "$FAIL" -gt 0 ]; then
  echo " DO NOT DRIVE. Fix the mismatches above first — a drive on an"
  echo " unverified config measures something other than what you deployed."
  echo "════════════════════════════════════════════════════════════════"
  exit 1
fi
if [ "$WARN" -gt 0 ]; then
  echo " Config verified against live nodes. WARNINGS above are known"
  echo " hardware limitations, not deployment errors — cleared to drive,"
  echo " but correct any doc predictions the warnings named before citing"
  echo " numbers from this run."
else
  echo " Config verified against live nodes. Cleared to drive."
fi
echo "════════════════════════════════════════════════════════════════"
