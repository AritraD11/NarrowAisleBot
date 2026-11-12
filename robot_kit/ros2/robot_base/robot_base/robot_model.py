"""
robot_model.py - read robot_config.yaml, fill in every "auto", and check it.

Used by generate.py and by tools/encoder_logger.py. The ROS nodes never read
the YAML themselves; they get flat parameters that generate.py writes into
config/robot.yaml. That keeps one source of truth and one place that
interprets it (this file).

load_config(path) returns the config dict with:
  - every wheel's x, y, ax, ay, counts_per_rev resolved to numbers
  - nav.controller and nav.inflation_radius resolved
  - lists (kff, kstat) checked against the number of wheels
and raises ConfigError with a plain-English message on anything wrong.
"""

import math
import os

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from .kinematics import DRIVE_TYPES, HOLONOMIC_TYPES, Wheel, DriveModel


class ConfigError(ValueError):
    pass


ALIASES = {
    "l": "left", "r": "right",
    "fl": "front_left", "fr": "front_right",
    "rl": "rear_left", "rr": "rear_right",
    "ml": "middle_left", "mr": "middle_right",
    "bl": "rear_left", "br": "rear_right",
    "back_left": "rear_left", "back_right": "rear_right",
}

# Which pins each driver type needs, in the order the firmware stores them
# (PIN_A, PIN_B, PIN_C).
DRIVER_PINS = {
    "pwm_dir": ("pwm", "dir", None),
    "pwm_in1_in2": ("pwm", "in1", "in2"),
    "dual_pwm": ("pwm_fwd", "pwm_rev", None),
}

# Mecanum roller handedness for the standard mounting. With these signs,
# +vy (left) spins front_left and rear_right backwards and the other two
# forwards, which is the usual layout. Verify on the robot (manual 10.3).
MECANUM_AUTO_SIGN = {
    "front_left": -1, "front_right": +1,
    "rear_left": +1, "rear_right": -1,
}


def canonical(name):
    n = str(name).strip().lower().replace("-", "_").replace(" ", "_")
    return ALIASES.get(n, n)


def _auto_xy(name, drive, track, base):
    n = canonical(name)
    half_t, half_b = track / 2.0, base / 2.0
    side = None
    if n.endswith("left") or n == "left":
        side = +1
    elif n.endswith("right") or n == "right":
        side = -1
    if side is None:
        raise ConfigError(
            f"wheel '{name}': cannot place it automatically. Name it left/right, "
            f"front_left/front_right/rear_left/rear_right (or fl/fr/rl/rr), or give x and y.")
    if n.startswith("front"):
        x = half_b
    elif n.startswith("rear"):
        x = -half_b
    else:
        x = 0.0
    if drive in ("skid_steer", "mecanum") and n in ("left", "right") and base > 0:
        raise ConfigError(f"wheel '{name}': with a wheelbase, name wheels front_/rear_/middle_ "
                          f"or give x and y explicitly.")
    return x, side * half_t


def _num(v, what):
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ConfigError(f"{what} must be a number, got {v!r}")


def resolve(cfg):
    """Resolve and validate a config dict in place. Returns it."""
    robot = cfg.get("robot") or {}
    drive = robot.get("drive_type")
    if drive not in DRIVE_TYPES:
        raise ConfigError(f"robot.drive_type must be one of {DRIVE_TYPES}, got {drive!r}")
    r = _num(robot.get("wheel_radius"), "robot.wheel_radius")
    if not 0.005 < r < 1.0:
        raise ConfigError(f"robot.wheel_radius {r} m looks wrong (expect 0.005 to 1.0)")
    track = _num(robot.get("track_width", 0), "robot.track_width")
    base = _num(robot.get("wheelbase", 0), "robot.wheelbase")
    robot.setdefault("track_width_scale", 1.0)
    robot.setdefault("lateral_scale", 1.0)

    wheels = cfg.get("wheels") or []
    if not wheels:
        raise ConfigError("wheels: list at least one driven wheel")
    if len(wheels) > 6:
        raise ConfigError("the firmware template supports up to 6 motors")
    names = [str(w.get("name", "")).strip() for w in wheels]
    if any(not n for n in names) or len(set(names)) != len(names):
        raise ConfigError("every wheel needs a unique name")
    if drive == "differential" and len(wheels) != 2:
        raise ConfigError("drive_type differential needs exactly 2 wheels "
                          "(use skid_steer for 4 or 6)")
    if drive == "mecanum" and len(wheels) != 4:
        raise ConfigError("drive_type mecanum needs exactly 4 wheels")

    dtype = (cfg.get("driver") or {}).get("type")
    if dtype not in DRIVER_PINS:
        raise ConfigError(f"driver.type must be one of {tuple(DRIVER_PINS)}, got {dtype!r}")

    for i, w in enumerate(wheels):
        tag = f"wheels[{i}] ({w['name']})"
        x, y = w.get("x", "auto"), w.get("y", "auto")
        if x == "auto" or y == "auto" or x is None or y is None:
            if drive == "omni":
                raise ConfigError(f"{tag}: omni wheels need explicit x, y and drive_angle_deg")
            ax_, ay_ = _auto_xy(w["name"], drive, track, base)
            x = ax_ if x in ("auto", None) else x
            y = ay_ if y in ("auto", None) else y
        w["x"], w["y"] = _num(x, f"{tag}.x"), _num(y, f"{tag}.y")

        if drive in ("differential", "skid_steer"):
            w["ax"], w["ay"] = 1.0, 0.0
        elif drive == "mecanum":
            s = w.get("mecanum_sign", "auto")
            if s in ("auto", None):
                s = MECANUM_AUTO_SIGN.get(canonical(w["name"]))
                if s is None:
                    raise ConfigError(f"{tag}: name mecanum wheels front_left/front_right/"
                                      f"rear_left/rear_right, or set mecanum_sign")
            s = int(s)
            if s not in (-1, 1):
                raise ConfigError(f"{tag}.mecanum_sign must be +1 or -1")
            w["mecanum_sign"] = s
            w["ax"], w["ay"] = 1.0, float(s)
        else:  # omni
            ang = math.radians(_num(w.get("drive_angle_deg"), f"{tag}.drive_angle_deg"))
            w["ax"], w["ay"] = math.cos(ang), math.sin(ang)

        cpr = w.get("counts_per_rev", "auto")
        if cpr in ("auto", None):
            ppr = _num(w.get("encoder_ppr"), f"{tag}.encoder_ppr")
            dec = _num(w.get("encoder_decoding", 4), f"{tag}.encoder_decoding")
            gear = _num(w.get("gear_ratio", 1), f"{tag}.gear_ratio")
            cpr = ppr * dec * gear
        cpr = _num(cpr, f"{tag}.counts_per_rev")
        if cpr <= 0:
            raise ConfigError(f"{tag}: counts_per_rev must be positive")
        w["counts_per_rev"] = cpr
        dec = int(_num(w.get("encoder_decoding", 4), f"{tag}.encoder_decoding"))
        if dec not in (2, 4):
            raise ConfigError(f"{tag}.encoder_decoding must be 2 or 4 for the firmware template")
        w["encoder_decoding"] = dec
        for k in ("motor_dir", "encoder_dir"):
            v = int(w.get(k, 1))
            if v not in (-1, 1):
                raise ConfigError(f"{tag}.{k} must be +1 or -1")
            w[k] = v

        pins = w.get("pins") or {}
        for pin_name in [p for p in DRIVER_PINS[dtype] if p] + ["enc_a", "enc_b"]:
            if pin_name not in pins:
                raise ConfigError(f"{tag}.pins needs '{pin_name}' for driver.type {dtype}")

    decs = {w["encoder_decoding"] for w in wheels}
    if len(decs) != 1:
        raise ConfigError("all wheels must use the same encoder_decoding")

    # The model has to be solvable, or odometry is meaningless.
    model = build_model(cfg)

    mcu = cfg.setdefault("mcu", {})
    n = len(wheels)
    for k in ("kff", "kstat"):
        v = mcu.get(k)
        if v in (None, "auto"):
            v = [0.0] * n
        if not isinstance(v, (list, tuple)) or len(v) != n:
            raise ConfigError(f"mcu.{k} needs exactly {n} values (one per wheel)")
        mcu[k] = [float(x) for x in v]
    if mcu.get("encoder_backend") not in ("pcnt", "isr"):
        raise ConfigError("mcu.encoder_backend must be pcnt or isr")
    if mcu.get("encoder_backend") == "pcnt" and mcu.get("board") != "esp32":
        raise ConfigError("encoder_backend pcnt only exists on the classic ESP32; use isr")

    nav = cfg.setdefault("nav", {})
    ctrl = nav.get("controller", "auto")
    if ctrl in ("auto", None):
        ctrl = "mppi" if drive in HOLONOMIC_TYPES else "rpp"
    if ctrl not in ("rpp", "mppi"):
        raise ConfigError("nav.controller must be auto, rpp or mppi")
    nav["controller"] = ctrl

    fp = footprint(cfg)
    circ = max(math.hypot(px, py) for px, py in fp)
    if nav.get("inflation_radius", "auto") in ("auto", None):
        nav["inflation_radius"] = round(circ + 0.10, 3)
    nav["circumscribed_radius"] = round(circ, 4)
    cfg["_model"] = model
    return cfg


def build_model(cfg):
    robot = cfg["robot"]
    wheels = [Wheel(w["name"], w["x"], w["y"], w["ax"], w["ay"]) for w in cfg["wheels"]]
    return DriveModel(wheels, robot["wheel_radius"],
                      robot["drive_type"] in HOLONOMIC_TYPES,
                      robot.get("track_width_scale", 1.0),
                      robot.get("lateral_scale", 1.0))


def footprint(cfg, padded=True):
    """Rectangle corners in base_link, counter-clockwise from front-left."""
    body = cfg["robot"]["body"]
    L, W = _num(body["length"], "body.length"), _num(body["width"], "body.width")
    cx = _num(body.get("center_x", 0.0), "body.center_x")
    m = _num(body.get("footprint_margin", 0.0), "body.footprint_margin") if padded else 0.0
    hx, hy = L / 2 + m, W / 2 + m
    return [(cx + hx, hy), (cx - hx, hy), (cx - hx, -hy), (cx + hx, -hy)]


def load_config(path):
    if yaml is None:
        raise ConfigError("PyYAML missing: sudo apt install python3-yaml")
    path = os.path.expanduser(path)
    with open(path) as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ConfigError(f"{path} is empty or not a YAML mapping")
    return resolve(cfg)
