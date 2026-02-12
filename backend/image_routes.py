"""
Ephemeral Image CAPTCHA — API Routes

POST /captcha/image/generate  → issue a new challenge
POST /captcha/image/validate  → verify user clicks
"""

import json
import time
import uuid

from fastapi import APIRouter, HTTPException

from . import captcha_token, config, db
from . import image_challenge as gen
from . import image_validator as val
from . import models

router = APIRouter(prefix="/captcha/image", tags=["image-captcha"])


@router.post("/generate", response_model=models.ImageNewChallengeResponse)
def generate() -> models.ImageNewChallengeResponse:
    """
    Generate a new image CAPTCHA challenge.

    Returns line definitions and canvas config to the client.
    Intersection coordinates are stored server-side only.
    """
    challenge = gen.generate_challenge()
    client = challenge["client_data"]
    server = challenge["server_data"]

    challenge_id = uuid.uuid4().hex
    ttl_ms = config.IMAGE_CHALLENGE_TTL_MS
    now = time.time()
    expires_at = now + ttl_ms / 1000.0

    # Sign a token binding this challenge
    token_payload = {
        "cid": challenge_id,
        "ttl": ttl_ms,
        "iat": now,
        "type": "image",
    }
    token = captcha_token.sign(token_payload)

    # Persist server-side (intersections never leave the server)
    db.save_image_challenge(
        challenge_id=challenge_id,
        intersections=server["intersections"],
        num_intersections=server["numIntersections"],
        ttl_ms=ttl_ms,
    )

    return models.ImageNewChallengeResponse(
        challengeId=challenge_id,
        token=token,
        ttlMs=ttl_ms,
        expiresAt=expires_at,
        lines=[models.ImageLineDefinition(**l) for l in client["lines"]],
        canvas=client["canvas"],
        instruction=client["instruction"],
        numIntersections=client["numIntersections"],
    )


@router.post("/validate", response_model=models.ImageVerifyResponse)
def validate(req: models.ImageVerifyRequest) -> models.ImageVerifyResponse:
    """
    Validate user clicks against stored intersection coordinates.

    The token is verified, TTL is checked, and clicks are matched
    against ground-truth intersections within a tolerance radius.
    The challenge is consumed after one attempt (pass or fail).
    """
    # ── Token verification ───────────────────────────────────────
    try:
        payload = captcha_token.verify(req.token)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid token")

    challenge_id = payload.get("cid")
    if challenge_id != req.challengeId:
        raise HTTPException(status_code=400, detail="token/challenge mismatch")

    # ── Load challenge from DB ───────────────────────────────────
    row = db.get_image_challenge(challenge_id)
    if row is None:
        raise HTTPException(status_code=404, detail="challenge not found")

    if row["used"]:
        raise HTTPException(status_code=410, detail="challenge already used")

    # ── TTL check ────────────────────────────────────────────────
    created_at = row["created_at"]
    ttl_ms = row["ttl_ms"]
    now = time.time()
    elapsed_ms = (now - created_at) * 1000.0

    if elapsed_ms > ttl_ms:
        db.mark_image_challenge_used(challenge_id)
        return models.ImageVerifyResponse(
            passed=False,
            reason="challenge expired",
            matched=0,
            expected=row["num_intersections"],
            excess=len(req.clicks),
            tooFast=False,
        )

    # ── Mark as used (one-shot: pass or fail) ────────────────────
    db.mark_image_challenge_used(challenge_id)

    # ── Validate clicks ──────────────────────────────────────────
    intersections = json.loads(row["intersections_json"])
    clicks = [{"x": c.x, "y": c.y} for c in req.clicks]

    result = val.validate_clicks(
        clicks=clicks,
        intersections=intersections,
        solve_time_ms=elapsed_ms,
    )

    # ── Log attempt ─────────────────────────────────────────────
    db.save_image_attempt({
        "attempt_id": uuid.uuid4().hex,
        "challenge_id": challenge_id,
        "num_lines": 0,  # line count not stored in DB schema
        "num_intersections": row["num_intersections"],
        "num_clicks": len(req.clicks),
        "matched": result["matched"],
        "excess": result["excess"],
        "passed": result["passed"],
        "reason": result["reason"],
        "solve_time_ms": elapsed_ms,
        "too_fast": result["too_fast"],
        "clicks": [{"x": c.x, "y": c.y} for c in req.clicks],
    })

    return models.ImageVerifyResponse(
        passed=result["passed"],
        reason=result["reason"],
        matched=result["matched"],
        expected=result["expected"],
        excess=result["excess"],
        tooFast=result["too_fast"],
    )
