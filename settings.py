"""
settings.py
Wyckoff Pro v3
"""

from pathlib import Path

# ----------------------------
# Project
# ----------------------------

APP_NAME = "Wyckoff Pro v3"
APP_VERSION = "3.0.0"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"
EXPORT_DIR = BASE_DIR / "exports"

for folder in [DATA_DIR, CACHE_DIR, LOG_DIR, EXPORT_DIR]:
    folder.mkdir(exist_ok=True)

# ----------------------------
# Database
# ----------------------------

DATABASE_FILE = DATA_DIR / "wyckoff.db"

# ----------------------------
# Scan
# ----------------------------

DEFAULT_PERIOD = "2y"
DEFAULT_INTERVAL = "1d"

MAX_THREADS = 12

MIN_PRICE = 5.0
MIN_VOLUME = 300000
MIN_MARKET_CAP = 1_000_000_000

DEFAULT_MIN_SCORE = 60

# ----------------------------
# Indicators
# ----------------------------

EMA_FAST = 20
EMA_SLOW = 50

RSI_PERIOD = 14
ATR_PERIOD = 14
ADX_PERIOD = 14
MFI_PERIOD = 14

BB_PERIOD = 20
KC_PERIOD = 20

# ----------------------------
# AI
# ----------------------------

LOOKAHEAD_DAYS = 5

TRAIN_MIN_ROWS = 300

MODEL_FILE = DATA_DIR / "model.pkl"

# ----------------------------
# Wyckoff
# ----------------------------

WYCKOFF_WEIGHTS = {
    "compression": 20,
    "smart_money": 20,
    "volume": 15,
    "trend": 15,
    "spring": 10,
    "sos": 10,
    "lps": 5,
    "proximity": 5
}

# ----------------------------
# Portfolio
# ----------------------------

DEFAULT_RISK_PERCENT = 1.0

# ----------------------------
# Charts
# ----------------------------

CHART_HEIGHT = 900

# ----------------------------
# Export
# ----------------------------

EXPORT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ----------------------------
# Colors
# ----------------------------

BUY_COLOR = "#00C853"
WATCH_COLOR = "#FFD600"
SELL_COLOR = "#D50000"

# ----------------------------
# Debug
# ----------------------------

DEBUG = False
