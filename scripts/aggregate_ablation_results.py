#!/usr/bin/env python3
import argparse
import csv
import math
import re
import sys
from pathlib import Path


ATTEMPT_RE = re.compile(r"attempts=(\d+)\s+passed=(\d+)")
VARIANT_RE = re.compile(r"^##\s+(.+)$")
RUN_RE = re.compile(r"^\d{8}_\d{6}$")


def _wilson_ci(k, n, z=1.96):
    if n <= 0:
        return 0.0, 0.0
    phat = k / n
    denom = 1 + (z * z) / n
    center = (phat + (z * z) / (2 * n)) / denom
    margin = (z * math.sqrt((phat * (1 - phat) + (z * z) / (4 * n)) / n)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def _latest_run_dir(root: Path) -> Path:
    if not root.exists():
        raise FileNotFoundError(f"Run root not found: {root}")
    dirs = [p for p in root.iterdir() if p.is_dir()]
    if not dirs:
        raise FileNotFoundError(f"No runs found under {root}")
    timestamp_dirs = [p for p in dirs if RUN_RE.match(p.name)]
    if timestamp_dirs:
        return max(timestamp_dirs, key=lambda p: p.name)
    return max(dirs, key=lambda p: p.stat().st_mtime)


def _parse_results(results_path: Path):
    records = []
    current_variant = None
    for line in results_path.read_text().splitlines():
        match = VARIANT_RE.match(line.strip())
        if match:
            current_variant = match.group(1).strip()
            continue
        match = ATTEMPT_RE.search(line)
        if match and current_variant:
            attempts = int(match.group(1))
            passed = int(match.group(2))
            records.append((current_variant, attempts, passed))
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate ablation run results into CSV with 95% Wilson CIs."
    )
    parser.add_argument(
        "--root",
        default="logs/ablations",
        help="Root directory for ablation runs (default: logs/ablations).",
    )
    parser.add_argument(
        "--run",
        default=None,
        help="Specific run directory (name or path). Defaults to latest.",
    )
    parser.add_argument("--output", default=None, help="Write CSV to file (default: stdout).")
    args = parser.parse_args()

    root = Path(args.root)
    if args.run:
        run_dir = Path(args.run)
        if not run_dir.is_dir():
            run_dir = root / args.run
    else:
        run_dir = _latest_run_dir(root)

    if not run_dir.is_dir():
        print(f"Run directory not found: {run_dir}", file=sys.stderr)
        return 1

    rows = []
    for variant_dir in sorted([p for p in run_dir.iterdir() if p.is_dir()]):
        results_path = variant_dir / "results.txt"
        if not results_path.exists():
            continue
        for bot_variant, attempts, passed in _parse_results(results_path):
            ci_low, ci_high = _wilson_ci(passed, attempts)
            rows.append(
                {
                    "run": run_dir.name,
                    "ablation_variant": variant_dir.name,
                    "bot_variant": bot_variant,
                    "attempts": attempts,
                    "passed": passed,
                    "pass_rate": round((passed / attempts) * 100, 2) if attempts else 0.0,
                    "ci_low": round(ci_low * 100, 2),
                    "ci_high": round(ci_high * 100, 2),
                }
            )

    if not rows:
        print(f"No results found under {run_dir}", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else None
    out_fh = output.open("w", newline="") if output else sys.stdout
    writer = csv.DictWriter(
        out_fh,
        fieldnames=[
            "run",
            "ablation_variant",
            "bot_variant",
            "attempts",
            "passed",
            "pass_rate",
            "ci_low",
            "ci_high",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
    if output:
        out_fh.close()
        print(f"Wrote {len(rows)} rows to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
