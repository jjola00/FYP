"""
Playwright Browser-Automation Bot — Line Tracing CAPTCHA
=========================================================
Tests whether behavioral detection holds when a bot operates through
the real browser DOM → Canvas → JS event handlers → API pipeline,
rather than hitting the API directly (as bot_sim.py does).

Strategies:
  1. constant    — uniform speed, no jitter (most detectable)
  2. jittered    — adds spatial noise to each step
  3. curvature   — slows on curves, adds jitter + timing variance
  4. humanlike   — ballistic profile (accel/decel), hesitation, jitter

Usage:
  pip install playwright numpy requests
  playwright install chromium
  python playwright_line_bot.py --strategy constant --attempts 1 --headed
  python playwright_line_bot.py --strategy all --attempts 20
"""

import argparse
import asyncio
import json
import math
import random
import time
from dataclasses import dataclass, field

import numpy as np
import requests

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Install playwright: pip install playwright && playwright install chromium")
    exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
FRONTEND_URL = "http://localhost:9002"
BACKEND_URL = "http://localhost:8000"
CANVAS_SELECTOR = "canvas"
CANVAS_WAIT_MS = 8000


@dataclass
class BotResult:
    strategy: str
    attempt: int
    passed: bool
    failure_reason: str = ""
    solve_time_ms: float = 0
    points_generated: int = 0


@dataclass
class RunSummary:
    strategy: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: list = field(default_factory=list)

    @property
    def pass_rate(self):
        return (self.passed / self.total * 100) if self.total else 0


# ---------------------------------------------------------------------------
# Path fetching — uses the real API with correct field names
# ---------------------------------------------------------------------------
def fetch_challenge():
    """Create a new line challenge and return challenge data."""
    resp = requests.post(f"{BACKEND_URL}/captcha/line/new", timeout=10)
    resp.raise_for_status()
    return resp.json()


def peek_path(challenge_id: str, nonce: str, token: str,
              x: float, y: float, pointer_type: str = "mouse"):
    """Peek to reveal path segments ahead of current position."""
    resp = requests.post(
        f"{BACKEND_URL}/captcha/line/peek",
        json={
            "challengeId": challenge_id,
            "nonce": nonce,
            "token": token,
            "cursor": [x, y],
            "pointerType": pointer_type,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def collect_full_path(challenge_id: str, nonce: str, token: str,
                      start_x: float, start_y: float):
    """Iteratively peek to collect the full path polyline."""
    all_points = [(start_x, start_y)]
    cx, cy = start_x, start_y

    for _ in range(80):  # safety limit
        try:
            data = peek_path(challenge_id, nonce, token, cx, cy)
        except Exception:
            break

        ahead = data.get("ahead", [])
        if not ahead:
            break

        for pt in ahead:
            px, py = pt[0], pt[1]
            if (px, py) != (cx, cy):
                all_points.append((px, py))
                cx, cy = px, py

        # If close to the end, stop peeking
        dist_to_end = data.get("distanceToEnd", 999)
        if dist_to_end < 5:
            # Include finish point if revealed
            finish = data.get("finish")
            if finish:
                all_points.append((finish[0], finish[1]))
            break

        time.sleep(0.065)  # respect peek rate limit (60ms min)

    return all_points


# ---------------------------------------------------------------------------
# Trajectory generation strategies
# ---------------------------------------------------------------------------
def strategy_constant(path_points, step_ms=12):
    """Uniform speed, no jitter — most bot-like."""
    trajectory = []
    for px, py in path_points:
        trajectory.append({"x": px, "y": py, "delay_ms": step_ms})
    return trajectory


def strategy_jittered(path_points, step_ms=14, jitter_px=1.5):
    """Adds spatial noise but keeps timing uniform."""
    trajectory = []
    for px, py in path_points:
        jx = px + random.gauss(0, jitter_px)
        jy = py + random.gauss(0, jitter_px)
        trajectory.append({"x": jx, "y": jy, "delay_ms": step_ms})
    return trajectory


def strategy_curvature(path_points, base_ms=16, jitter_px=1.0, slow_factor=2.0):
    """Slows down on curves (curvature-aware), adds jitter."""
    trajectory = []
    n = len(path_points)

    for i, (px, py) in enumerate(path_points):
        curvature = 0
        if 1 <= i < n - 1:
            x0, y0 = path_points[i - 1]
            x1, y1 = px, py
            x2, y2 = path_points[i + 1]
            v1 = (x1 - x0, y1 - y0)
            v2 = (x2 - x1, y2 - y1)
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            m1 = math.hypot(*v1) + 1e-9
            m2 = math.hypot(*v2) + 1e-9
            cos_a = max(-1, min(1, dot / (m1 * m2)))
            curvature = 1 - cos_a

        delay = base_ms + curvature * slow_factor * base_ms
        delay += random.gauss(0, 3)
        delay = max(8, delay)

        jx = px + random.gauss(0, jitter_px)
        jy = py + random.gauss(0, jitter_px)
        trajectory.append({"x": jx, "y": jy, "delay_ms": delay})

    return trajectory


def strategy_humanlike(path_points, base_ms=18, jitter_px=1.2):
    """
    Ballistic profile (accelerate early, decelerate late),
    micro-hesitations at high curvature, spatial jitter.
    """
    trajectory = []
    n = len(path_points)

    for i, (px, py) in enumerate(path_points):
        progress = i / max(n - 1, 1)

        if progress < 0.15:
            speed_mult = 1.5 + (0.15 - progress) * 5
        elif progress > 0.85:
            speed_mult = 1.5 + (progress - 0.85) * 5
        else:
            speed_mult = 0.7

        curvature = 0
        if 1 <= i < n - 1:
            x0, y0 = path_points[i - 1]
            x1, y1 = px, py
            x2, y2 = path_points[i + 1]
            v1 = (x1 - x0, y1 - y0)
            v2 = (x2 - x1, y2 - y1)
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            m1 = math.hypot(*v1) + 1e-9
            m2 = math.hypot(*v2) + 1e-9
            cos_a = max(-1, min(1, dot / (m1 * m2)))
            curvature = 1 - cos_a

        hesitation = 0
        if curvature > 0.3 and random.random() < 0.4:
            hesitation = random.uniform(20, 80)

        delay = base_ms * speed_mult + curvature * 15 + hesitation
        delay += random.gauss(0, 4)
        delay = max(6, delay)

        jx = px + random.gauss(0, jitter_px)
        jy = py + random.gauss(0, jitter_px)
        trajectory.append({"x": jx, "y": jy, "delay_ms": delay})

    return trajectory


STRATEGIES = {
    "constant": strategy_constant,
    "jittered": strategy_jittered,
    "curvature": strategy_curvature,
    "humanlike": strategy_humanlike,
}


# ---------------------------------------------------------------------------
# Canvas coordinate mapping
# ---------------------------------------------------------------------------
async def get_canvas_bbox(page):
    """Get the Canvas element's bounding box on the page."""
    canvas = await page.wait_for_selector(CANVAS_SELECTOR, timeout=CANVAS_WAIT_MS)
    bbox = await canvas.bounding_box()
    if not bbox:
        raise RuntimeError("Could not get Canvas bounding box")
    return bbox


def canvas_to_page(cx, cy, bbox, canvas_logical_size=400):
    """Convert canvas logical coordinates (0-400) to page pixel coordinates."""
    scale_x = bbox["width"] / canvas_logical_size
    scale_y = bbox["height"] / canvas_logical_size
    page_x = bbox["x"] + cx * scale_x
    page_y = bbox["y"] + cy * scale_y
    return page_x, page_y


# ---------------------------------------------------------------------------
# Consent flow automation
# ---------------------------------------------------------------------------
async def navigate_consent_flow(page):
    """Navigate through info sheet + consent form to reach the CAPTCHA page."""
    await page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=15000)
    await page.wait_for_timeout(2000)

    # The app may redirect to /info-sheet via client-side JS — wait for URL to settle
    await page.wait_for_timeout(1000)
    url = page.url
    print(f"    [consent] Landed on: {url}")

    # Info sheet — scroll down and click Continue
    if "/info-sheet" in url:
        print("    [consent] On info sheet, clicking Continue...")
        btn = page.get_by_role("button", name="Continue")
        await btn.scroll_into_view_if_needed()
        await btn.wait_for(state="visible", timeout=5000)
        await btn.click()
        await page.wait_for_timeout(2000)

    # Consent page
    url = page.url
    print(f"    [consent] Now on: {url}")
    if "/consent" in url:
        print("    [consent] Checking all boxes...")
        # Try "Check all" link first
        try:
            check_all = page.get_by_text("Check all", exact=True)
            await check_all.scroll_into_view_if_needed()
            await check_all.click()
            await page.wait_for_timeout(500)
        except Exception:
            checkboxes = page.locator('input[type="checkbox"]')
            count = await checkboxes.count()
            for i in range(count):
                await checkboxes.nth(i).check()
                await page.wait_for_timeout(50)

        # Click "I Agree & Continue"
        agree_btn = page.get_by_role("button", name="I Agree & Continue")
        await agree_btn.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        await agree_btn.click()
        await page.wait_for_timeout(2000)

    # Should now be on the main CAPTCHA page
    url = page.url
    print(f"    [consent] Final URL: {url}")

    # If we're still not on the root, something went wrong
    if "/info-sheet" in url or "/consent" in url:
        raise RuntimeError(f"Failed to complete consent flow, stuck on {url}")


# ---------------------------------------------------------------------------
# Main bot execution
# ---------------------------------------------------------------------------
async def run_single_attempt(page, strategy_name: str, attempt_num: int,
                             is_first_attempt: bool = False) -> BotResult:
    """Execute one bot attempt through the browser."""
    result = BotResult(strategy=strategy_name, attempt=attempt_num, passed=False)

    try:
        # 1. Handle consent flow on first attempt
        if is_first_attempt:
            await navigate_consent_flow(page)
            # Dismiss tutorial if present
            try:
                dialog = page.locator('[role="dialog"]')
                await dialog.wait_for(state="visible", timeout=3000)
                got_it = dialog.get_by_role("button", name="Got it")
                await got_it.click()
                await page.wait_for_timeout(500)
                print("    [tutorial] Dismissed tutorial dialog")
            except Exception:
                print("    [tutorial] No tutorial dialog found")
        else:
            # Dismiss failure tutorial dialog if present from previous attempt
            try:
                dialog = page.locator('[role="dialog"]')
                if await dialog.count() > 0:
                    got_it = dialog.get_by_role("button", name="Got it")
                    await got_it.click()
                    await page.wait_for_timeout(300)
            except Exception:
                pass

        # 4. Wait for canvas
        bbox = await get_canvas_bbox(page)
        print(f"    [canvas] bbox: {bbox['width']:.0f}x{bbox['height']:.0f} at ({bbox['x']:.0f},{bbox['y']:.0f})")

        # 5. Click "New Challenge" and intercept the API response to get
        #    the SAME challenge the frontend is using.
        challenge = None

        async def intercept_challenge(response):
            nonlocal challenge
            if "/captcha/line/new" in response.url and response.status == 200:
                challenge = await response.json()

        page.on("response", intercept_challenge)

        new_btn = page.get_by_role("button", name="New Challenge")
        await new_btn.click()
        # Wait for the challenge response
        await page.wait_for_timeout(1500)
        page.remove_listener("response", intercept_challenge)

        if not challenge:
            result.failure_reason = "failed_to_intercept_challenge"
            return result

        challenge_id = challenge["challengeId"]
        nonce = challenge["nonce"]
        token = challenge["token"]
        start_point = challenge["startPoint"]
        start_x, start_y = start_point[0], start_point[1]

        # 6. Peek to collect full path using the intercepted challenge
        print(f"    [path] Collecting path from ({start_x:.0f}, {start_y:.0f})...")
        path_points = collect_full_path(challenge_id, nonce, token, start_x, start_y)
        print(f"    [path] Got {len(path_points)} points")

        if len(path_points) < 5:
            result.failure_reason = "insufficient_path_points"
            return result

        # 7. Generate trajectory
        strategy_fn = STRATEGIES[strategy_name]
        trajectory = strategy_fn(path_points)
        result.points_generated = len(trajectory)

        # 8. Execute mouse movements on the Canvas
        t_start = time.time()

        # Move to start and press down
        sx, sy = canvas_to_page(trajectory[0]["x"], trajectory[0]["y"], bbox)
        await page.mouse.move(sx, sy)
        await page.wait_for_timeout(100)
        await page.mouse.down()
        await page.wait_for_timeout(50)

        # Trace the path
        for point in trajectory[1:]:
            px, py = canvas_to_page(point["x"], point["y"], bbox)
            delay = max(1, int(point["delay_ms"]))
            await page.mouse.move(px, py, steps=1)
            await page.wait_for_timeout(delay)

        # Release
        await page.mouse.up()
        t_end = time.time()
        result.solve_time_ms = (t_end - t_start) * 1000

        # 9. Wait for verification result
        await page.wait_for_timeout(2000)

        # 10. Check result from DOM
        #     The status text shows "Passed." on success or error messages on failure.
        #     Also check for the confetti (canvas-confetti creates a canvas).
        #     The status element has role="status".
        try:
            status_el = page.locator('[role="status"]').first
            status_text = await status_el.text_content(timeout=3000)
            status_text = (status_text or "").strip().lower()
            print(f"    [result] Status text: '{status_text}'")

            if "passed" in status_text:
                result.passed = True
            elif status_text and status_text != "status":
                result.failure_reason = status_text
        except Exception as e:
            print(f"    [result] Could not read status: {e}")

        # Also check if failure tutorial dialog appeared
        if not result.passed:
            try:
                dialog = page.locator('[role="dialog"]')
                if await dialog.count() > 0:
                    title = await dialog.locator('[class*="DialogTitle"]').first.text_content(timeout=1000)
                    result.failure_reason = f"tutorial_shown: {title}"
                    # Dismiss it
                    dismiss = dialog.get_by_role("button", name="Got it")
                    await dismiss.click()
                    await page.wait_for_timeout(300)
            except Exception:
                pass

        if not result.passed and not result.failure_reason:
            result.failure_reason = "unknown"

    except Exception as e:
        result.failure_reason = f"error: {str(e)[:200]}"

    return result


async def run_strategy(strategy_name: str, attempts: int, headless: bool = True) -> RunSummary:
    """Run multiple attempts with a given strategy."""
    summary = RunSummary(strategy=strategy_name)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = await context.new_page()

        for i in range(attempts):
            result = await run_single_attempt(
                page, strategy_name, i + 1,
                is_first_attempt=(i == 0),
            )
            summary.total += 1
            if result.passed:
                summary.passed += 1
            else:
                summary.failed += 1
            summary.results.append(result)

            status = "PASS" if result.passed else f"FAIL ({result.failure_reason})"
            print(f"  [{strategy_name}] attempt {i+1}/{attempts}: {status}  "
                  f"({result.solve_time_ms:.0f}ms, {result.points_generated} pts)")

            # Small delay between attempts
            await page.wait_for_timeout(random.randint(500, 1500))

        await browser.close()

    return summary


# ---------------------------------------------------------------------------
# CLI + reporting
# ---------------------------------------------------------------------------
def print_report(summaries: list[RunSummary]):
    print("\n" + "=" * 65)
    print("PLAYWRIGHT LINE TRACING BOT — RESULTS SUMMARY")
    print("=" * 65)
    print(f"{'Strategy':<15} {'Total':>6} {'Pass':>6} {'Fail':>6} {'Pass Rate':>10}")
    print("-" * 65)
    for s in summaries:
        print(f"{s.strategy:<15} {s.total:>6} {s.passed:>6} {s.failed:>6} {s.pass_rate:>9.1f}%")
    print("-" * 65)

    total = sum(s.total for s in summaries)
    passed = sum(s.passed for s in summaries)
    rate = (passed / total * 100) if total else 0
    print(f"{'OVERALL':<15} {total:>6} {passed:>6} {total-passed:>6} {rate:>9.1f}%")
    print("=" * 65)


def save_results(summaries: list[RunSummary], filename: str = "playwright_line_results.json"):
    data = []
    for s in summaries:
        for r in s.results:
            data.append({
                "strategy": r.strategy,
                "attempt": r.attempt,
                "passed": r.passed,
                "failure_reason": r.failure_reason,
                "solve_time_ms": r.solve_time_ms,
                "points_generated": r.points_generated,
            })
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nResults saved to {filename}")


async def main():
    global FRONTEND_URL, BACKEND_URL

    parser = argparse.ArgumentParser(description="Playwright Line Tracing Bot")
    parser.add_argument("--strategy", default="all",
                        choices=["constant", "jittered", "curvature", "humanlike", "all"])
    parser.add_argument("--attempts", type=int, default=10)
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--frontend-url", default=FRONTEND_URL)
    parser.add_argument("--backend-url", default=BACKEND_URL)
    parser.add_argument("--output", default="playwright_line_results.json")
    args = parser.parse_args()

    FRONTEND_URL = args.frontend_url
    BACKEND_URL = args.backend_url

    strategies = list(STRATEGIES.keys()) if args.strategy == "all" else [args.strategy]
    summaries = []

    for strat in strategies:
        print(f"\n--- Running strategy: {strat} ({args.attempts} attempts) ---")
        summary = await run_strategy(strat, args.attempts, headless=not args.headed)
        summaries.append(summary)

    print_report(summaries)
    save_results(summaries, args.output)


if __name__ == "__main__":
    asyncio.run(main())
