#!/bin/bash
# 01_base_system.sh - OS packages, locale, serial-port permissions.
# Safe to run more than once.
source "$(dirname "$0")/common.sh"

step "1. Base system"
. /etc/os-release
[ "$VERSION_CODENAME" = "noble" ] || die "needs Ubuntu 24.04 (noble); this is $PRETTY_NAME"
ok "Ubuntu $VERSION_ID ($VERSION_CODENAME)"
[ "$(uname -m)" = "aarch64" ] || warn "not aarch64 ($(uname -m)); fine on a PC, unexpected on a Pi 5"
curl -sSf -o /dev/null https://github.com || die "no internet. Connect the Pi (Wi-Fi or Ethernet) first."
ok "internet reachable"

run sudo apt-get update
run sudo apt-get -y upgrade
run sudo apt-get install -y git curl wget rsync build-essential cmake pkg-config \
    python3-pip python3-venv python3-serial python3-yaml python3-numpy python3-matplotlib \
    software-properties-common locales i2c-tools openssh-server net-tools iw
ok "base packages"

run sudo locale-gen en_US en_US.UTF-8
run sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ok "locale en_US.UTF-8"

# Two Ubuntu desktop services that grab USB serial adapters:
#  brltty (braille displays) claims CH340 and CP210x adapters and the
#  /dev/ttyUSB* node disappears seconds after you plug the board in.
#  ModemManager probes new ttyACM devices with modem AT commands, which an
#  Arduino receives as garbage, and holds the port while it does.
if dpkg -s brltty >/dev/null 2>&1; then
    run sudo apt-get remove -y brltty
    ok "removed brltty (it steals USB serial adapters)"
fi
if systemctl list-unit-files | grep -q '^ModemManager'; then
    run sudo systemctl disable --now ModemManager
    ok "disabled ModemManager (it probes serial ports)"
fi

run sudo usermod -aG dialout "$USER"
getent group i2c >/dev/null && run sudo usermod -aG i2c "$USER"
ok "$USER in dialout (serial ports). Takes effect at the next login."

run sudo systemctl enable --now ssh
ok "ssh enabled"

# The dashboard's web server. pip into the user's own site-packages, pinned
# to the versions the kit was tested with.
run pip3 install --user --break-system-packages "fastapi==0.162.5" "uvicorn==0.54.0" "websockets==17.4"
ok "fastapi, uvicorn, websockets"
