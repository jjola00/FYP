"""
Ephemeral Image CAPTCHA — Core Challenge Generator

Procedurally generates line intersection challenges where users click on
the points where lines cross. Every parameter is randomised per-call
following MTD (Moving Target Defense) movement strategy principles.

Architecture: docs/image-captcha-architecture.md
Research:     docs/image-captcha-research.md
"""

import random
from math import comb
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from . import config

# ─── Types ───────────────────────────────────────────────────────────────

Point = Tuple[float, float]

# ─── Colour palette — high-contrast, visually distinct ───────────────────

COLOUR_PALETTE = [
    "#E53935",  # Red
    "#1E88E5",  # Blue
    "#43A047",  # Green
    "#FB8C00",  # Orange
    "#8E24AA",  # Purple
    "#00ACC1",  # Cyan
    "#F4511E",  # Deep Orange
    "#3949AB",  # Indigo
]

# ─── Instruction templates ───────────────────────────────────────────────
# Count is intentionally NOT revealed to the user (security measure).

_INSTRUCTIONS = [
    "Click where the lines cross",
    "Tap each point where lines intersect",
    "Mark where lines meet",
    "Click the crossing points of the lines",
    "Select every point where lines cross",
    "Find and click where lines meet",
    "Identify where the coloured lines overlap",
    "Locate the spots where lines cross",
    "Tap where one line crosses another",
    "Click where the lines converge",
]

# ─── Background colour variants ─────────────────────────────────────────

_BACKGROUNDS = ["#FFFFFF", "#F5F5F5", "#FAFAFA", "#F0F0F0"]

# ─── Challenge parameters (flat constants, no difficulty tiers) ──────────

_NUM_LINES = (2, 3)
_TARGET_INTERSECTIONS = (1, 3)
_LINE_TYPES = ["straight", "quadratic"]


# ─── Bézier evaluation ──────────────────────────────────────────────────


def _evaluate_bezier(control_points: np.ndarray, t: np.ndarray) -> np.ndarray:
    """
    Evaluate a Bézier curve of arbitrary degree at parameter values *t*.

    Uses the explicit Bernstein polynomial basis for vectorised evaluation.

    Args:
        control_points: (n+1, 2) control points for a degree-n curve.
        t: (N,) parameter values in [0, 1].

    Returns:
        (N, 2) evaluated points on the curve.
    """
    n = len(control_points) - 1
    points = np.zeros((len(t), 2))
    for i, cp in enumerate(control_points):
        # Bernstein basis: C(n,i) * t^i * (1-t)^(n-i)
        basis = comb(n, i) * (t ** i) * ((1 - t) ** (n - i))
        points += np.outer(basis, cp)
    return points


# ─── Line generation ────────────────────────────────────────────────────


def _random_point(canvas_w: int, canvas_h: int, margin: int) -> List[float]:
    """Random point within the margin-inset canvas area."""
    return [
        float(random.randint(margin, canvas_w - margin)),
        float(random.randint(margin, canvas_h - margin)),
    ]


def _ensure_min_length(
    p1: List[float],
    p2: List[float],
    min_length: float,
    canvas_w: int,
    canvas_h: int,
    margin: int,
) -> List[float]:
    """Re-roll p2 until the segment p1→p2 meets *min_length*."""
    while np.hypot(p2[0] - p1[0], p2[1] - p1[1]) < min_length:
        p2 = _random_point(canvas_w, canvas_h, margin)
    return p2


def _generate_straight_line(
    canvas_w: int, canvas_h: int, margin: int
) -> Dict[str, Any]:
    """Straight line segment between two random points."""
    min_len = min(canvas_w, canvas_h) * 0.4
    p1 = _random_point(canvas_w, canvas_h, margin)
    p2 = _ensure_min_length(p1, _random_point(canvas_w, canvas_h, margin),
                            min_len, canvas_w, canvas_h, margin)
    return {"type": "straight", "points": [p1, p2]}


def _generate_quadratic_bezier(
    canvas_w: int, canvas_h: int, margin: int
) -> Dict[str, Any]:
    """Quadratic Bézier curve (degree 2) with 3 random control points."""
    min_len = min(canvas_w, canvas_h) * 0.3
    p0 = _random_point(canvas_w, canvas_h, margin)
    p2 = _ensure_min_length(p0, _random_point(canvas_w, canvas_h, margin),
                            min_len, canvas_w, canvas_h, margin)
    p1 = _random_point(canvas_w, canvas_h, margin)  # interior control point
    return {"type": "quadratic", "points": [p0, p1, p2]}


def _generate_cubic_bezier(
    canvas_w: int, canvas_h: int, margin: int
) -> Dict[str, Any]:
    """Cubic Bézier curve (degree 3) with 4 random control points."""
    min_len = min(canvas_w, canvas_h) * 0.3
    p0 = _random_point(canvas_w, canvas_h, margin)
    p3 = _ensure_min_length(p0, _random_point(canvas_w, canvas_h, margin),
                            min_len, canvas_w, canvas_h, margin)
    p1 = _random_point(canvas_w, canvas_h, margin)
    p2 = _random_point(canvas_w, canvas_h, margin)
    return {"type": "cubic", "points": [p0, p1, p2, p3]}


_LINE_GENERATORS = {
    "straight": _generate_straight_line,
    "quadratic": _generate_quadratic_bezier,
    "cubic": _generate_cubic_bezier,
}


# ─── Intersection finding (vectorised with numpy) ───────────────────────


def _sample_line(
    line_def: Dict[str, Any],
    num_samples: int = 500,
) -> np.ndarray:
    """
    Sample a line or curve at evenly spaced parameter values.

    Returns:
        (num_samples, 2) array of points along the curve.
    """
    cp = np.array(line_def["points"])
    t = np.linspace(0.0, 1.0, num_samples)

    if line_def["type"] == "straight":
        # Linear interpolation: P0 + t*(P1 - P0)
        return cp[0] + np.outer(t, cp[1] - cp[0])

    return _evaluate_bezier(cp, t)


def _find_polyline_intersections(
    points_a: np.ndarray,
    points_b: np.ndarray,
    cluster_radius: float,
) -> List[List[float]]:
    """
    Find all intersection points between two polylines using vectorised
    segment–segment intersection tests.

    Each polyline is a (N, 2) array of ordered sample points.  Consecutive
    pairs form segments.  For every (seg_a, seg_b) pair across the two
    polylines, the standard 2-D parametric intersection test is applied:

        A1 + t·(A2 − A1) = B1 + s·(B2 − B1)

    Solved via cross-products.  Valid when 0 ≤ t ≤ 1 and 0 ≤ s ≤ 1.

    Nearby raw intersections are clustered within *cluster_radius* so that
    the same geometric crossing is reported only once.
    """
    A1 = points_a[:-1]  # (N-1, 2)
    A2 = points_a[1:]
    B1 = points_b[:-1]  # (M-1, 2)
    B2 = points_b[1:]

    # Direction vectors, broadcast to (N-1, M-1, 2)
    dA = (A2 - A1)[:, np.newaxis, :]
    dB = (B2 - B1)[np.newaxis, :, :]
    diff = B1[np.newaxis, :, :] - A1[:, np.newaxis, :]

    # 2-D cross product: a×b = a_x·b_y − a_y·b_x
    denom = dA[..., 0] * dB[..., 1] - dA[..., 1] * dB[..., 0]

    with np.errstate(divide="ignore", invalid="ignore"):
        t = (diff[..., 0] * dB[..., 1] - diff[..., 1] * dB[..., 0]) / denom
        s = (diff[..., 0] * dA[..., 1] - diff[..., 1] * dA[..., 0]) / denom

    valid = (
        (np.abs(denom) > 1e-10)
        & (t >= 0) & (t <= 1)
        & (s >= 0) & (s <= 1)
    )

    idx = np.where(valid)
    if len(idx[0]) == 0:
        return []

    # Intersection coords: A1[i] + t[i,j] · dA_raw[i]
    dA_raw = A2 - A1  # (N-1, 2)
    raw = A1[idx[0]] + t[idx[0], idx[1], np.newaxis] * dA_raw[idx[0]]

    return _cluster_points(raw, cluster_radius)


def _cluster_points(
    points: np.ndarray,
    radius: float,
) -> List[List[float]]:
    """
    Greedy clustering: merge points within *radius* and return centroids.
    """
    if len(points) == 0:
        return []

    clusters: List[List[float]] = []
    used = np.zeros(len(points), dtype=bool)

    for i in range(len(points)):
        if used[i]:
            continue
        dists = np.linalg.norm(points[i:] - points[i], axis=1)
        nearby = np.where(dists < radius)[0] + i
        used[nearby] = True
        centroid = points[nearby].mean(axis=0)
        clusters.append([round(float(centroid[0]), 2),
                         round(float(centroid[1]), 2)])

    return clusters


def _find_all_intersections(
    lines: List[Dict[str, Any]],
    num_samples: int,
    cluster_radius: float,
    canvas_w: int,
    canvas_h: int,
    margin: int,
) -> List[List[float]]:
    """
    Compute all pairwise intersection points across a list of lines/curves.

    Points outside the visible canvas (minus *margin*) are discarded.
    """
    sampled = [_sample_line(l, num_samples) for l in lines]

    all_pts: List[List[float]] = []
    for i in range(len(sampled)):
        for j in range(i + 1, len(sampled)):
            all_pts.extend(
                _find_polyline_intersections(sampled[i], sampled[j], cluster_radius)
            )

    # Filter to canvas bounds
    filtered = [
        pt for pt in all_pts
        if margin <= pt[0] <= canvas_w - margin
        and margin <= pt[1] <= canvas_h - margin
    ]

    # Final cross-pair deduplication
    if len(filtered) > 1:
        arr = np.array(filtered)
        filtered = _cluster_points(arr, cluster_radius)
        filtered = [[round(p[0], 2), round(p[1], 2)] for p in filtered]

    return filtered


# ─── Guaranteed intersection fallback ────────────────────────────────────


def _force_intersecting_line(
    existing_line: Dict[str, Any],
    canvas_w: int,
    canvas_h: int,
    margin: int,
    num_samples: int,
) -> Dict[str, Any]:
    """
    Generate a straight line guaranteed to cross *existing_line*.

    Strategy: pick a point on the existing curve, then draw a line through
    it at a random angle.
    """
    samples = _sample_line(existing_line, num_samples)
    # Pick a point away from the endpoints
    idx = random.randint(num_samples // 5, num_samples * 4 // 5)
    cross_pt = samples[idx]

    angle = random.uniform(0, np.pi)
    half_len = random.uniform(100, 180)
    dx = half_len * np.cos(angle)
    dy = half_len * np.sin(angle)

    x1 = float(np.clip(cross_pt[0] - dx, margin, canvas_w - margin))
    y1 = float(np.clip(cross_pt[1] - dy, margin, canvas_h - margin))
    x2 = float(np.clip(cross_pt[0] + dx, margin, canvas_w - margin))
    y2 = float(np.clip(cross_pt[1] + dy, margin, canvas_h - margin))

    return {"type": "straight", "points": [[x1, y1], [x2, y2]]}


# ─── Main entry point ───────────────────────────────────────────────────


def generate_challenge(
    canvas_w: Optional[int] = None,
    canvas_h: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate a complete image CAPTCHA challenge.

    Returns a dict with two top-level keys:

    * ``client_data`` — safe to send to the browser (line definitions,
      colours, canvas config, instruction text).
    * ``server_data`` — **NEVER** sent to the client (intersection
      coordinates used for validation).

    Every visual parameter is randomised per-call (MTD movement strategy).
    """
    canvas_w = canvas_w or config.IMAGE_CANVAS_WIDTH_PX
    canvas_h = canvas_h or config.IMAGE_CANVAS_HEIGHT_PX
    margin = config.IMAGE_CANVAS_MARGIN_PX
    ix_margin = config.IMAGE_INTERSECTION_MARGIN_PX
    samples = config.IMAGE_BEZIER_SAMPLE_RESOLUTION
    cluster_r = config.IMAGE_INTERSECTION_CLUSTER_RADIUS_PX
    max_retries = config.IMAGE_MAX_GENERATION_RETRIES

    num_lines = random.randint(*_NUM_LINES)
    target_min, target_max = _TARGET_INTERSECTIONS
    available_types: List[str] = _LINE_TYPES

    lines: List[Dict[str, Any]] = []
    intersections: List[List[float]] = []

    # ── Try random generation until intersection count is in range ──
    for _attempt in range(max_retries):
        colours = random.sample(
            COLOUR_PALETTE, min(num_lines, len(COLOUR_PALETTE))
        )
        lines = []
        for i in range(num_lines):
            lt = random.choice(available_types)
            line = _LINE_GENERATORS[lt](canvas_w, canvas_h, margin)
            line["colour"] = colours[i]
            line["thickness"] = round(
                random.uniform(
                    config.IMAGE_LINE_THICKNESS_MIN,
                    config.IMAGE_LINE_THICKNESS_MAX,
                ),
                1,
            )
            lines.append(line)

        intersections = _find_all_intersections(
            lines, samples, cluster_r, canvas_w, canvas_h, ix_margin,
        )

        if target_min <= len(intersections) <= target_max:
            break
    else:
        # ── Guarantee fallback: force intersections ──────────────
        colours = random.sample(
            COLOUR_PALETTE, min(num_lines, len(COLOUR_PALETTE))
        )
        lines = []
        first = _LINE_GENERATORS[random.choice(available_types)](
            canvas_w, canvas_h, margin,
        )
        first["colour"] = colours[0]
        first["thickness"] = round(
            random.uniform(
                config.IMAGE_LINE_THICKNESS_MIN,
                config.IMAGE_LINE_THICKNESS_MAX,
            ),
            1,
        )
        lines.append(first)

        for i in range(1, num_lines):
            # Force each new line through a point on a previous line
            target_line = lines[random.randint(0, len(lines) - 1)]
            forced = _force_intersecting_line(
                target_line, canvas_w, canvas_h, margin, samples,
            )
            forced["colour"] = colours[i]
            forced["thickness"] = round(
                random.uniform(
                    config.IMAGE_LINE_THICKNESS_MIN,
                    config.IMAGE_LINE_THICKNESS_MAX,
                ),
                1,
            )
            lines.append(forced)

        intersections = _find_all_intersections(
            lines, samples, cluster_r, canvas_w, canvas_h, ix_margin,
        )

    # ── Build instruction text ───────────────────────────────────
    instruction = random.choice(_INSTRUCTIONS)

    # ── Assemble client-safe line data ───────────────────────────
    client_lines = [
        {
            "type": l["type"],
            "points": l["points"],
            "colour": l["colour"],
            "thickness": l["thickness"],
        }
        for l in lines
    ]

    return {
        "client_data": {
            "lines": client_lines,
            "canvas": {
                "width": canvas_w,
                "height": canvas_h,
                "background": random.choice(_BACKGROUNDS),
            },
            "instruction": instruction,
            "numIntersections": len(intersections),
        },
        "server_data": {
            "intersections": intersections,
            "numIntersections": len(intersections),
        },
    }
