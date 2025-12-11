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

# Pointer profiles
POINTER_CONFIG = {
    "mouse": {"tolerance_px": 20, "line_thickness_px": 3},
    "touch": {"tolerance_px": 30, "line_thickness_px": 6},
}

FALLBACK_AFTER_FAILURES = 3

# Storage
DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "captcha.db"
