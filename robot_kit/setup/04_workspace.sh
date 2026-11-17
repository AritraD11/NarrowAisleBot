#!/bin/bash
# 04_workspace.sh - regenerate configs, copy the kit's ROS package into the
# workspace and build it. Run it again after ANY change to the kit or to
# robot_config.yaml. It is the one "deploy" command.
source "$(dirname "$0")/common.sh"
step "4. Workspace"
python3 "$KIT/generate.py" || die "generate.py rejected robot_config.yaml (message above)"
load_env
source /opt/ros/jazzy/setup.bash
mkdir -p "$ROBOT_WS/src"
run rsync -a --delete --exclude '__pycache__' "$KIT/ros2/robot_base/" "$ROBOT_WS/src/robot_base/"
ok "robot_base copied to $ROBOT_WS/src/robot_base"
( cd "$ROBOT_WS" && rosdep install --from-paths src --ignore-src -y -r >> "$LOG" 2>&1 ) \
    || warn "rosdep could not resolve everything (see $LOG); the build may still work"
( cd "$ROBOT_WS" && colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release \
    >> "$LOG" 2>&1 ) || die "colcon build failed: tail -50 $LOG"
ok "colcon build"
echo
echo "  sha256 of what was deployed (compare with the kit if in doubt):"
( cd "$ROBOT_WS/src/robot_base" && sha256sum config/*.yaml urdf/*.urdf | sed 's/^/    /' )
