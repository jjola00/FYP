import json
import math
import random
import time
import uuid
from typing import Dict, List, Tuple

import fastapi
from fastapi.middleware.cors import CORSMiddleware

from . import config, db, models, path, token

app = fastapi.FastAPI(title="Ephemeral Line CAPTCHA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


def _challenge_tolerance(challenge_row: Dict, pointer_type: str) -> float:
    # Use stored per-challenge tolerance, with pen treated as touch.
    if pointer_type == "mouse":
        return float(challenge_row["tolerance_mouse"])
    return float(challenge_row["tolerance_touch"])


def _speed_stats(traj: List[models.TrajectorySample]) -> Tuple[float, float]:
    distances = []
    durations = []
    for i in range(1, len(traj)):
        dx = traj[i].x - traj[i - 1].x
        dy = traj[i].y - traj[i - 1].y
        dt = max(1, traj[i].t - traj[i - 1].t)
        distances.append((dx * dx + dy * dy) ** 0.5)
        durations.append(dt / 1000.0)
    if not distances:
        return 0.0, 0.0
    total_dist = sum(distances)
    total_time = sum(durations)
    mean_speed = total_dist / total_time if total_time else 0.0
    max_speed = max(d / t for d, t in zip(distances, durations) if t > 0)
    return mean_speed, max_speed


def _pause_stats(traj: List[models.TrajectorySample], pause_gap_ms: int = 150):
    pauses = []
    count = 0
    for i in range(1, len(traj)):
        gap = traj[i].t - traj[i - 1].t
        if gap >= pause_gap_ms:
            count += 1
            pauses.append(gap)
    return count, pauses


@app.post("/captcha/line/new", response_model=models.NewChallengeResponse)
def new_challenge() -> models.NewChallengeResponse:
    challenge_id = uuid.uuid4().hex
    seed = uuid.uuid4().hex
    points, length = path.generate_path(seed)
    ttl_ms = config.CHALLENGE_TTL_MS
    expires_at = time.time() + ttl_ms / 1000.0
    nonce = uuid.uuid4().hex
    issued_at = time.time()

    # Per-challenge tolerance jitter
    base_mouse = config.POINTER_CONFIG["mouse"]["tolerance_px"]
    base_touch = config.POINTER_CONFIG["touch"]["tolerance_px"]
    jitter_mouse = random.uniform(-config.TOLERANCE_JITTER_MOUSE_PX, config.TOLERANCE_JITTER_MOUSE_PX)
    jitter_touch = random.uniform(-config.TOLERANCE_JITTER_TOUCH_PX, config.TOLERANCE_JITTER_TOUCH_PX)
    tolerance_mouse = max(1.0, base_mouse + jitter_mouse)
    tolerance_touch = max(1.0, base_touch + jitter_touch)

    db.save_challenge(
        challenge_id=challenge_id,
        seed=seed,
        points=[[float(f"{x:.2f}"), float(f"{y:.2f}")] for x, y in points],
        path_length=length,
        ttl_ms=ttl_ms,
        nonce=nonce,
        tolerance_mouse=tolerance_mouse,
        tolerance_touch=tolerance_touch,
        jitter_mouse=jitter_mouse,
        jitter_touch=jitter_touch,
    )

    token_payload = {
        "cid": challenge_id,
        "seed": seed,
        "ttl": ttl_ms,
        "iat": issued_at,
        "nonce": nonce,
    }
    signed_token = token.sign(token_payload)

    return models.NewChallengeResponse(
        challengeId=challenge_id,
        ttlMs=ttl_ms,
        expiresAt=expires_at,
        nonce=nonce,
        token=signed_token,
        startPoint=[float(f"{points[0][0]:.2f}"), float(f"{points[0][1]:.2f}")],
        tolerance={
            "mouse": round(tolerance_mouse),
            "touch": round(tolerance_touch),
        },
        targetCompletionMs=config.TARGET_COMPLETION_TIME_MS,
        trail={
            "visibleMs": config.TRAIL_VISIBLE_MS,
            "fadeoutMs": config.TRAIL_FADEOUT_MS,
        },
        canvas={"width": config.CANVAS_WIDTH_PX, "height": config.CANVAS_HEIGHT_PX},
    )


@app.post("/captcha/line/peek", response_model=models.PeekResponse)
def peek_path(payload: models.PeekRequest):
    challenge_row = db.get_challenge(payload.challengeId)
    if not challenge_row:
        raise fastapi.HTTPException(status_code=404, detail="Unknown challenge")
    row_keys = challenge_row.keys()
    nonce_used = challenge_row["nonce_used"] if "nonce_used" in row_keys else 0
    if nonce_used:
        raise fastapi.HTTPException(status_code=410, detail="Challenge already used")

    created_at = float(challenge_row["created_at"])
    ttl_ms = int(challenge_row["ttl_ms"])
    expires_at = created_at + ttl_ms / 1000.0

    try:
        claims = token.verify(payload.token)
    except Exception:
        raise fastapi.HTTPException(status_code=401, detail="Invalid token")
    if claims.get("cid") != payload.challengeId or claims.get("nonce") != payload.nonce:
        raise fastapi.HTTPException(status_code=401, detail="Token mismatch")

    if time.time() > expires_at:
        raise fastapi.HTTPException(status_code=410, detail="Challenge expired")

    points = json.loads(challenge_row["points_json"])
    ahead_polyline = path.lookahead(points, (payload.cursor[0], payload.cursor[1]))
    distance_to_end = path.distance_to_end(points, (payload.cursor[0], payload.cursor[1]))
    finish_point = points[-1] if distance_to_end <= config.FINISH_REVEAL_PX else None
    return models.PeekResponse(
        ahead=[[float(f"{x:.2f}"), float(f"{y:.2f}")] for x, y in ahead_polyline],
        behind=[],
        distanceToEnd=float(f"{distance_to_end:.2f}"),
        finish=[float(f"{points[-1][0]:.2f}"), float(f"{points[-1][1]:.2f}")] if finish_point else None,
    )


@app.post("/captcha/line/verify", response_model=models.VerifyResponse)
def verify_attempt(payload: models.VerifyRequest):
    challenge_row = db.get_challenge(payload.challengeId)
    if not challenge_row:
        raise fastapi.HTTPException(status_code=404, detail="Unknown challenge")
    row_keys = challenge_row.keys()
    nonce_used = challenge_row["nonce_used"] if "nonce_used" in row_keys else 0
    if nonce_used:
        raise fastapi.HTTPException(status_code=410, detail="Challenge already used")

    created_at = float(challenge_row["created_at"])
    ttl_ms = int(challenge_row["ttl_ms"])
    expires_at = created_at + ttl_ms / 1000.0
    now = time.time()
    ttl_expired = now > expires_at

    try:
        claims = token.verify(payload.token)
    except Exception:
        raise fastapi.HTTPException(status_code=401, detail="Invalid token")
    if (
        claims.get("cid") != payload.challengeId
        or claims.get("nonce") != payload.nonce
        or claims.get("ttl") != ttl_ms
    ):
        raise fastapi.HTTPException(status_code=401, detail="Token mismatch")

    base_tolerance = (
        config.POINTER_CONFIG["mouse"]["tolerance_px"]
        if payload.pointerType == "mouse"
        else config.POINTER_CONFIG["touch"]["tolerance_px"]
    )
    try:
        tolerance_px = _challenge_tolerance(challenge_row, payload.pointerType)
    except Exception:
        tolerance_px = base_tolerance
    if payload.devicePixelRatio and payload.devicePixelRatio >= 2:
        tolerance_px *= 1.1
    tolerance_jitter = tolerance_px - base_tolerance

    path_points = json.loads(challenge_row["points_json"])
    coverage_hits = 0
    monotonic = True
    jumps_ok = True
    min_samples = len(payload.trajectory) >= config.MIN_SAMPLES
    last_t = payload.trajectory[0].t
    total_seg_len = 0.0
    covered_seg_len = 0.0
    speeds: List[float] = []
    accels: List[float] = []
    for idx, sample in enumerate(payload.trajectory):
        if idx > 0 and sample.t <= last_t:
            monotonic = False
            break
        if idx > 0:
            prev = payload.trajectory[idx - 1]
            jump_dist = ((sample.x - prev.x) ** 2 + (sample.y - prev.y) ** 2) ** 0.5
            if jump_dist > tolerance_px * 2:
                jumps_ok = False
                break
            total_seg_len += jump_dist
            dt_s = max(0.001, (sample.t - prev.t) / 1000.0)
            speed = jump_dist / dt_s
            speeds.append(speed)
            if len(speeds) > 1:
                accels.append((speeds[-1] - speeds[-2]) / dt_s)
            if (
                path.min_distance_to_polyline((sample.x, sample.y), path_points) <= tolerance_px
                and path.min_distance_to_polyline((prev.x, prev.y), path_points) <= tolerance_px
            ):
                covered_seg_len += jump_dist
        last_t = sample.t

    for sample in payload.trajectory:
        dist = path.min_distance_to_polyline((sample.x, sample.y), path_points)
        if dist <= tolerance_px:
            coverage_hits += 1
    coverage_ratio = coverage_hits / len(payload.trajectory)
    coverage_len_ratio = covered_seg_len / total_seg_len if total_seg_len > 0 else 0.0

    duration_ms = payload.trajectory[-1].t - payload.trajectory[0].t
    too_fast = duration_ms < config.TOO_FAST_THRESHOLD_MS
    end_point = path_points[-1]
    last_sample = payload.trajectory[-1]
    end_distance = math.hypot(last_sample.x - end_point[0], last_sample.y - end_point[1])
    end_reached = end_distance <= tolerance_px

    mean_speed, max_speed = _speed_stats(payload.trajectory)
    pause_count, pause_durations = _pause_stats(payload.trajectory)
    deviation_stats = {"mean": None, "max": None}
    deviations = []
    for sample in payload.trajectory:
        deviations.append(path.min_distance_to_polyline((sample.x, sample.y), path_points))
    if deviations:
        deviation_stats["mean"] = sum(deviations) / len(deviations)
        deviation_stats["max"] = max(deviations)

    speed_const_flag = False
    accel_flag = False
    if speeds and mean_speed > 0:
        mean_s = sum(speeds) / len(speeds)
        var_s = sum((s - mean_s) ** 2 for s in speeds) / len(speeds)
        std_s = var_s ** 0.5
        if std_s / mean_s < config.SPEED_CONSTANTITY_RATIO:
            speed_const_flag = True
    if accels:
        max_accel = max(abs(a) for a in accels)
        if max_accel > config.MAX_ACCEL_PX_PER_S2:
            accel_flag = True

    behavioural_flag = speed_const_flag or accel_flag
    if not min_samples:
        reason = "insufficient_samples"
        passed = False
    elif not monotonic:
        reason = "non_monotonic_time"
        passed = False
    elif not jumps_ok:
        reason = "jump_detected"
        passed = False
    elif coverage_len_ratio < config.REQUIRED_COVERAGE_RATIO:
        reason = "low_coverage"
        passed = False
    elif coverage_ratio < config.REQUIRED_COVERAGE_RATIO:
        reason = "low_coverage"
        passed = False
    elif not end_reached:
        reason = "incomplete"
        passed = False
    elif ttl_expired:
        reason = "timeout"
        passed = False
    elif too_fast:
        reason = "too_fast"
        passed = False
    else:
        # Behavioural signals are logged but not blocking until thresholds are tuned.
        reason = "success" if not behavioural_flag else "success_with_behavioural_flag"
        passed = True

    db.save_attempt(
        {
            "attempt_id": uuid.uuid4().hex,
            "session_id": payload.sessionId,
            "challenge_id": payload.challengeId,
            "pointer_type": payload.pointerType,
            "os_family": payload.osFamily,
            "browser_family": payload.browserFamily,
            "device_pixel_ratio": payload.devicePixelRatio,
            "path_seed": challenge_row["seed"],
            "path_length_px": float(challenge_row["path_length"]),
            "tolerance_px": tolerance_px,
            "tolerance_jitter_px": tolerance_jitter,
            "ttl_ms": ttl_ms,
            "started_at": payload.trajectory[0].t,
            "ended_at": payload.trajectory[-1].t,
            "duration_ms": duration_ms,
            "outcome_reason": reason,
            "coverage_ratio": coverage_ratio,
            "coverage_len_ratio": coverage_len_ratio,
            "mean_speed": mean_speed,
            "max_speed": max_speed,
            "pause_count": pause_count,
            "pause_durations_ms": pause_durations,
            "deviation_stats": deviation_stats,
            "speed_const_flag": speed_const_flag,
            "accel_flag": accel_flag,
            "behavioural_flag": behavioural_flag,
            "trajectory": [s.dict() for s in payload.trajectory],
        }
    )

    # Mark nonce used to prevent replay
    db.mark_challenge_used(payload.challengeId)

    return models.VerifyResponse(
        passed=passed,
        reason=reason,
        coverageRatio=coverage_ratio,
        durationMs=duration_ms,
        ttlExpired=ttl_expired,
        tooFast=too_fast,
        behaviouralFlag=behavioural_flag,
        newChallengeRecommended=not passed,
        thresholds={
            "requiredCoverageRatio": config.REQUIRED_COVERAGE_RATIO,
            "tooFastMs": config.TOO_FAST_THRESHOLD_MS,
            "ttlMs": ttl_ms,
        },
        expiresAt=expires_at,
    )


@app.get("/health")
def healthcheck():
    return {"status": "ok", "time": time.time()}
