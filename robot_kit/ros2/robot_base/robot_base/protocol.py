"""
protocol.py - the Pi <-> microcontroller serial protocol, in one place.

Shared by the ROS bridge (mcu_bridge.py) and the encoder logger
(tools/encoder_logger.py). Nothing here imports ROS.

Wire format (identical in spirit to NarrowAisleBot's ESP32 v3.0 protocol,
generalised from 4 motors to N):

  Pi -> MCU, every command framed as <...>:
    <V,w0,...,wN-1>   wheel velocity targets, rad/s, closed loop
    <M,p0,...,pN-1>   raw PWM, open loop, until the next V/B/T
    <B,vx,vy,wz>      body twist, the MCU runs the inverse kinematics
    <T,i,w>           one motor closed loop
    <S>               E-STOP, latches until <E1>
    <E1> / <E0>       enable (and clear E-STOP) / disable
    <W1> / <W0>       command watchdog on / off
    <Y1> / <Y0>       runaway / stall / overspeed trips on / off
    <G,kp,ki,kd>      PID gains
    <F,...N>          feedforward slope Kff per motor
    <K,...N>          static friction Kstat per motor
    <A,accel>         setpoint slew limit rad/s^2, 0 = off
    <X,vmax>          wheel speed clamp rad/s
    <L0> <L1[,hz]> <L2[,hz]>   telemetry off / basic / extended
    <O> <R>           print / zero accumulated wheel angles
    <P> <I> <?> <H>   ping / config dump / live state / help

  MCU -> Pi:
    telemetry lines, plain CSV, first field is the MCU's millis():
      L1:  ms, then per motor: target, actual, pwm            (1 + 3N fields)
      L2:  L1, then per motor: error, ff, iterm, pos_rad      (1 + 7N fields)
    replies, always in square brackets: [PONG] [OK,...] [ERR,...]
      [WARN,...] [TRIP,...] [INFO,...] [MOTORS,N,name0,...] ...

Any line that is neither is ignored, so a boot banner never breaks parsing.
"""

import threading
import time

BASIC_FIELDS = ("target", "actual", "pwm")
EXT_FIELDS = ("error", "ff", "iterm", "pos_rad")


def frame(*parts):
    return "<" + ",".join(str(p) for p in parts) + ">"


def fmt(v, nd=3):
    return f"{v:.{nd}f}"


def cmd_velocity(rates):
    return frame("V", *(fmt(r) for r in rates))


def cmd_pwm(pwms):
    return frame("M", *(str(int(round(p))) for p in pwms))


def cmd_gains(kp, ki, kd):
    return frame("G", fmt(kp, 4), fmt(ki, 4), fmt(kd, 4))


def cmd_per_motor(letter, values):
    return frame(letter, *(fmt(v, 4) for v in values))


class Telemetry:
    __slots__ = ("mcu_ms", "target", "actual", "pwm",
                 "error", "ff", "iterm", "pos_rad", "extended", "values")

    def __init__(self, mcu_ms, values, n):
        self.mcu_ms = mcu_ms
        self.values = values                       # everything after the stamp
        self.target = [values[3 * i] for i in range(n)]
        self.actual = [values[3 * i + 1] for i in range(n)]
        self.pwm = [values[3 * i + 2] for i in range(n)]
        self.extended = len(values) >= 7 * n
        if self.extended:
            b = 3 * n
            self.error = [values[b + 4 * i] for i in range(n)]
            self.ff = [values[b + 4 * i + 1] for i in range(n)]
            self.iterm = [values[b + 4 * i + 2] for i in range(n)]
            self.pos_rad = [values[b + 4 * i + 3] for i in range(n)]
        else:
            self.error = self.ff = self.iterm = self.pos_rad = None


def parse_telemetry(line, n):
    """Return Telemetry or None. Accepts exactly 1+3N or 1+7N fields."""
    if not line or not line[0].isdigit() or "," not in line:
        return None
    parts = line.split(",")
    if len(parts) not in (1 + 3 * n, 1 + 7 * n):
        return None
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        return None
    return Telemetry(int(vals[0]), vals[1:], n)


def parse_reply(line):
    """'[OK,GAINS,1,2,3]' -> ('OK', ['GAINS', '1', '2', '3']). None if not a reply."""
    if not (line.startswith("[") and line.endswith("]")):
        return None
    body = line[1:-1].split(",")
    return body[0], body[1:]


def align_to_mcu_clock(rows):
    """Re-time rows [(pi_time, Telemetry)] on the microcontroller's clock.

    USB delivery jitters the Pi-side arrival time by milliseconds to tens of
    milliseconds. The MCU's millis() stamp is taken when the sample is
    made. Delays only ever make a line arrive LATER, so the smallest
    (arrival - mcu_time) over the run is the true offset between the two
    clocks; adding it to every mcu_time gives sample times on the Pi's
    clock without the transport jitter. Crystal drift (~50 ppm) is a few
    ms over a minute and is ignored.
    """
    if not rows:
        return []
    offset = min(t - tel.mcu_ms / 1000.0 for t, tel in rows)
    return [(tel.mcu_ms / 1000.0 + offset, tel) for t, tel in rows]


def csv_header(names, extended):
    cols = ["pi_time_s", "mcu_ms"]
    for nm in names:
        cols += [f"{nm}_{f}" for f in ("target_rads", "actual_rads", "pwm")]
    if extended:
        for nm in names:
            cols += [f"{nm}_{f}" for f in EXT_FIELDS]
    return cols


class SerialLink:
    """A serial port with a background reader thread.

    Every line is timestamped on arrival in the reader thread (so writer
    activity never adds jitter to the timestamps), then handed to
    on_line(t, line) if given. Telemetry rows can also be collected into a
    list between start_collect() and stop_collect().
    """

    def __init__(self, port, baud, n_motors=None, on_line=None,
                 open_delay=2.0, verbose=False):
        import serial  # imported here so the pure helpers work without pyserial
        self._serial_mod = serial
        self.port = port
        self.ser = serial.Serial(port, baud, timeout=0.1, write_timeout=1.0)
        # Opening the port resets most boards (DTR). Give it time to boot.
        time.sleep(open_delay)
        self.ser.reset_input_buffer()
        self.n = n_motors
        self.on_line = on_line
        self.verbose = verbose
        self.rows = []
        self.replies = []
        self._collect = False
        self._lock = threading.Lock()
        self._wlock = threading.Lock()
        self.running = True
        self.last_rx = 0.0
        self.error = None
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        buf = b""
        while self.running:
            try:
                # Read what is waiting, or block for ONE byte. ser.read(512)
                # with a timeout waits until 512 bytes pile up, so lines
                # arrive in bursts and get timestamped up to ~100 ms late.
                # NarrowAisleBot's nab_pid_logger.py does exactly that.
                chunk = self.ser.read(self.ser.in_waiting or 1)
            except Exception as e:  # serial.SerialException, OSError
                self.error = str(e)
                self.running = False
                break
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode("ascii", "ignore").strip()
                if line:
                    self._handle(time.time(), line)
            if len(buf) > 4096:          # garbage with no newline: drop it
                buf = b""

    def _handle(self, t, line):
        self.last_rx = t
        if self.on_line:
            try:
                self.on_line(t, line)
            except Exception:
                pass
        if line.startswith("["):
            with self._lock:
                self.replies.append((t, line))
                del self.replies[:-200]
            if self.verbose:
                print(f"    {line}")
            return
        if self._collect and self.n:
            tel = parse_telemetry(line, self.n)
            if tel is not None:
                with self._lock:
                    self.rows.append((t, tel))

    def send(self, cmd, settle=0.02):
        with self._wlock:
            self.ser.write(cmd.encode("ascii"))
            self.ser.flush()
        if settle:
            time.sleep(settle)

    def query(self, cmd, prefix, timeout=1.0):
        """Send cmd, wait for the first reply starting with '[' + prefix."""
        self.drain_replies()
        self.send(cmd, 0)
        t_end = time.time() + timeout
        while time.time() < t_end:
            with self._lock:
                for _, r in self.replies:
                    if r.startswith("[" + prefix):
                        return r
            time.sleep(0.01)
        return None

    def start_collect(self):
        with self._lock:
            self.rows = []
            self._collect = True

    def stop_collect(self):
        with self._lock:
            self._collect = False
            return list(self.rows)

    def drain_replies(self):
        with self._lock:
            r = list(self.replies)
            self.replies.clear()
        return r

    def close(self, stop=True):
        if stop:
            for c in ("<S>", "<L0>", "<E0>"):
                try:
                    self.send(c, 0.03)
                except Exception:
                    pass
        self.running = False
        time.sleep(0.15)
        try:
            self.ser.close()
        except Exception:
            pass


def read_identity(link, timeout=1.5):
    """Ask the firmware who it is. Returns dict with 'info', 'n', 'names'
    (n/names None if the firmware does not print [MOTORS,...])."""
    link.drain_replies()
    link.send("<I>", 0)
    t_end = time.time() + timeout
    out = {"info": None, "n": None, "names": None, "lines": []}
    while time.time() < t_end:
        time.sleep(0.05)
        for _, r in link.drain_replies():
            out["lines"].append(r)
            p = parse_reply(r)
            if not p:
                continue
            tag, fields = p
            if tag == "INFO":
                out["info"] = ",".join(fields)
            elif tag == "MOTORS" and fields:
                try:
                    out["n"] = int(fields[0])
                    out["names"] = fields[1:1 + out["n"]]
                except ValueError:
                    pass
        if out["n"] is not None and out["info"] is not None:
            break
    return out
