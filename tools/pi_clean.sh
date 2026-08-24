#!/usr/bin/env bash
# pi_clean.sh - remove accumulated waste from the AisleBot Pi.
#
# DRY RUN BY DEFAULT. Prints what it would remove and how much that frees.
# Nothing is touched until you pass --apply.
#
#   bash /tmp/pi_clean.sh            # show me what you would do
#   bash /tmp/pi_clean.sh --apply    # actually do it
#
# Deliberately DOES NOT TOUCH:
#   ~/aislebot_logs   - your run data. Copy it off the Pi first; a separate
#                       decision, made separately.
#   ~/slam_tests      - 128 MB, unidentified. Reported, never deleted.
#   ~/ros2_ws/src     - except four items named individually in section 8,
#                       and those are tarballed before removal.
#   ~/ros2_ws/build   - deleting it costs a full rebuild for 85 MB. Bad trade
#                       on the day you need to deploy and drive.
#
# Run it from a normal shell (not the graphical session). sudo is prompted
# for once and used for journald, apt, snap and systemd only.

APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

WS="$HOME/ros2_ws"
STAMP=$(date +%Y%m%d_%H%M%S)
FREED=0

sec()  { printf '\n===== %s =====\n' "$1"; }
kb()   { du -sk "$1" 2>/dev/null | cut -f1; }
human(){ numfmt --to=iec --suffix=B $(( ${1:-0} * 1024 )) 2>/dev/null || echo "${1}K"; }

# would <bytes-kb> <description>
would() { FREED=$(( FREED + ${1:-0} )); printf '  %-10s %s\n' "$(human "${1:-0}")" "$2"; }
run()   { if [ "$APPLY" = "1" ]; then eval "$1"; else printf '    would run: %s\n' "$1"; fi; }

echo "### AisleBot Pi cleanup  $(date -Is)"
if [ "$APPLY" = "1" ]; then echo "### MODE: APPLY - changes are real"
else echo "### MODE: DRY RUN - nothing will be modified. Re-run with --apply."; fi
echo "### disk before:"; df -h / | tail -1

sec "1 JOURNALD  (568 MB on this Pi, unbounded by default)"
echo "  current: $(journalctl --disk-usage 2>/dev/null)"
jkb=$(du -sk /var/log/journal 2>/dev/null | cut -f1)
jfree=$(( ${jkb:-0} - 102400 )); [ "$jfree" -lt 0 ] && jfree=0
would "$jfree" "vacuum journald down to 100 MB"
run "sudo journalctl --vacuum-size=100M"
# Cap it permanently so this does not come back.
if ! grep -q '^SystemMaxUse=' /etc/systemd/journald.conf 2>/dev/null; then
  echo "  + capping journald at 100M permanently (SystemMaxUse)"
  run "echo 'SystemMaxUse=100M' | sudo tee -a /etc/systemd/journald.conf >/dev/null"
  run "sudo systemctl restart systemd-journald"
fi

sec "2 ROS LOG DIRS  (5267 run dirs under ~/.ros/log)"
n=$(ls -1 "$HOME/.ros/log" 2>/dev/null | wc -l)
k=$(kb "$HOME/.ros/log")
echo "  $n entries"
would "${k:-0}" "delete every run dir under ~/.ros/log (regenerates on next run)"
run "rm -rf \"$HOME/.ros/log\"/* "

sec "3 COLCON BUILD LOGS  (62 dirs under ~/ros2_ws/log)"
n=$(ls -1 "$WS/log" 2>/dev/null | wc -l)
k=$(kb "$WS/log")
echo "  $n entries"
would "${k:-0}" "delete colcon build logs, keeping the 3 newest"
if [ "$APPLY" = "1" ]; then
  ls -1dt "$WS/log"/build_* 2>/dev/null | tail -n +4 | xargs -r rm -rf
else
  echo "    would run: keep 3 newest build_* dirs, rm -rf the rest"
fi

sec "4 YDLIDAR SDK BUILD TREE"
k=$(kb "$HOME/YDLidar-SDK/build")
echo "  the SDK itself is installed system-wide; this is just the build tree"
would "${k:-0}" "delete ~/YDLidar-SDK/build"
run "rm -rf \"$HOME/YDLidar-SDK/build\""

sec "5 VS CODE SERVER  (regenerates automatically on next connect)"
k=$(kb "$HOME/.vscode")
would "${k:-0}" "delete ~/.vscode"
run "rm -rf \"$HOME/.vscode\""

sec "6 OLD KERNEL"
RUNNING=$(uname -r)
echo "  running: $RUNNING  (this one is never touched)"
for pkg in $(dpkg -l 'linux-image-6*' 2>/dev/null | awk '/^ii/{print $2}'); do
  ver=${pkg#linux-image-}
  if [ "$ver" = "$RUNNING" ]; then
    echo "  KEEP   $pkg  (running kernel)"
  elif [ "$pkg" = "linux-image-raspi" ]; then
    echo "  KEEP   $pkg  (meta-package, pulls the current kernel)"
  else
    would 250000 "purge $pkg  (~estimate)"
    run "sudo apt-get -y purge $pkg"
  fi
done
run "sudo apt-get -y autoremove --purge"
run "sudo apt-get clean"

sec "7 SNAPS  (3.0 GB in /var/lib/snapd, 1019 MB in ~/snap)"
echo "  Headless robot: the browser, mail client and store are not used."
echo "  --purge skips the snapshot, which would otherwise keep the data on disk."
for s in thunderbird firefox snap-store snapd-desktop-integration; do
  if snap list "$s" >/dev/null 2>&1; then
    k=$(kb "$HOME/snap/$s")
    would "${k:-0}" "snap remove --purge $s  (+ its squashfs under /var/lib/snapd)"
    run "sudo snap remove --purge $s"
  fi
done
echo "  -- now-unused bases (removed only after the apps above are gone) --"
for s in gnome-42-2204 gnome-46-2404 gtk-common-themes mesa-2404; do
  if snap list "$s" >/dev/null 2>&1; then
    would 200000 "snap remove --purge $s  (~estimate; snapd refuses if still in use)"
    run "sudo snap remove --purge $s"
  fi
done
echo "  -- stop snapd hoarding old revisions --"
run "sudo snap set system refresh.retain=2"

sec "8 DESKTOP AUTOSTART"
echo "  current default target: $(systemctl get-default 2>/dev/null)"
echo "  Boots to console instead of GNOME. Frees ~250 MB RAM and a core"
echo "  during every mapping run - see Research_Journal.md 17.25, where CPU"
echo "  starvation killed SLAM and the LiDAR pipeline outright mid-run."
echo "  REVERSIBLE: sudo systemctl set-default graphical.target"
echo "  On demand without rebooting: sudo systemctl isolate graphical.target"
run "sudo systemctl set-default multi-user.target"
# Ubuntu names it gdm3; some images ship gdm. set-default alone is already
# sufficient, so a missing unit here is not a failure.
for dm in gdm3 gdm; do
  systemctl list-unit-files "$dm.service" 2>/dev/null | grep -q "$dm" && { run "sudo systemctl disable $dm"; break; }
done
echo "  NOTE: takes effect at the next reboot. SSH is unaffected either way."

sec "9 WORKSPACE DEAD CODE"
echo "  Tarballed to ~/aislebot_deadcode_${STAMP}.tar.gz before removal -"
echo "  there is no git clone on this Pi, so deleted means gone."
DEAD=""
for f in "$WS/src/mecanum_robot/mecanum_robot/phone_dashboard.bak.py" \
         "$WS/src/mecanum_robot/mecanum_robot/arm_bridge.bak.py" \
         "$WS/src/mecanum_robot/launch/hardware.launch.py"; do
  [ -e "$f" ] && { echo "  dead: ${f#"$WS/"}"; DEAD="$DEAD $f"; }
done
# rf2o is a recorded dead end - Research_Journal.md 13.5. Nothing launches it.
if [ -d "$WS/src/rf2o_laser_odometry" ]; then
  k=$(( $(kb "$WS/src/rf2o_laser_odometry") + $(kb "$WS/build/rf2o_laser_odometry") + $(kb "$WS/install/rf2o_laser_odometry") ))
  echo "  dead: src/rf2o_laser_odometry  (dropped in 13.5; no launch file references it)"
  would "${k:-0}" "remove rf2o_laser_odometry from src, build and install"
  DEAD="$DEAD $WS/src/rf2o_laser_odometry"
fi
if [ -n "$DEAD" ]; then
  run "tar czf \"$HOME/aislebot_deadcode_${STAMP}.tar.gz\" ${DEAD# } && rm -rf ${DEAD# } \"$WS/build/rf2o_laser_odometry\" \"$WS/install/rf2o_laser_odometry\""
else
  echo "  nothing to remove"
fi

sec "10 REPORTED, NOT TOUCHED"
for p in "$HOME/aislebot_logs" "$HOME/slam_tests" "$WS/build" "$HOME/.config" "$HOME/.local" "$HOME/aislebot_backup" "$HOME/AisleBot_Master_Backup.zip" "$HOME/dl" "$HOME/cp210x-cfg" "$HOME/Downloads"; do
  [ -e "$p" ] && printf '  %-8s %s\n' "$(du -sh "$p" 2>/dev/null | cut -f1)" "$p"
done
echo "  -- what is in slam_tests? (listing only) --"
ls -1 "$HOME/slam_tests" 2>/dev/null | head -12
echo "  -- rotated boot logs --"
ls -1 "$HOME"/*.log.*.gz 2>/dev/null | sed 's/^/    /'

sec "SUMMARY"
printf '  estimated reclaim: %s\n' "$(human "$FREED")"
echo "  disk now:"; df -h / | tail -1
if [ "$APPLY" != "1" ]; then
  echo
  echo "  DRY RUN - nothing above was done. Re-run with --apply to execute."
fi
