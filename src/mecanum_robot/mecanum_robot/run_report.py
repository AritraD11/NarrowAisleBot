#!/usr/bin/env python3
"""
NarrowAisleBot — automated post-run analysis report
=====================================================
A pure-stdlib Python port of docs/tools/telemetry_analyzer.html's metrics
and findings logic (PID tracking + map quality), for automatic use right
after a mapping run — no browser, no manual drag-and-drop.

Exists because phone_dashboard.py's stop_mapping() runs headless on the
Pi and needs to generate the same report the HTML tool would, without a
browser to open it in. The two implementations compute the same numbers
from the same CSV/PGM/YAML inputs; keep them in sync by hand if either
changes.

Reads a run's telemetry CSV (pi_time_s + FR/FL/RR/RL_target_rads/
actual_rads/pwm — the same 13-column format tools/nab_pid_logger.py and
phone_dashboard.py's start_recording() both already write) plus an
optional matching .pgm/.yaml map pair from map_saver_cli, and writes a
single JSON report next to them.

    ./run_report.py run_20260807_143022.csv \
        --map run_20260807_143022

Also importable directly: generate_report(csv_path, pgm_path=None,
yaml_path=None) -> dict, used by phone_dashboard.py.

Aritra Das (25D0074) — IIT Bombay — Prof. Ambarish Kunwar
"""

import argparse
import csv as csvmod
import json
import math
import os
import sys
from datetime import datetime, timezone

MOTORS = ["FR", "FL", "RR", "RL"]
REQUIRED_COLUMNS = ["pi_time_s"] + [
    f"{m}_{f}" for m in MOTORS for f in ("target_rads", "actual_rads", "pwm")
]
PWM_SAT_DEFAULT = 230
SETTLE_BAND_DEFAULT = 0.05


# ─── small stats helpers (mirrors telemetry_analyzer.html) ────────────

def _finite(values):
    return [v for v in values if isinstance(v, float) and math.isfinite(v)]


def _mean(values):
    v = _finite(values)
    return sum(v) / len(v) if v else float("nan")


def _rms(values):
    v = _finite(values)
    return math.sqrt(sum(x * x for x in v) / len(v)) if v else float("nan")


def _mae(values):
    v = [abs(x) for x in _finite(values)]
    return sum(v) / len(v) if v else float("nan")


def _max_abs(values):
    v = [abs(x) for x in _finite(values)]
    return max(v) if v else float("nan")


def _median(values):
    v = sorted(_finite(values))
    if not v:
        return float("nan")
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2.0


def _to_number(value):
    if value is None:
        return float("nan")
    s = str(value).strip()
    if not s or s == "-" or s.lower() == "nan":
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


# ─── CSV loading, mirrors loadTelemetryFromText() ──────────────────────

def load_telemetry_csv(path):
    """Parse a run CSV into normalized rows: time (from t0), the 12
    target/actual/pwm columns, and a derived *_error per motor."""
    with open(path, newline='', encoding='utf-8-sig') as f:
        table = [row for row in csvmod.reader(f) if any(c.strip() for c in row)]
    if len(table) < 2:
        raise ValueError("CSV has no data rows.")
    header = [h.strip() for h in table[0]]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    index = {h: i for i, h in enumerate(header)}

    raw_rows = []
    invalid_cells = 0
    for src in table[1:]:
        item = {}
        for col in REQUIRED_COLUMNS:
            j = index[col]
            val = _to_number(src[j]) if j < len(src) else float("nan")
            item[col] = val
            if not math.isfinite(val):
                invalid_cells += 1
        raw_rows.append(item)

    valid_times = [r for r in raw_rows if math.isfinite(r["pi_time_s"])]
    if not valid_times:
        raise ValueError("No valid pi_time_s values.")
    t0 = valid_times[0]["pi_time_s"]

    normalized = []
    for i, r in enumerate(raw_rows):
        if not math.isfinite(r["pi_time_s"]):
            continue
        out = {"index": i, "time": r["pi_time_s"] - t0}
        for col in REQUIRED_COLUMNS:
            out[col] = r[col]
        for m in MOTORS:
            out[f"{m}_error"] = out[f"{m}_actual_rads"] - out[f"{m}_target_rads"]
        if math.isfinite(out["time"]):
            normalized.append(out)
    normalized.sort(key=lambda r: r["time"])

    if len(normalized) < 2:
        raise ValueError("Need at least two valid telemetry rows.")
    duration = normalized[-1]["time"] - normalized[0]["time"]
    return {"rows": normalized, "invalidCells": invalid_cells, "duration": max(0.0, duration)}


# ─── PID metrics, mirrors detectSettlingTimes() / computeMetrics() ────

def detect_settling_times(rows, motor, band, min_step=0.1, hold_samples=10):
    tgt_key, act_key = f"{motor}_target_rads", f"{motor}_actual_rads"
    clean = [r for r in rows
             if math.isfinite(r["time"]) and math.isfinite(r[tgt_key]) and math.isfinite(r[act_key])]
    n = len(clean)
    results = []
    for i in range(n - hold_samples - 1):
        prev, nxt = clean[i][tgt_key], clean[i + 1][tgt_key]
        if abs(nxt - prev) <= min_step or abs(nxt) < min_step:
            continue
        tol = max(abs(nxt) * band, 0.02)
        settled_index = None
        for k in range(i + 1, n - hold_samples):
            if all(abs(clean[k + h][act_key] - nxt) <= tol for h in range(hold_samples)):
                settled_index = k
                break
        results.append(None if settled_index is None else
                        clean[settled_index]["time"] - clean[i + 1]["time"])
    return results


def compute_pid_metrics(rows, pwm_sat=PWM_SAT_DEFAULT, settle_band=SETTLE_BAND_DEFAULT):
    times = [r["time"] for r in rows]
    dts = [times[i] - times[i - 1] for i in range(1, len(times))]
    duration = times[-1] - times[0] if len(times) > 1 else 0.0
    sample_rate = len(rows) / duration if duration > 0 else float("nan")
    median_dt = _median(dts)
    max_gap = max(dts) if dts else float("nan")

    command_rows = feedback_rows = 0
    for r in rows:
        commanded = any(abs(r[f"{m}_target_rads"]) > 0.01 or abs(r[f"{m}_pwm"]) > 0.5 for m in MOTORS)
        feedback = any(abs(r[f"{m}_actual_rads"]) > 0.01 for m in MOTORS)
        command_rows += commanded
        feedback_rows += feedback

    by_motor = {}
    for m in MOTORS:
        target = [r[f"{m}_target_rads"] for r in rows]
        actual = [r[f"{m}_actual_rads"] for r in rows]
        pwm = [r[f"{m}_pwm"] for r in rows]
        err = [r[f"{m}_error"] for r in rows]
        target_rows = sum(1 for r in rows if abs(r[f"{m}_target_rads"]) > 0.01)
        pwm_rows = sum(1 for r in rows if abs(r[f"{m}_pwm"]) > 0.5)
        actual_rows = sum(1 for r in rows if abs(r[f"{m}_actual_rads"]) > 0.01)
        sat_rows = sum(1 for r in rows if abs(r[f"{m}_pwm"]) >= pwm_sat)
        settle_times = detect_settling_times(rows, m, settle_band)
        settled = [v for v in settle_times if v is not None and math.isfinite(v)]
        by_motor[m] = {
            "rmsError": _rms(err), "maeError": _mae(err), "maxAbsError": _max_abs(err),
            "meanTarget": _mean(target), "meanActual": _mean(actual),
            "maxAbsTarget": _max_abs(target), "maxAbsActual": _max_abs(actual),
            "maxAbsPwm": _max_abs(pwm),
            "targetRows": target_rows, "pwmRows": pwm_rows, "actualRows": actual_rows,
            "satRows": sat_rows, "satPct": (sat_rows / len(rows) * 100.0) if rows else 0.0,
            "settleCount": len(settle_times), "settledCount": len(settled),
            "meanSettleTime": _mean(settled) if settled else float("nan"),
            "deadFeedback": (target_rows > 5 or pwm_rows > 5) and actual_rows == 0,
        }

    fr_rl = [r["FR_actual_rads"] - r["RL_actual_rads"] for r in rows]
    fl_rr = [r["FL_actual_rads"] - r["RR_actual_rads"] for r in rows]

    worst_motor, worst_val = None, float("-inf")
    for m in MOTORS:
        v = by_motor[m]["rmsError"]
        if math.isfinite(v) and v > worst_val:
            worst_motor, worst_val = m, v

    max_sat_motor, max_sat_val = None, float("-inf")
    for m in MOTORS:
        v = by_motor[m]["satPct"]
        if v > max_sat_val:
            max_sat_motor, max_sat_val = m, v

    all_feedback_dead = command_rows > 5 and feedback_rows == 0
    some_feedback_dead = any(by_motor[m]["deadFeedback"] for m in MOTORS)
    high_saturation = any(by_motor[m]["satPct"] > 20 for m in MOTORS)
    health = "bad" if all_feedback_dead else ("warn" if (some_feedback_dead or high_saturation) else "ok")

    return {
        "duration": duration, "samples": len(rows), "sampleRate": sample_rate,
        "medianDt": median_dt, "maxGap": max_gap,
        "commandRows": command_rows, "feedbackRows": feedback_rows,
        "byMotor": by_motor, "frRlRms": _rms(fr_rl), "flRrRms": _rms(fl_rr),
        "worstMotor": worst_motor, "maxSatMotor": max_sat_motor, "health": health,
        "allFeedbackDead": all_feedback_dead, "someFeedbackDead": some_feedback_dead,
        "highSaturation": high_saturation,
    }


def build_pid_findings(run, metrics):
    out = []
    if metrics["allFeedbackDead"]:
        out.append({
            "level": "bad", "title": "No encoder feedback while commanded",
            "body": f"{metrics['commandRows']} rows have target/PWM activity, but no motor "
                    f"reports nonzero actual velocity. This points to the common encoder/PCNT "
                    f"feedback path.",
        })
    for m in MOTORS:
        mm = metrics["byMotor"][m]
        if mm["deadFeedback"]:
            out.append({
                "level": "bad", "title": f"{m} feedback is stuck at zero",
                "body": f"{m} has {mm['targetRows']} target rows and {mm['pwmRows']} PWM rows, "
                        f"but {mm['actualRows']} feedback rows.",
            })
    saturated = [m for m in MOTORS if metrics["byMotor"][m]["satPct"] > 20]
    if saturated:
        parts = ", ".join(f"{m}: {metrics['byMotor'][m]['satPct']:.1f}%" for m in saturated)
        out.append({
            "level": "warn", "title": "PWM saturation is high",
            "body": f"{parts}. High saturation can hide tuning problems and cause windup.",
        })
    if math.isfinite(metrics["maxGap"]) and math.isfinite(metrics["medianDt"]) \
            and metrics["maxGap"] > metrics["medianDt"] * 5:
        out.append({
            "level": "warn", "title": "Telemetry gap detected",
            "body": f"Largest sample gap is {metrics['maxGap']:.3f} s; "
                    f"median gap is {metrics['medianDt']:.3f} s.",
        })
    if metrics["frRlRms"] > 0.3 or metrics["flRrRms"] > 0.3:
        out.append({
            "level": "warn", "title": "Diagonal mismatch is visible",
            "body": f"FR-RL RMS is {metrics['frRlRms']:.3f} rad/s and "
                    f"FL-RR RMS is {metrics['flRrRms']:.3f} rad/s.",
        })
    if run.get("invalidCells", 0) > 0:
        out.append({
            "level": "info", "title": "Invalid numeric cells were ignored",
            "body": f"{run['invalidCells']} cells were parsed as blank/invalid values.",
        })
    if not out:
        out.append({
            "level": "ok", "title": "No major telemetry fault detected",
            "body": "The selected window has command activity and measurable feedback "
                    "without severe saturation flags.",
        })
    return out


# ─── Map (.pgm + .yaml), mirrors parsePgm() / computeMapStats() ───────

def parse_simple_yaml(text):
    """Minimal key: value parser. map_saver_cli's YAML is flat enough
    that a full YAML library isn't needed — this reads it the same way
    telemetry_analyzer.html's parseSimpleYaml() does in the browser."""
    out = {}
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        idx = line.find(":")
        if idx == -1:
            continue
        key = line[:idx].strip()
        value = line[idx + 1:].strip()
        hash_idx = value.find(" #")
        if hash_idx != -1:
            value = value[:hash_idx].strip()
        if value.startswith("[") and value.endswith("]"):
            value = [_to_number(s.strip()) for s in value[1:-1].split(",")]
        elif value in ("true", "false"):
            value = (value == "true")
        else:
            num = _to_number(value)
            value = num if math.isfinite(num) else value.strip("\"'")
        out[key] = value
    return out


def parse_pgm(path):
    """Reads a P5 (binary) or P2 (ASCII) PGM, as written by map_saver_cli."""
    with open(path, "rb") as f:
        data = f.read()
    pos = 0

    def skip_ws_and_comments():
        nonlocal pos
        while pos < len(data):
            c = data[pos]
            if c == 0x23:  # '#'
                while pos < len(data) and data[pos] != 0x0A:
                    pos += 1
            elif c in (0x20, 0x09, 0x0A, 0x0D):
                pos += 1
            else:
                break

    def read_token():
        nonlocal pos
        skip_ws_and_comments()
        start = pos
        while pos < len(data) and data[pos] not in (0x20, 0x09, 0x0A, 0x0D):
            pos += 1
        return data[start:pos].decode("ascii", "ignore")

    magic = read_token()
    if magic not in ("P5", "P2"):
        raise ValueError(f'Not a PGM file (expected P5/P2 header, got "{magic}")')
    width, height, maxval = int(read_token()), int(read_token()), int(read_token())
    if not (width and height and maxval):
        raise ValueError("Malformed PGM header.")

    if magic == "P5":
        pos += 1  # single whitespace byte separating header from binary data
        pixels = data[pos:pos + width * height]
        if len(pixels) < width * height:
            raise ValueError("PGM binary data is truncated.")
        pixels = list(pixels)
    else:
        pixels = [int(read_token()) for _ in range(width * height)]

    return {"width": width, "height": height, "maxval": maxval, "data": pixels}


def classify_map_pixel(value):
    """Standard ROS occupancy-grid PGM convention, as written by nav2's
    map_saver_cli: 0 = occupied, 205 = unknown, 254 = free. Classify by
    nearest reference value rather than exact match, in case of any
    encoder/format variation."""
    d_occ, d_unk, d_free = abs(value - 0), abs(value - 205), abs(value - 254)
    if d_occ <= d_unk and d_occ <= d_free:
        return "occupied"
    if d_free <= d_unk and d_free <= d_occ:
        return "free"
    return "unknown"


def compute_map_stats(pgm, yaml_meta):
    occupied = free = unknown = 0
    for v in pgm["data"]:
        cls = classify_map_pixel(v)
        if cls == "occupied":
            occupied += 1
        elif cls == "free":
            free += 1
        else:
            unknown += 1
    total = pgm["width"] * pgm["height"]
    resolution = yaml_meta.get("resolution")
    resolution = float(resolution) if isinstance(resolution, (int, float)) else 0.05
    return {
        "width": pgm["width"], "height": pgm["height"], "total": total,
        "occupied": occupied, "free": free, "unknown": unknown,
        "occupiedPct": (occupied / total * 100.0) if total else 0.0,
        "freePct": (free / total * 100.0) if total else 0.0,
        "unknownPct": (unknown / total * 100.0) if total else 0.0,
        "resolution": resolution,
        "extentWidthM": pgm["width"] * resolution,
        "extentHeightM": pgm["height"] * resolution,
    }


def build_map_findings(stats):
    out = []
    if stats["unknownPct"] > 90:
        out.append({
            "level": "bad", "title": "Almost entirely unmapped",
            "body": f"{stats['unknownPct']:.1f}% unknown. This run barely covered any area — "
                    f"drive further, with some loop closure, before saving next time.",
        })
    elif stats["unknownPct"] > 70:
        out.append({
            "level": "warn", "title": "Sparse coverage",
            "body": f"{stats['unknownPct']:.1f}% unknown. Fine as a pipeline check, "
                    f"not yet a usable map for navigation.",
        })
    else:
        out.append({
            "level": "ok", "title": "Reasonable coverage",
            "body": f"{stats['unknownPct']:.1f}% unknown, {stats['freePct']:.1f}% free, "
                    f"{stats['occupiedPct']:.1f}% occupied.",
        })
    if stats["occupiedPct"] < 0.5:
        out.append({
            "level": "warn", "title": "Almost no occupied space resolved",
            "body": "Very few wall/obstacle cells detected. Check the drive path actually "
                    "passed close enough to real obstacles for slam_toolbox's scan matching "
                    "to resolve them.",
        })
    return out


# ─── Combined report ────────────────────────────────────────────────

def generate_report(csv_path, pgm_path=None, yaml_path=None,
                     pwm_sat=PWM_SAT_DEFAULT, settle_band=SETTLE_BAND_DEFAULT):
    """Build the same combined PID + map report as telemetry_analyzer.html's
    Export JSON button, for one run, without a browser."""
    run = load_telemetry_csv(csv_path)
    metrics = compute_pid_metrics(run["rows"], pwm_sat, settle_band)
    findings = build_pid_findings(run, metrics)

    map_block = None
    if pgm_path and yaml_path and os.path.exists(pgm_path) and os.path.exists(yaml_path):
        pgm = parse_pgm(pgm_path)
        with open(yaml_path, encoding="utf-8") as f:
            yaml_meta = parse_simple_yaml(f.read())
        stats = compute_map_stats(pgm, yaml_meta)
        map_block = {
            "pgmName": os.path.basename(pgm_path),
            "yamlName": os.path.basename(yaml_path),
            "stats": stats,
            "findings": build_map_findings(stats),
        }

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "thresholds": {"pwmSat": pwm_sat, "settleBand": settle_band},
        "name": os.path.basename(csv_path),
        "invalidCells": run["invalidCells"],
        "duration": metrics["duration"], "samples": metrics["samples"],
        "sampleRate": metrics["sampleRate"],
        "commandRows": metrics["commandRows"], "feedbackRows": metrics["feedbackRows"],
        "health": metrics["health"],
        "frRlRms": metrics["frRlRms"], "flRrRms": metrics["flRrRms"],
        "byMotor": metrics["byMotor"], "findings": findings, "map": map_block,
    }


def _json_safe(obj):
    """json.dumps emits bare NaN/Infinity by default (invalid JSON); the
    browser tool's JSON.stringify turns those into null, so match that."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def write_report(report, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(_json_safe(report), f, indent=2)
    return out_path


# ─── CLI ────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="NarrowAisleBot post-run analysis report (PID + map)",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("csv", help="run telemetry CSV (pi_time_s + 12 motor columns)")
    ap.add_argument("--map", dest="map_prefix", default=None,
                     help="prefix for a matching .pgm/.yaml pair from map_saver_cli "
                          "(e.g. --map run_20260807_143022 looks for that .pgm and .yaml)")
    ap.add_argument("-o", "--out", default=None,
                     help="output JSON path (default: <csv-without-ext>_report.json)")
    args = ap.parse_args()

    pgm_path = yaml_path = None
    if args.map_prefix:
        pgm_path, yaml_path = args.map_prefix + ".pgm", args.map_prefix + ".yaml"

    try:
        report = generate_report(args.csv, pgm_path, yaml_path)
    except (ValueError, OSError) as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1

    out_path = args.out or (os.path.splitext(args.csv)[0] + "_report.json")
    write_report(report, out_path)

    print(f"Report written -> {out_path}")
    print(f"Health: {report['health']}   ({report['samples']} samples, "
          f"{report['duration']:.1f}s @ {report['sampleRate']:.1f} Hz)")
    for finding in report["findings"]:
        print(f"  [{finding['level'].upper()}] {finding['title']}")
    if report["map"]:
        s = report["map"]["stats"]
        print(f"Map: {s['unknownPct']:.1f}% unknown, {s['freePct']:.1f}% free, "
              f"{s['occupiedPct']:.1f}% occupied ({s['width']}x{s['height']} px)")
        for finding in report["map"]["findings"]:
            print(f"  [{finding['level'].upper()}] {finding['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
