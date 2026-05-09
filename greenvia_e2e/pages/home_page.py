"""
HomePage
========
Public homepage — open it and click the 'Border Trip' top-nav link.
"""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage


class HomePage(BasePage):
    BORDER_TRIP_NAV = (By.CSS_SELECTOR, "a[role='menuitem'][href='/border-trip']")

    def open(self, base_url: str) -> None:
        self.driver.get(base_url)
        self.page_fully_loaded()

    def click_border_trip(self) -> None:
        self.wait.until(EC.element_to_be_clickable(self.BORDER_TRIP_NAV)).click()
        self.wait.until(EC.url_contains("/border-trip"))
        self.page_fully_loaded()
