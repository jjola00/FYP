#!/usr/bin/env python3
"""
Export Metrics Script

Queries both attempt_logs (line CAPTCHA) and image_attempt_logs (image CAPTCHA)
and produces a summary JSON for the FYP paper.

Usage:
    python -m backend.scripts.export_metrics
    python -m backend.scripts.export_metrics --output metrics.json
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import config


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_avg(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def export_image_metrics(conn: sqlite3.Connection) -> dict:
    """Extract metrics from image_attempt_logs."""
    rows = conn.execute("SELECT * FROM image_attempt_logs").fetchall()

    if not rows:
        return {"total_attempts": 0, "message": "No image CAPTCHA attempts logged"}

    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    solve_times = [r["solve_time_ms"] for r in rows]
    passed_solve_times = [r["solve_time_ms"] for r in rows if r["passed"]]
    reasons = Counter(r["reason"] for r in rows if not r["passed"])

    return {
        "total_attempts": total,
        "passed": passed,
        "solve_rate": passed / total,
        "avg_solve_time_ms": _safe_avg(passed_solve_times),
        "avg_all_solve_time_ms": _safe_avg(solve_times),
        "failure_reasons": dict(reasons.most_common()),
        "avg_excess_clicks": _safe_avg([r["excess"] for r in rows]),
    }


def export_line_metrics(conn: sqlite3.Connection) -> dict:
    """Extract metrics from attempt_logs (line CAPTCHA)."""
    try:
        rows = conn.execute("SELECT * FROM attempt_logs").fetchall()
    except sqlite3.OperationalError:
        return {"total_attempts": 0, "message": "No line CAPTCHA attempt_logs table"}

    if not rows:
        return {"total_attempts": 0, "message": "No line CAPTCHA attempts logged"}

    total = len(rows)
    passed = sum(1 for r in rows if r["outcome_reason"] == "success")
    durations = [r["duration_ms"] for r in rows if r["outcome_reason"] == "success"]
    reasons = Counter(r["outcome_reason"] for r in rows if r["outcome_reason"] != "success")

    bot_scores = [r["bot_score"] for r in rows if r["bot_score"] is not None]
    behavioural_flagged = sum(
        1 for r in rows if r["behavioural_flag"]
    )

    return {
        "total_attempts": total,
        "passed": passed,
        "solve_rate": passed / total,
        "avg_solve_time_ms": _safe_avg(durations),
        "failure_reasons": dict(reasons.most_common()),
        "bot_score_distribution": {
            "mean": _safe_avg(bot_scores),
            "max": max(bot_scores) if bot_scores else 0,
            "min": min(bot_scores) if bot_scores else 0,
        },
        "behavioural_flag_count": behavioural_flagged,
        "behavioural_flag_rate": behavioural_flagged / total if total else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Export CAPTCHA metrics")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    args = parser.parse_args()

    if not config.DB_PATH.exists():
        print(f"Database not found at {config.DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = _get_conn()

    metrics = {
        "image_captcha": export_image_metrics(conn),
        "line_captcha": export_line_metrics(conn),
        "config": {
            "image_ttl_ms": config.IMAGE_CHALLENGE_TTL_MS,
            "image_click_tolerance_px": config.IMAGE_CLICK_TOLERANCE_PX,
            "image_min_solve_time_ms": config.IMAGE_MIN_SOLVE_TIME_MS,
            "line_ttl_ms": config.CHALLENGE_TTL_MS,
        },
    }

    conn.close()

    output = json.dumps(metrics, indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Metrics written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
