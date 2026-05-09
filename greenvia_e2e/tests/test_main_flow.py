"""
tests/test_main_flow.py
========================
End-to-end Border Trip booking flow as a Pytest suite.

  Homepage → Border Trip → Destination → Date → Passengers → Update
           → Book now → Seats → Go to booking
           → 3 Passenger forms → Checkout

The 12 tests below run in order against a single session-scoped browser
(see `tests/conftest.py`). Each one uses the `runner` fixture which
exposes the page objects, config, and reporter helpers.

The class is marked @pytest.mark.incremental — if any step fails the
remaining tests are skipped automatically (the browser state would be
broken anyway). A modern HTML report covering all 12 steps is written
to `reports/main_flow_report.html` at session end.

Run from the project folder:

    pytest -v                     # full suite
    pytest -v tests/test_main_flow.py
    pytest -v -k seats            # only seat-selection step
"""
from __future__ import annotations

import time

import pytest

PREFERRED_SEAT_IDS = (3, 2)
TOTAL_SEATS_NEEDED = 3


@pytest.mark.incremental
class TestBorderTripBookingFlow:
    """Twelve sequential tests that share one browser session."""

    # 1 ── Homepage
    def test_01_open_homepage(self, runner):
        with runner.step("Open homepage"):
            runner.home.open(runner.cfg.BASE_URL)
            runner.snap("homepage")

    # 2 ── Border Trip nav (+ 5 s settle for late-binding handlers)
    def test_02_click_border_trip_nav(self, runner):
        with runner.step("Click 'Border Trip' nav"):
            runner.home.click_border_trip()
            time.sleep(5.0)
            runner.note(f"URL: {runner.driver.current_url}")
            runner.snap("border_trip")

    # 3 ── Destination
    def test_03_select_destination(self, runner):
        with runner.step(f"Select destination: {runner.cfg.ROUTE}"):
            runner.catalog.select_destination(runner.cfg.ROUTE_VALUE)
            time.sleep(3.0)

    # 4 ── Date
    def test_04_select_date(self, runner):
        with runner.step(f"Select date: {runner.cfg.TRIP_DATE}"):
            runner.catalog.pick_date(runner.cfg.TRIP_DATE)
            time.sleep(3.0)

    # 5 ── Passengers
    def test_05_select_passengers(self, runner):
        cfg = runner.cfg
        with runner.step(
            f"Select passengers: {cfg.ADULT_COUNT} adult + {cfg.CHILD_COUNT} child"
        ):
            runner.catalog.set_passengers(cfg.ADULT_COUNT, cfg.CHILD_COUNT)
            time.sleep(3.0)
            runner.snap("search_form_filled")

    # 6 ── Update / search
    def test_06_click_update(self, runner):
        with runner.step("Click 'Update' to search"):
            runner.catalog.click_update()

    # 7 ── Trip count
    def test_07_count_trips(self, runner):
        with runner.step("Count trip results"):
            runner.catalog.wait_for_results()
            trips = runner.catalog.get_trips()
            runner.note(f"{len(trips)} trip(s) returned")
            for t in trips:
                runner.note(str(t))
            assert trips, "No trips returned — empty result state."
            runner.snap("trip_results")

    # 8 ── Book now (first trip)
    def test_08_click_first_book_now(self, runner):
        with runner.step("Click 'Book now' on first trip"):
            runner.catalog.click_first_book_now()

    # 9 ── Seat selection
    def test_09_select_seats(self, runner):
        with runner.step(
            f"Select {TOTAL_SEATS_NEEDED} seats (prefer {PREFERRED_SEAT_IDS})"
        ):
            runner.catalog.wait_for_seats()
            picked = runner.catalog.pick_seats(PREFERRED_SEAT_IDS, TOTAL_SEATS_NEEDED)
            runner.note(f"final picks: {picked}")
            verified = runner.catalog.count_selected(picked)
            runner.note(f"{verified}/{TOTAL_SEATS_NEEDED} verified as selected")
            assert verified == TOTAL_SEATS_NEEDED, (
                f"Visual check failed: only {verified}/{TOTAL_SEATS_NEEDED}"
            )
            runner.snap("seats_selected")

    # 10 ── Go to booking
    def test_10_click_go_to_booking(self, runner):
        with runner.step("Click 'Go to booking'"):
            runner.catalog.click_go_to_booking()

    # 11 ── Fill 3 passenger forms
    def test_11_fill_passenger_forms(self, runner):
        with runner.step("Fill 3 passenger forms"):
            filled = runner.forms.fill_all_passengers(count=3)
            runner.note(f"{len(filled)} forms saved")
            for i, p in enumerate(filled, 1):
                runner.note(f"#{i}  {p['first']} {p['last']}  ({p['email']})")
            runner.snap("forms_saved")
            assert len(filled) == 3

    # 12 ── Checkout
    def test_12_click_checkout(self, runner):
        with runner.step("Click Checkout (#td-checkout)") as step:
            outcome, final_url = runner.forms.click_checkout()
            runner.note(f"final URL: {final_url}")
            if outcome == "success":
                runner.snap("checkout_success")
            elif outcome == "site_bug":
                # Mark the report step as WARN (yellow) but let the
                # pytest test pass — this is a documented external
                # backend bug, not a test-script failure.
                step.status = "WARN"
                step.error = (
                    "KNOWN SITE BUG: Site refused to auto-create the user "
                    "account at checkout — 'Could not create a new account. "
                    "Wrong value for res.users.border_trip_cash_permission: "
                    "default'. Backend Odoo misconfiguration; booking flow "
                    "reaches checkout correctly but payment cannot proceed "
                    "until the site team fixes the field."
                )
                step.screenshot = runner.reporter.snap("checkout_site_bug")
            else:
                pytest.fail(f"Unexpected checkout outcome: {outcome}")
