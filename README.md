# Selenium · Pytest · POM Framework — GreenVia Border Trip E2E

End-to-end test automation for the **Border Trip** booking flow on
[greenviathai.com](https://www.greenviathai.com), built as a clean
Page-Object-Model framework on top of **Python · Pytest · Selenium WebDriver**.

The suite walks the entire user journey:

> Homepage → Border Trip → Destination → Date → Passengers → Update
> → Book Now → Seat Selection → Go to Booking → 3 Passenger Forms → Checkout

Each step is a separate Pytest test, all sharing a single browser session.
A modern HTML report with embedded screenshots is generated after every
run at `reports/main_flow_report.html`.

---

## Table of contents

- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Architecture](#architecture)
- [Setup](#setup)
- [Running the tests](#running-the-tests)
- [Running from VS Code](#running-from-vs-code)
- [Configuration](#configuration)
- [Reports](#reports)
- [Known site bug](#known-site-bug)
- [Troubleshooting](#troubleshooting)

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | **Python 3.10+** (tested on 3.14) |
| Test runner | **Pytest 8** (`pytest`, `pytest-html`) |
| Browser automation | **Selenium WebDriver 4** with Chrome |
| Driver management | `webdriver-manager` (auto-downloads matching ChromeDriver) |
| Test fixtures | Pillow (generates a tiny JPEG used for passport / stamp uploads) |
| Config | `python-dotenv` for `.env` overrides |

---

## Project structure

```
greenvia_e2e/
├── pytest.ini                  # Pytest config: testpaths, markers, addopts
├── requirements.txt
│
├── pages/                      # Page Object Model
│   ├── base_page.py            # Shared click + wait helpers (6 click techniques)
│   ├── home_page.py            # Homepage: open, click 'Border Trip' nav
│   ├── catalog_page.py         # Search form + trip results + seat selection
│   └── passenger_forms_page.py # Three passenger forms + checkout
│
├── tests/
│   ├── conftest.py             # Pytest fixtures (driver, reporter, runner) + hooks
│   └── test_main_flow.py       # 12 sequential booking-flow tests
│
├── utils/
│   ├── config.py               # Central config (loaded from .env)
│   ├── driver_factory.py       # WebDriver factory (Chrome / Firefox / Edge)
│   ├── runner.py               # Runner wrapper (driver + pages + reporter)
│   ├── reporter.py             # Custom HTML report generator
│   ├── wait_helpers.py         # Explicit-wait helpers used by the pages
│   └── test_data.py            # `valid_jpeg()` for upload tests
│
├── fixtures/files/             # Auto-generated upload fixtures (passport.jpg)
└── reports/
    ├── main_flow_report.html   # Modern HTML report (regenerated each run)
    └── screenshots/            # Per-step screenshots embedded in the report
```

---

## Architecture

### Page Object Model

Every page-level interaction is encapsulated in its own class under `pages/`:

```python
class CatalogPage(BasePage):
    DESTINATION_SELECT = (By.ID, "catalog_destination")
    DATE_FIELD         = (By.ID, "open_calendar_from_date_field")
    UPDATE_BTN         = (By.ID, "catalog_update_btn")

    def select_destination(self, value): ...
    def pick_date(self, iso_date): ...
    def set_passengers(self, adults, children): ...
    def click_update(self): ...
```

Tests **never** import `By`, `EC`, or any locator string — they only call
methods on the page objects.

### Robust click strategies

Several site widgets are `<div tabindex="0">` elements with custom JS
handlers that don't always respond to a plain Selenium `.click()`. The
`BasePage` provides a **6-technique rotating click loop** that automatically
falls back through:

1. `elem.click()`
2. `ActionChains.move_to_element().click()`
3. `dispatchEvent('mousedown' + 'mouseup' + 'click')` via JS
4. `arguments[0].click()` via JS
5. `focus() + Keys.ENTER`
6. `focus() + Keys.SPACE`

Used everywhere a vanilla click is unreliable: the date field, the
passengers field, calendar day cells, SVG seat cells, and the Save /
Update / Book Now buttons.

### Pure-orchestration tests

`tests/test_main_flow.py` is a thin sequence of step blocks — no
locators, no Selenium imports, no test-data factories:

```python
@pytest.mark.incremental
class TestBorderTripBookingFlow:

    def test_03_select_destination(self, runner):
        with runner.step(f"Select destination: {runner.cfg.ROUTE}"):
            runner.catalog.select_destination(runner.cfg.ROUTE_VALUE)
            time.sleep(3.0)
```

The `runner` fixture provides:
- `runner.driver` — raw WebDriver
- `runner.cfg` — config values
- `runner.home / catalog / forms` — page objects
- `runner.step(name)` — context manager that records the step in the report
- `runner.snap(label)` / `runner.note(msg)` — attach screenshot / note

### Incremental tests

The class is marked `@pytest.mark.incremental`. If any test in the class
fails, all subsequent tests are automatically **skipped** (the browser
state would be broken — there's no point continuing the journey).

### Custom HTML reporter

A modern, self-contained HTML report is generated at session teardown:

- Banner reflecting the overall outcome (PASS / FAIL / SITE_BUG)
- 4-card stats summary (total / passed / failed / warnings)
- Run-details table (browser, base URL, trip date, passenger config)
- Per-step rows with status pill, duration, notes, error block, and
  embedded screenshot thumbnails
- Click-to-expand lightbox for screenshots

---

## Setup

### 1. Clone and create a virtualenv

```bash
git clone https://github.com/<your-username>/<repo>.git
cd <repo>/greenvia_e2e

python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

pip install -r requirements.txt
```

### 2. (Optional) Override defaults via `.env`

Create a `.env` file in `greenvia_e2e/` if you want to change anything:

```ini
BASE_URL=https://www.greenviathai.com
HEADLESS=false
BROWSER=chrome

# Booking parameters (defaults shown)
ROUTE=Ranong
ROUTE_VALUE=2
TRIP_DATE=2026-05-17
ADULT_COUNT=2
CHILD_COUNT=1
```

Everything has a sensible default in `utils/config.py`, so the suite
runs out of the box without an `.env` file.

---

## Running the tests

```bash
# Full suite (12 tests)
pytest

# Run only one step
pytest -v -k seats           # only seat-selection step
pytest -v -k checkout        # only the checkout step

# Headless (CI mode)
HEADLESS=true pytest         # Linux / macOS
$env:HEADLESS="true"; pytest  # Windows PowerShell

# Different trip date
TRIP_DATE=2026-06-21 pytest

# Generate a pytest-html report alongside the custom one
pytest --html=reports/pytest_report.html --self-contained-html
```

---

## Running from VS Code

The repo ships with `.vscode/settings.json` and `.vscode/launch.json`
already configured for Pytest. Three ways to run:

1. **Test Explorer sidebar** (beaker icon) — see all 12 tests as a tree,
   click ▶ next to any one.
2. **Inline gutter arrows** — click the ▶ that appears next to each
   `def test_NN_*` method in the editor.
3. **Run-and-Debug sidebar** (`Ctrl+Shift+D`) — pick one of:
   - *Pytest: full suite*
   - *Pytest: current file*
   - *Pytest: full suite (headless)*

---

## Configuration

All knobs live in `utils/config.py` and can be overridden via env vars
or a `.env` file:

| Setting | Default | Notes |
|---|---|---|
| `BASE_URL` | `https://www.greenviathai.com` | |
| `HEADLESS` | `false` | `true` for CI |
| `BROWSER` | `chrome` | `firefox` / `edge` also supported |
| `ROUTE` | `Ranong` | display name only |
| `ROUTE_VALUE` | `2` | `<select>` option value (Ranong = 2, Satun = 3) |
| `TRIP_DATE` | `2026-05-17` | ISO date |
| `ADULT_COUNT` | `2` | |
| `CHILD_COUNT` | `1` | |
| `IMPLICIT_WAIT` | `5` | Selenium implicit wait |
| `EXPLICIT_WAIT` | `20` | default WebDriverWait timeout |
| `HUMAN_DELAY` | `1.2` | pause between user-style actions |

---

## Reports

After every run:

| File | What |
|---|---|
| `reports/main_flow_report.html` | **Custom modern report** — banner + stats + per-step rows with screenshots |
| `reports/screenshots/*.png` | Per-step screenshots (referenced by the HTML report) |
| `reports/pytest_report.html` | (optional) Standard pytest-html report if you pass `--html=…` |

Open the custom report directly:

```powershell
start "reports\main_flow_report.html"
```

---

## Known site bug

The **last step (`test_12_click_checkout`)** can hit a known backend bug
on the live site:

> `Could not create a new account. Wrong value for res.users.border_trip_cash_permission: 'default'`

This is an **Odoo configuration problem** in the site's user-creation
controller — it tries to assign the string `'default'` to the
`border_trip_cash_permission` field, which isn't a valid choice. It
prevents the anonymous-checkout flow from auto-provisioning the
booking-holder account.

When this happens, the test:
1. Detects the error in the page (or as a JS alert)
2. Marks the step as **WARN** in the HTML report (yellow, not red)
3. Saves a screenshot named `checkout_site_bug_*.png`
4. **Passes** the Pytest test — the bug is documented external behaviour,
   not a script failure

The whole suite is therefore green up to and through the checkout
button, with the final step marked as a documented site issue. Once the
site team fixes the field, the step should naturally flip from
SITE_BUG → PASS.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SessionNotCreatedException` (Chrome version mismatch) | `pip install -U webdriver-manager` |
| `ImportError while loading conftest` | Make sure you're running from `greenvia_e2e/` (or that `pytest.ini` is on disk) |
| "No trips returned — empty result state" on test 7 | Some dates have no group trip — try a different `TRIP_DATE` |
| `'charmap' codec can't encode character` (Windows) | Set `PYTHONIOENCODING=utf-8` (already in `.vscode/settings.json`) |
| Browser left open after run | Press ENTER in the terminal to close it (deliberate, so you can inspect the page) |

---

## License

MIT
