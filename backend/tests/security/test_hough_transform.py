#!/usr/bin/env python3
"""
Security Test: Classical CV Attack (Hough Transform)

Generates CAPTCHA challenges, renders to PNG, runs OpenCV Hough Transform
pipeline, and records the solve rate.

Usage:
    python -m backend.tests.security.test_hough_transform --n 50

Requires:
    pip install opencv-python matplotlib numpy
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def render_challenge_to_image(client_data: dict) -> np.ndarray:
    """Render a challenge to a numpy array (H, W, 3) BGR image."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("ERROR: matplotlib is required. Install with: pip install matplotlib")
        sys.exit(1)

    canvas = client_data["canvas"]
    w, h = canvas["width"], canvas["height"]

    fig, ax = plt.subplots(1, 1, figsize=(w / 100, h / 100), dpi=100)
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    ax.set_facecolor("#0a0f1d")
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("#0a0f1d")

    for line in client_data["lines"]:
        pts = line["points"]
        if line["type"] == "straight":
            ax.plot(
                [pts[0][0], pts[1][0]],
                [pts[0][1], pts[1][1]],
                color=line["colour"],
                linewidth=line["thickness"],
            )
        else:
            t = np.linspace(0, 1, 200)
            cp = np.array(pts)
            if line["type"] == "quadratic":
                points = (
                    np.outer((1 - t) ** 2, cp[0])
                    + np.outer(2 * (1 - t) * t, cp[1])
                    + np.outer(t**2, cp[2])
                )
            else:
                points = (
                    np.outer((1 - t) ** 3, cp[0])
                    + np.outer(3 * (1 - t) ** 2 * t, cp[1])
                    + np.outer(3 * (1 - t) * t**2, cp[2])
                    + np.outer(t**3, cp[3])
                )
            ax.plot(
                points[:, 0],
                points[:, 1],
                color=line["colour"],
                linewidth=line["thickness"],
            )

    fig.canvas.draw()
    data = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    data = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    plt.close()

    return data[:, :, ::-1]  # RGB → BGR for OpenCV


def find_hough_intersections(img: np.ndarray, canvas_w: int, canvas_h: int) -> list:
    """Run Hough Transform pipeline and find intersections of detected lines."""
    try:
        import cv2
    except ImportError:
        print("ERROR: opencv-python is required. Install with: pip install opencv-python")
        sys.exit(1)

    # Resize to match canvas dimensions
    img = cv2.resize(img, (canvas_w, canvas_h))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Probabilistic Hough Transform
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=50, maxLineGap=10)

    if lines is None:
        return []

    # Find intersections of all detected line pairs
    intersections = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            x1, y1, x2, y2 = lines[i][0]
            x3, y3, x4, y4 = lines[j][0]

            denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(denom) < 1e-10:
                continue

            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
            ix = x1 + t * (x2 - x1)
            iy = y1 + t * (y2 - y1)

            # Only keep points within canvas
            if 10 <= ix <= canvas_w - 10 and 10 <= iy <= canvas_h - 10:
                intersections.append([ix, iy])

    # Cluster nearby intersections
    if not intersections:
        return []

    from backend.image_challenge import _cluster_points

    return _cluster_points(np.array(intersections), radius=15.0)


def main():
    parser = argparse.ArgumentParser(description="Hough Transform Attack Test")
    parser.add_argument("--n", type=int, default=50, help="Number of challenges")
    args = parser.parse_args()

    from backend.image_challenge import generate_challenge
    from backend.image_validator import validate_clicks

    results = {"total": args.n, "solved": 0, "failed": 0}
    line_type_results = {"straight_only": {"total": 0, "solved": 0}, "has_curves": {"total": 0, "solved": 0}}

    for i in range(args.n):
        challenge = generate_challenge()
        client_data = challenge["client_data"]
        server_data = challenge["server_data"]

        has_curves = any(l["type"] != "straight" for l in client_data["lines"])
        category = "has_curves" if has_curves else "straight_only"
        line_type_results[category]["total"] += 1

        img = render_challenge_to_image(client_data)
        canvas_w = client_data["canvas"]["width"]
        canvas_h = client_data["canvas"]["height"]

        detected = find_hough_intersections(img, canvas_w, canvas_h)
        clicks = [{"x": p[0], "y": p[1]} for p in detected[: server_data["numIntersections"] + 1]]

        result = validate_clicks(
            clicks=clicks,
            intersections=server_data["intersections"],
            solve_time_ms=5000,
        )

        if result["passed"]:
            results["solved"] += 1
            line_type_results[category]["solved"] += 1
        else:
            results["failed"] += 1

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{args.n}")

    print(f"\n{'='*50}")
    print(f"Hough Transform Attack Results:")
    print(f"  Total:   {results['total']}")
    print(f"  Solved:  {results['solved']} ({results['solved']/max(1,results['total'])*100:.1f}%)")
    print(f"  Failed:  {results['failed']}")
    print()
    for cat, data in line_type_results.items():
        if data["total"] > 0:
            rate = data["solved"] / data["total"] * 100
            print(f"  {cat}: {data['solved']}/{data['total']} ({rate:.1f}%)")


if __name__ == "__main__":
    main()
