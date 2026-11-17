"""
telemetry_csv.py - write mcu_bridge telemetry rows to CSV. No ROS, so the
dashboard's mock mode and the ROS logger share it.
"""

import csv
import os
from datetime import datetime

from robot_base.protocol import csv_header


class TelemetryCsv:
    """Shared by this node and the dashboard."""

    def __init__(self, log_dir, names, tag="ros"):
        d = os.path.expanduser(log_dir)
        os.makedirs(d, exist_ok=True)
        self.path = os.path.join(d, f"{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        self.names = list(names)
        self.n = len(self.names)
        self.fh = None
        self.w = None
        self.rows = 0

    def add(self, t, data):
        """data = [mcu_ms, values...] as mcu_bridge publishes it."""
        vals = list(data[1:])
        if len(vals) not in (3 * self.n, 7 * self.n):
            return
        if self.fh is None:
            self.fh = open(self.path, "w", newline="")
            self.w = csv.writer(self.fh)
            self.w.writerow(csv_header(self.names, len(vals) == 7 * self.n))
        self.w.writerow([f"{t:.4f}", int(data[0])] + [f"{v:g}" for v in vals])
        self.rows += 1
        if self.rows % 50 == 0:
            self.fh.flush()

    def close(self):
        if self.fh:
            self.fh.close()
            self.fh = None
        return self.path if self.rows else None
