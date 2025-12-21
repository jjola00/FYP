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
    nonce: str
    token: str
    startPoint: List[float]
    tolerance: dict  # display hint (rounded)
    targetCompletionMs: int
    trail: dict
    canvas: dict


class PeekRequest(BaseModel):
    challengeId: str
    nonce: str
    token: str
    cursor: List[float]


class PeekResponse(BaseModel):
    ahead: List[List[float]]
    behind: List[List[float]]
    distanceToEnd: float
    finish: Optional[List[float]] = None


class VerifyRequest(BaseModel):
    challengeId: str
    nonce: str
    token: str
    sessionId: str
    pointerType: Literal["mouse", "touch", "pen"]
    osFamily: Optional[str] = None
    browserFamily: Optional[str] = None
    devicePixelRatio: Optional[float] = None
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
    behaviouralFlag: bool = Field(False, description="True when behavioural checks (e.g., constant velocity) were tripped but not blocked.")
    newChallengeRecommended: bool
    thresholds: dict
    expiresAt: float
