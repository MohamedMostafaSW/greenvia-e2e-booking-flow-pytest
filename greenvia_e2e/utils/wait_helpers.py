"""
Wait helpers used by the page objects.

Only the helpers actually called by `pages/*.py` live here:
    wait_for_page_load          — readyState=complete
    wait_for_no_loading_indicator — common spinners gone
    wait_until_fully_loaded     — both of the above
    wait_for_dom_stable         — DOM unchanged for stability_ms
"""
from __future__ import annotations

import time as _time

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from utils.config import cfg


def _wait(driver: WebDriver, timeout: int | None = None) -> WebDriverWait:
    return WebDriverWait(driver, timeout or cfg.EXPLICIT_WAIT)


def wait_for_page_load(driver: WebDriver, timeout: int | None = None) -> bool:
    return _wait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


# Common loading indicator selectors observed across modern themes / Odoo.
_LOADING_SELECTORS = (
    ".loading",
    ".loader",
    ".spinner",
    ".o_loading",
    ".o_loading_indicator",
    ".loading-overlay",
    ".page-loader",
    ".preloader",
    "[data-loading='true']",
)


def wait_for_no_loading_indicator(
    driver: WebDriver,
    timeout: int | None = None,
) -> bool:
    """Block until no visible loading spinner / overlay remains on the page."""
    selector = ", ".join(_LOADING_SELECTORS)

    def _no_visible_loader(d: WebDriver) -> bool:
        return d.execute_script(
            """
            const sel = arguments[0];
            const els = document.querySelectorAll(sel);
            for (const el of els) {
                const cs = window.getComputedStyle(el);
                if (cs.display !== 'none' && cs.visibility !== 'hidden'
                    && el.offsetParent !== null) {
                    return false;
                }
            }
            return true;
            """,
            selector,
        )

    return _wait(driver, timeout).until(_no_visible_loader)


def wait_until_fully_loaded(driver: WebDriver, timeout: int | None = None) -> None:
    """document.readyState === 'complete' AND no visible loading spinner."""
    wait_for_page_load(driver, timeout)
    wait_for_no_loading_indicator(driver, timeout)


def wait_for_dom_stable(
    driver: WebDriver,
    stability_ms: int = 500,
    total_timeout_s: float = 15.0,
    poll_ms: int = 100,
) -> bool:
    """
    Block until the DOM has been unchanged for *stability_ms* ms.

    Useful right before clicking custom widgets — modern SPAs finish
    `readyState=complete` quickly but keep mounting JS event handlers
    for a few hundred ms after that. Clicking before the handler is
    bound is a silent no-op.

    Returns True on stability, False on timeout.
    """
    deadline = _time.time() + total_timeout_s
    last_size = -1
    stable_since: float | None = None

    while _time.time() < deadline:
        try:
            size = driver.execute_script(
                "return document.documentElement.outerHTML.length"
            )
        except Exception:
            _time.sleep(poll_ms / 1000.0)
            continue

        if size == last_size:
            if stable_since is None:
                stable_since = _time.time()
            elif (_time.time() - stable_since) * 1000 >= stability_ms:
                return True
        else:
            last_size = size
            stable_since = None

        _time.sleep(poll_ms / 1000.0)

    return False
