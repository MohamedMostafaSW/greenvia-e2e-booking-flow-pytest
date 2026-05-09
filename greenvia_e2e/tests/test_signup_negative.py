"""
tests/test_signup_negative.py
==============================
Negative scenario for the internal Sign Up popup on greenviathai.com.

  Open homepage → Click 'Log in/Sign up' → Click 'Sign Up' link
                → Fill all fields → Submit → Capture error

Filling a perfectly valid registration form on the live site currently
triggers a known backend bug:

    "Could not create a new account. Wrong value for
     res.users.border_trip_cash_permission: 'default'"

The site's Odoo controller assigns the string `'default'` to a
selection field that doesn't accept that value, so anonymous accounts
cannot be created. This test exists to **verify that the bug is still
present** and to document the exact error text in the HTML report.

The test passes when the expected error is captured. It will start
failing the moment the site team fixes the field default — which is
the desired behaviour for a regression-style negative test.
"""
from __future__ import annotations

import time

import pytest

# Test data — generated fresh per run so re-runs don't reuse the same
# email (would otherwise hit a different "user already exists" error).
EMAIL_PREFIX        = "mohamed.mostafa"
FIRST_NAME          = "Mohamed"
LAST_NAME           = "Mostafa"
DATE_OF_BIRTH       = "2000-09-15"
PHONE_NUMBER        = "0812345678"
NATIONALITY_VALUE   = "78"           # Georgia
PASSWORD            = "MoHa@2025Pwd"  # 12 chars, mixed case + digit + symbol


@pytest.mark.incremental
class TestSignUpNegative:
    """4-step negative scenario: confirm the backend signup bug."""

    # 1 ── Open homepage
    def test_01_open_homepage(self, runner):
        with runner.step("Open homepage"):
            runner.home.open(runner.cfg.BASE_URL)
            runner.snap("signup_homepage")

    # 2 ── Open the Sign Up popup
    def test_02_open_signup_popup(self, runner):
        with runner.step("Open Sign Up popup ('Log in/Sign up' → 'Sign Up' link)"):
            runner.signup.open_popup()
            runner.snap("signup_popup_open")

    # 3 ── Fill all signup fields with valid data
    def test_03_fill_signup_form(self, runner):
        with runner.step("Fill every signup field with valid data"):
            email = f"{EMAIL_PREFIX}.{int(time.time())}@example.com"
            runner.signup.fill_form(
                email=email,
                first_name=FIRST_NAME,
                last_name=LAST_NAME,
                dob=DATE_OF_BIRTH,
                phone=PHONE_NUMBER,
                nationality_value=NATIONALITY_VALUE,
                password=PASSWORD,
            )
            runner.note(f"email used: {email}")
            runner.note(f"name: {FIRST_NAME} {LAST_NAME}")
            runner.note(f"DOB: {DATE_OF_BIRTH}")
            runner.note(f"phone: {PHONE_NUMBER}")
            runner.note("nationality: Georgia (value=78)")
            runner.note("password: 12 chars, mixed-case + digit + symbol")
            runner.snap("signup_form_filled")

    # 4 ── Submit and capture the expected backend-bug error
    def test_04_submit_and_capture_error(self, runner):
        with runner.step("Submit + capture the known backend-bug error"):
            runner.signup.submit()
            error_text = runner.signup.get_error_text(timeout=15)

            runner.driver.execute_script("""
             const popup = document.querySelector('.modal-body');
                if (popup) {
                 popup.scrollTop = 0;
                }
                 """)
            runner.snap("signup_error_displayed")

            # The test PASSES if the expected error was surfaced.
            assert error_text, (
                "No error message appeared after Sign Up submit. The site "
                "may have started accepting anonymous registrations — "
                "this negative test should be revisited."
            )

            runner.note(f"error captured: {error_text!r}")

            assert any(
                phrase in error_text
                for phrase in (
                    "Could not create a new account",
                    "border_trip_cash_permission",
                )
            ), (
                "Captured an error, but it doesn't match the documented "
                f"backend bug. Got: {error_text!r}"
            )
