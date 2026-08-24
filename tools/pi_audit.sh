#!/usr/bin/env bash
# pi_audit.sh - read-only inventory of the AisleBot Raspberry Pi.
#
# Deletes NOTHING. Prints a report you can paste back for review.
# The companion script tools/pi_clean.sh does the deleting, and only
# after a human has read this report.
#
# Usage (on the Pi):
#   curl -sSL -o /tmp/pi_audit.sh \
#     https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/mapping-autonomous-nav-695glw/tools/pi_audit.sh
#   bash /tmp/pi_audit.sh                 # local inventory only
#   bash /tmp/pi_audit.sh --online        # also diff deployed code against GitHub
#
# --online needs the Pi on a network with internet (eduroam, not aislebot-ap).

BRANCH="${AISLEBOT_BRANCH:-claude/mapping-autonomous-nav-695glw}"
RAW="https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/${BRANCH}"
ONLINE=0
[ "${1:-}" = "--online" ] && ONLINE=1

WS="$HOME/ros2_ws"
LOGS="$HOME/aislebot_logs"

sec() { printf '\n===== %s =====\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }
sz() { du -sh "$1" 2>/dev/null | cut -f1; }

printf '### AisleBot Pi audit  %s\n' "$(date -Is 2>/dev/null)"
printf '### script rev 1  branch %s  online=%s\n' "$BRANCH" "$ONLINE"

sec "1 IDENTITY"
echo "host    : $(hostname)  (mDNS: $(hostname).local)"
echo "user    : $(whoami)   groups: $(id -Gn)"
echo "uptime  : $(uptime -p 2>/dev/null)"
echo "model   : $( [ -r /proc/device-tree/model ] && tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo '(not a Pi / unreadable)')"
echo "kernel  : $(uname -srm)"
have lsb_release && echo "os      : $(lsb_release -ds)"
echo "ros     : ${ROS_DISTRO:-<not sourced in this shell>}"
ls -d /opt/ros/* 2>/dev/null | sed 's/^/ros dirs: /'

sec "2 CLOCK"
have timedatectl && timedatectl 2>/dev/null | sed -n '1,8p'

sec "3 THERMAL / POWER"
if have vcgencmd; then
  echo "temp      : $(vcgencmd measure_temp 2>/dev/null)"
  echo "throttled : $(vcgencmd get_throttled 2>/dev/null)   (0x0 = clean)"
else
  t=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)
  [ -n "$t" ] && echo "temp      : $((t/1000)) C"
  echo "throttled : vcgencmd unavailable"
fi

sec "4 MEMORY"
free -h 2>/dev/null
echo "-- swap --"; swapon --show 2>/dev/null || echo "(none)"

sec "5 DISK"
df -h / /boot /boot/firmware 2>/dev/null | sort -u
echo
echo "-- \$HOME total: $(sz "$HOME") --"
echo "-- top-level entries in \$HOME, largest first --"
du -sh "$HOME"/* "$HOME"/.[!.]* 2>/dev/null | sort -rh | head -25

sec "6 NETWORK"
if have nmcli; then
  echo "-- active --"; nmcli -t -f NAME,TYPE,DEVICE con show --active 2>/dev/null
  echo "-- saved connections (autoconnect priority) --"
  for c in $(nmcli -t -f NAME con show 2>/dev/null); do
    p=$(nmcli -t -f connection.autoconnect,connection.autoconnect-priority con show "$c" 2>/dev/null | tr '\n' ' ')
    echo "  $c :: $p"
  done
fi
echo "-- addresses --"; ip -4 -br addr 2>/dev/null
echo "-- default route --"; ip route show default 2>/dev/null
echo -n "-- internet (ping 8.8.8.8): "; ping -c1 -W2 8.8.8.8 >/dev/null 2>&1 && echo OK || echo FAIL
echo -n "-- dns (github.com): "; getent hosts github.com >/dev/null 2>&1 && echo OK || echo FAIL
echo -n "-- avahi/mDNS daemon: "; systemctl is-active avahi-daemon 2>/dev/null || echo "not found"

sec "7 SERVICES"
echo "aislebot.service : enabled=$(systemctl is-enabled aislebot.service 2>&1)  active=$(systemctl is-active aislebot.service 2>&1)"
systemctl show aislebot.service -p ExecStart --value 2>/dev/null | sed 's/^/  exec: /'
echo "-- other enabled non-vendor units --"
systemctl list-unit-files --state=enabled --no-pager 2>/dev/null \
  | grep -viE 'systemd-|dbus|getty|network|ssh|udev|cron|rsyslog|apport|snapd|unattended|e2scrub|multipath|blk|lvm|open-iscsi|cloud-init|polkit|ModemManager|wpa_|avahi|thermald|gdm|packagekit|bluetooth' \
  | head -20
echo "-- failed units --"; systemctl --failed --no-pager 2>/dev/null | head -10

sec "8 USB / SERIAL DEVICES"
ls -l /dev/serial/by-id/ 2>/dev/null || echo "(no /dev/serial/by-id)"
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
echo "-- udev rule --"
ls -l /etc/udev/rules.d/99-aislebot.rules 2>/dev/null || echo "99-aislebot.rules NOT INSTALLED"
have lsusb && { echo "-- lsusb --"; lsusb; }

sec "9 ROS WORKSPACE"
for d in "$WS" "$WS/src" "$WS/build" "$WS/install" "$WS/log"; do
  [ -e "$d" ] && printf '%-24s %s\n' "$d" "$(sz "$d")" || printf '%-24s MISSING\n' "$d"
done
echo "-- packages in $WS/src --"
ls -1 "$WS/src" 2>/dev/null
echo "-- colcon build log dirs (each build leaves one) --"
ls -1 "$WS/log" 2>/dev/null | wc -l | sed 's/^/  count: /'
ls -1t "$WS/log" 2>/dev/null | head -3 | sed 's/^/  newest: /'
echo "-- stray files at $WS top level --"
find "$WS" -maxdepth 1 -type f -printf '%TY-%Tm-%Td %10s %p\n' 2>/dev/null | sort

sec "10 DEPLOYED CODE (mtime / size / sha256)"
find "$WS/src" -type f \( -name '*.py' -o -name '*.yaml' -o -name '*.xml' -o -name '*.urdf' -o -name '*.cfg' -o -name '*.html' \) \
  -not -path '*/build/*' -not -path '*/install/*' 2>/dev/null | sort | while read -r f; do
  printf '%s  %8s  %s  %s\n' "$(date -r "$f" +%Y-%m-%d 2>/dev/null)" "$(stat -c %s "$f" 2>/dev/null)" "$(sha256sum "$f" 2>/dev/null | cut -c1-12)" "${f#"$WS/src/"}"
done

sec "11 PI-SIDE CONFIG (the files launch loads by absolute path)"
for f in "$WS/slam_nodom.yaml" "$WS/src/ydlidar_ros2_driver/params/ydlidar_params.yaml" "$HOME/start_aislebot.sh"; do
  if [ -f "$f" ]; then
    printf '%s\n  mtime %s   lines %s   sha256 %s\n' "$f" "$(date -r "$f" +%F' '%T)" "$(wc -l < "$f")" "$(sha256sum "$f" | cut -d' ' -f1)"
  else
    printf '%s\n  MISSING\n' "$f"
  fi
done
echo "-- slam_nodom backups / other yaml at ws root --"
ls -lt "$WS"/*.yaml 2>/dev/null | head -10

sec "12 RUN DATA ($LOGS)"
if [ -d "$LOGS" ]; then
  echo "total: $(sz "$LOGS")   files: $(find "$LOGS" -maxdepth 1 -type f 2>/dev/null | wc -l)"
  echo "-- by extension --"
  find "$LOGS" -maxdepth 1 -type f 2>/dev/null | sed 's/.*\.//' | sort | uniq -c | sort -rn
  echo "-- 15 largest --"
  du -ah "$LOGS" 2>/dev/null | sort -rh | head -15
  echo "-- runs that have a saved MAP (.pgm) --"
  ls -1 "$LOGS"/*.pgm 2>/dev/null | sed 's#.*/##' || echo "  NONE"
  echo "-- oldest 5 / newest 5 by mtime --"
  ls -1t "$LOGS" 2>/dev/null | tail -5 | sed 's/^/  old: /'
  ls -1t "$LOGS" 2>/dev/null | head -5 | sed 's/^/  new: /'
else
  echo "$LOGS MISSING"
fi
echo "-- rosbag directories anywhere under \$HOME --"
find "$HOME" -maxdepth 3 -type d -name 'rosbag2_*' -printf '%p\n' 2>/dev/null | while read -r d; do printf '  %-8s %s\n' "$(sz "$d")" "$d"; done

sec "13 LOG / CACHE SIZES (cleanup candidates)"
for p in "$HOME/aislebot_boot.log" "$HOME/.ros/log" "$HOME/.ros" "$HOME/.cache" "$HOME/.cache/pip" "$HOME/YDLidar-SDK" "$HOME/YDLidar-SDK/build" "$WS/build" "$WS/log" /var/log /var/cache/apt/archives /var/lib/snapd; do
  [ -e "$p" ] && printf '%-34s %s\n' "$p" "$(sz "$p")"
done
echo "-- install logs in \$HOME --"
ls -lt "$HOME"/aislebot_install_*.log 2>/dev/null | head -10 || echo "  none"
echo "-- journald on-disk --"; have journalctl && journalctl --disk-usage 2>/dev/null
echo "-- .ros/log run dirs --"; ls -1 "$HOME/.ros/log" 2>/dev/null | wc -l | sed 's/^/  count: /'

sec "14 PACKAGES / SNAPS (old + redundant)"
if have apt-get; then
  echo "-- autoremovable --"
  apt-get -s autoremove 2>/dev/null | grep -E '^Remv|packages will be removed|freed' | head -20
fi
echo "-- installed kernels --"
dpkg -l 'linux-image-*' 2>/dev/null | awk '/^ii/{print "  "$2"  "$3}'
echo "  running: $(uname -r)"
if have snap; then
  echo "-- snaps (disabled revisions are pure waste) --"
  snap list --all 2>/dev/null | awk '{print "  "$1"  "$3"  "$6}'
fi

sec "15 WHAT IS RUNNING NOW"
ps -eo pcpu,pmem,etime,comm --sort=-pcpu 2>/dev/null | head -12
echo "-- aislebot-related processes --"
pgrep -af 'ros2|python3.*mecanum|ydlidar|slam_toolbox|phone_dashboard|nav2|component_container' 2>/dev/null | cut -c1-140 | head -20
if have ros2; then
  echo "-- ros2 node list (5s timeout) --"
  timeout 5 ros2 node list 2>/dev/null || echo "  (no ROS graph / not sourced)"
fi

if [ "$ONLINE" = "1" ]; then
sec "16 DEPLOYED CODE vs GITHUB (branch $BRANCH)"
  tmp=$(mktemp -d)
  # path-on-pi : path-in-repo
  set -- \
    "$WS/src/mecanum_robot/mecanum_robot/phone_dashboard.py:src/mecanum_robot/mecanum_robot/phone_dashboard.py" \
    "$WS/src/mecanum_robot/mecanum_robot/odometry_publisher.py:src/mecanum_robot/mecanum_robot/odometry_publisher.py" \
    "$WS/src/mecanum_robot/mecanum_robot/esp32_bridge.py:src/mecanum_robot/mecanum_robot/esp32_bridge.py" \
    "$WS/src/mecanum_robot/mecanum_robot/joy_to_aislebot.py:src/mecanum_robot/mecanum_robot/joy_to_aislebot.py" \
    "$WS/src/mecanum_robot/mecanum_robot/run_report.py:src/mecanum_robot/mecanum_robot/run_report.py" \
    "$WS/src/mecanum_robot/mecanum_robot/lcd_display.py:src/mecanum_robot/mecanum_robot/lcd_display.py" \
    "$WS/src/mecanum_robot/mecanum_robot/arm_bridge.py:src/mecanum_robot/mecanum_robot/arm_bridge.py" \
    "$WS/src/mecanum_robot/mecanum_robot/mecanum_teleop_asymmetric.py:src/mecanum_robot/mecanum_robot/mecanum_teleop_asymmetric.py" \
    "$WS/src/mecanum_robot/mecanum_robot/keyboard_teleop.py:src/mecanum_robot/mecanum_robot/keyboard_teleop.py" \
    "$WS/src/mecanum_robot/launch/mapping_full.launch.py:src/mecanum_robot/launch/mapping_full.launch.py" \
    "$WS/src/mecanum_robot/launch/aislebot_full.launch.py:src/mecanum_robot/launch/aislebot_full.launch.py" \
    "$WS/src/mecanum_robot/config/twist_mux.yaml:src/mecanum_robot/config/twist_mux.yaml" \
    "$WS/src/mecanum_robot/setup.py:src/mecanum_robot/setup.py" \
    "$WS/src/mecanum_robot/urdf/aislebot.urdf:src/mecanum_robot/urdf/aislebot.urdf" \
    "$WS/src/mecanum_navigation/mecanum_navigation/goal_pose_adapter.py:src/mecanum_navigation/mecanum_navigation/goal_pose_adapter.py" \
    "$WS/src/mecanum_navigation/mecanum_navigation/cmd_vel_axis_adapter.py:src/mecanum_navigation/mecanum_navigation/cmd_vel_axis_adapter.py" \
    "$WS/src/mecanum_navigation/launch/navigation.launch.py:src/mecanum_navigation/launch/navigation.launch.py" \
    "$WS/src/mecanum_navigation/config/nav2_params.yaml:src/mecanum_navigation/config/nav2_params.yaml" \
    "$WS/src/mecanum_navigation/config/ekf_params.yaml:src/mecanum_navigation/config/ekf_params.yaml" \
    "$WS/src/scan_relay/scan_relay.py:src/scan_relay/scan_relay.py" \
    "$WS/slam_nodom.yaml:system/slam_nodom_stageB.yaml"
  for pair in "$@"; do
    pi="${pair%%:*}"; repo="${pair#*:}"
    out="$tmp/$(echo "$repo" | tr / _)"
    if curl -fsSL -o "$out" "$RAW/$repo" 2>/dev/null; then
      if [ ! -f "$pi" ]; then
        printf 'MISSING-ON-PI  %s\n' "$repo"
      elif cmp -s "$pi" "$out"; then
        printf 'match          %s\n' "$repo"
      else
        printf 'DIFFERS        %s   (pi %s lines / %s B, repo %s lines / %s B)\n' \
          "$repo" "$(wc -l < "$pi")" "$(stat -c %s "$pi")" "$(wc -l < "$out")" "$(stat -c %s "$out")"
      fi
    else
      printf 'FETCH-FAILED   %s\n' "$repo"
    fi
  done
  echo "-- files on the Pi that the repo does not have (possible dead code) --"
  find "$WS/src" -type f -name '*.py' -not -path '*/build/*' -not -path '*/install/*' \
    -not -path '*ydlidar*' 2>/dev/null | sort | while read -r f; do
    rel="src/${f#"$WS/src/"}"
    curl -fsI "$RAW/$rel" >/dev/null 2>&1 || echo "  EXTRA: ${f#"$WS/src/"}"
  done
  rm -rf "$tmp"
fi

printf '\n### end of audit\n'
