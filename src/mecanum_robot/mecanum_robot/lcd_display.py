#!/usr/bin/env python3
"""
lcd_display.py — persistent network-status display.

Was drive/arm/lift telemetry until 13 Aug 2026, replaced at the user's
explicit request: this session spent real time unable to find the Pi on
the network after switching between eduroam / IITB-Wireless / the
AisleBot-Pi AP (mDNS unreachable more than once, IP changing on every
switch) with no way to check except an already-open SSH session — exactly
the thing that's unavailable right after a network switch. Reading the IP
straight off the robot removes the discovery step entirely. Movement
state was explicitly declared no longer needed on this display.

Two lines, refreshed every 2s (the IP changes on a network switch, not
4x/second like the old wheel-speed telemetry did — no reason to hit the
I2C bus that often):

    line 1: the current IP address
    line 2: AP   :8080   -- on the AisleBot-Pi AP's fixed address
                             (10.42.0.1, Important_Commands.md §1) --
                             :8080 is phone_dashboard.py's port, so this
                             line doubles as "here is the dashboard URL"
            NET  :22     -- any other network (eduroam, IITB-Wireless,
                             home wifi, ...) -- :22 is ssh, which is the
                             only thing these networks are used for
            NO NETWORK   -- no interface has a route at all
"""
import re
import subprocess

import rclpy
from rclpy.node import Node
from RPLCD.i2c import CharLCD


WLAN_IFACE = 'wlan0'
AP_IP = '10.42.0.1'   # AisleBot-Pi AP's fixed address (Important_Commands.md §1)
AP_PORT = 8080        # phone_dashboard.py's port
NET_PORT = 22          # ssh -- the only thing eduroam/IITB-Wireless/etc. are for


class LCDDisplay(Node):

    def __init__(self):
        super().__init__('lcd_display')

        try:
            self.lcd = CharLCD(
                i2c_expander='PCF8574',
                address=0x27,
                port=1,
                cols=16,
                rows=2,
                dotsize=8
            )
            self.lcd.clear()
            self.lcd_ok = True
            self.get_logger().info('LCD initialized at 0x27')
        except Exception as e:
            self.lcd_ok = False
            self.get_logger().error(f'LCD init failed: {e}')

        self._last_shown = None
        self.create_timer(2.0, self.update_display)
        self.update_display()

    def _get_ip(self):
        # Read the IP straight off the interface rather than inferring it by
        # opening a socket toward the internet (the previous approach). That
        # trick needs a route to exist -- even an unused one -- and the
        # AisleBot-Pi AP deliberately has no upstream route at all (no
        # internet uplink, by design). It failed silently into "NO NETWORK"
        # in exactly the one mode this display exists to cover.
        try:
            out = subprocess.check_output(
                ['ip', '-4', '-o', 'addr', 'show', WLAN_IFACE],
                stderr=subprocess.DEVNULL, timeout=1.0,
            ).decode()
            m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', out)
            return m.group(1) if m else None
        except Exception:
            return None

    def update_display(self):
        if not self.lcd_ok:
            return

        ip = self._get_ip()
        if ip is None:
            line1, line2 = 'NO NETWORK', '(check wifi)'
        elif ip == AP_IP:
            line1, line2 = ip, f'AP   :{AP_PORT}'
        else:
            line1, line2 = ip[:16], f'NET  :{NET_PORT}'

        shown = (line1, line2)
        if shown == self._last_shown:
            return  # unchanged since last check -- skip the I2C write
        self._last_shown = shown

        try:
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(f'{line1:<16}'[:16])
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(f'{line2:<16}'[:16])
        except Exception as e:
            self.get_logger().warn(f'LCD write error: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = LCDDisplay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if node.lcd_ok:
                node.lcd.clear()
                node.lcd.write_string('AISLEBOT OFF')
        except Exception:
            pass
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
