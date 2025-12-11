import json
import time
import uuid
from typing import Dict, List, Tuple

import fastapi
from fastapi.middleware.cors import CORSMiddleware

from . import config, db, models, path

app = fastapi.FastAPI(title="Ephemeral Line CAPTCHA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


def _pick_tolerance(pointer_type: str) -> int:
    if pointer_type == "mouse":
        return config.POINTER_CONFIG["mouse"]["tolerance_px"]
    # treat pen same as touch
    return config.POINTER_CONFIG["touch"]["tolerance_px"]


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

    db.save_challenge(
        challenge_id=challenge_id,
        seed=seed,
        points=[[float(f"{x:.2f}"), float(f"{y:.2f}")] for x, y in points],
        path_length=length,
        ttl_ms=ttl_ms,
    )

    tolerance = {
        "mouse": _pick_tolerance("mouse"),
        "touch": _pick_tolerance("touch"),
    }

    return models.NewChallengeResponse(
        challengeId=challenge_id,
        ttlMs=ttl_ms,
        expiresAt=expires_at,
        pathSeed=seed,
        pathLengthPx=length,
        points=[[float(f"{x:.2f}"), float(f"{y:.2f}")] for x, y in points],
        canvas={"width": config.CANVAS_WIDTH_PX, "height": config.CANVAS_HEIGHT_PX},
        tolerance=tolerance,
        targetCompletionMs=config.TARGET_COMPLETION_TIME_MS,
        trail={
            "visibleMs": config.TRAIL_VISIBLE_MS,
            "fadeoutMs": config.TRAIL_FADEOUT_MS,
        },
    )


@app.post("/captcha/line/verify", response_model=models.VerifyResponse)
def verify_attempt(payload: models.VerifyRequest):
    challenge_row = db.get_challenge(payload.challengeId)
    if not challenge_row:
        raise fastapi.HTTPException(status_code=404, detail="Unknown challenge")

    created_at = float(challenge_row["created_at"])
    ttl_ms = int(challenge_row["ttl_ms"])
    expires_at = created_at + ttl_ms / 1000.0
    now = time.time()
    ttl_expired = now > expires_at

    tolerance_px = _pick_tolerance(payload.pointerType)
    path_points = json.loads(challenge_row["points_json"])
    coverage_hits = 0
    for sample in payload.trajectory:
        dist = path.min_distance_to_polyline((sample.x, sample.y), path_points)
        if dist <= tolerance_px:
            coverage_hits += 1
    coverage_ratio = coverage_hits / len(payload.trajectory)

    duration_ms = payload.trajectory[-1].t - payload.trajectory[0].t
    too_fast = duration_ms < config.TOO_FAST_THRESHOLD_MS

    mean_speed, max_speed = _speed_stats(payload.trajectory)
    pause_count, pause_durations = _pause_stats(payload.trajectory)
    deviation_stats = {"mean": None, "max": None}
    deviations = []
    for sample in payload.trajectory:
        deviations.append(path.min_distance_to_polyline((sample.x, sample.y), path_points))
    if deviations:
        deviation_stats["mean"] = sum(deviations) / len(deviations)
        deviation_stats["max"] = max(deviations)

    if ttl_expired:
        reason = "timeout"
        passed = False
    elif too_fast:
        reason = "too_fast"
        passed = False
    elif coverage_ratio < config.REQUIRED_COVERAGE_RATIO:
        reason = "low_coverage"
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
            "path_seed": challenge_row["seed"],
            "path_length_px": float(challenge_row["path_length"]),
            "tolerance_px": tolerance_px,
            "ttl_ms": ttl_ms,
            "started_at": payload.trajectory[0].t,
            "ended_at": payload.trajectory[-1].t,
            "duration_ms": duration_ms,
            "outcome_reason": reason,
            "coverage_ratio": coverage_ratio,
            "mean_speed": mean_speed,
            "max_speed": max_speed,
            "pause_count": pause_count,
            "pause_durations_ms": pause_durations,
            "deviation_stats": deviation_stats,
            "trajectory": [s.dict() for s in payload.trajectory],
        }
    )

    return models.VerifyResponse(
        passed=passed,
        reason=reason,
        coverageRatio=coverage_ratio,
        durationMs=duration_ms,
        ttlExpired=ttl_expired,
        tooFast=too_fast,
        newChallengeRecommended=not passed,
        thresholds={
            "requiredCoverageRatio": config.REQUIRED_COVERAGE_RATIO,
            "tooFastMs": config.TOO_FAST_THRESHOLD_MS,
            "ttlMs": ttl_ms,
        },
    )


@app.get("/health")
def healthcheck():
    return {"status": "ok", "time": time.time()}
