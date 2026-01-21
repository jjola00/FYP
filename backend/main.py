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


def _pointer_behaviour(pointer_type: str) -> Dict[str, float]:
    key = "mouse" if pointer_type == "mouse" else "touch"
    return config.POINTER_BEHAVIOR.get(key, {})


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    idx = int(pct * (len(values_sorted) - 1))
    return values_sorted[max(0, min(idx, len(values_sorted) - 1))]


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
    now = time.time()
    last_peek_at = float(challenge_row["last_peek_at"]) if challenge_row["last_peek_at"] else None
    if config.ENFORCE_PEEK_RATE and last_peek_at is not None:
        since_ms = (now - last_peek_at) * 1000.0
        if since_ms < config.PEEK_MIN_INTERVAL_MS:
            raise fastapi.HTTPException(status_code=429, detail="Peek rate limit")

    peek_count = int(challenge_row["peek_count"]) if "peek_count" in row_keys and challenge_row["peek_count"] is not None else 0
    if config.ENFORCE_PEEK_BUDGET and peek_count >= config.PEEK_MAX_COUNT:
        raise fastapi.HTTPException(status_code=429, detail="Peek budget exceeded")

    cursor = (payload.cursor[0], payload.cursor[1])
    pos, dist = path.position_and_distance(points, cursor)
    last_pos = float(challenge_row["peek_pos"]) if "peek_pos" in row_keys and challenge_row["peek_pos"] is not None else 0.0

    if config.ENFORCE_PEEK_DISTANCE:
        tol_mouse = (
            float(challenge_row["tolerance_mouse"])
            if "tolerance_mouse" in row_keys and challenge_row["tolerance_mouse"] is not None
            else config.POINTER_CONFIG["mouse"]["tolerance_px"]
        )
        tol_touch = (
            float(challenge_row["tolerance_touch"])
            if "tolerance_touch" in row_keys and challenge_row["tolerance_touch"] is not None
            else config.POINTER_CONFIG["touch"]["tolerance_px"]
        )
        max_tol = max(tol_mouse, tol_touch)
        if dist > max_tol * config.PEEK_DISTANCE_FACTOR:
            db.update_peek_progress(payload.challengeId, last_pos, now, peek_count + 1)
            return models.PeekResponse(
                ahead=[],
                behind=[],
                distanceToEnd=float(f"{path.distance_to_end(points, cursor):.2f}"),
                finish=None,
            )

    if config.ENFORCE_PEEK_STATE and last_peek_at is not None:
        delta_s = max(0.001, now - last_peek_at)
        max_advance = config.PEEK_MAX_ADVANCE_PX_PER_S * delta_s + config.PEEK_ADVANCE_MARGIN_PX
        if pos > last_pos + max_advance:
            raise fastapi.HTTPException(status_code=400, detail="Peek jump too far")
        if pos < last_pos - config.PROGRESS_BACKTRACK_PX:
            raise fastapi.HTTPException(status_code=400, detail="Peek backtrack too far")

    new_pos = max(last_pos, pos)
    db.update_peek_progress(payload.challengeId, new_pos, now, peek_count + 1)

    ahead_polyline = path.lookahead(
        points,
        cursor,
        ahead=config.PEEK_AHEAD_PX,
        behind=config.PEEK_BEHIND_PX,
    )
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
    behaviour = _pointer_behaviour(payload.pointerType)
    speed_const_ratio = behaviour.get("speed_const_ratio", config.SPEED_CONSTANTITY_RATIO)
    max_accel = behaviour.get("max_accel_px_per_s2", config.MAX_ACCEL_PX_PER_S2)
    max_speed_limit = behaviour.get("max_speed_px_per_s", config.MAX_SPEED_PX_PER_S)
    max_avg_speed_limit = behaviour.get("max_avg_speed_px_per_s", config.MAX_AVG_SPEED_PX_PER_S)
    max_backtrack_ratio = behaviour.get("max_backtrack_sample_ratio", config.MAX_BACKTRACK_SAMPLE_RATIO)
    min_accel_sign_changes = behaviour.get("min_accel_sign_changes", config.MIN_ACCEL_SIGN_CHANGES)
    min_dt_cv = behaviour.get("min_dt_cv", 0.0)
    min_dd_cv = behaviour.get("min_dd_cv", 0.0)
    curvature_var_ratio_min = behaviour.get("curvature_var_ratio_min", config.CURVATURE_VAR_RATIO_MIN)
    curvature_min_samples = int(behaviour.get("curvature_min_samples", config.CURVATURE_MIN_SAMPLES))

    path_points = json.loads(challenge_row["points_json"])
    cums = path.cumulative_lengths(path_points)
    curvatures = path.curvature_profile(path_points)
    curvature_values = [c for c in curvatures if c > 0]
    curvature_low = _percentile(curvature_values, config.CURVATURE_LOW_PCTL) if curvature_values else None
    curvature_high = _percentile(curvature_values, config.CURVATURE_HIGH_PCTL) if curvature_values else None
    coverage_hits = 0
    monotonic = True
    jumps_ok = True
    min_samples = len(payload.trajectory) >= config.MIN_SAMPLES
    backtrack_samples = 0
    last_t = payload.trajectory[0].t
    total_seg_len = 0.0
    covered_seg_len = 0.0
    speeds: List[float] = []
    accels: List[float] = []
    speed_low: List[float] = []
    speed_high: List[float] = []
    dt_samples: List[float] = []
    dd_samples: List[float] = []
    last_pos = None
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
            dt_ms = sample.t - prev.t
            dt_s = max(0.001, dt_ms / 1000.0)
            speed = jump_dist / dt_s
            speeds.append(speed)
            if dt_ms > 0:
                dt_samples.append(float(dt_ms))
            dd_samples.append(float(jump_dist))
            if len(speeds) > 1:
                accels.append((speeds[-1] - speeds[-2]) / dt_s)
            if (
                path.min_distance_to_polyline((sample.x, sample.y), path_points) <= tolerance_px
                and path.min_distance_to_polyline((prev.x, prev.y), path_points) <= tolerance_px
            ):
                covered_seg_len += jump_dist
        pos = path.position_along_path(path_points, (sample.x, sample.y))
        if curvature_low is not None and curvature_high is not None and idx > 0:
            idx_pos = path.index_at_position(cums, pos)
            curvature = curvatures[idx_pos]
            if curvature >= curvature_high:
                speed_high.append(speeds[-1])
            elif curvature <= curvature_low:
                speed_low.append(speeds[-1])
        if last_pos is None:
            last_pos = pos
        else:
            if pos + config.PROGRESS_BACKTRACK_PX < last_pos:
                backtrack_samples += 1
            else:
                last_pos = max(last_pos, pos)
        last_t = sample.t

    for sample in payload.trajectory:
        dist = path.min_distance_to_polyline((sample.x, sample.y), path_points)
        if dist <= tolerance_px:
            coverage_hits += 1
    coverage_ratio = coverage_hits / len(payload.trajectory)
    coverage_len_ratio = covered_seg_len / total_seg_len if total_seg_len > 0 else 0.0
    backtrack_ratio = backtrack_samples / len(payload.trajectory)
    progress_ok = True
    if config.ENFORCE_MONOTONIC_PATH:
        progress_ok = backtrack_ratio <= max_backtrack_ratio

    duration_ms = payload.trajectory[-1].t - payload.trajectory[0].t
    min_duration_ms = config.TOO_FAST_THRESHOLD_MS
    if config.ENFORCE_MIN_DURATION:
        path_length = float(challenge_row["path_length"])
        min_duration_ms = max(min_duration_ms, (path_length / max_avg_speed_limit) * 1000.0)
    too_fast = duration_ms < min_duration_ms
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
    speed_violation = False
    accel_sign_change_flag = False
    regularity_flag = False
    regularity_dt_cv = None
    regularity_dd_cv = None
    curvature_flag = False
    curvature_var_low = None
    curvature_var_high = None
    if speeds and mean_speed > 0:
        mean_s = sum(speeds) / len(speeds)
        var_s = sum((s - mean_s) ** 2 for s in speeds) / len(speeds)
        std_s = var_s ** 0.5
        if std_s / mean_s < speed_const_ratio:
            speed_const_flag = True
    if accels:
        max_accel_seen = max(abs(a) for a in accels)
        if max_accel_seen > max_accel:
            accel_flag = True
        prev_sign = 0
        sign_changes = 0
        for accel in accels:
            sign = 1 if accel > 0 else -1 if accel < 0 else 0
            if sign and prev_sign and sign != prev_sign:
                sign_changes += 1
            if sign:
                prev_sign = sign
        if len(accels) >= 3 and sign_changes < min_accel_sign_changes:
            accel_sign_change_flag = True
    if config.ENFORCE_SPEED_LIMITS and max_speed > max_speed_limit:
        speed_violation = True
    if dt_samples and dd_samples:
        mean_dt = sum(dt_samples) / len(dt_samples)
        mean_dd = sum(dd_samples) / len(dd_samples)
        if mean_dt > 0:
            var_dt = sum((d - mean_dt) ** 2 for d in dt_samples) / len(dt_samples)
            regularity_dt_cv = (var_dt ** 0.5) / mean_dt
        if mean_dd > 0:
            var_dd = sum((d - mean_dd) ** 2 for d in dd_samples) / len(dd_samples)
            regularity_dd_cv = (var_dd ** 0.5) / mean_dd
        if (
            regularity_dt_cv is not None
            and regularity_dd_cv is not None
            and regularity_dt_cv < min_dt_cv
            and regularity_dd_cv < min_dd_cv
        ):
            regularity_flag = True

    if speed_low and speed_high and len(speed_low) >= curvature_min_samples and len(speed_high) >= curvature_min_samples:
        mean_low = sum(speed_low) / len(speed_low)
        mean_high = sum(speed_high) / len(speed_high)
        if mean_low > 0:
            curvature_var_low = sum((s - mean_low) ** 2 for s in speed_low) / len(speed_low)
        if mean_high > 0:
            curvature_var_high = sum((s - mean_high) ** 2 for s in speed_high) / len(speed_high)
        if curvature_var_low is not None and curvature_var_high is not None:
            if curvature_var_low <= 1e-6 and curvature_var_high <= 1e-6:
                curvature_flag = True
            elif curvature_var_high <= curvature_var_low * curvature_var_ratio_min:
                curvature_flag = True

    behavioural_flag = speed_const_flag or accel_flag or accel_sign_change_flag
    bot_score = (
        (1 if speed_const_flag else 0)
        + (1 if accel_flag else 0)
        + (1 if accel_sign_change_flag else 0)
        + (1 if speed_violation else 0)
        + (1 if regularity_flag else 0)
        + (1 if curvature_flag else 0)
        + (1 if not progress_ok else 0)
        + (1 if too_fast else 0)
    )
    if ttl_expired:
        reason = "timeout"
        passed = False
    elif not min_samples:
        reason = "insufficient_samples"
        passed = False
    elif not monotonic:
        reason = "non_monotonic_time"
        passed = False
    elif not jumps_ok:
        reason = "jump_detected"
        passed = False
    elif config.ENFORCE_MONOTONIC_PATH and not progress_ok:
        reason = "non_monotonic_path"
        passed = False
    elif config.ENFORCE_SPEED_LIMITS and speed_violation:
        reason = "speed_violation"
        passed = False
    elif not end_reached:
        reason = "incomplete"
        passed = False
    elif coverage_len_ratio < config.REQUIRED_COVERAGE_RATIO:
        reason = "low_coverage"
        passed = False
    elif coverage_ratio < config.REQUIRED_COVERAGE_RATIO:
        reason = "low_coverage"
        passed = False
    elif too_fast:
        reason = "too_fast"
        passed = False
    elif config.ENFORCE_REGULARITY and regularity_flag:
        reason = "regularity"
        passed = False
    elif config.ENFORCE_CURVATURE_ADAPTATION and curvature_flag:
        reason = "no_curvature_adaptation"
        passed = False
    elif config.ENFORCE_BEHAVIOURAL and behavioural_flag:
        reason = "behavioural"
        passed = False
    else:
        reason = "success"
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
            "speed_violation": speed_violation,
            "bot_score": bot_score,
            "regularity_dt_cv": regularity_dt_cv,
            "regularity_dd_cv": regularity_dd_cv,
            "curvature_var_low": curvature_var_low,
            "curvature_var_high": curvature_var_high,
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
