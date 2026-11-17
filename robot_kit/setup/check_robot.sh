#!/bin/bash
# check_robot.sh - is the robot actually running what you think it is?
# Read-only. Asks the LIVE system, never a file: a value in a YAML file is
# not a value on the robot (NarrowAisleBot ran three days of drives on SLAM
# defaults because a tuned file never reached the Pi).
#
#   ~/robot_kit/setup/check_robot.sh          (alias: rk-check)
KIT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$KIT/setup/generated/robot.env"
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash 2>/dev/null
# shellcheck disable=SC1091
[ -f "$ROBOT_WS/install/setup.bash" ] && source "$ROBOT_WS/install/setup.bash"
export ROS_DOMAIN_ID="$ROBOT_DOMAIN_ID" RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo" priority="default" multicast="false"/></Interfaces></General></Domain></CycloneDDS>'
pass=0; fail=0
p() { echo "  ok    $*"; pass=$((pass+1)); }
f() { echo "  FAIL  $*"; fail=$((fail+1)); }
hz() { timeout 6 ros2 topic hz "$1" 2>/dev/null | grep -m1 "average rate" | awk '{print $3}'; }

echo "== devices"
[ -e "/dev/$MCU_DEVICE" ] && p "/dev/$MCU_DEVICE -> $(readlink -f "/dev/$MCU_DEVICE")" || f "/dev/$MCU_DEVICE missing"
if [ "$LIDAR_MODEL" != "none" ]; then
  [ -e "/dev/$LIDAR_DEVICE" ] && p "/dev/$LIDAR_DEVICE -> $(readlink -f "/dev/$LIDAR_DEVICE")" || f "/dev/$LIDAR_DEVICE missing"
fi
groups | grep -qw dialout && p "user in dialout" || f "user not in dialout (log out and in after 01_base_system.sh)"

echo "== service"
systemctl is-active --quiet robot && p "robot.service active" || f "robot.service not active (rk-start; rk-log)"

echo "== graph"
ros2 daemon stop >/dev/null 2>&1   # stale daemon caches show nodes that are long gone
nodes=$(timeout 10 ros2 node list 2>/dev/null)
for n in mcu_bridge base_controller wheel_odometry twist_mux robot_state_publisher; do
  echo "$nodes" | grep -qx "/$n" && p "node /$n" || f "node /$n not running"
done
dups=$(echo "$nodes" | sort | uniq -d)
[ -z "$dups" ] && p "no duplicate nodes" || f "duplicate nodes (two launches?): $dups"

echo "== data"
r=$(hz /wheel_states); [ -n "$r" ] && p "/wheel_states at $r Hz" || f "/wheel_states silent: no telemetry from the MCU"
r=$(hz /odom); [ -n "$r" ] && p "/odom at $r Hz" || f "/odom silent"
timeout 5 ros2 run tf2_ros tf2_echo odom base_link 2>/dev/null | grep -q Translation \
  && p "TF odom -> base_link exists" || f "no TF odom -> base_link (SLAM will hang at Activating)"
if echo "$nodes" | grep -q scan_filter; then
  r=$(hz /scan_filtered); [ -n "$r" ] && p "/scan_filtered at $r Hz" || f "/scan_filtered silent"
fi

echo "== live parameters (from the running nodes, not from files)"
for q in "mcu_bridge port" "mcu_bridge wheel_names" "base_controller drive_type" \
         "wheel_odometry lateral_scale" "wheel_odometry track_width_scale"; do
  set -- $q
  v=$(timeout 5 ros2 param get "/$1" "$2" 2>/dev/null)
  [ -n "$v" ] && p "$1.$2: ${v#*: }" || f "$1.$2: no answer"
done
if echo "$nodes" | grep -qx /slam_toolbox; then
  for q in use_scan_matching max_laser_range scan_topic; do
    v=$(timeout 5 ros2 param get /slam_toolbox "$q" 2>/dev/null); p "slam_toolbox.$q: ${v#*: }"
  done
fi
if echo "$nodes" | grep -qx /controller_server; then
  v=$(timeout 5 ros2 param get /controller_server odom_topic 2>/dev/null); p "controller_server.odom_topic: ${v#*: }"
fi

echo "== Pi"
t=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null); [ -n "$t" ] && p "CPU $((t/1000)) C"
command -v vcgencmd >/dev/null && p "throttled: $(vcgencmd get_throttled)"
df -h "$HOME" | awk 'NR==2 {print "  info  disk: " $4 " free of " $2}'
echo
echo "$pass ok, $fail failed"
[ "$fail" -eq 0 ]
