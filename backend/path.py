import math
import random
from typing import List, Tuple

from . import config

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


def generate_path(seed: str) -> Tuple[List[Point], float]:
    """
    Generate a smooth cubic path with 1–2 gentle bends and target length 200–300 px.
    Returns the sampled points and approximate length.
    """
    rnd = random.Random(seed)
    attempts = 0
    while True:
        attempts += 1
        margin = 60
        p0 = (
            rnd.uniform(margin, config.CANVAS_WIDTH_PX * 0.3),
            rnd.uniform(margin, config.CANVAS_HEIGHT_PX * 0.7),
        )
        p3 = (
            rnd.uniform(config.CANVAS_WIDTH_PX * 0.7, config.CANVAS_WIDTH_PX - margin),
            rnd.uniform(margin, config.CANVAS_HEIGHT_PX * 0.7),
        )

        bend_strength = rnd.uniform(-80, 80)
        p1 = (
            p0[0] + rnd.uniform(60, 120),
            p0[1] + bend_strength,
        )
        p2 = (
            p3[0] - rnd.uniform(60, 120),
            p3[1] - bend_strength / 2,
        )

        samples = 80
        pts = [_bezier_point(i / (samples - 1), p0, p1, p2, p3) for i in range(samples)]
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
