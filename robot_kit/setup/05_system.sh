#!/bin/bash
# 05_system.sh - udev rule, shell environment, systemd service.
source "$(dirname "$0")/common.sh"
load_env
step "5. System integration"

run sudo cp "$KIT/setup/generated/99-robot.rules" /etc/udev/rules.d/99-robot.rules
run sudo udevadm control --reload-rules
run sudo udevadm trigger
ok "udev rule installed: /dev/$MCU_DEVICE, /dev/$LIDAR_DEVICE"

add() { grep -qxF "$1" "$HOME/.bashrc" || echo "$1" >> "$HOME/.bashrc"; }
add ""
add "# ── robot kit ──────────────────────────────────────────────"
add "source /opt/ros/jazzy/setup.bash"
add "[ -f $ROBOT_WS/install/setup.bash ] && source $ROBOT_WS/install/setup.bash"
add "export ROS_DOMAIN_ID=$ROBOT_DOMAIN_ID"
add "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
add "export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name=\"lo\" priority=\"default\" multicast=\"false\"/></Interfaces></General></Domain></CycloneDDS>'"
add "alias rk-gen='python3 $KIT/generate.py'"
add "alias rk-build='$KIT/setup/04_workspace.sh && source $ROBOT_WS/install/setup.bash'"
add "alias rk-start='sudo systemctl start robot'"
add "alias rk-stop='sudo systemctl stop robot'"
add "alias rk-restart='sudo systemctl restart robot'"
add "alias rk-status='systemctl status robot --no-pager'"
add "alias rk-log='tail -f $HOME/robot_boot.log'"
add "alias rk-check='$KIT/setup/check_robot.sh'"
add "alias rk-ports='ls -l /dev/$MCU_DEVICE /dev/$LIDAR_DEVICE 2>&1'"
ok "~/.bashrc: ROS environment and rk-* aliases"

sudo tee /etc/systemd/system/robot.service > /dev/null <<UNIT
[Unit]
Description=Robot kit base stack (bridge, controller, odometry, twist_mux, dashboard)
After=network.target systemd-udev-settle.service
Wants=systemd-udev-settle.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=/bin/bash $KIT/setup/start_robot.sh
Restart=on-failure
RestartSec=10s
# mixed: SIGINT/SIGTERM to the launch process first, so the dashboard can
# save an open map and stop SLAM cleanly; everything else is killed after
# the timeout. (NarrowAisleBot once lost a 24-minute map to a restart.)
KillMode=mixed
KillSignal=SIGINT
TimeoutStopSec=30s

[Install]
WantedBy=multi-user.target
UNIT
run sudo systemctl daemon-reload
if [ "$ROBOT_AUTOSTART" = "true" ]; then
    run sudo systemctl enable robot.service
    ok "robot.service enabled at boot (start now with: sudo systemctl start robot)"
else
    ok "robot.service installed, not enabled (system.autostart is false)"
fi
mkdir -p "$LOG_DIR" "$HOME/maps"
ok "log dir $LOG_DIR, maps in ~/maps"
