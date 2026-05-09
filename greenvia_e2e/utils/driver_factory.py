"""
Driver factory.
Returns a configured Selenium WebDriver for the browser in cfg.BROWSER.
"""
from __future__ import annotations

import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from utils.config import cfg

log = logging.getLogger(__name__)

_WINDOW_SIZE = (1440, 900)


def _chrome() -> webdriver.Chrome:
    options = ChromeOptions()
    if cfg.HEADLESS:
        options.add_argument("--headless=new")
        # Headless windows can't be "maximized" — give them a big size instead
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    if not cfg.HEADLESS:
        # Belt-and-suspenders: some Chrome builds ignore --start-maximized
        try:
            driver.maximize_window()
        except Exception:
            pass
    # Remove navigator.webdriver flag (helps avoid bot detection on OAuth)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return driver


def _firefox() -> webdriver.Firefox:
    options = FirefoxOptions()
    if cfg.HEADLESS:
        options.add_argument("--headless")
    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    if cfg.HEADLESS:
        driver.set_window_size(*_WINDOW_SIZE)
    else:
        try:
            driver.maximize_window()
        except Exception:
            driver.set_window_size(*_WINDOW_SIZE)
    return driver


def _edge() -> webdriver.Edge:
    options = EdgeOptions()
    if cfg.HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")
    service = EdgeService(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    if not cfg.HEADLESS:
        try:
            driver.maximize_window()
        except Exception:
            pass
    return driver


_FACTORY = {
    "chrome": _chrome,
    "firefox": _firefox,
    "edge": _edge,
}


def create_driver() -> webdriver.Remote:
    """Return a fully configured WebDriver instance."""
    browser = cfg.BROWSER
    if browser not in _FACTORY:
        raise ValueError(f"Unsupported browser '{browser}'. Choose: {list(_FACTORY)}")
    log.info("Starting %s (headless=%s)", browser, cfg.HEADLESS)
    driver = _FACTORY[browser]()
    driver.implicitly_wait(cfg.IMPLICIT_WAIT)
    driver.set_page_load_timeout(cfg.PAGE_LOAD_TIMEOUT)
    return driver
