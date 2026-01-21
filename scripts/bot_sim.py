#!/usr/bin/env python3
import argparse
import json
import math
import random
import sys
import time
import urllib.request


def _post_json(url, payload, timeout=5, retries=3, retry_sleep=0.12):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                time.sleep(retry_sleep)
                continue
            raise


def _dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _angle(a, b, c):
    abx = a[0] - b[0]
    aby = a[1] - b[1]
    cbx = c[0] - b[0]
    cby = c[1] - b[1]
    ab_len = math.hypot(abx, aby)
    cb_len = math.hypot(cbx, cby)
    if ab_len <= 1e-6 or cb_len <= 1e-6:
        return 0.0
    cos_theta = (abx * cbx + aby * cby) / (ab_len * cb_len)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return math.acos(cos_theta)


def _segment_curvatures(points):
    if len(points) < 3:
        return [0.0] * max(0, len(points) - 1)
    curvatures = [0.0] * (len(points) - 1)
    for i in range(1, len(points) - 1):
        angle = _angle(points[i - 1], points[i], points[i + 1])
        curvatures[i] = min(1.0, angle / math.pi)
    return curvatures


def _step_along(
    polyline,
    start,
    max_advance,
    step_px,
    step_ms,
    jitter_px,
    t_ms,
    traj,
    step_ms_jitter=0.0,
    curvature_slow_factor=0.0,
    curvature_ms_jitter=0.0,
):
    if not polyline:
        return start, t_ms
    points = [start]
    for p in polyline:
        if p != points[-1]:
            points.append(p)
    curvatures = None
    if curvature_slow_factor > 0 or curvature_ms_jitter > 0:
        curvatures = _segment_curvatures(points)

    remaining = max_advance
    curr = start
    for i in range(1, len(points)):
        target = points[i]
        seg_len = _dist(curr, target)
        seg_curv = curvatures[i - 1] if curvatures else 0.0
        while seg_len > 0 and remaining > 0:
            step = min(step_px, seg_len, remaining)
            ratio = step / seg_len if seg_len else 0
            nx = curr[0] + (target[0] - curr[0]) * ratio
            ny = curr[1] + (target[1] - curr[1]) * ratio
            if jitter_px > 0:
                nx += random.uniform(-jitter_px, jitter_px)
                ny += random.uniform(-jitter_px, jitter_px)
            step_ms_eff = float(step_ms)
            if curvature_slow_factor > 0:
                step_ms_eff *= 1.0 + seg_curv * curvature_slow_factor
            if step_ms_jitter > 0:
                step_ms_eff *= 1.0 + random.uniform(-step_ms_jitter, step_ms_jitter)
            if curvature_ms_jitter > 0:
                step_ms_eff *= 1.0 + random.uniform(-curvature_ms_jitter, curvature_ms_jitter) * seg_curv
            step_ms_eff = max(1.0, step_ms_eff)
            t_ms += step_ms_eff
            traj.append({"x": nx, "y": ny, "t": int(t_ms)})
            curr = (nx, ny)
            seg_len = _dist(curr, target)
            remaining -= step
        if remaining <= 0:
            break
        curr = target
    return curr, t_ms


def _forward_polyline(polyline, cursor):
    if not polyline:
        return []
    best_i = 0
    best_dist = float("inf")
    for i, p in enumerate(polyline):
        d = _dist(cursor, p)
        if d < best_dist:
            best_dist = d
            best_i = i
    # Skip the nearest point to avoid stepping backward into the "behind" segment.
    if best_i + 1 < len(polyline):
        return polyline[best_i + 1 :]
    return polyline[best_i:]


def run_attempt(
    base_url,
    pointer_type,
    step_px,
    step_ms,
    step_ms_jitter,
    advance_px,
    jitter_px,
    curvature_slow_factor,
    curvature_ms_jitter,
    max_ms,
    peek_interval_ms,
    verbose,
):
    new_url = f"{base_url}/captcha/line/new"
    peek_url = f"{base_url}/captcha/line/peek"
    verify_url = f"{base_url}/captcha/line/verify"

    new = _post_json(new_url, {})
    challenge_id = new["challengeId"]
    token = new["token"]
    nonce = new["nonce"]
    ttl_ms = int(new["ttlMs"])
    cursor = [new["startPoint"][0], new["startPoint"][1]]

    t_ms = 0
    trajectory = [{"x": cursor[0], "y": cursor[1], "t": int(t_ms)}]

    max_duration = min(ttl_ms, max_ms)
    loops = 0
    last_peek_ts = 0.0
    while t_ms < max_duration:
        loops += 1
        now = time.time()
        since = (now - last_peek_ts) * 1000.0 if last_peek_ts else None
        if since is not None and since < peek_interval_ms:
            time.sleep((peek_interval_ms - since) / 1000.0)
        peek = _post_json(
            peek_url,
            {"challengeId": challenge_id, "nonce": nonce, "token": token, "cursor": cursor},
        )
        last_peek_ts = time.time()
        ahead = _forward_polyline(peek.get("ahead") or [], cursor)
        finish = peek.get("finish")
        if finish and (not ahead or ahead[-1] != finish):
            ahead = ahead + [finish]
        cursor, t_ms = _step_along(
            ahead,
            cursor,
            advance_px,
            step_px,
            step_ms,
            jitter_px,
            t_ms,
            trajectory,
            step_ms_jitter=step_ms_jitter,
            curvature_slow_factor=curvature_slow_factor,
            curvature_ms_jitter=curvature_ms_jitter,
        )
        if finish and _dist(cursor, finish) <= step_px:
            break
        if loops > 2000:
            break

    verify_payload = {
        "challengeId": challenge_id,
        "nonce": nonce,
        "token": token,
        "sessionId": "bot-session",
        "pointerType": pointer_type,
        "osFamily": "bot",
        "browserFamily": "bot",
        "devicePixelRatio": 1,
        "trajectory": trajectory,
    }
    result = _post_json(verify_url, verify_payload)
    if verbose:
        print(
            f"attempt={challenge_id} passed={result['passed']} reason={result['reason']} "
            f"duration={result['durationMs']:.0f}ms coverage={result['coverageRatio']:.2f}"
        )
    return result


def main():
    parser = argparse.ArgumentParser(description="Simple local bot simulation for line CAPTCHA.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL.")
    parser.add_argument("--attempts", type=int, default=10, help="Number of attempts.")
    parser.add_argument("--pointer-type", default="mouse", choices=["mouse", "touch", "pen"])
    parser.add_argument("--step-px", type=float, default=5.0, help="Step size per sample (px).")
    parser.add_argument("--step-ms", type=int, default=16, help="Time per step (ms).")
    parser.add_argument(
        "--step-ms-jitter",
        type=float,
        default=0.0,
        help="Fractional jitter applied to step timing (e.g., 0.1 = +/-10%).",
    )
    parser.add_argument("--advance-px", type=float, default=40.0, help="Max advance per peek (px).")
    parser.add_argument("--jitter-px", type=float, default=0.0, help="Uniform jitter per step (px).")
    parser.add_argument(
        "--curvature-aware",
        action="store_true",
        help="Adapt step timing based on local curvature from peeked segments.",
    )
    parser.add_argument(
        "--curvature-slow-factor",
        type=float,
        default=1.0,
        help="Extra slowdown multiplier at high curvature (0 disables).",
    )
    parser.add_argument(
        "--curvature-ms-jitter",
        type=float,
        default=0.0,
        help="Additional timing jitter scaled by curvature (fractional).",
    )
    parser.add_argument("--max-ms", type=int, default=5500, help="Max duration per attempt (ms).")
    parser.add_argument("--peek-interval-ms", type=int, default=120, help="Minimum delay between peeks (ms).")
    parser.add_argument("--verbose", action="store_true", help="Print per-attempt output.")
    args = parser.parse_args()

    curvature_slow_factor = args.curvature_slow_factor if args.curvature_aware else 0.0
    curvature_ms_jitter = args.curvature_ms_jitter if args.curvature_aware else 0.0
    passed = 0
    reasons = {}
    for _ in range(args.attempts):
        try:
            result = run_attempt(
                args.base_url,
                args.pointer_type,
                args.step_px,
                args.step_ms,
                args.step_ms_jitter,
                args.advance_px,
                args.jitter_px,
                curvature_slow_factor,
                curvature_ms_jitter,
                args.max_ms,
                args.peek_interval_ms,
                args.verbose,
            )
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            continue
        reasons[result["reason"]] = reasons.get(result["reason"], 0) + 1
        if result["passed"]:
            passed += 1

    print(f"attempts={args.attempts} passed={passed} pass_rate={(passed / max(1, args.attempts)) * 100:.1f}%")
    print("reasons:")
    for reason, count in sorted(reasons.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {reason}: {count}")


if __name__ == "__main__":
    raise SystemExit(main())
