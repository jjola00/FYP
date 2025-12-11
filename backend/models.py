from typing import List, Literal, Optional

from pydantic import BaseModel, Field, validator

from . import config


class TrajectorySample(BaseModel):
    x: float
    y: float
    t: int = Field(..., description="Client timestamp in ms (monotonic or epoch)")


class NewChallengeResponse(BaseModel):
    challengeId: str
    ttlMs: int
    expiresAt: float
    pathSeed: str
    pathLengthPx: float
    points: List[List[float]]
    canvas: dict
    tolerance: dict
    targetCompletionMs: int
    trail: dict


class VerifyRequest(BaseModel):
    challengeId: str
    sessionId: str
    pointerType: Literal["mouse", "touch", "pen"]
    osFamily: Optional[str] = None
    browserFamily: Optional[str] = None
    trajectory: List[TrajectorySample]

    @validator("trajectory")
    def trajectory_has_samples(cls, v: List[TrajectorySample]) -> List[TrajectorySample]:
        if len(v) < 2:
            raise ValueError("trajectory requires at least two samples")
        return v


class VerifyResponse(BaseModel):
    passed: bool
    reason: str
    coverageRatio: float
    durationMs: float
    ttlExpired: bool
    tooFast: bool
    newChallengeRecommended: bool
    thresholds: dict
