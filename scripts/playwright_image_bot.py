"""
Playwright Browser-Automation Bot — Image Intersection CAPTCHA
================================================================
Full attack pipeline: rendered Canvas → screenshot → OpenCV → click.

Strategies:
  1. hough       — Canny + HoughLinesP to detect lines, compute intersections
  2. random      — Click random Canvas positions (control/baseline)
  3. center      — Click near center (naive heuristic)

Usage:
  pip install playwright opencv-python-headless numpy
  playwright install chromium
  python playwright_image_bot.py --strategy hough --attempts 1 --headed
  python playwright_image_bot.py --strategy all --attempts 20
"""

import argparse
import asyncio
import json
import math
import random
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Install playwright: pip install playwright && playwright install chromium")
    exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
FRONTEND_URL = "http://localhost:9002"
CANVAS_SELECTOR = "canvas"
CANVAS_LOGICAL_SIZE = 400


@dataclass
class BotResult:
    strategy: str
    attempt: int
    passed: bool
    failure_reason: str = ""
    solve_time_ms: float = 0
    intersections_found: int = 0
    clicks_made: int = 0


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
# CV: intersection detection from screenshot
# ---------------------------------------------------------------------------
def find_intersections_hough(screenshot_bytes: bytes, canvas_w: int, canvas_h: int):
    """Detect lines via Hough transform, compute intersection points."""
    nparr = np.frombuffer(screenshot_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    img_resized = cv2.resize(img, (CANVAS_LOGICAL_SIZE, CANVAS_LOGICAL_SIZE))
    gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100, apertureSize=3)

    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)

    lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi / 180,
        threshold=30, minLineLength=30, maxLineGap=15,
    )

    if lines is None or len(lines) < 2:
        return []

    intersections = []
    line_list = [l[0] for l in lines]

    for i in range(len(line_list)):
        for j in range(i + 1, len(line_list)):
            pt = line_intersection(line_list[i], line_list[j])
            if pt is not None:
                x, y = pt
                margin = 15
                if margin < x < CANVAS_LOGICAL_SIZE - margin and margin < y < CANVAS_LOGICAL_SIZE - margin:
                    intersections.append((x, y))

    clustered = cluster_points(intersections, radius=20)
    return clustered


def line_intersection(line1, line2):
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-6:
        return None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    ix = x1 + t * (x2 - x1)
    iy = y1 + t * (y2 - y1)
    return (ix, iy)


def cluster_points(points, radius=20):
    if not points:
        return []

    used = [False] * len(points)
    clusters = []

    for i in range(len(points)):
        if used[i]:
            continue
        cluster = [points[i]]
        used[i] = True
        for j in range(i + 1, len(points)):
            if used[j]:
                continue
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            if math.hypot(dx, dy) < radius:
                cluster.append(points[j])
                used[j] = True

        cx = sum(p[0] for p in cluster) / len(cluster)
        cy = sum(p[1] for p in cluster) / len(cluster)
        clusters.append((cx, cy))

    return clusters


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------
def strategy_hough(screenshot_bytes, canvas_w, canvas_h):
    return find_intersections_hough(screenshot_bytes, canvas_w, canvas_h)


def strategy_random(screenshot_bytes, canvas_w, canvas_h):
    n_clicks = random.randint(2, 3)
    margin = 30
    return [
        (random.uniform(margin, CANVAS_LOGICAL_SIZE - margin),
         random.uniform(margin, CANVAS_LOGICAL_SIZE - margin))
        for _ in range(n_clicks)
    ]


def strategy_center(screenshot_bytes, canvas_w, canvas_h):
    cx, cy = CANVAS_LOGICAL_SIZE / 2, CANVAS_LOGICAL_SIZE / 2
    return [
        (cx + random.gauss(0, 30), cy + random.gauss(0, 30))
        for _ in range(2)
    ]


STRATEGIES = {
    "hough": strategy_hough,
    "random": strategy_random,
    "center": strategy_center,
}


# ---------------------------------------------------------------------------
# Canvas coordinate mapping
# ---------------------------------------------------------------------------
def canvas_to_page(cx, cy, bbox):
    scale_x = bbox["width"] / CANVAS_LOGICAL_SIZE
    scale_y = bbox["height"] / CANVAS_LOGICAL_SIZE
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
    await page.wait_for_timeout(1000)
    url = page.url
    print(f"    [consent] Landed on: {url}")

    if "/info-sheet" in url:
        print("    [consent] On info sheet, clicking Continue...")
        btn = page.get_by_role("button", name="Continue")
        await btn.scroll_into_view_if_needed()
        await btn.wait_for(state="visible", timeout=5000)
        await btn.click()
        await page.wait_for_timeout(2000)

    url = page.url
    print(f"    [consent] Now on: {url}")
    if "/consent" in url:
        print("    [consent] Checking all boxes...")
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

        agree_btn = page.get_by_role("button", name="I Agree & Continue")
        await agree_btn.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        await agree_btn.click()
        await page.wait_for_timeout(2000)

    url = page.url
    print(f"    [consent] Final URL: {url}")

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
        # 1. Consent flow on first attempt
        if is_first_attempt:
            await navigate_consent_flow(page)

            # Dismiss line tutorial if it pops up
            try:
                dialog = page.locator('[role="dialog"]')
                await dialog.wait_for(state="visible", timeout=2000)
                got_it = dialog.get_by_role("button", name="Got it")
                await got_it.click()
                await page.wait_for_timeout(500)
            except Exception:
                pass

        # 2. Switch to "Spot the Crossings" tab
        try:
            tab = page.get_by_role("tab", name="Spot the Crossings")
            if await tab.is_enabled():
                await tab.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        # 3. Dismiss image tutorial dialog if present
        try:
            dialog = page.locator('[role="dialog"]')
            await dialog.wait_for(state="visible", timeout=2000)
            got_it = dialog.get_by_role("button", name="Got it")
            await got_it.click()
            await page.wait_for_timeout(500)
            print("    [tutorial] Dismissed tutorial dialog")
        except Exception:
            pass

        # 4. Click "New Challenge" to get a fresh image challenge
        try:
            new_btn = page.get_by_role("button", name="New Challenge")
            await new_btn.click()
            await page.wait_for_timeout(1500)
        except Exception:
            pass

        # 5. Wait for canvas to render
        canvas = await page.wait_for_selector(CANVAS_SELECTOR, timeout=CANVAS_WAIT_MS)
        await page.wait_for_timeout(1000)

        bbox = await canvas.bounding_box()
        if not bbox:
            result.failure_reason = "no_canvas_bbox"
            return result

        print(f"    [canvas] bbox: {bbox['width']:.0f}x{bbox['height']:.0f}")

        # 6. Screenshot the canvas
        screenshot = await canvas.screenshot(type="png")

        # 7. Run strategy to find click targets
        t_start = time.time()
        strategy_fn = STRATEGIES[strategy_name]
        click_targets = strategy_fn(screenshot, int(bbox["width"]), int(bbox["height"]))
        result.intersections_found = len(click_targets)
        print(f"    [cv] Found {len(click_targets)} intersection(s)")

        if not click_targets:
            result.failure_reason = "no_intersections_detected"
            result.solve_time_ms = (time.time() - t_start) * 1000
            return result

        # 8. Wait to exceed min solve time
        await page.wait_for_timeout(900)

        # 9. Click each detected intersection
        for cx, cy in click_targets:
            px, py = canvas_to_page(cx, cy, bbox)
            await page.mouse.click(px, py)
            result.clicks_made += 1
            await page.wait_for_timeout(random.randint(150, 350))

        # 10. Click Submit button
        try:
            submit = page.get_by_role("button", name="Submit")
            await submit.click(timeout=3000)
        except Exception:
            pass

        t_end = time.time()
        result.solve_time_ms = (t_end - t_start) * 1000

        # 11. Wait for result
        await page.wait_for_timeout(2000)

        # 12. Check outcome via status text
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

        # Dismiss failure tutorial dialog if present
        if not result.passed:
            try:
                dialog = page.locator('[role="dialog"]')
                if await dialog.count() > 0:
                    got_it = dialog.get_by_role("button", name="Got it")
                    await got_it.click()
                    await page.wait_for_timeout(300)
            except Exception:
                pass

        if not result.passed and not result.failure_reason:
            result.failure_reason = "rejected"

    except Exception as e:
        result.failure_reason = f"error: {str(e)[:200]}"

    return result


CANVAS_WAIT_MS = 8000


async def run_strategy(strategy_name: str, attempts: int, headless: bool = True) -> RunSummary:
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
                  f"({result.solve_time_ms:.0f}ms, found={result.intersections_found}, "
                  f"clicks={result.clicks_made})")

            await page.wait_for_timeout(random.randint(500, 1000))

        await browser.close()

    return summary


# ---------------------------------------------------------------------------
# CLI + reporting
# ---------------------------------------------------------------------------
def print_report(summaries: list[RunSummary]):
    print("\n" + "=" * 70)
    print("PLAYWRIGHT IMAGE INTERSECTION BOT — RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Strategy':<15} {'Total':>6} {'Pass':>6} {'Fail':>6} {'Pass Rate':>10} {'Avg Found':>10}")
    print("-" * 70)
    for s in summaries:
        avg_found = (sum(r.intersections_found for r in s.results) / s.total) if s.total else 0
        print(f"{s.strategy:<15} {s.total:>6} {s.passed:>6} {s.failed:>6} "
              f"{s.pass_rate:>9.1f}% {avg_found:>9.1f}")
    print("-" * 70)

    total = sum(s.total for s in summaries)
    passed = sum(s.passed for s in summaries)
    rate = (passed / total * 100) if total else 0
    print(f"{'OVERALL':<15} {total:>6} {passed:>6} {total-passed:>6} {rate:>9.1f}%")
    print("=" * 70)


def save_results(summaries: list[RunSummary], filename: str = "playwright_image_results.json"):
    data = []
    for s in summaries:
        for r in s.results:
            data.append({
                "strategy": r.strategy,
                "attempt": r.attempt,
                "passed": r.passed,
                "failure_reason": r.failure_reason,
                "solve_time_ms": r.solve_time_ms,
                "intersections_found": r.intersections_found,
                "clicks_made": r.clicks_made,
            })
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nResults saved to {filename}")


async def main():
    global FRONTEND_URL

    parser = argparse.ArgumentParser(description="Playwright Image Intersection Bot")
    parser.add_argument("--strategy", default="all",
                        choices=["hough", "random", "center", "all"])
    parser.add_argument("--attempts", type=int, default=10)
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--frontend-url", default=FRONTEND_URL)
    parser.add_argument("--output", default="playwright_image_results.json")
    args = parser.parse_args()

    FRONTEND_URL = args.frontend_url

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
