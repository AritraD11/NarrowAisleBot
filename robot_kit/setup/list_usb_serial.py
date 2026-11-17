#!/usr/bin/env python3
"""
list_usb_serial.py - which USB serial device is which, ready to paste into
robot_config.yaml. Standard library only.

    python3 setup/list_usb_serial.py

Plug in ONE board at a time and run it each time: the new entry is that
board. For each /dev/ttyUSB* and /dev/ttyACM* it prints the USB vendor and
product id, the serial number, the physical port path, and any /dev symlink
already pointing at it.

If two devices print the same vendor, product AND serial (NarrowAisleBot's
ESP32 and its YDLIDAR adapter did: two CP2102s, both serial "0001"), udev can
only tell them apart by the USB socket they are plugged into. Then fill
usb_port_path for BOTH, and never swap the cables.
"""
import argparse
import glob
import os


def read(path):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def usb_parent(sys_dev):
    """Walk up from the tty's device directory to the USB device (the
    directory that has idVendor)."""
    d = os.path.realpath(sys_dev)
    while d and d != "/":
        if os.path.exists(os.path.join(d, "idVendor")):
            return d
        d = os.path.dirname(d)
    return None


def scan(root="/"):
    out = []
    ttys = sorted(glob.glob(os.path.join(root, "sys/class/tty/ttyUSB*")) +
                  glob.glob(os.path.join(root, "sys/class/tty/ttyACM*")))
    links = {}
    for l in glob.glob(os.path.join(root, "dev/*")):
        if os.path.islink(l):
            links.setdefault(os.path.basename(os.path.realpath(l)), []).append(os.path.basename(l))
    for t in ttys:
        name = os.path.basename(t)
        usb = usb_parent(os.path.join(t, "device"))
        if not usb:
            continue
        out.append({
            "dev": "/dev/" + name,
            "vid": read(os.path.join(usb, "idVendor")),
            "pid": read(os.path.join(usb, "idProduct")),
            "serial": read(os.path.join(usb, "serial")),
            "manufacturer": read(os.path.join(usb, "manufacturer")),
            "product": read(os.path.join(usb, "product")),
            "port_path": os.path.basename(usb),
            "symlinks": links.get(name, []),
        })
    return out


KNOWN = {("10c4", "ea60"): "Silicon Labs CP210x (many ESP32 boards, YDLIDAR and RPLIDAR adapters)",
         ("1a86", "7523"): "WCH CH340 (cheap Arduino clones, some ESP32 boards)",
         ("1a86", "55d4"): "WCH CH9102 (newer ESP32 boards)",
         ("0403", "6001"): "FTDI FT232",
         ("2341", "0042"): "Arduino Mega 2560 (genuine)",
         ("2341", "0043"): "Arduino Uno (genuine)",
         ("303a", "1001"): "ESP32-S3 / C3 native USB",
         ("2e8a", "000a"): "Raspberry Pi Pico (RP2040)",
         ("16c0", "0483"): "Teensy"}


def main():
    ap = argparse.ArgumentParser(description="list USB serial devices")
    ap.add_argument("--root", default="/", help="filesystem root (for testing)")
    a = ap.parse_args()
    devs = scan(a.root)
    if not devs:
        print("No /dev/ttyUSB* or /dev/ttyACM* devices. Plug the board in (data cable, not a\n"
              "charge-only one) and check  dmesg | tail  for what the kernel saw.")
        return 1
    ids = {}
    for d in devs:
        ids.setdefault((d["vid"], d["pid"], d["serial"]), []).append(d["dev"])
    for d in devs:
        print(f"\n{d['dev']}   {d['manufacturer']} {d['product']}".rstrip())
        guess = KNOWN.get((d["vid"], d["pid"]))
        if guess:
            print(f"  (looks like: {guess})")
        if d["symlinks"]:
            print(f"  already linked as: {', '.join('/dev/' + s for s in d['symlinks'])}")
        print("  paste into robot_config.yaml (mcu: or lidar:):")
        print(f'    usb_vendor_id: "{d["vid"]}"')
        print(f'    usb_product_id: "{d["pid"]}"')
        print(f'    usb_serial: "{d["serial"]}"')
        print(f'    usb_port_path: ""          # this socket is "{d["port_path"]}"')
    clashes = [v for v in ids.values() if len(v) > 1]
    for c in clashes:
        print(f"\n!! {', '.join(c)} have the SAME vendor, product and serial. udev cannot tell\n"
              f"   them apart. Set usb_port_path for each (the socket values above) and do not\n"
              f"   move those cables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
