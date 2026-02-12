import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")

# Canvas sizing
CANVAS_WIDTH_PX = 400
CANVAS_HEIGHT_PX = 400

# Path characteristics
PATH_TRAVEL_PX_MIN = 200
PATH_TRAVEL_PX_MAX = 300
MAX_GENTLE_BENDS = 2

# Timing
TARGET_COMPLETION_TIME_MS = 3000
CHALLENGE_TTL_MS = 10_000  # give humans more slack; bots are constrained by other checks
TOO_FAST_THRESHOLD_MS = 1_000
TRAIL_VISIBLE_MS = 700
TRAIL_FADEOUT_MS = 900
REQUIRED_COVERAGE_RATIO = 0.75  # 70–80% allowed; default to 75%
MIN_SAMPLES = 20

# Peek behavior
PEEK_AHEAD_PX = 90
PEEK_BEHIND_PX = 12
PEEK_MIN_INTERVAL_MS = 80  # cap peek rate to ~12/s
PEEK_MAX_COUNT = 200
PEEK_MAX_ADVANCE_PX_PER_S = 1200
PEEK_ADVANCE_MARGIN_PX = 35
PEEK_DISTANCE_FACTOR = 1.2
PROGRESS_BACKTRACK_PX = 10

# Peek decay - reduce lookahead if cursor hasn't advanced much
PEEK_DECAY_MIN_ADVANCE_PX = 10  # need this much advance to get full lookahead
PEEK_DECAY_FACTOR = 0.6  # multiply lookahead by this when no advance
PEEK_DECAY_MIN_PX = 30  # minimum lookahead even with full decay
PEEK_EFFICIENCY_WARN_RATIO = 3.0  # warn if peeks/distance exceeds this

# Enforcement toggles (for ablation testing)
ENFORCE_PEEK_STATE = _env_bool("ENFORCE_PEEK_STATE", True)
ENFORCE_PEEK_RATE = _env_bool("ENFORCE_PEEK_RATE", True)
ENFORCE_PEEK_DISTANCE = _env_bool("ENFORCE_PEEK_DISTANCE", True)
ENFORCE_PEEK_BUDGET = _env_bool("ENFORCE_PEEK_BUDGET", True)
ENFORCE_PEEK_DECAY = _env_bool("ENFORCE_PEEK_DECAY", True)
ENFORCE_TRAJECTORY_HASH = _env_bool("ENFORCE_TRAJECTORY_HASH", False)  # Enable after frontend update
CLIENT_TIMING_TOLERANCE_MS = 500  # Allow 500ms clock skew between client/server timing
ENFORCE_MONOTONIC_PATH = _env_bool("ENFORCE_MONOTONIC_PATH", True)
ENFORCE_SPEED_LIMITS = _env_bool("ENFORCE_SPEED_LIMITS", True)
ENFORCE_MIN_DURATION = _env_bool("ENFORCE_MIN_DURATION", True)
ENFORCE_REGULARITY = _env_bool("ENFORCE_REGULARITY", True)
ENFORCE_CURVATURE_ADAPTATION = _env_bool("ENFORCE_CURVATURE_ADAPTATION", True)
ENFORCE_BEHAVIOURAL = _env_bool("ENFORCE_BEHAVIOURAL", True)
ENFORCE_BALLISTIC_PROFILE = _env_bool("ENFORCE_BALLISTIC_PROFILE", True)
ENFORCE_HESITATION = _env_bool("ENFORCE_HESITATION", True)

# Pointer profiles
POINTER_CONFIG = {
    "mouse": {"tolerance_px": 20, "line_thickness_px": 3},
    "touch": {"tolerance_px": 30, "line_thickness_px": 6},
}

# Per-challenge tolerance jitter
TOLERANCE_JITTER_MOUSE_PX = 2
TOLERANCE_JITTER_TOUCH_PX = 3

# Finish reveal threshold (distance to end of path in px)
FINISH_REVEAL_PX = 40

FALLBACK_AFTER_FAILURES = 3

# Storage
DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "captcha.db"

# Security
# SECRET_KEY used for HMAC tokens (set via env in production)
SECRET_KEY = "change-me-to-a-secret-key"

# Behavioural thresholds (fallbacks)
SPEED_CONSTANTITY_RATIO = 0.08  # std/mean below this is suspiciously constant
MAX_ACCEL_PX_PER_S2 = 12000  # coarse cap for unrealistic acceleration spikes
MAX_SPEED_PX_PER_S = 2000  # cap on instantaneous speed
MAX_AVG_SPEED_PX_PER_S = 800  # cap on average speed (min duration)
MAX_BACKTRACK_SAMPLE_RATIO = 0.1
MIN_ACCEL_SIGN_CHANGES = 1
CURVATURE_LOW_PCTL = 0.3
CURVATURE_HIGH_PCTL = 0.7
CURVATURE_VAR_RATIO_MIN = 1.15
CURVATURE_MIN_SAMPLES = 6
CURVATURE_SLOWDOWN_RATIO_MIN = 1.08  # mean_low / mean_high minimum to consider "slowing on curves"
CURVATURE_CV_EPS = 0.03  # treat CV below this as "near-constant"
CURVATURE_NO_SLOWDOWN_RATIO_MAX = 1.04  # below this is "no slowdown"
CURVATURE_CONTRAST_MIN_RAD = 0.06  # below this, curvature buckets are too similar to conclude
MIN_DEVIATION_MEAN_FRAC = 0.02  # mean deviation must not be *too* perfect (as a fraction of tolerance)
MIN_DEVIATION_MAX_FRAC = 0.06  # max deviation must not be *too* perfect (as a fraction of tolerance)

# Ballistic profile thresholds (human velocity curve: accel -> cruise -> decel)
BALLISTIC_THIRD_RATIO_MIN = 0.5  # first third should have >= this fraction of peak speed (relaxed)
BALLISTIC_FINAL_DECEL_MIN = 0.08  # final third speed should be at least this much slower than mid (relaxed)

# Hesitation detection (micro-pauses at high-curvature points)
HESITATION_PAUSE_MS_MIN = 40  # minimum pause duration to count as hesitation
HESITATION_PAUSE_MS_MAX = 200  # maximum (longer is suspicious)
HESITATION_MIN_COUNT = 0  # disabled for now - some humans trace smoothly without pauses
HESITATION_CURVATURE_PCTL = 0.7  # look for pauses near high-curvature regions (top 30%)

POINTER_BEHAVIOR = {
    "mouse": {
        "max_speed_px_per_s": 2000,
        "max_avg_speed_px_per_s": 900,
        "max_backtrack_sample_ratio": 0.1,
        "min_accel_sign_changes": 2,
        "speed_const_ratio": 0.15,
        "max_accel_px_per_s2": 12000,
        "min_dt_cv": 0.05,
        "min_dd_cv": 0.05,
        "curvature_var_ratio_min": 1.15,
        "curvature_min_samples": 6,
        "ballistic_third_ratio_min": 0.5,
        "ballistic_final_decel_min": 0.08,
        "hesitation_min_count": 0,
    },
    "touch": {
        "max_speed_px_per_s": 1800,
        "max_avg_speed_px_per_s": 750,
        "max_backtrack_sample_ratio": 0.12,
        "min_accel_sign_changes": 2,
        "speed_const_ratio": 0.18,
        "max_accel_px_per_s2": 10000,
        "min_dt_cv": 0.04,
        "min_dd_cv": 0.04,
        "curvature_var_ratio_min": 1.15,
        "curvature_min_samples": 6,
        "ballistic_third_ratio_min": 0.45,
        "ballistic_final_decel_min": 0.06,
        "hesitation_min_count": 0,
    },
}

# Secret key for signing tokens (use env override in production)
SECRET_KEY = os.getenv("LINE_CAPTCHA_SECRET", "dev-secret-change-me")

# ─── Image CAPTCHA (line intersection click challenge) ───────────
IMAGE_CANVAS_WIDTH_PX = 400
IMAGE_CANVAS_HEIGHT_PX = 400
IMAGE_CANVAS_MARGIN_PX = 30  # keep line endpoints away from edges
IMAGE_INTERSECTION_MARGIN_PX = 10  # filter intersections too close to edges

IMAGE_LINE_THICKNESS_MIN = 2.0
IMAGE_LINE_THICKNESS_MAX = 5.0

IMAGE_CLICK_TOLERANCE_PX = int(os.getenv("IMAGE_CLICK_TOLERANCE_PX", "15"))  # how close a click must be to count

# Timing — TTL is configurable; TODO: match line CAPTCHA once confirmed
IMAGE_CHALLENGE_TTL_MS = int(os.getenv("IMAGE_CAPTCHA_TTL_MS", "30000"))
IMAGE_MIN_SOLVE_TIME_MS = int(os.getenv("IMAGE_MIN_SOLVE_MS", "800"))  # below this is bot-like
ENFORCE_IMAGE_MIN_SOLVE = _env_bool("ENFORCE_IMAGE_MIN_SOLVE", True)

# Geometry computation
IMAGE_BEZIER_SAMPLE_RESOLUTION = int(os.getenv("IMAGE_BEZIER_SAMPLE_RESOLUTION", "500"))
IMAGE_INTERSECTION_CLUSTER_RADIUS_PX = float(os.getenv("IMAGE_INTERSECTION_CLUSTER_RADIUS_PX", "3.0"))

# Generation retry budget
IMAGE_MAX_GENERATION_RETRIES = int(os.getenv("IMAGE_MAX_GENERATION_RETRIES", "50"))
