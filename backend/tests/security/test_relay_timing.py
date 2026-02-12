#!/usr/bin/env python3
"""
Security Test: CAPTCHA Farm Relay Timing Simulation

Generates challenges, simulates relay delays, submits correct clicks
after the delay, and measures at which point the TTL starts rejecting.

Usage:
    python -m backend.tests.security.test_relay_timing

No external dependencies required beyond the backend itself.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    from backend import config, db
    from backend.image_challenge import generate_challenge
    from backend.image_validator import validate_clicks

    db.init_db()

    ttl_s = config.IMAGE_CHALLENGE_TTL_MS / 1000.0
    print(f"Image CAPTCHA TTL: {config.IMAGE_CHALLENGE_TTL_MS}ms ({ttl_s}s)")
    print()

    # Test delays from 0s to TTL+5s in 2s increments
    delays = list(range(0, int(ttl_s) + 6, 2))

    results = []
    for delay_s in delays:
        challenge = generate_challenge()
        server_data = challenge["server_data"]
        intersections = server_data["intersections"]
        clicks = [{"x": ix[0], "y": ix[1]} for ix in intersections]

        # Simulate relay delay
        if delay_s > 0:
            print(f"  Simulating {delay_s}s relay delay...", end=" ", flush=True)
            time.sleep(delay_s)
        else:
            print(f"  Testing {delay_s}s delay (immediate)...", end=" ", flush=True)

        # The elapsed time is the relay delay
        elapsed_ms = delay_s * 1000.0

        result = validate_clicks(
            clicks=clicks,
            intersections=intersections,
            solve_time_ms=elapsed_ms,
        )

        # Also check if elapsed_ms > TTL (simulating what the route does)
        ttl_expired = elapsed_ms > config.IMAGE_CHALLENGE_TTL_MS

        status = "PASSED" if (result["passed"] and not ttl_expired) else "REJECTED"
        reason = "TTL expired" if ttl_expired else result["reason"]
        results.append({"delay_s": delay_s, "status": status, "reason": reason})
        print(f"{status} ({reason})")

    print(f"\n{'='*50}")
    print("Relay Timing Results:")
    print(f"{'Delay (s)':<12} {'Status':<12} {'Reason'}")
    print("-" * 50)
    for r in results:
        print(f"{r['delay_s']:<12} {r['status']:<12} {r['reason']}")

    # Find the boundary
    passed = [r for r in results if r["status"] == "PASSED"]
    rejected = [r for r in results if r["status"] == "REJECTED"]
    if passed and rejected:
        max_passed = max(r["delay_s"] for r in passed)
        min_rejected = min(r["delay_s"] for r in rejected)
        print(f"\nMax successful relay delay: {max_passed}s")
        print(f"Min rejected relay delay:  {min_rejected}s")
        print(f"TTL boundary:              {ttl_s}s")
        print(f"\nRelay window: ~{max_passed}s (human must solve + transfer within this)")
    elif not rejected:
        print(f"\nAll delays passed — TTL ({ttl_s}s) may be too generous")
    else:
        print(f"\nAll delays rejected — timing checks are strict")


if __name__ == "__main__":
    main()
