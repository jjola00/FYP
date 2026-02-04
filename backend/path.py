import math
import random
from typing import List, Tuple

import config

Point = Tuple[float, float]


def _bezier_point(t: float, p0: Point, p1: Point, p2: Point, p3: Point) -> Point:
    u = 1 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t
    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return (x, y)


def _approx_length(points: List[Point]) -> float:
    length = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        length += math.hypot(dx, dy)
    return length


def _cumulative_lengths(points: List[Point]) -> List[float]:
    cums = [0.0]
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        cums.append(cums[-1] + math.hypot(dx, dy))
    return cums


def _nearest_position(points: List[Point], cums: List[float], cursor: Point) -> Tuple[float, Point]:
    best_dist = float("inf")
    best_pos = 0.0
    best_point = points[0]
    for i in range(1, len(points)):
        x1, y1 = points[i - 1]
        x2, y2 = points[i]
        dx = x2 - x1
        dy = y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq == 0:
            proj = 0.0
        else:
            proj = ((cursor[0] - x1) * dx + (cursor[1] - y1) * dy) / seg_len_sq
        proj = max(0.0, min(1.0, proj))
        proj_x = x1 + proj * dx
        proj_y = y1 + proj * dy
        dist = math.hypot(cursor[0] - proj_x, cursor[1] - proj_y)
        if dist < best_dist:
            best_dist = dist
            best_point = (proj_x, proj_y)
            best_pos = cums[i - 1] + proj * math.hypot(dx, dy)
    return best_pos, best_point


def _interp(p1: Point, p2: Point, alpha: float) -> Point:
    return (p1[0] + (p2[0] - p1[0]) * alpha, p1[1] + (p2[1] - p1[1]) * alpha)


def _sample_between(points: List[Point], cums: List[float], start: float, end: float) -> List[Point]:
    if end <= 0:
        return [points[0]]
    total = cums[-1]
    start = max(0.0, min(start, total))
    end = max(start, min(end, total))
    result: List[Point] = []
    for i in range(1, len(points)):
        seg_start = cums[i - 1]
        seg_end = cums[i]
        seg_len = seg_end - seg_start
        if seg_end < start or seg_start > end or seg_len == 0:
            continue
        s = max(start, seg_start)
        e = min(end, seg_end)
        alpha_s = (s - seg_start) / seg_len
        alpha_e = (e - seg_start) / seg_len
        p_s = _interp(points[i - 1], points[i], alpha_s)
        p_e = _interp(points[i - 1], points[i], alpha_e)
        if not result:
            result.append(p_s)
        elif result[-1] != p_s:
            result.append(p_s)
        result.append(p_e)
    if not result:
        result = [points[0]]
    return result


def lookahead(points: List[Point], cursor: Point, ahead: float = 60.0, behind: float = 20.0) -> List[Point]:
    """
    Return a short polyline around the cursor position along the path:
    - cursor projected to nearest point along the path
    - include up to `ahead` distance ahead and `behind` distance behind
    """
    cums = _cumulative_lengths(points)
    pos, _ = _nearest_position(points, cums, cursor)
    start = pos - behind
    end = pos + ahead
    return _sample_between(points, cums, start, end)


def position_and_distance(points: List[Point], cursor: Point) -> Tuple[float, float]:
    """
    Return the cursor's projection position along the path and its distance to the path.
    """
    cums = _cumulative_lengths(points)
    pos, proj = _nearest_position(points, cums, cursor)
    dist = math.hypot(cursor[0] - proj[0], cursor[1] - proj[1])
    return pos, dist


def position_along_path(points: List[Point], cursor: Point) -> float:
    """
    Return the cursor's projection position along the path.
    """
    pos, _ = position_and_distance(points, cursor)
    return pos


def _generate_horizontal_path(rnd: random.Random, left_to_right: bool = True) -> List[Point]:
    """Generate a horizontal-dominant path (left-to-right or right-to-left)."""
    margin = 60
    w, h = config.CANVAS_WIDTH_PX, config.CANVAS_HEIGHT_PX

    if left_to_right:
        p0 = (rnd.uniform(margin, w * 0.3), rnd.uniform(margin, h - margin))
        p3 = (rnd.uniform(w * 0.7, w - margin), rnd.uniform(margin, h - margin))
    else:
        p0 = (rnd.uniform(w * 0.7, w - margin), rnd.uniform(margin, h - margin))
        p3 = (rnd.uniform(margin, w * 0.3), rnd.uniform(margin, h - margin))

    bend_strength = rnd.uniform(-80, 80)
    dx = p3[0] - p0[0]
    p1 = (p0[0] + dx * 0.33, p0[1] + bend_strength)
    p2 = (p0[0] + dx * 0.66, p3[1] - bend_strength / 2)

    samples = 80
    return [_bezier_point(i / (samples - 1), p0, p1, p2, p3) for i in range(samples)]


def _generate_vertical_path(rnd: random.Random, top_to_bottom: bool = True) -> List[Point]:
    """Generate a vertical-dominant path (top-to-bottom or bottom-to-top)."""
    margin = 60
    w, h = config.CANVAS_WIDTH_PX, config.CANVAS_HEIGHT_PX

    if top_to_bottom:
        p0 = (rnd.uniform(margin, w - margin), rnd.uniform(margin, h * 0.3))
        p3 = (rnd.uniform(margin, w - margin), rnd.uniform(h * 0.7, h - margin))
    else:
        p0 = (rnd.uniform(margin, w - margin), rnd.uniform(h * 0.7, h - margin))
        p3 = (rnd.uniform(margin, w - margin), rnd.uniform(margin, h * 0.3))

    bend_strength = rnd.uniform(-80, 80)
    dy = p3[1] - p0[1]
    p1 = (p0[0] + bend_strength, p0[1] + dy * 0.33)
    p2 = (p3[0] - bend_strength / 2, p0[1] + dy * 0.66)

    samples = 80
    return [_bezier_point(i / (samples - 1), p0, p1, p2, p3) for i in range(samples)]


def _generate_diagonal_path(rnd: random.Random) -> List[Point]:
    """Generate a diagonal path (corner to corner variations)."""
    margin = 60
    w, h = config.CANVAS_WIDTH_PX, config.CANVAS_HEIGHT_PX

    # Pick two opposite-ish corners
    corners = [
        ((margin, margin), (w - margin, h - margin)),           # top-left to bottom-right
        ((w - margin, margin), (margin, h - margin)),           # top-right to bottom-left
        ((margin, h - margin), (w - margin, margin)),           # bottom-left to top-right
        ((w - margin, h - margin), (margin, margin)),           # bottom-right to top-left
    ]
    start_corner, end_corner = rnd.choice(corners)

    # Add some randomness to the corners
    p0 = (start_corner[0] + rnd.uniform(-20, 20), start_corner[1] + rnd.uniform(-20, 20))
    p3 = (end_corner[0] + rnd.uniform(-20, 20), end_corner[1] + rnd.uniform(-20, 20))

    # Control points create a gentle curve
    bend_strength = rnd.uniform(-60, 60)
    mid_x = (p0[0] + p3[0]) / 2
    mid_y = (p0[1] + p3[1]) / 2
    p1 = (mid_x + bend_strength, p0[1] + (p3[1] - p0[1]) * 0.25)
    p2 = (mid_x - bend_strength, p0[1] + (p3[1] - p0[1]) * 0.75)

    samples = 80
    return [_bezier_point(i / (samples - 1), p0, p1, p2, p3) for i in range(samples)]


def _generate_s_curve_path(rnd: random.Random) -> List[Point]:
    """Generate an S-curve with two opposing bends (tests curvature adaptation)."""
    margin = 60
    w, h = config.CANVAS_WIDTH_PX, config.CANVAS_HEIGHT_PX

    # Horizontal S-curve (left to right with up-down-up or down-up-down pattern)
    p0 = (rnd.uniform(margin, w * 0.25), rnd.uniform(h * 0.3, h * 0.7))
    p3 = (rnd.uniform(w * 0.75, w - margin), rnd.uniform(h * 0.3, h * 0.7))

    # Mid point
    mid_x = (p0[0] + p3[0]) / 2
    mid_y = (p0[1] + p3[1]) / 2

    # First bend direction (up or down)
    bend_dir = rnd.choice([-1, 1])
    bend_amount = rnd.uniform(50, 90)

    # First curve: start to middle
    p1_a = (p0[0] + (mid_x - p0[0]) * 0.5, p0[1] + bend_dir * bend_amount)
    p2_a = (mid_x - 20, mid_y + bend_dir * bend_amount * 0.3)

    # Second curve: middle to end (opposite bend)
    p1_b = (mid_x + 20, mid_y - bend_dir * bend_amount * 0.3)
    p2_b = (p3[0] - (p3[0] - mid_x) * 0.5, p3[1] - bend_dir * bend_amount)

    # Sample both curves
    samples_per_curve = 40
    pts = []
    for i in range(samples_per_curve):
        t = i / (samples_per_curve - 1)
        pts.append(_bezier_point(t, p0, p1_a, p2_a, (mid_x, mid_y)))
    for i in range(1, samples_per_curve):  # skip first to avoid duplicate
        t = i / (samples_per_curve - 1)
        pts.append(_bezier_point(t, (mid_x, mid_y), p1_b, p2_b, p3))

    return pts


# Path family weights (can be tuned)
PATH_FAMILIES = [
    ("horizontal_lr", _generate_horizontal_path, {"left_to_right": True}, 3),
    ("horizontal_rl", _generate_horizontal_path, {"left_to_right": False}, 2),
    ("vertical_tb", _generate_vertical_path, {"top_to_bottom": True}, 2),
    ("vertical_bt", _generate_vertical_path, {"top_to_bottom": False}, 1),
    ("diagonal", _generate_diagonal_path, {}, 2),
    ("s_curve", _generate_s_curve_path, {}, 3),
]


def generate_path(seed: str) -> Tuple[List[Point], float]:
    """
    Generate a smooth path from one of several families.
    Returns the sampled points and approximate length.

    Path families:
    - horizontal_lr: left to right (classic)
    - horizontal_rl: right to left
    - vertical_tb: top to bottom
    - vertical_bt: bottom to top
    - diagonal: corner to corner
    - s_curve: S-shaped with two bends (better curvature testing)
    """
    rnd = random.Random(seed)

    # Weighted random selection of path family
    total_weight = sum(f[3] for f in PATH_FAMILIES)
    choice = rnd.uniform(0, total_weight)
    cumulative = 0
    selected_family = PATH_FAMILIES[0]
    for family in PATH_FAMILIES:
        cumulative += family[3]
        if choice <= cumulative:
            selected_family = family
            break

    family_name, generator, kwargs, _ = selected_family

    attempts = 0
    while True:
        attempts += 1
        pts = generator(rnd, **kwargs)
        length = _approx_length(pts)

        if config.PATH_TRAVEL_PX_MIN <= length <= config.PATH_TRAVEL_PX_MAX:
            return pts, length
        if attempts >= 10:
            # Accept closest we found after several tries to avoid dead loops.
            return pts, length


def min_distance_to_polyline(point: Point, polyline: List[Point]) -> float:
    """
    Compute the minimum distance from a point to a polyline.
    """
    px, py = point
    best = float("inf")
    for i in range(1, len(polyline)):
        x1, y1 = polyline[i - 1]
        x2, y2 = polyline[i]
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            dist = math.hypot(px - x1, py - y1)
        else:
            t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
            t = max(0.0, min(1.0, t))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist = math.hypot(px - proj_x, py - proj_y)
        if dist < best:
            best = dist
    return best


def distance_to_end(points: List[Point], cursor: Point) -> float:
    """
    Compute the distance (in px) from the cursor's nearest projection on the path to the end of the path.
    """
    cums = _cumulative_lengths(points)
    pos, _ = _nearest_position(points, cums, cursor)
    return max(0.0, cums[-1] - pos)


def cumulative_lengths(points: List[Point]) -> List[float]:
    return _cumulative_lengths(points)


def index_at_position(cums: List[float], pos: float) -> int:
    for i, value in enumerate(cums):
        if value >= pos:
            return max(0, i)
    return max(0, len(cums) - 1)


def curvature_profile(points: List[Point]) -> List[float]:
    if len(points) < 3:
        return [0.0 for _ in points]
    curvatures = [0.0 for _ in points]
    for i in range(1, len(points) - 1):
        x1, y1 = points[i - 1]
        x2, y2 = points[i]
        x3, y3 = points[i + 1]
        ax, ay = x2 - x1, y2 - y1
        bx, by = x3 - x2, y3 - y2
        len_a = math.hypot(ax, ay)
        len_b = math.hypot(bx, by)
        if len_a == 0 or len_b == 0:
            curvatures[i] = 0.0
            continue
        dot = ax * bx + ay * by
        cos_theta = max(-1.0, min(1.0, dot / (len_a * len_b)))
        curvatures[i] = math.acos(cos_theta)
    return curvatures
