import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

CATEGORIES = ["plastic", "paper", "metal", "glass", "organic"]


def _database_uri():
    """DATABASE_URL wins; else build a MySQL URL from MYSQL_* vars (password is URL-encoded);
    else fall back to local SQLite."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if os.environ.get("MYSQL_PASSWORD") is not None and os.environ.get("MYSQL_USER"):
        from urllib.parse import quote_plus

        e = os.environ
        return (
            f"mysql+pymysql://{quote_plus(e['MYSQL_USER'])}:{quote_plus(e['MYSQL_PASSWORD'])}"
            f"@{e.get('MYSQL_HOST', 'localhost')}:{e.get('MYSQL_PORT', '3306')}"
            f"/{e.get('MYSQL_DATABASE', 'smart_waste')}?charset=utf8mb4"
        )
    return "sqlite:///" + str(BASE_DIR / "instance" / "waste.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}

    MODEL_PATH = str(BASE_DIR / "ml" / "model" / "waste_cnn.keras")
    CLASS_NAMES_PATH = str(BASE_DIR / "ml" / "model" / "class_names.json")
    IMAGE_SIZE = 128
    MIN_CONFIDENCE = 0.0  # set e.g. 0.5 to reject low-confidence predictions

    CATEGORIES = CATEGORIES
    # Configurable rule: which categories count as recyclable.
    RECYCLABLE_CATEGORIES = {"plastic", "paper", "metal", "glass"}

    # Bin fullness is SIMULATED: each classified item adds an estimated volume (litres)
    # to a compartment with a configured maximum capacity (litres). No sensors are used.
    ESTIMATED_VOLUME_LITRES = {
        "plastic": 0.5,
        "paper": 0.3,
        "metal": 0.25,
        "glass": 0.6,
        "organic": 0.8,
    }
    DEFAULT_COMPARTMENT_CAPACITY = 20.0
    ALMOST_FULL_PERCENT = 70.0
    ALERT_PERCENT = 90.0

    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"  # set 1 behind HTTPS


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = str(BASE_DIR / "uploads_test")
