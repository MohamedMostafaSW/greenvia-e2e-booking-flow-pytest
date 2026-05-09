"""
PassengerFormsPage
==================
Three-passenger detail forms + Checkout button.

Each form lives inside `<form.o_passenger_details_form>`. Many fields
share an `id` across the three forms (invalid HTML but real), so we
always scope queries to a specific form element.

The shared per-passenger data (Georgia / DTV 180 / DOB / etc.) lives
inside this page object as defaults. The orchestration script just
calls `forms.fill_all_passengers(count=3)` and `forms.click_checkout()`.

Stamp Expiry Date is computed dynamically as `TRIP_DATE + 2 months`.
"""
from __future__ import annotations

import calendar
import logging
import random
import string
import time
from datetime import date, datetime
from typing import List, Tuple

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage, CLICK_TECHNIQUES
from utils.config import cfg
from utils.test_data import valid_jpeg

log = logging.getLogger(__name__)

# ── Per-passenger defaults (shared across all 3 passengers) ───────────
NATIONALITY_VALUE = "78"          # Georgia
VISA_TYPE_VALUE   = "3"           # DTV
VISA_TENURE_VALUE = "4"           # 180 Days
GENDER_VALUE      = "male"
DOB               = "1995-06-15"  # any past date (max=today)
PASSPORT_EXPIRY   = "2030-12-31"  # ≥ 2028
PICKUP_LOCATION   = "PTT Chalong"
PICKUP_MAP_LINK   = "https://maps.app.goo.gl/5gaxHmUt1uGj5Hbz8?g_st=ic"

# Site-bug detection (anonymous-checkout backend error)
SITE_BUG_PHRASES = (
    "border_trip_cash_permission",
    "Could not create a new account",
)
SUCCESS_URL_PARTS = ("checkout", "payment", "order", "summary", "confirm")


def _add_months(d: date, months: int) -> date:
    """Return d + N months, clamping the day to the new month's last day."""
    new_month = ((d.month - 1 + months) % 12) + 1
    new_year  = d.year + (d.month - 1 + months) // 12
    last_day  = calendar.monthrange(new_year, new_month)[1]
    return date(new_year, new_month, min(d.day, last_day))


def stamp_expiry_for(trip_iso_date: str, months_after: int = 2) -> str:
    """Stamp Expiry = trip date + N months (default 2). ISO YYYY-MM-DD."""
    trip = datetime.strptime(trip_iso_date, "%Y-%m-%d").date()
    return _add_months(trip, months_after).isoformat()


class PassengerFormsPage(BasePage):
    PASSENGER_FORMS = (By.CSS_SELECTOR, "form.o_passenger_details_form")

    # Real DOM checkout button + fallbacks
    CHECKOUT_BTN          = (By.ID, "td-checkout")
    CHECKOUT_BTN_FALLBACK = (
        By.CSS_SELECTOR,
        "button.passenger-checkout-submit-btn:not(.d-none)",
    )
    CHECKOUT_BTN_FALLBACK2 = (
        By.XPATH,
        "//button[contains(translate(., 'CHECKOUT', 'checkout'), 'checkout')"
        " and not(contains(@class, 'd-none'))]",
    )

    # ── Public API ────────────────────────────────────────────────────
    def fill_all_passengers(self, count: int = 3) -> List[dict]:
        """
        Wait for the expected number of passenger forms, then fill each
        with shared defaults + a random first/last name (mohamedXXX /
        mostafaXXX). Saves each form before moving to the next.
        Returns a list of {first, last, email, phone} dicts.
        """
        forms = self._wait_for_forms(expected=count)
        log.info("  %d forms detected", len(forms))

        doc_path = valid_jpeg()
        log.info("  using upload file: %s", doc_path)
        stamp_expiry = stamp_expiry_for(cfg.TRIP_DATE, months_after=2)
        log.info("  stamp expiry computed: %s (= trip date + 2 months)",
                 stamp_expiry)

        filled: List[dict] = []
        for i, form in enumerate(forms):
            data = self._fill_one_form(form, i, doc_path, stamp_expiry)
            filled.append(data)
            time.sleep(1.0)
            self._click_save_in_form(form)
            log.info("  ✓ saved passenger #%d: %s %s",
                     i + 1, data["first"], data["last"])
            time.sleep(2.0)
        return filled

    def click_checkout(self) -> Tuple[str, str]:
        """
        Click the checkout button and detect outcome:
          ('success', current_url)  — navigated to a checkout-like URL
          ('site_bug', current_url) — 'border_trip_cash_permission' error
          raises RuntimeError on real timeout.
        """
        time.sleep(2.0)
        url_before = self.driver.current_url

        loc = None
        for candidate in (self.CHECKOUT_BTN,
                          self.CHECKOUT_BTN_FALLBACK,
                          self.CHECKOUT_BTN_FALLBACK2):
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(candidate)
                )
                loc = candidate
                log.info("  using checkout selector: %s", candidate)
                break
            except TimeoutException:
                continue
        if loc is None:
            raise RuntimeError("Could not find any checkout button on the page")

        self.force_click(loc, label="Checkout")

        deadline = time.time() + 45
        while time.time() < deadline:
            if self._detect_site_bug():
                return ("site_bug", self.driver.current_url)
            if self._detect_success(url_before):
                self.page_fully_loaded()
                return ("success", self.driver.current_url)
            time.sleep(0.5)

        raise RuntimeError("Checkout navigation never happened.")

    # ── Internal: filling one form ────────────────────────────────────
    def _wait_for_forms(self, expected: int) -> List:
        self.wait.until(EC.presence_of_element_located(self.PASSENGER_FORMS))
        time.sleep(2.0)
        forms = self.driver.find_elements(*self.PASSENGER_FORMS)
        if len(forms) != expected:
            raise RuntimeError(
                f"Expected {expected} passenger forms, got {len(forms)}"
            )
        return forms

    def _fill_one_form(
        self,
        form,
        form_index: int,
        doc_path: str,
        stamp_expiry: str,
    ) -> dict:
        first = "mohamed" + _random_3()
        last  = "mostafa" + _random_3()
        email = _random_email()
        phone = _random_phone()
        log.info("  filling passenger %d: %s %s", form_index + 1, first, last)

        self._expand_form(form)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'start', behavior:'instant'});",
            form,
        )
        time.sleep(0.5)

        # Names + DOB + gender + nationality
        self._set_input(form, "first_name", first)
        self._set_input(form, "last_name",  last)
        self._set_input(form, "date_of_birth", DOB)
        self._set_select(form, "gender",      GENDER_VALUE)
        self._set_select(form, "nationality", NATIONALITY_VALUE)
        # Visa
        self._set_select(form, "visa_type",   VISA_TYPE_VALUE)
        self._set_select(form, "visa_tenure", VISA_TENURE_VALUE)
        # Passport / stamp expiry dates
        self._set_input(form, "passport_expiry_date", PASSPORT_EXPIRY)
        self._set_input(form, "stamp_expiry_date",    stamp_expiry)
        # Document uploads (hidden file inputs)
        self._upload_file(form, "passport_photo", doc_path)
        self._upload_file(form, "stamp_photo",    doc_path)
        # Contact
        self._set_input(form, "email",        email)
        self._set_input(form, "phone_number", phone)
        # Location (uses index-suffixed IDs)
        pickup_id = f"pickup_location_name_{form_index}"
        map_id    = f"location_link_{form_index}"
        self._js_set_value(self.driver.find_element(By.ID, pickup_id),
                           PICKUP_LOCATION)
        self._js_set_value(self.driver.find_element(By.ID, map_id),
                           PICKUP_MAP_LINK)

        return {"first": first, "last": last, "email": email, "phone": phone}

    def _click_save_in_form(self, form) -> None:
        btn = form.find_element(
            By.CSS_SELECTOR,
            "button.passenger-submit-btn:not(.d-none)",
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', behavior:'instant'});",
            btn,
        )
        time.sleep(0.3)
        for i, (name, fn) in enumerate(CLICK_TECHNIQUES, start=1):
            try:
                fn(self.driver, btn)
                log.info("  ✓ Save clicked via '%s' (attempt %02d)", name, i)
                return
            except Exception as exc:
                log.debug("  Save attempt %02d (%s): %s", i, name, exc)
        raise RuntimeError("Could not click Save button with any technique.")

    # ── Internal: DOM helpers ─────────────────────────────────────────
    def _expand_form(self, form) -> None:
        self.driver.execute_script(
            """
            const root = arguments[0];
            for (const el of root.querySelectorAll('.collapse')) {
                el.classList.add('show');
                el.style.display = 'block';
                el.style.height = 'auto';
                el.style.visibility = 'visible';
            }
            """,
            form,
        )

    def _set_input(self, form, name: str, value: str) -> None:
        elem = form.find_element(By.NAME, name)
        self._js_set_value(elem, value)

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

    def _set_select(self, form, name: str, value: str) -> None:
        sel = form.find_element(By.NAME, name)
        self.driver.execute_script(
            """
            const sel = arguments[0], want = arguments[1];
            for (const opt of sel.options) {
                if (opt.value === want) {
                    sel.value = want;
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    sel.dispatchEvent(new Event('input',  {bubbles: true}));
                    return true;
                }
            }
            return false;
            """,
            sel,
            value,
        )

    def _upload_file(self, form, name: str, file_path: str) -> None:
        elem = form.find_element(By.NAME, name)
        elem.send_keys(str(file_path))

    # ── Internal: checkout outcome detection ──────────────────────────
    def _detect_site_bug(self) -> bool:
        try:
            alert = self.driver.switch_to.alert
            txt = alert.text or ""
            if any(p in txt for p in SITE_BUG_PHRASES):
                alert.accept()
                return True
            alert.accept()
        except Exception:
            pass
        for phrase in SITE_BUG_PHRASES:
            try:
                if self.driver.find_elements(By.XPATH, f"//*[contains(., '{phrase}')]"):
                    return True
            except Exception:
                continue
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text or ""
            if any(p in body_text for p in SITE_BUG_PHRASES):
                return True
        except Exception:
            pass
        return False

    def _detect_success(self, url_before: str) -> bool:
        if self.driver.current_url == url_before:
            return False
        url_lower = self.driver.current_url.lower()
        return any(s in url_lower for s in SUCCESS_URL_PARTS)


# ── Local random data generators ──────────────────────────────────────
def _random_3() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=3))


def _random_email() -> str:
    return f"mohamed.{random.randint(100000, 999999)}@example.com"


def _random_phone() -> str:
    return "08" + "".join(random.choices(string.digits, k=8))
