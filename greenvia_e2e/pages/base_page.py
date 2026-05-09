"""
BasePage
========
Shared utilities for every page object — click techniques, retry-loops
and full-page-load waits. The site uses several <div tabindex="0">
custom widgets whose JS click handlers don't always respond to a plain
Selenium .click(); these helpers cycle through six techniques so we
can hit the one that actually fires the handler.
"""
from __future__ import annotations

import logging
import time
from typing import Tuple

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils import wait_helpers as wh

log = logging.getLogger(__name__)


# Six different click techniques the popup-opener / force-click cycles
# through. Each is `(label, function_taking_(driver, element))`.
CLICK_TECHNIQUES = [
    ("native click",
     lambda d, e: e.click()),
    ("ActionChains click",
     lambda d, e: ActionChains(d).move_to_element(e).pause(0.2).click().perform()),
    ("dispatchEvent mouse",
     lambda d, e: d.execute_script(
         "const el=arguments[0];"
         "el.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window}));"
         "el.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,view:window}));"
         "el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));",
         e,
     )),
    ("js click",
     lambda d, e: d.execute_script("arguments[0].click();", e)),
    ("focus + Enter",
     lambda d, e: (d.execute_script("arguments[0].focus();", e),
                   e.send_keys("\n"))),
    ("focus + Space",
     lambda d, e: (d.execute_script("arguments[0].focus();", e),
                   e.send_keys(" "))),
]


class BasePage:
    """All page objects inherit from this."""

    DEFAULT_TIMEOUT = 30

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, self.DEFAULT_TIMEOUT)

    # ── Page-load waits ───────────────────────────────────────────────
    def page_fully_loaded(self, timeout: int | None = None) -> None:
        """document.readyState=complete + no spinner + DOM stable 600 ms."""
        t = timeout or self.DEFAULT_TIMEOUT
        wh.wait_until_fully_loaded(self.driver, timeout=t)
        wh.wait_for_dom_stable(self.driver, stability_ms=600, total_timeout_s=15)

    # ── Locator presence helpers ──────────────────────────────────────
    def find(self, locator: Tuple[str, str], timeout: int = 10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )

    def find_all(self, locator: Tuple[str, str]):
        return self.driver.find_elements(*locator)

    def is_visible(self, locator: Tuple[str, str]) -> bool:
        try:
            return self.driver.find_element(*locator).is_displayed()
        except Exception:
            return False

    # ── Click helpers ─────────────────────────────────────────────────
    def force_click(
        self,
        locator: Tuple[str, str],
        label: str,
        attempts: int = 15,
    ) -> None:
        """
        Click *locator* using rotating techniques until one of them
        doesn't raise. Used for elements where plain .click() is
        unreliable (custom JS handlers, SVG paths, etc.).
        """
        for i in range(1, attempts + 1):
            name, fn = CLICK_TECHNIQUES[(i - 1) % len(CLICK_TECHNIQUES)]
            try:
                elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(locator)
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center', behavior:'instant'});",
                    elem,
                )
                time.sleep(0.2)
                fn(self.driver, elem)
                log.info("  ✓ '%s' clicked on attempt %02d via '%s'", label, i, name)
                return
            except Exception as exc:
                log.debug("  attempt %02d (%s) raised %s", i, name, exc)
                time.sleep(0.3)
        raise TimeoutException(f"Could not click '{label}' after {attempts} attempts.")

    def force_open_popup(
        self,
        trigger_loc: Tuple[str, str],
        popup_loc: Tuple[str, str],
        label: str,
        attempts: int = 30,
        wait_each: float = 2.0,
    ) -> None:
        """
        Click *trigger_loc* with rotating techniques until *popup_loc*
        is actually visible. Tries up to *attempts* times.
        """
        log.info("opening '%s' popup…", label)
        for i in range(1, attempts + 1):
            name, fn = CLICK_TECHNIQUES[(i - 1) % len(CLICK_TECHNIQUES)]
            try:
                elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(trigger_loc)
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center', behavior:'instant'});",
                    elem,
                )
                time.sleep(0.3)
                fn(self.driver, elem)
            except Exception as exc:
                log.debug("attempt %02d (%s) raised %s", i, name, exc)
            try:
                WebDriverWait(self.driver, wait_each).until(
                    EC.visibility_of_element_located(popup_loc)
                )
                log.info("  ✓ '%s' popup opened on attempt %02d via '%s'",
                         label, i, name)
                return
            except TimeoutException:
                time.sleep(1.0)
        raise TimeoutException(
            f"'{label}' popup never opened after {attempts} click attempts."
        )

    # ── Alert helper ──────────────────────────────────────────────────
    def dismiss_any_alert(self) -> str | None:
        """If a JS alert is showing, capture its text and dismiss it."""
        try:
            alert = self.driver.switch_to.alert
            text = alert.text
            alert.accept()
            return text
        except Exception:
            return None
