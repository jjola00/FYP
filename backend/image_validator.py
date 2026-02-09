"""
Ephemeral Image CAPTCHA — Click Validator

Validates user clicks against stored intersection coordinates.
Tolerance-radius matching with configurable grace clicks and timing checks.
"""

from typing import Any, Dict, List

import numpy as np

from . import config


def validate_clicks(
    clicks: List[Dict[str, float]],
    intersections: List[List[float]],
    solve_time_ms: float,
) -> Dict[str, Any]:
    """
    Validate a set of user clicks against the known intersection points.

    Args:
        clicks: List of {"x": float, "y": float} click coordinates.
        intersections: List of [x, y] ground-truth intersection coordinates
                       (from server_data, never exposed to client).
        solve_time_ms: Time in milliseconds from challenge issue to submission.

    Returns:
        Dict with keys:
            passed (bool): Whether the challenge was solved correctly.
            reason (str): Human-readable explanation.
            matched (int): How many intersections were matched.
            expected (int): Total intersection count.
            excess (int): Clicks that didn't match any intersection.
            too_fast (bool): Whether solve time was suspiciously fast.
    """
    tolerance = config.IMAGE_CLICK_TOLERANCE_PX
    max_extra = config.IMAGE_MAX_EXTRA_CLICKS
    min_time = config.IMAGE_MIN_SOLVE_TIME_MS

    expected = len(intersections)

    # ── Timing check ─────────────────────────────────────────────
    too_fast = solve_time_ms < min_time
    if too_fast and config.ENFORCE_IMAGE_MIN_SOLVE:
        return {
            "passed": False,
            "reason": "solved too fast",
            "matched": 0,
            "expected": expected,
            "excess": len(clicks),
            "too_fast": True,
        }

    if expected == 0:
        # Edge case: no intersections (shouldn't happen with good generation)
        return {
            "passed": len(clicks) == 0,
            "reason": "no intersections expected" if len(clicks) == 0 else "unexpected clicks",
            "matched": 0,
            "expected": 0,
            "excess": len(clicks),
            "too_fast": False,
        }

    # ── Convert to numpy arrays ──────────────────────────────────
    if len(clicks) == 0:
        return {
            "passed": False,
            "reason": "no clicks submitted",
            "matched": 0,
            "expected": expected,
            "excess": 0,
            "too_fast": False,
        }

    click_arr = np.array([[c["x"], c["y"]] for c in clicks])  # (C, 2)
    ix_arr = np.array(intersections)  # (I, 2)

    # ── Match each intersection to the nearest click ─────────────
    # Distance matrix: (I, C)
    dists = np.linalg.norm(
        ix_arr[:, np.newaxis, :] - click_arr[np.newaxis, :, :],
        axis=2,
    )

    matched_intersections = 0
    used_clicks = set()

    # Greedy matching: for each intersection, find the closest unused click
    for i in range(len(ix_arr)):
        row = dists[i]
        # Sort click indices by distance to this intersection
        order = np.argsort(row)
        for j in order:
            if j not in used_clicks and row[j] <= tolerance:
                used_clicks.add(j)
                matched_intersections += 1
                break

    excess = len(clicks) - len(used_clicks)

    # ── Determine pass/fail ──────────────────────────────────────
    all_matched = matched_intersections == expected
    within_grace = excess <= max_extra

    if all_matched and within_grace:
        passed = True
        reason = "all intersections clicked"
    elif not all_matched:
        missing = expected - matched_intersections
        passed = False
        reason = f"missed {missing} intersection{'s' if missing != 1 else ''}"
    else:
        passed = False
        reason = f"too many extra clicks ({excess})"

    return {
        "passed": passed,
        "reason": reason,
        "matched": matched_intersections,
        "expected": expected,
        "excess": excess,
        "too_fast": False,
    }
