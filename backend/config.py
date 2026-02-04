import os
from pathlib import Path


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
CHALLENGE_TTL_MS = 8_000  # give humans more slack; bots are constrained by other checks
TOO_FAST_THRESHOLD_MS = 1_000
TRAIL_VISIBLE_MS = 700
TRAIL_FADEOUT_MS = 900
REQUIRED_COVERAGE_RATIO = 0.75  # 70–80% allowed; default to 75%
MIN_SAMPLES = 20

# Peek behavior
PEEK_AHEAD_PX = 40
PEEK_BEHIND_PX = 8
PEEK_MIN_INTERVAL_MS = 100  # cap peek rate to ~10/s
PEEK_MAX_COUNT = 120
PEEK_MAX_ADVANCE_PX_PER_S = 800
PEEK_ADVANCE_MARGIN_PX = 20
PEEK_DISTANCE_FACTOR = 1.2
PROGRESS_BACKTRACK_PX = 10

# Enforcement toggles (for ablation testing)
ENFORCE_PEEK_STATE = _env_bool("ENFORCE_PEEK_STATE", True)
ENFORCE_PEEK_RATE = _env_bool("ENFORCE_PEEK_RATE", True)
ENFORCE_PEEK_DISTANCE = _env_bool("ENFORCE_PEEK_DISTANCE", True)
ENFORCE_PEEK_BUDGET = _env_bool("ENFORCE_PEEK_BUDGET", True)
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
BALLISTIC_THIRD_RATIO_MIN = 0.7  # first third should have >= this fraction of peak speed
BALLISTIC_FINAL_DECEL_MIN = 0.15  # final third speed should be at least this much slower than mid

# Hesitation detection (micro-pauses at high-curvature points)
HESITATION_PAUSE_MS_MIN = 40  # minimum pause duration to count as hesitation
HESITATION_PAUSE_MS_MAX = 200  # maximum (longer is suspicious)
HESITATION_MIN_COUNT = 1  # humans should have at least this many micro-pauses
HESITATION_CURVATURE_PCTL = 0.7  # look for pauses near high-curvature regions (top 30%)

POINTER_BEHAVIOR = {
    "mouse": {
        "max_speed_px_per_s": 2000,
        "max_avg_speed_px_per_s": 900,
        "max_backtrack_sample_ratio": 0.1,
        "min_accel_sign_changes": 2,
        "speed_const_ratio": 0.15,
        "max_accel_px_per_s2": 12000,
        "min_dt_cv": 0.08,
        "min_dd_cv": 0.08,
        "curvature_var_ratio_min": 1.15,
        "curvature_min_samples": 6,
        "ballistic_third_ratio_min": 0.7,
        "ballistic_final_decel_min": 0.15,
        "hesitation_min_count": 1,
    },
    "touch": {
        "max_speed_px_per_s": 1800,
        "max_avg_speed_px_per_s": 750,
        "max_backtrack_sample_ratio": 0.12,
        "min_accel_sign_changes": 2,
        "speed_const_ratio": 0.18,
        "max_accel_px_per_s2": 10000,
        "min_dt_cv": 0.07,
        "min_dd_cv": 0.07,
        "curvature_var_ratio_min": 1.15,
        "curvature_min_samples": 6,
        "ballistic_third_ratio_min": 0.65,
        "ballistic_final_decel_min": 0.12,
        "hesitation_min_count": 1,
    },
}

# Secret key for signing tokens (use env override in production)
SECRET_KEY = os.getenv("LINE_CAPTCHA_SECRET", "dev-secret-change-me")
