import os
from pathlib import Path

# Canvas sizing
CANVAS_WIDTH_PX = 400
CANVAS_HEIGHT_PX = 400

# Path characteristics
PATH_TRAVEL_PX_MIN = 200
PATH_TRAVEL_PX_MAX = 300
MAX_GENTLE_BENDS = 2

# Timing
TARGET_COMPLETION_TIME_MS = 3000
CHALLENGE_TTL_MS = 12_000  # acceptable range 10–15s
TOO_FAST_THRESHOLD_MS = 1_000
TRAIL_VISIBLE_MS = 400
TRAIL_FADEOUT_MS = 600
REQUIRED_COVERAGE_RATIO = 0.75  # 70–80% allowed; default to 75%
MIN_SAMPLES = 20

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

# Behavioural thresholds
SPEED_CONSTANTITY_RATIO = 0.08  # std/mean below this is suspiciously constant
MAX_ACCEL_PX_PER_S2 = 12000  # coarse cap for unrealistic acceleration spikes

# Secret key for signing tokens (use env override in production)
SECRET_KEY = os.getenv("LINE_CAPTCHA_SECRET", "dev-secret-change-me")
