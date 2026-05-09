"""
Central configuration.
All values come from the .env file (or OS environment).
Import `cfg` wherever settings are needed - never hard-code URLs or credentials.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env", override=False)


def _bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes")


def _int(key: str, default: int = 0) -> int:
    return int(os.getenv(key, default))


class Config:
    # Browser
    BROWSER: str = os.getenv("BROWSER", "chrome").lower()
    HEADLESS: bool = _bool("HEADLESS", False)

    # URLs
    BASE_URL: str = os.getenv("BASE_URL", "https://www.greenviathai.com").rstrip("/")
    LOGIN_URL: str = "/web/login"
    SIGNUP_URL: str = "/web/signup"
    BORDER_TRIP_URL: str = "/border-trip"

    # Auth
    AUTH_METHOD: str = os.getenv("AUTH_METHOD", "google").lower()  # google | internal
    GOOGLE_EMAIL: str = os.getenv("GOOGLE_EMAIL", "")
    GOOGLE_PASSWORD: str = os.getenv("GOOGLE_PASSWORD", "")
    INTERNAL_EMAIL: str = os.getenv("INTERNAL_EMAIL", "")
    INTERNAL_PASSWORD: str = os.getenv("INTERNAL_PASSWORD", "")
    SESSION_COOKIE_FILE: Path = Path(
        os.getenv("SESSION_COOKIE_FILE", "fixtures/session_cookies.json")
    )

    # Timeouts
    IMPLICIT_WAIT: int = _int("IMPLICIT_WAIT", 5)
    EXPLICIT_WAIT: int = _int("EXPLICIT_WAIT", 20)
    PAGE_LOAD_TIMEOUT: int = _int("PAGE_LOAD_TIMEOUT", 30)
    # Pause inserted between human-style actions (destination → date →
    # passengers) so the run is visually readable. Lower it (or set 0)
    # for fast / CI runs.
    HUMAN_DELAY: float = float(os.getenv("HUMAN_DELAY", "1.2"))

    # Booking params (shared across tests) - dates target the next May 17 window.
    ROUTE: str = os.getenv("ROUTE", "Ranong")
    ROUTE_VALUE: str = os.getenv("ROUTE_VALUE", "2")  # <select> option value for Ranong
    ORIGIN: str = os.getenv("ORIGIN", "Phuket")
    ORIGIN_VALUE: str = os.getenv("ORIGIN_VALUE", "1")
    PASSENGER_COUNT: int = _int("PASSENGER_COUNT", 3)
    # The passenger panel splits passengers into adults + children.
    # Default: 2 adults + 1 child = 3 total (matches PASSENGER_COUNT).
    ADULT_COUNT: int = _int("ADULT_COUNT", 2)
    CHILD_COUNT: int = _int("CHILD_COUNT", 1)
    TRIP_DATE: str = os.getenv("TRIP_DATE", "2026-05-17")        # ISO
    TRIP_DATE_DISPLAY: str = os.getenv("TRIP_DATE_DISPLAY", "May 17")  # human

    NATIONALITY: str = "Georgia"
    NATIONALITY_VALUE: str = "78"  # Confirmed from /web/signup <select> option
    VISA_TYPE: str = "DTV 180"
    PASSPORT_EXPIRY: str = "2028-12-31"  # not earlier than 2028
    ENTRY_EXPIRY: str = "2026-05-20"     # not earlier than May 18 of the trip year

    COMFORT_SEATS: int = 2
    REGULAR_SEATS: int = 1


cfg = Config()
