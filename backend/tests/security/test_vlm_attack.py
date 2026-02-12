#!/usr/bin/env python3
"""
Security Test: VLM Screenshot Attack

Generates CAPTCHA challenges, renders them to PNG, feeds to a VLM API,
and records the solve rate.

Usage:
    python -m backend.tests.security.test_vlm_attack --n 50 --api openai

Requires:
    - OPENAI_API_KEY or GOOGLE_API_KEY environment variable
    - pip install matplotlib Pillow requests
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def render_challenge_to_png(client_data: dict, output_path: str) -> None:
    """Render a challenge's client_data line definitions to a PNG file."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        from matplotlib.path import Path as MplPath
        import matplotlib.patches as mpatches
    except ImportError:
        print("ERROR: matplotlib is required. Install with: pip install matplotlib")
        sys.exit(1)

    canvas = client_data["canvas"]
    w, h = canvas["width"], canvas["height"]

    fig, ax = plt.subplots(1, 1, figsize=(w / 100, h / 100), dpi=100)
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)  # Flip Y axis to match canvas coordinates
    ax.set_facecolor("#0a0f1d")
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("#0a0f1d")

    # Draw challenge lines
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
            # For curves, sample points
            import numpy as np

            t = np.linspace(0, 1, 200)
            cp = np.array(pts)
            if line["type"] == "quadratic":
                points = (
                    np.outer((1 - t) ** 2, cp[0])
                    + np.outer(2 * (1 - t) * t, cp[1])
                    + np.outer(t**2, cp[2])
                )
            else:  # cubic
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

    plt.savefig(output_path, bbox_inches="tight", pad_inches=0, dpi=100)
    plt.close()


def query_openai_vlm(image_path: str) -> str:
    """Send image to OpenAI GPT-4o and ask for intersection coordinates."""
    import base64
    import requests

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY environment variable")

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "This image shows colored lines on a dark background. "
                                "How many intersection points are there and where are they? "
                                "Return coordinates as a JSON array of [x, y] pairs. "
                                "The image is 400x400 pixels. Only return the JSON array, nothing else."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 300,
        },
    )
    return resp.json()["choices"][0]["message"]["content"]


def parse_vlm_response(response_text: str) -> list:
    """Extract coordinate pairs from VLM response text."""
    # Try to find JSON array in the response
    match = re.search(r"\[[\s\S]*\]", response_text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return []


def main():
    parser = argparse.ArgumentParser(description="VLM Attack Test")
    parser.add_argument("--n", type=int, default=10, help="Number of challenges")
    parser.add_argument("--api", choices=["openai"], default="openai")
    args = parser.parse_args()

    from backend.image_challenge import generate_challenge
    from backend.image_validator import validate_clicks

    results = {"total": args.n, "solved": 0, "failed": 0, "errors": 0}
    tmp_dir = Path("/tmp/vlm_attack_test")
    tmp_dir.mkdir(exist_ok=True)

    for i in range(args.n):
        print(f"\n--- Challenge {i + 1}/{args.n} ---")
        challenge = generate_challenge()
        client_data = challenge["client_data"]
        server_data = challenge["server_data"]

        png_path = str(tmp_dir / f"challenge_{i}.png")
        render_challenge_to_png(client_data, png_path)

        try:
            t0 = time.time()
            response = query_openai_vlm(png_path)
            elapsed = time.time() - t0
            print(f"  VLM response ({elapsed:.1f}s): {response[:200]}")

            coords = parse_vlm_response(response)
            clicks = [{"x": c[0], "y": c[1]} for c in coords if len(c) >= 2]
            print(f"  Parsed {len(clicks)} clicks, expected {server_data['numIntersections']}")

            result = validate_clicks(
                clicks=clicks,
                intersections=server_data["intersections"],
                solve_time_ms=5000,  # Ignore timing for VLM test
            )

            if result["passed"]:
                results["solved"] += 1
                print(f"  SOLVED")
            else:
                results["failed"] += 1
                print(f"  FAILED: {result['reason']}")
        except Exception as e:
            results["errors"] += 1
            print(f"  ERROR: {e}")

    print(f"\n{'='*50}")
    print(f"VLM Attack Results ({args.api}):")
    print(f"  Total:   {results['total']}")
    print(f"  Solved:  {results['solved']} ({results['solved']/max(1,results['total'])*100:.1f}%)")
    print(f"  Failed:  {results['failed']}")
    print(f"  Errors:  {results['errors']}")


if __name__ == "__main__":
    main()
