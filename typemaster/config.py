"""Central configuration: every tunable constant lives here."""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "TypeMaster"
APP_TAGLINE = "Type faster. Type cleaner. Beat your best."
FOUNDER_NAME = "Ritesh Kumar Singh"
FOUNDER_TITLE = "Founder & CEO"
SPLASH_SECONDS = float(os.environ.get("TYPEMASTER_SPLASH", "3"))  # boot screen length (tests set 0)
PAGES = ("Home", "Practice", "Daily", "Key Doctor", "Progress", "Rewards", "Analytics", "Leaderboard")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Override with the TYPEMASTER_DB environment variable (used by the tests).
DB_PATH = Path(os.environ.get("TYPEMASTER_DB", PROJECT_ROOT / "data" / "typemaster.db"))
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "typing_engine"

DURATIONS: tuple[int, ...] = (30, 60, 120)
DIFFICULTIES: tuple[str, ...] = ("Easy", "Medium", "Hard")

# Minimum characters of text generated per duration (enough for ~180 WPM).
TARGET_CHARS: dict[int, int] = {30: 450, 60: 900, 120: 1800}

# Scoring / validation limits
CHARS_PER_WORD = 5            # industry-standard "word" length
MAX_PLAUSIBLE_WPM = 350       # anything faster is rejected (paste / tampering)
MIN_ELAPSED_SEC = 1.0         # shorter runs are too noisy to score
ELAPSED_TOLERANCE_SEC = 3.0   # allowed client/server timing slack
MAX_SERIES_POINTS = 125       # per-second pace samples accepted per test

# Player names
NAME_MIN = 2
NAME_MAX = 20

LEADERBOARD_SIZE = 25

# Daily challenge: same text for every player, fixed setup
DAILY_DURATION = 60
DAILY_DIFFICULTY = "Medium"

# Key Doctor
MIN_KEY_ATTEMPTS = 10    # a key needs this many attempts before it can be called "weak"
MAX_WRONG_INDEXES = 2000
MODES = ("standard", "daily", "drill")

# Certificates: the secret signs certificate IDs so they can be verified. Set your own in production:
#   TYPEMASTER_CERT_SECRET=some-long-random-string
CERT_SECRET = os.environ.get("TYPEMASTER_CERT_SECRET", "typemaster-dev-secret")
ASSETS_DIR = PROJECT_ROOT / "assets"
STREAK_GOAL = 5          # the featured streak challenge
