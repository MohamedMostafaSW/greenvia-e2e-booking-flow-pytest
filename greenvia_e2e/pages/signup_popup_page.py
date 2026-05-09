"""
SignUpPopupPage
===============
The internal email/password registration popup on greenviathai.com.

Flow:
  1. Click the homepage 'Log in/Sign up' button
        <a class="o_login_button" data-action="open-login-popup">…</a>
  2. The login popup appears — click its 'Sign Up' link
        <a class="text-primary">Sign Up</a>
  3. The popup body swaps to the registration form (8 fields):
        Email, First Name, Last Name, Date of Birth, Contact Phone Number,
        Citizenship (<select>), Password, Confirm Password
        + <button class="tp-signup-submit">Sign Up</button>

Submitting a valid form on the live site currently triggers a known
backend bug:

    Could not create a new account. Wrong value for
    res.users.border_trip_cash_permission: 'default'

This page object is used by the negative-scenario test to capture and
verify that error.
"""
from __future__ import annotations

import logging
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage

log = logging.getLogger(__name__)

# Phrases the site uses for the known backend error
SIGNUP_ERROR_PHRASES = (
    "Could not create a new account",
    "border_trip_cash_permission",
)


class SignUpPopupPage(BasePage):
    # ── Triggers ──────────────────────────────────────────────────────
    LOGIN_TRIGGER = (
        By.CSS_SELECTOR,
        "a.o_login_button[data-action='open-login-popup']",
    )
    SIGNUP_LINK = (
        By.XPATH,
        "//a[contains(@class, 'text-primary') and normalize-space()='Sign Up']",
    )

    # ── Popup container (after Sign Up link click) ────────────────────
    POPUP = (By.CSS_SELECTOR, ".tp-signup-popup, .o_signup_popup")

    # ── Form fields ───────────────────────────────────────────────────
    EMAIL          = (By.CSS_SELECTOR, "input[type='email'].tp-signup-input")
    FIRST_NAME     = (By.CSS_SELECTOR, "input.tp-signup-input[placeholder='e.g. John']")
    LAST_NAME      = (By.CSS_SELECTOR, "input.tp-signup-input[placeholder='e.g. Doe']")
    DATE_OF_BIRTH  = (By.CSS_SELECTOR, "input[type='date'].tp-signup-input")
    PHONE          = (
        By.XPATH,
        "//label[normalize-space()='Contact Phone Number']"
        "/following-sibling::input[1]",
    )
    NATIONALITY    = (By.CSS_SELECTOR, "select.tp-signup-input")
    PASSWORDS      = (By.CSS_SELECTOR, "input[type='password'].tp-signup-input")
    SUBMIT_BTN     = (By.CSS_SELECTOR, "button.tp-signup-submit")

    # ── Error display (matches any element containing a known phrase) ─
    ERROR_MESSAGE = (
        By.XPATH,
        "//*[contains(., 'Could not create a new account')"
        " or contains(., 'border_trip_cash_permission')]",
    )

    # ── Actions ───────────────────────────────────────────────────────
    def open_popup(self) -> None:
        """Click 'Log in/Sign up', then the inner 'Sign Up' link."""
        self.force_click(self.LOGIN_TRIGGER, label="Log in/Sign up")
        time.sleep(1.0)
        self.force_click(self.SIGNUP_LINK, label="Sign Up link")
        WebDriverWait(self.driver, 15).until(
            EC.visibility_of_element_located(self.POPUP)
        )
        time.sleep(1.0)

    def fill_form(
        self,
        *,
        email: str,
        first_name: str,
        last_name: str,
        dob: str,
        phone: str,
        nationality_value: str,
        password: str,
    ) -> None:
        """Fill every field in the registration form via JS for reliability."""
        log.info("  filling sign-up form: %s / %s %s", email, first_name, last_name)

        self._js_set_value(self.find(self.EMAIL),         email)
        self._js_set_value(self.find(self.FIRST_NAME),    first_name)
        self._js_set_value(self.find(self.LAST_NAME),     last_name)
        self._js_set_value(self.find(self.DATE_OF_BIRTH), dob)
        self._js_set_value(self.find(self.PHONE),         phone)

        # Nationality <select>
        sel = self.find(self.NATIONALITY)
        self.driver.execute_script(
            """
            const s = arguments[0], want = arguments[1];
            for (const opt of s.options) {
                if (opt.value === want) {
                    s.value = want;
                    s.dispatchEvent(new Event('change', {bubbles: true}));
                    return true;
                }
            }
            return false;
            """,
            sel,
            nationality_value,
        )

        # Two password inputs (Password + Confirm Password)
        pw_inputs = self.driver.find_elements(*self.PASSWORDS)
        if len(pw_inputs) < 2:
            raise RuntimeError(
                f"Expected ≥2 password inputs, got {len(pw_inputs)}"
            )
        self._js_set_value(pw_inputs[0], password)
        self._js_set_value(pw_inputs[1], password)

    def submit(self) -> None:
        """Click the popup's Sign Up submit button."""
        self.force_click(self.SUBMIT_BTN, label="Sign Up submit")

    def get_error_text(self, timeout: int = 15) -> str | None:
        """
        Wait for the known backend error to appear and return its text.
        Polls the page body for any of the known error phrases — the
        site renders the error in a styled box inside the popup body.
        Returns None if no error appears within *timeout* seconds.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                body_text = (
                    self.driver.find_element(By.TAG_NAME, "body").text or ""
                )
                if any(p in body_text for p in SIGNUP_ERROR_PHRASES):
                    # Try to fetch the smallest enclosing element with the
                    # error so the snapshot text is precise.
                    try:
                        elem = self.driver.find_element(*self.ERROR_MESSAGE)
                        return (elem.text or "").strip()
                    except Exception:
                        # Fall back to scanning body lines
                        for line in body_text.splitlines():
                            if any(p in line for p in SIGNUP_ERROR_PHRASES):
                                return line.strip()
                        return body_text
            except Exception:
                pass
            time.sleep(0.5)
        return None

    # ── Internal: JS value setter ─────────────────────────────────────
    def _js_set_value(self, elem, value: str) -> None:
        self.driver.execute_script(
            """
            const el = arguments[0], v = arguments[1];
            el.value = v;
            el.dispatchEvent(new Event('input',  {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            """,
            elem,
            value,
        )
