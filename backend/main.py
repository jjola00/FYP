import hashlib
import json
import math
import random
import time
import uuid
from typing import Dict, List, Tuple

import fastapi
from fastapi.middleware.cors import CORSMiddleware

from . import config, db, models, path, captcha_token

app = fastapi.FastAPI(title="Ephemeral Line CAPTCHA")

# CORS: Use ALLOWED_ORIGINS env var (comma-separated) or default to localhost for dev
import os
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:9002").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

db.init_db()


def _challenge_tolerance(challenge_row: Dict, pointer_type: str) -> float:
    # Use stored per-challenge tolerance, with pen treated as touch.
    if pointer_type == "mouse":
        return float(challenge_row["tolerance_mouse"])
    return float(challenge_row["tolerance_touch"])


def _compute_trajectory_hash(trajectory: List[models.TrajectorySample], nonce: str, challenge_id: str) -> str:
    """Compute SHA-256 hash of trajectory data + nonce + challenge_id for client binding."""
    # Normalize trajectory to prevent floating point differences
    traj_str = "|".join(f"{s.x:.1f},{s.y:.1f},{s.t}" for s in trajectory)
    data = f"{traj_str}:{nonce}:{challenge_id}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]  # First 32 chars


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
    signed_token = captcha_token.sign(token_payload)

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
        claims = captcha_token.verify(payload.token)
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

    # Calculate cursor advancement since last peek
    cursor_advance = max(0.0, pos - last_pos) if last_peek_at is not None else config.PEEK_DECAY_MIN_ADVANCE_PX

    # Progressive decay: reduce lookahead if cursor hasn't advanced much
    if config.ENFORCE_PEEK_DECAY and cursor_advance < config.PEEK_DECAY_MIN_ADVANCE_PX:
        # Scale lookahead based on how much cursor advanced
        advance_ratio = cursor_advance / config.PEEK_DECAY_MIN_ADVANCE_PX
        decay_multiplier = config.PEEK_DECAY_FACTOR + (1 - config.PEEK_DECAY_FACTOR) * advance_ratio
        effective_ahead = max(config.PEEK_DECAY_MIN_PX, config.PEEK_AHEAD_PX * decay_multiplier)
    else:
        effective_ahead = config.PEEK_AHEAD_PX

    db.update_peek_progress(payload.challengeId, new_pos, now, peek_count + 1)

    ahead_polyline = path.lookahead(
        points,
        cursor,
        ahead=effective_ahead,
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
        claims = captcha_token.verify(payload.token)
    except Exception:
        raise fastapi.HTTPException(status_code=401, detail="Invalid token")
    if (
        claims.get("cid") != payload.challengeId
        or claims.get("nonce") != payload.nonce
        or claims.get("ttl") != ttl_ms
    ):
        raise fastapi.HTTPException(status_code=401, detail="Token mismatch")

    # Verify trajectory hash if provided (client binding)
    trajectory_hash_valid = True
    if config.ENFORCE_TRAJECTORY_HASH:
        if not payload.trajectoryHash:
            raise fastapi.HTTPException(status_code=400, detail="Trajectory hash required")
        expected_hash = _compute_trajectory_hash(payload.trajectory, payload.nonce, payload.challengeId)
        if payload.trajectoryHash != expected_hash:
            trajectory_hash_valid = False
            raise fastapi.HTTPException(status_code=400, detail="Trajectory hash mismatch")
    elif payload.trajectoryHash:
        # Verify if provided even when not enforced (for gradual rollout)
        expected_hash = _compute_trajectory_hash(payload.trajectory, payload.nonce, payload.challengeId)
        trajectory_hash_valid = payload.trajectoryHash == expected_hash

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
    ballistic_third_ratio_min = behaviour.get("ballistic_third_ratio_min", config.BALLISTIC_THIRD_RATIO_MIN)
    ballistic_final_decel_min = behaviour.get("ballistic_final_decel_min", config.BALLISTIC_FINAL_DECEL_MIN)
    hesitation_min_count = int(behaviour.get("hesitation_min_count", config.HESITATION_MIN_COUNT))

    path_points = json.loads(challenge_row["points_json"])
    cums = path.cumulative_lengths(path_points)
    curvatures = path.curvature_profile(path_points)
    curvature_values = [c for c in curvatures if c > 0]
    curvature_low = _percentile(curvature_values, config.CURVATURE_LOW_PCTL) if curvature_values else None
    curvature_high = _percentile(curvature_values, config.CURVATURE_HIGH_PCTL) if curvature_values else None
    curvature_contrast_rad = (
        (curvature_high - curvature_low)
        if curvature_low is not None and curvature_high is not None
        else None
    )
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
    max_jump_px = max(config.CANVAS_WIDTH_PX, config.CANVAS_HEIGHT_PX) * 0.75
    for idx, sample in enumerate(payload.trajectory):
        if idx > 0 and sample.t <= last_t:
            monotonic = False
            break
        if idx > 0:
            prev = payload.trajectory[idx - 1]
            jump_dist = ((sample.x - prev.x) ** 2 + (sample.y - prev.y) ** 2) ** 0.5
            # Only treat extremely large discontinuities as invalid; pointer events can be sparse/coalesced.
            if jump_dist > max_jump_px:
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
    coverage_ok = (
        coverage_ratio >= config.REQUIRED_COVERAGE_RATIO
        or coverage_len_ratio >= config.REQUIRED_COVERAGE_RATIO
    )
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

    too_perfect_flag = False
    if deviation_stats["mean"] is not None and deviation_stats["max"] is not None:
        min_mean_dev = max(0.25, tolerance_px * config.MIN_DEVIATION_MEAN_FRAC)
        min_max_dev = max(0.8, tolerance_px * config.MIN_DEVIATION_MAX_FRAC)
        if deviation_stats["mean"] < min_mean_dev and deviation_stats["max"] < min_max_dev:
            too_perfect_flag = True

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
        # Only enforce "sign change" expectations when speed is suspiciously constant.
        if len(accels) >= 3 and sign_changes < min_accel_sign_changes and speed_const_flag:
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
        if regularity_dt_cv is not None and regularity_dd_cv is not None:
            # Only treat as bot-like when BOTH timing and step distance are highly regular.
            # (Pointer event timing can be fairly stable for real users.)
            if regularity_dt_cv < min_dt_cv and regularity_dd_cv < min_dd_cv:
                regularity_flag = True

    curvature_check_applied = False
    curvature_check_inconclusive = True
    curvature_slowdown_ratio = None
    curvature_cv_low = None
    curvature_cv_high = None
    curvature_mean_low = None
    curvature_mean_high = None
    if (
        speed_low
        and speed_high
        and len(speed_low) >= curvature_min_samples
        and len(speed_high) >= curvature_min_samples
        and curvature_contrast_rad is not None
        and curvature_contrast_rad >= config.CURVATURE_CONTRAST_MIN_RAD
    ):
        curvature_check_applied = True
        mean_low = sum(speed_low) / len(speed_low)
        mean_high = sum(speed_high) / len(speed_high)
        curvature_mean_low = mean_low
        curvature_mean_high = mean_high
        if mean_low > 0:
            curvature_var_low = sum((s - mean_low) ** 2 for s in speed_low) / len(speed_low)
        if mean_high > 0:
            curvature_var_high = sum((s - mean_high) ** 2 for s in speed_high) / len(speed_high)
        if curvature_var_low is not None and curvature_var_high is not None:
            # Use CVs for scale invariance; then require either slowdown OR increased variability on curves.
            std_low = max(0.0, curvature_var_low) ** 0.5
            std_high = max(0.0, curvature_var_high) ** 0.5
            if mean_low > 0:
                curvature_cv_low = std_low / mean_low
            if mean_high > 0:
                curvature_cv_high = std_high / mean_high
            if mean_high > 0 and mean_low > 0:
                curvature_slowdown_ratio = mean_low / mean_high

            if curvature_slowdown_ratio is not None and curvature_slowdown_ratio >= config.CURVATURE_SLOWDOWN_RATIO_MIN:
                curvature_check_inconclusive = False
                curvature_flag = False
            # Small slowdown is common even for smooth humans; don't block on weak evidence.
            elif curvature_slowdown_ratio is not None and curvature_slowdown_ratio >= config.CURVATURE_NO_SLOWDOWN_RATIO_MAX:
                curvature_check_inconclusive = True
                curvature_flag = False
            elif curvature_cv_low is not None and curvature_cv_high is not None:
                # With little/no slowdown, require increased variability on curves.
                if (
                    curvature_cv_low <= config.CURVATURE_CV_EPS
                    and curvature_cv_high <= config.CURVATURE_CV_EPS
                ):
                    curvature_check_inconclusive = False
                    curvature_flag = True
                elif curvature_cv_high <= curvature_cv_low * curvature_var_ratio_min:
                    curvature_check_inconclusive = False
                    curvature_flag = True

    # Ballistic profile check: humans accelerate early, cruise mid, decelerate late
    ballistic_flag = False
    ballistic_first_ratio = None
    ballistic_final_ratio = None
    if len(speeds) >= 9:
        n = len(speeds)
        third = n // 3
        first_third = speeds[:third]
        mid_third = speeds[third : 2 * third]
        final_third = speeds[2 * third :]
        peak_speed = max(speeds) if speeds else 1.0
        if peak_speed > 0:
            first_max = max(first_third) if first_third else 0
            ballistic_first_ratio = first_max / peak_speed
            mid_mean = sum(mid_third) / len(mid_third) if mid_third else 0
            final_mean = sum(final_third) / len(final_third) if final_third else 0
            if mid_mean > 0:
                ballistic_final_ratio = (mid_mean - final_mean) / mid_mean
            # Flag if profile is too flat (no acceleration buildup or no deceleration)
            if (
                ballistic_first_ratio < ballistic_third_ratio_min
                and ballistic_final_ratio is not None
                and ballistic_final_ratio < ballistic_final_decel_min
            ):
                ballistic_flag = True

    # Hesitation detection: humans micro-pause at high-curvature decision points
    hesitation_flag = False
    hesitation_count = 0
    hesitation_at_curves = 0
    if dt_samples and curvature_high is not None:
        for i, dt_ms in enumerate(dt_samples):
            if config.HESITATION_PAUSE_MS_MIN <= dt_ms <= config.HESITATION_PAUSE_MS_MAX:
                hesitation_count += 1
                # Check if this pause is near a high-curvature point
                if i + 1 < len(payload.trajectory):
                    sample = payload.trajectory[i + 1]
                    pos = path.position_along_path(path_points, (sample.x, sample.y))
                    idx_pos = path.index_at_position(cums, pos)
                    if idx_pos < len(curvatures) and curvatures[idx_pos] >= curvature_high:
                        hesitation_at_curves += 1
        # Flag if no hesitations found (bots with uniform timing lack micro-pauses)
        if hesitation_count < hesitation_min_count:
            hesitation_flag = True

    behavioural_flag = (
        speed_const_flag
        or accel_flag
        or accel_sign_change_flag
        or regularity_flag
        or curvature_flag
        or too_perfect_flag
        or ballistic_flag
        or hesitation_flag
    )
    bot_score = (
        (1 if speed_const_flag else 0)
        + (1 if accel_flag else 0)
        + (1 if accel_sign_change_flag else 0)
        + (1 if speed_violation else 0)
        + (1 if regularity_flag else 0)
        + (1 if curvature_flag else 0)
        + (1 if too_perfect_flag else 0)
        + (1 if not progress_ok else 0)
        + (1 if too_fast else 0)
        + (1 if ballistic_flag else 0)
        + (1 if hesitation_flag else 0)
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
    elif not coverage_ok:
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
    elif config.ENFORCE_BALLISTIC_PROFILE and ballistic_flag and hesitation_flag:
        # Both flat velocity profile AND no hesitations is strong bot evidence
        reason = "no_ballistic_profile"
        passed = False
    elif config.ENFORCE_HESITATION and hesitation_flag and regularity_flag:
        # No micro-pauses combined with regular timing
        reason = "no_hesitation"
        passed = False
    elif config.ENFORCE_BEHAVIOURAL and too_perfect_flag:
        reason = "too_perfect"
        passed = False
    # Only block on behavioural signals when there's strong evidence (multiple signals).
    elif config.ENFORCE_BEHAVIOURAL and (
        (accel_flag and regularity_flag)  # high accel alone is fine, needs regularity too
        or (speed_const_flag and regularity_flag)
        or (accel_sign_change_flag and regularity_flag)
        or (ballistic_flag and hesitation_flag)
    ):
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
            "too_perfect_flag": too_perfect_flag,
            "bot_score": bot_score,
            "regularity_dt_cv": regularity_dt_cv,
            "regularity_dd_cv": regularity_dd_cv,
            "curvature_var_low": curvature_var_low,
            "curvature_var_high": curvature_var_high,
            "ballistic_flag": ballistic_flag,
            "ballistic_first_ratio": ballistic_first_ratio,
            "ballistic_final_ratio": ballistic_final_ratio,
            "hesitation_flag": hesitation_flag,
            "hesitation_count": hesitation_count,
            "hesitation_at_curves": hesitation_at_curves,
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
        metrics={
            "coverageLenRatio": coverage_len_ratio,
            "coverageOk": coverage_ok,
            "endDistancePx": end_distance,
            "endReached": end_reached,
            "tolerancePx": tolerance_px,
            "minDurationMs": min_duration_ms,
            "meanSpeedPxPerS": mean_speed,
            "maxSpeedPxPerS": max_speed,
            "backtrackRatio": backtrack_ratio,
            "progressOk": progress_ok,
            "speedConstFlag": speed_const_flag,
            "accelFlag": accel_flag,
            "accelSignChangeFlag": accel_sign_change_flag,
            "speedViolation": speed_violation,
            "regularityDtCv": regularity_dt_cv,
            "regularityDdCv": regularity_dd_cv,
            "regularityFlag": regularity_flag,
            "tooPerfectFlag": too_perfect_flag,
            "curvatureVarLow": curvature_var_low,
            "curvatureVarHigh": curvature_var_high,
            "curvatureMeanLow": curvature_mean_low,
            "curvatureMeanHigh": curvature_mean_high,
            "curvatureCvLow": curvature_cv_low,
            "curvatureCvHigh": curvature_cv_high,
            "curvatureSlowdownRatio": curvature_slowdown_ratio,
            "curvatureCheckApplied": curvature_check_applied,
            "curvatureCheckInconclusive": curvature_check_inconclusive,
            "curvatureContrastRad": curvature_contrast_rad,
            "peekCount": int(challenge_row["peek_count"]) if "peek_count" in row_keys and challenge_row["peek_count"] is not None else 0,
            "peekEfficiency": (
                (int(challenge_row["peek_count"]) / max(1, float(challenge_row["path_length"]) / 100))
                if "peek_count" in row_keys and challenge_row["peek_count"] is not None
                else None
            ),
            "ballisticFlag": ballistic_flag,
            "ballisticFirstRatio": ballistic_first_ratio,
            "ballisticFinalRatio": ballistic_final_ratio,
            "hesitationFlag": hesitation_flag,
            "hesitationCount": hesitation_count,
            "hesitationAtCurves": hesitation_at_curves,
        },
        expiresAt=expires_at,
    )


@app.get("/health")
def healthcheck():
    return {"status": "ok", "time": time.time()}
