"""
CatalogPage
===========
Everything that happens on /border-trip and the seat-selection page that
follows it:

  Search form  →  Update  →  Trip results  →  Book now  →  Seat map
                                                          →  Go to booking

Three logical sub-areas live here as a single page object:

  • Search form     — Destination, calendar date picker, passengers popup,
                      Update button.
  • Trip results    — Trip cards rendered inside #catalog_trips_container,
                      the "Book now" link on the first group trip.
  • Seat selection  — SVG seat map (white = available, green = selected),
                      pick N seats with preferences + random fallback,
                      "Go to booking" button.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from pages.base_page import BasePage, CLICK_TECHNIQUES

log = logging.getLogger(__name__)

SELECTED_FILLS = {"green", "#00b481", "#00b481ff"}


@dataclass
class TripSummary:
    index: int
    trip_id: str
    trip_type: str
    base_price: str

    def __str__(self) -> str:
        return (f"#{self.index}  id={self.trip_id}  "
                f"type={self.trip_type}  price={self.base_price}")


class CatalogPage(BasePage):
    # ── Search form: destination ──────────────────────────────────────
    DESTINATION_SELECT = (By.ID, "catalog_destination")

    # ── Search form: date field + calendar popup ──────────────────────
    DATE_FIELD     = (By.ID, "open_calendar_from_date_field")
    CALENDAR_POPUP = (By.CSS_SELECTOR, ".custom-calendar-container")
    CAL_OVERLAY    = (By.CSS_SELECTOR, ".custom-calendar-overlay")
    CAL_NEXT_BTN   = (By.CSS_SELECTOR, ".calendar-nav-next:not(.disabled)")

    # ── Search form: passengers popup ─────────────────────────────────
    PAX_FIELD          = (By.ID, "open_passengers_popup")
    PAX_POPUP          = (By.CSS_SELECTOR, ".passengers-popup-container")
    PAX_ADULTS_INC     = (By.ID, "increase_adults")
    PAX_ADULTS_DEC     = (By.ID, "decrease_adults")
    PAX_ADULTS_COUNT   = (By.ID, "adults_count")
    PAX_CHILDREN_INC   = (By.ID, "increase_children")
    PAX_CHILDREN_DEC   = (By.ID, "decrease_children")
    PAX_CHILDREN_COUNT = (By.ID, "children_count")
    PAX_DONE_BTN       = (By.ID, "passengers_done_btn")

    # ── Search form: submit ───────────────────────────────────────────
    UPDATE_BTN = (By.ID, "catalog_update_btn")

    # ── Trip results ──────────────────────────────────────────────────
    TRIPS_CONTAINER = (By.ID, "catalog_trips_container")
    TRIP_CARDS      = (By.CSS_SELECTOR, "#catalog_trips_container .trip-card")
    EMPTY_STATE     = (By.ID, "catalog_empty_state")
    FIRST_BOOK_NOW  = (
        By.XPATH,
        "(//div[@id='catalog_trips_container']//a[normalize-space()='Book now'])[1]",
    )

    # ── Seat selection ────────────────────────────────────────────────
    SVG_SEAT          = (By.CSS_SELECTOR, ".svg-seat")
    GO_TO_BOOKING_BTN = (By.XPATH, "//button[normalize-space()='Go to booking']")

    # ════════════════════════════════════════════════════════════════
    # Search form actions
    # ════════════════════════════════════════════════════════════════
    def select_destination(self, value: str) -> None:
        elem = self.wait.until(EC.element_to_be_clickable(self.DESTINATION_SELECT))
        elem.click()
        Select(elem).select_by_value(value)

    def pick_date(self, iso_date: str) -> None:
        """
        Open the calendar, click the day with data-date=iso_date.
        The calendar auto-closes on day click — there is no Done button.
        """
        self.force_open_popup(self.DATE_FIELD, self.CALENDAR_POPUP, label="calendar")
        self._click_calendar_day(iso_date)
        self.wait.until(EC.invisibility_of_element_located(self.CALENDAR_POPUP))
        self.wait.until(EC.invisibility_of_element_located(self.CAL_OVERLAY))

    def _click_calendar_day(self, iso_date: str) -> None:
        day_loc = (
            By.CSS_SELECTOR,
            f".calendar-day[data-date='{iso_date}']"
            ":not(.calendar-day-disabled):not(.calendar-day-empty)",
        )
        for _ in range(24):
            try:
                cell = WebDriverWait(self.driver, 1).until(
                    EC.element_to_be_clickable(day_loc)
                )
                cell.click()
                return
            except TimeoutException:
                try:
                    WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable(self.CAL_NEXT_BTN)
                    ).click()
                except TimeoutException:
                    break
        raise TimeoutException(f"Could not click day cell for {iso_date}")

    def set_passengers(self, adults: int, children: int) -> None:
        self.force_open_popup(self.PAX_FIELD, self.PAX_POPUP, label="passengers")
        self._step_count(self.PAX_ADULTS_COUNT,
                         self.PAX_ADULTS_INC,   self.PAX_ADULTS_DEC,   adults)
        self._step_count(self.PAX_CHILDREN_COUNT,
                         self.PAX_CHILDREN_INC, self.PAX_CHILDREN_DEC, children)
        self.wait.until(EC.element_to_be_clickable(self.PAX_DONE_BTN)).click()
        self.wait.until(EC.invisibility_of_element_located(self.PAX_POPUP))

    def _step_count(self, display_loc, inc_loc, dec_loc, target: int) -> None:
        for _ in range(20):
            try:
                text = self.driver.find_element(*display_loc).text.strip()
                current = int(text) if text.isdigit() else 0
            except Exception:
                current = 0
            log.info("    stepper %s: current=%d target=%d",
                     display_loc[1], current, target)
            if current == target:
                return
            btn = inc_loc if current < target else dec_loc
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(btn)
            ).click()
            time.sleep(0.3)

    def click_update(self) -> None:
        self.wait.until(EC.element_to_be_clickable(self.UPDATE_BTN))
        self.force_click(self.UPDATE_BTN, label="Update")
        self.page_fully_loaded()

    # ════════════════════════════════════════════════════════════════
    # Trip results
    # ════════════════════════════════════════════════════════════════
    def wait_for_results(self) -> None:
        self.wait.until(EC.presence_of_element_located(self.TRIPS_CONTAINER))
        WebDriverWait(self.driver, 20).until(lambda d: (
            len(d.find_elements(*self.TRIP_CARDS)) > 0
            or d.find_element(*self.EMPTY_STATE).is_displayed()
        ))

    def get_trips(self) -> list[TripSummary]:
        cards = self.driver.find_elements(*self.TRIP_CARDS)
        return [
            TripSummary(
                index=i + 1,
                trip_id=c.get_attribute("data-trip-id") or "?",
                trip_type=c.get_attribute("data-trip-type") or "?",
                base_price=c.get_attribute("data-base-price") or "?",
            )
            for i, c in enumerate(cards)
        ]

    def click_first_book_now(self) -> None:
        self.force_click(self.FIRST_BOOK_NOW, label="first Book now")
        self.page_fully_loaded()

    # ════════════════════════════════════════════════════════════════
    # Seat selection
    # ════════════════════════════════════════════════════════════════
    def wait_for_seats(self) -> None:
        self.wait.until(EC.presence_of_element_located(self.SVG_SEAT))
        time.sleep(1.0)  # let SVG fully render

    def find_available_seats(self, count: int = 50) -> list[int]:
        """Return seat IDs whose fill is white (available)."""
        return self.driver.execute_script(
            """
            const need = arguments[0];
            const out = [];
            for (const el of document.querySelectorAll('path.svg-seat')) {
                const f = (el.getAttribute('fill') || el.style.fill || '').toLowerCase();
                if (f === 'white') {
                    const id = el.getAttribute('data-id') || el.id.replace('seat-','');
                    if (id) out.push(parseInt(id));
                    if (out.length >= need) break;
                }
            }
            return out;
            """,
            count,
        )

    def get_seat_state(self, seat_id: int) -> dict:
        return self.driver.execute_script(
            """
            const el = document.getElementById('seat-' + arguments[0]);
            if (!el) return null;
            return {
                fill: el.getAttribute('fill') || el.style.fill || '',
                cls:  el.getAttribute('class') || '',
            };
            """,
            seat_id,
        ) or {"fill": "", "cls": ""}

    def click_and_verify_seat(self, seat_id: int, max_attempts: int = 8):
        """
        Click seat-<id> with rotating click techniques. Returns:
          • True on successful selection (fill changed)
          • 'already_booked' if the site rejected it via JS alert
          • raises after `max_attempts` no-ops
        """
        seat_loc = (By.CSS_SELECTOR, f"#seat-{seat_id}")
        before = self.get_seat_state(seat_id)
        log.info("  seat-%d initial state: fill=%s", seat_id, before["fill"])

        for i in range(1, max_attempts + 1):
            name, fn = CLICK_TECHNIQUES[(i - 1) % len(CLICK_TECHNIQUES)]
            try:
                elem = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(seat_loc)
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center', behavior:'instant'});",
                    elem,
                )
                time.sleep(0.2)
                fn(self.driver, elem)
            except Exception as exc:
                log.debug("  attempt %02d (%s) raised %s", i, name, exc)
                alert_text = self.dismiss_any_alert()
                if alert_text:
                    log.warning("  seat-%d rejected by site: %s", seat_id, alert_text)
                    return "already_booked"
                continue

            alert_text = self.dismiss_any_alert()
            if alert_text:
                log.warning("  seat-%d rejected by site: %s", seat_id, alert_text)
                return "already_booked"

            time.sleep(0.5)
            after = self.get_seat_state(seat_id)
            if after["fill"] != before["fill"] or after["cls"] != before["cls"]:
                log.info("  ✓ seat-%d SELECTED via '%s' (fill: %s → %s)",
                         seat_id, name, before["fill"], after["fill"])
                return True
            log.debug("  attempt %02d (%s): no visual change", i, name)

        raise RuntimeError(
            f"seat-{seat_id} click did not register after {max_attempts} attempts"
        )

    def pick_seats(
        self,
        preferred: tuple[int, ...],
        total_needed: int,
    ) -> list[int]:
        """
        Try `preferred` seat IDs in order; for any that aren't available
        (or the site rejects), top up with random available seats until
        we have `total_needed` selected. Returns the final list.
        """
        available = self.find_available_seats(count=50)
        log.info("  available seat pool: %s", available)
        if len(available) < total_needed:
            raise RuntimeError(
                f"Only {len(available)} available seat(s) — need {total_needed}"
            )

        picked: list[int] = []

        def try_pick(sid: int) -> bool:
            if sid not in available or sid in picked:
                return False
            result = self.click_and_verify_seat(sid)
            if result is True:
                picked.append(sid)
                return True
            available.remove(sid)
            return False

        for sid in preferred:
            if len(picked) >= total_needed:
                break
            try_pick(sid)

        random_pool = [s for s in available if s not in picked]
        random.shuffle(random_pool)
        for sid in random_pool:
            if len(picked) >= total_needed:
                break
            try_pick(sid)

        if len(picked) != total_needed:
            raise RuntimeError(
                f"Expected {total_needed} seats selected, got {len(picked)}: {picked}"
            )
        return picked

    def count_selected(self, seat_ids: list[int]) -> int:
        selected = 0
        for n in seat_ids:
            s = self.get_seat_state(n)
            fill = (s["fill"] or "").strip().lower()
            cls  = (s["cls"]  or "").lower()
            if fill in SELECTED_FILLS or "selected" in cls:
                selected += 1
        return selected

    def click_go_to_booking(self) -> None:
        self.force_click(self.GO_TO_BOOKING_BTN, label="Go to booking")
        self.page_fully_loaded()
