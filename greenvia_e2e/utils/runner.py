"""
Runner
======
Tiny wrapper handed to a test as a fixture. Bundles the WebDriver,
the page objects, the central config, and Reporter shortcuts so the
test body stays free of any wiring code.

    def test_open_homepage(runner):
        with runner.step("Open homepage"):
            runner.home.open(runner.cfg.BASE_URL)
            runner.snap("homepage")
"""
from __future__ import annotations

from contextlib import contextmanager

from pages.catalog_page import CatalogPage
from pages.home_page import HomePage
from pages.passenger_forms_page import PassengerFormsPage
from pages.signup_popup_page import SignUpPopupPage
from utils.config import cfg
from utils.reporter import Reporter
from utils.wait_helpers import wait_until_fully_loaded, wait_for_dom_stable


class Runner:
    """Context handed to tests — exposes pages + reporter + config."""

    def __init__(self, driver, reporter: Reporter):
        self.driver = driver
        self.reporter = reporter
        self.cfg = cfg                  # config values: cfg.BASE_URL, cfg.ROUTE, …
        # Page objects
        self.home    = HomePage(driver)
        self.catalog = CatalogPage(driver)
        self.forms   = PassengerFormsPage(driver)
        self.signup  = SignUpPopupPage(driver)

    # ── Reporter passthroughs ─────────────────────────────────────────
    @contextmanager
    def step(self, name: str):
        with self.reporter.step(name) as s:
            yield s

    def snap(self, label: str = "") -> str:
        return self.reporter.attach_screenshot(label)

    def note(self, text: str) -> None:
        self.reporter.note(text)

    def wait_until_loaded(self) -> None:
        wait_until_fully_loaded(self.driver)
        wait_for_dom_stable(self.driver)

