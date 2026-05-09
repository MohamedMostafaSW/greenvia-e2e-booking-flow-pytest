"""
tests/conftest.py
=================
Pytest fixtures and hooks used by every test in tests/.

Fixtures (all session-scoped — the same browser carries the whole
booking flow from homepage to checkout):

    driver    — Selenium WebDriver, created once and quit at session end
    reporter  — Reporter instance; HTML report rendered on session teardown
    runner    — Runner wrapper exposing driver / pages / cfg / step helpers

Hooks:

  • Path bootstrap: makes pages/ and utils/ importable when pytest is
    invoked from any CWD.
  • Headless default: keeps the browser visible unless HEADLESS is set.
  • Incremental tests: if any test in a class marked @pytest.mark.incremental
    fails, subsequent tests in that class are skipped (since the browser
    state is broken — there's no point continuing the journey).
  • pytest_runtest_makereport: snaps a screenshot on every test failure
    and attaches it to the most recent step in the report.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# ── Path bootstrap ────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Default to a visible browser unless HEADLESS is explicitly set
os.environ.setdefault("HEADLESS", "false")

import pytest

from utils.config import cfg
from utils.driver_factory import create_driver
from utils.reporter import Reporter
from utils.runner import Runner


# ── Fixtures ──────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def reports_dir() -> Path:
    p = PROJECT_ROOT / "reports"
    p.mkdir(parents=True, exist_ok=True)
    (p / "screenshots").mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture(scope="session")
def reporter(reports_dir: Path):
    """Session-scoped Reporter; renders HTML report on teardown."""
    r = Reporter(reports_dir)
    r.set_meta(**{
        "Base URL":    cfg.BASE_URL,
        "Destination": f"{cfg.ROUTE} (value={cfg.ROUTE_VALUE})",
        "Trip date":   cfg.TRIP_DATE,
        "Passengers":  f"{cfg.ADULT_COUNT} adult(s) + {cfg.CHILD_COUNT} child(ren)",
        "Browser":     cfg.BROWSER,
        "Headless":    cfg.HEADLESS,
    })

    yield r

    # Decide overall outcome from collected step statuses
    r.run_ended = time.time()
    if any(s.status == "FAIL" for s in r.steps):
        outcome = "FAIL"
    elif any(s.status == "WARN" for s in r.steps):
        outcome = "SITE_BUG"
    elif r.steps:
        outcome = "PASS"
    else:
        outcome = "UNKNOWN"
    r.set_outcome(outcome)

    report_path = reports_dir / "main_flow_report.html"
    r.render(report_path)

    # Visible footer in stdout so the path is easy to find
    print()
    print("=" * 60)
    print(f"  HTML report → {report_path}")
    print("=" * 60)


@pytest.fixture(scope="session")
def driver():
    """Selenium WebDriver — one browser for the whole session."""
    d = create_driver()
    yield d
    try:
        d.quit()
    except Exception:
        pass


@pytest.fixture(scope="session")
def runner(driver, reporter):
    """Bundle of driver + page objects + reporter shortcuts handed to tests."""
    reporter.attach_driver(driver)
    return Runner(driver, reporter)


# ── Hook: incremental tests ───────────────────────────────────────────
# If a test in a class marked @pytest.mark.incremental fails, all
# subsequent tests in that class are skipped (their browser state is
# broken — continuing the journey would just produce noise).
def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.skip(f"previous test failed ({previousfailed.name})")
