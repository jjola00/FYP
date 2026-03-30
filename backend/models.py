from typing import Any, Dict, List, Literal, Optional

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
    pointerType: Optional[Literal["mouse", "touch", "pen"]] = "mouse"


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
    trajectoryHash: Optional[str] = None  # Client-computed hash for binding
    clientTimingMs: Optional[float] = None  # Client-reported total duration

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
    metrics: dict = Field(default_factory=dict)
    expiresAt: float


# ─── Image CAPTCHA models ────────────────────────────────────────────────


class ImageLineDefinition(BaseModel):
    type: Literal["straight", "quadratic", "cubic"]
    points: List[List[float]]
    colour: str
    thickness: float


class ImageNewChallengeResponse(BaseModel):
    challengeId: str
    token: str
    ttlMs: int
    expiresAt: float
    lines: List[ImageLineDefinition]
    canvas: Dict[str, Any]
    instruction: str


class ImageClickCoordinate(BaseModel):
    x: float
    y: float


class ImageVerifyRequest(BaseModel):
    challengeId: str
    token: str
    clicks: List[ImageClickCoordinate]
    pointerType: Optional[Literal["mouse", "touch", "pen"]] = "mouse"


class ImageVerifyResponse(BaseModel):
    passed: bool
    reason: str
    matched: int
    expected: int
    excess: int
    tooFast: bool


# ─── Feedback models ─────────────────────────────────────────────────


class FeedbackItem(BaseModel):
    id: str
    name: Optional[str]
    category: str
    device: str
    message: str
    imageFilenames: List[str] = Field(default_factory=list)
    createdAt: float


# ─── Questionnaire models ─────────────────────────────────────────────


class QuestionnaireRequest(BaseModel):
    sessionId: str
    deviceType: str
    ageRange: str
    techComfort: int = Field(..., ge=1, le=5)
    captchaFrequency: int = Field(..., ge=1, le=5)
    captcha1Difficulty: int = Field(..., ge=1, le=5)
    captcha1Frustration: int = Field(..., ge=1, le=5)
    captcha2Difficulty: int = Field(..., ge=1, le=5)
    captcha2Frustration: int = Field(..., ge=1, le=5)
    comments: Optional[str] = None
