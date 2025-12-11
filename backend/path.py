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
