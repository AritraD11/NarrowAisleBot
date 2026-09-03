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

PASS=0; FAIL=0
ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAIL=$((FAIL+1)); }
info() { printf '  ....  %s\n' "$1"; }

# get_param <node> <param> -> prints the bare value, or "" if unreachable
get_param() {
  timeout 10 ros2 param get "$1" "$2" 2>/dev/null \
    | sed -n 's/^[A-Za-z ]*value is: //p' | tail -1
}

expect() {   # expect <node> <param> <wanted>
  local node="$1" p="$2" want="$3" got
  got="$(get_param "$node" "$p")"
  if [ -z "$got" ]; then
    bad "$node $p — NODE OR PARAM UNREACHABLE (is it running?)"
  elif [ "$got" = "$want" ]; then
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
# frequency: 6.0 is a REQUEST. support_motor_dtr is false, so the driver may
# not control the motor at all and the hardware can quietly ignore it.
# This is the check that settles it, and the deviation matters more than
# the mean: motor speed ripple becomes angular error in every sweep.
echo "  measuring /scan for 10 s ..."
HZ_OUT="$(timeout 12 ros2 topic hz /scan 2>/dev/null | tail -4)"
if [ -n "$HZ_OUT" ]; then
  echo "$HZ_OUT" | sed 's/^/        /'
  RATE="$(echo "$HZ_OUT" | sed -n 's/.*average rate: \([0-9.]*\).*/\1/p' | tail -1)"
  if [ -n "$RATE" ]; then
    if awk -v r="$RATE" 'BEGIN{exit !(r>5.4 && r<6.6)}'; then
      ok "scan rate ${RATE} Hz — the 6.0 Hz request took effect"
    else
      bad "scan rate ${RATE} Hz — the hardware IGNORED frequency: 6.0"
      info "  the X4 Pro sets scan speed by motor PWM and support_motor_dtr"
      info "  is false. If this reads ~10, the density gain did not happen"
      info "  and every prediction resting on 833 pts/rev is void."
    fi
  fi
else
  bad "/scan is not publishing at all"
fi

echo
echo "── 5. Beam count — settles a contradiction in our own docs ─────"
# Stack_Assessment §3A computes points/rev = 5000/f, giving 833 at 6 Hz.
# README.md states ~1258 pts/scan at ~11.5 Hz, which is ~14.5 kHz, not 5.
# Both cannot be right, and the +67% density prediction rests on the first.
N="$(timeout 10 ros2 topic echo /scan --once --field ranges 2>/dev/null \
     | tr ',' '\n' | grep -c '[0-9]')"
if [ "${N:-0}" -gt 0 ]; then
  info "beams per scan: $N   (5000/6 predicts ~833)"
  if [ "$N" -gt 700 ] && [ "$N" -lt 950 ]; then
    ok "beam count matches the 5000/f model — Stack_Assessment §3A is right"
  else
    bad "beam count $N does not match 5000/f — README's 1258 figure may be"
    info "  the correct one. Update whichever doc is wrong BEFORE citing it."
  fi
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
printf ' %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo " DO NOT DRIVE. Fix the mismatches above first — a drive on an"
  echo " unverified config measures something other than what you deployed."
  echo "════════════════════════════════════════════════════════════════"
  exit 1
fi
echo " Config verified against live nodes. Cleared to drive."
echo "════════════════════════════════════════════════════════════════"
