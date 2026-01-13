#!/usr/bin/env python3
import argparse
import sqlite3
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

DB_PATH = Path("data") / "captcha.db"


def _is_pass(reason: str) -> bool:
    return reason in ("success", "success_with_behavioural_flag")


def _median(values):
    return statistics.median(values) if values else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize line CAPTCHA attempts.")
    parser.add_argument("--limit", type=int, default=200, help="Max attempts to analyze (newest first).")
    parser.add_argument("--since-hours", type=float, default=None, help="Only include attempts within N hours.")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"No database found at {DB_PATH}.")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    params = []
    where = ""
    if args.since_hours is not None:
        cutoff = time.time() - (args.since_hours * 3600)
        where = "WHERE created_at >= ?"
        params.append(cutoff)

    query = f"""
        SELECT pointer_type, duration_ms, outcome_reason, coverage_ratio, created_at
        FROM attempt_logs
        {where}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(args.limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        print("No attempts found for the selected window.")
        return 0

    total = len(rows)
    pass_rows = [r for r in rows if _is_pass(r["outcome_reason"])]
    pass_count = len(pass_rows)
    pass_rate = (pass_count / total) * 100

    durations_all = [float(r["duration_ms"]) for r in rows if r["duration_ms"] is not None]
    durations_pass = [float(r["duration_ms"]) for r in pass_rows if r["duration_ms"] is not None]
    coverage_all = [float(r["coverage_ratio"]) for r in rows if r["coverage_ratio"] is not None]

    reasons = Counter(r["outcome_reason"] for r in rows)
    by_pointer = defaultdict(lambda: {"total": 0, "pass": 0, "durations": []})
    for r in rows:
        key = r["pointer_type"] or "unknown"
        by_pointer[key]["total"] += 1
        if _is_pass(r["outcome_reason"]):
            by_pointer[key]["pass"] += 1
        if r["duration_ms"] is not None:
            by_pointer[key]["durations"].append(float(r["duration_ms"]))

    print(f"Attempts analyzed: {total}")
    print(f"Pass rate: {pass_count}/{total} ({pass_rate:.1f}%)")
    if durations_pass:
        print(f"Median solve time (passes): {statistics.median(durations_pass):.0f} ms")
    if durations_all:
        print(f"Median duration (all): {statistics.median(durations_all):.0f} ms")
    if coverage_all:
        print(f"Median coverage (all): {statistics.median(coverage_all) * 100:.1f}%")

    print("Failure reasons:")
    for reason, count in reasons.most_common():
        if _is_pass(reason):
            continue
        print(f"  {reason}: {count}")

    print("By pointer type:")
    for pointer, stats in sorted(by_pointer.items()):
        rate = (stats["pass"] / stats["total"]) * 100 if stats["total"] else 0
        med = _median(stats["durations"])
        med_text = f"{med:.0f} ms" if med is not None else "n/a"
        print(f"  {pointer}: {stats['pass']}/{stats['total']} ({rate:.1f}%), median {med_text}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
