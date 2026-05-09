# GreenVia Border Trip – E2E Test Suite

Automated end-to-end tests for [greenviathai.com](https://www.greenviathai.com) using
**Python · Pytest · Selenium WebDriver**.

---

## Project Structure

```
greenvia_e2e/
├── conftest.py                  # Shared fixtures (driver, auth, screenshots)
├── pytest.ini                   # Pytest configuration
├── requirements.txt
├── .env.example                 # Environment variable template → copy to .env
│
├── pages/                       # Page Object Model
│   ├── base_page.py             # Shared Selenium wrappers
│   ├── home_page.py
│   ├── auth_page.py             # Google OAuth
│   ├── catalog_page.py          # Route / date / passenger search
│   ├── search_results_page.py
│   ├── seat_selection_page.py
│   ├── passenger_form_page.py   # Passenger data + file upload
│   └── checkout_page.py
│
├── tests/
│   ├── test_main_flow.py        # Happy-path E2E
│   ├── test_file_uploads.py     # Upload behaviour
│   └── test_negative.py        # Validation / negative cases
│
├── utils/
│   ├── config.py                # Central config (loaded from .env)
│   ├── driver_factory.py        # WebDriver factory (Chrome / Firefox / Edge)
│   ├── wait_helpers.py          # Explicit-wait helpers
│   ├── screenshot.py            # Auto-screenshot on failure
│   ├── session_manager.py       # Cookie persistence (bypass OAuth)
│   └── test_data.py             # Passenger factories + test files
│
├── fixtures/
│   ├── files/                   # Generated test files (JPEG, PDF, PNG, …)
│   └── session_cookies.json     # Saved OAuth session (generated – see below)
│
└── reports/
    ├── report.html              # pytest-html report
    └── screenshots/             # Failure screenshots
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ (tested on 3.14) |
| Google Chrome / Firefox / Edge | latest |
| ChromeDriver | auto-managed via `webdriver-manager` |

---

## Setup

### 1. Create a virtual environment and install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env         # Windows: copy .env.example .env
```

Edit `.env`. Two auth methods are supported:

| `AUTH_METHOD` | Required env vars | Notes |
|---------------|-------------------|-------|
| `google` (default, matches task spec) | `GOOGLE_EMAIL`, `GOOGLE_PASSWORD` | Use **only** with `--setup-auth` (manual login). Scripted Google login is fragile. |
| `internal` | `INTERNAL_EMAIL`, `INTERNAL_PASSWORD` | Email + password against `/web/login`. Reliable, but the task spec asks for Google. |

### 3. Pre-flight smoke check (no auth required)

Before running the full suite, verify the public-page selectors against
the live site:

```bash
python smoke_check.py
```

Expected output: a list of `[OK]` lines ending with `Ready for pytest --setup-auth.`

### 4. Authentication setup (one-time)

Google OAuth cannot be reliably automated end-to-end (CAPTCHA, 2FA,
bot detection). Run this once:

```bash
pytest --setup-auth
```

What happens:
1. A visible Chrome window opens at `https://www.greenviathai.com/web/login`.
2. Click **"Log in with Google"** and complete the sign-in manually.
3. **First-time users:** complete the post-OAuth registration form
   (set Nationality = **Georgia**, value=78) and submit.
4. Return to the GreenVia tab.
5. Press **ENTER** in the terminal.
6. Cookies are saved to `fixtures/session_cookies.json`.

Every subsequent `pytest` run loads those cookies and skips OAuth.

> Use a dedicated test Google account. Do not use a personal account.

If cookies expire, just re-run `pytest --setup-auth`.

---

## Running from an IDE

Open the **outer** folder (`greenvia_e2e/`, the one that contains `.venv/`) in
your IDE — both VS Code and PyCharm configs are checked in.

### VS Code

1. Open the outer folder in VS Code.
2. When prompted, install the recommended extensions
   (Python, Pylance, debugpy — listed in `.vscode/extensions.json`).
3. The interpreter is already pointed at `.venv\Scripts\python.exe`
   via `.vscode/settings.json`.
4. Open the **Test Explorer** (beaker icon) — pytest discovery runs
   automatically and lists all 31 tests.
5. To debug a single test, click the ▶ next to it; or use the
   **Run and Debug** sidebar (▶ icon) and pick one of the launch configs:
   - *Pytest: full suite*
   - *Pytest: current file*
   - *Pytest: happy-path only*
   - *Pytest: file uploads*
   - *Pytest: negative tests*
   - *Pytest: setup auth (one-time)*
   - *Smoke check (no auth)*

### PyCharm

1. Open the outer folder in PyCharm. The existing project SDK
   (*Python 3.14 (greenvia_e2e)*, pointing at `.venv`) and pytest
   test runner are pre-configured in `.idea/`.
2. The run-configuration dropdown (top-right toolbar) already has:
   - *Pytest: full suite*
   - *Pytest: main flow*
   - *Pytest: file uploads*
   - *Pytest: negative*
   - *Pytest: setup-auth (one-time)*
   - *Smoke check (no auth)*
3. To debug, hit the bug icon next to any run config, or right-click
   any test function and choose **Debug 'pytest in test_…'**.
4. If PyCharm shows a "No interpreter configured" warning, go to
   **File ▸ Settings ▸ Project ▸ Python Interpreter**, click ⚙ ▸
   *Add Local Interpreter* ▸ *Existing*, and pick
   `<project>\.venv\Scripts\python.exe`.

---

## Running Tests

```bash
# All tests
pytest

# Happy-path only (fast smoke check)
pytest -m smoke

# Full E2E suite
pytest -m e2e

# Upload behaviour
pytest -m upload

# Negative tests
pytest -m negative

# Single test file
pytest tests/test_main_flow.py -v

# Run with a specific browser
BROWSER=firefox pytest

# Headless (CI)
HEADLESS=true pytest
```

### Parallel execution

```bash
pytest -n auto          # uses all CPU cores via pytest-xdist
```

### HTML report

```bash
pytest --html=reports/report.html --self-contained-html
```

Report is also generated automatically on every run (see `pytest.ini`).

---

## Test Coverage

### `test_main_flow.py` – Happy Path

| Step | Verified |
|------|---------|
| Homepage loads | ✓ |
| User is authenticated | ✓ |
| Navigate to Border Trip catalog | ✓ |
| Search: route=Ranong, 3 pax, May 17 | ✓ |
| Search params preserved in results | ✓ |
| Trip cards displayed | ✓ |
| Book Now → Seat selection | ✓ |
| 2 comfort + 1 regular seats selected | ✓ |
| Passenger form has 3 forms | ✓ |
| All forms filled (Georgia / DTV 180) | ✓ |
| Documents uploaded for all passengers | ✓ |
| Checkout page reached | ✓ |
| Booking details correct at checkout | ✓ |
| No payment triggered | ✓ |

### `test_file_uploads.py`

| Check | Outcome |
|-------|---------|
| Valid JPEG accepted | ✓ |
| Valid PDF accepted | ✓ |
| Valid PNG accepted | ✓ |
| Upload fields per passenger | ✓ |
| Invalid type (.exe) | documented |
| Oversized file (25 MB) | documented |

### `test_negative.py`

| Check | Expected |
|-------|---------|
| Empty form → validation error | ✓ |
| Missing nationality → error | ✓ |
| Missing passport expiry → error | ✓ |
| Passport expiry before 2028 | ✓ |
| Entry expiry before May 18 | ✓ |
| No document uploaded | documented |
| Invalid file type at form | documented |
| Past / far-future date search | empty state |
| Search with no route | validation error |

---

## Live-DOM Findings (Phase A discovery, 2026-05-08)

Captured by walking the public site. See [LOCATORS.md](LOCATORS.md) for full notes.

| Page | Status | Confirmed |
|---|---|---|
| Homepage | Verified by `smoke_check.py` | Login control, Border Trip nav |
| `/web/login` | Verified | Email/password fields + "Log in with Google" link (full-redirect OAuth, scope `openid+profile+email`) |
| `/web/signup` | Verified | Full registration form. Nationality `<select>`: **Georgia = value="78"** |
| `/border-trip` | Verified by `smoke_check.py` | Single-page architecture (form + filters + results). Origin/destination are native `<select>` (Phuket=1, Ranong=2, Satun=3). Submit = **"Update"** button. Date = weekday-strip buttons + "Pick a Date" calendar. |
| Seat selection | **NEEDS LIVE RUN** | Not reachable without an active booking flow |
| Passenger form | **NEEDS LIVE RUN** | Same — refine after first authenticated run |
| Checkout | **NEEDS LIVE RUN** | Same |

Findings worth noting:
- The task spec says "Internal registration is disabled", but the form at `/web/signup`
  is fully present and accepts input. Documented in TEST_REPORT as a discrepancy.
- The site is built on Odoo (URL pattern `/web/login`, `/auth_oauth/signin`).

## Known Limitations & Assumptions

### Authentication
- Google OAuth automation is unreliable by design (CAPTCHA, 2FA, bot detection).
- Workaround: `--setup-auth` manual setup with cookie persistence.
- Tests requiring auth use a session-scoped driver to minimise OAuth calls.
- Internal email/password login is also wired (set `AUTH_METHOD=internal`) as a
  fallback if Google is blocked.

### Locators
- Public-page selectors (homepage, /web/login, /web/signup, /border-trip) were
  verified live via `smoke_check.py` and direct DOM inspection.
- Gated-page selectors (seat selection, passenger form, checkout) are educated
  guesses based on common patterns + the Odoo architecture. Refine these after
  the first authenticated run; failure screenshots saved in `reports/screenshots/`
  pinpoint the locators that need updating.

### Date picker
- The catalog uses a horizontal weekday-button strip (covering ~6 days) plus a
  "Pick a Date" button that opens a calendar widget for arbitrary dates.
- `CatalogPage.select_date()` clicks the strip button if the target falls in
  the visible range; otherwise it opens the calendar and steps month-by-month
  using common datepicker class names. The exact calendar markup is unconfirmed
  and may need tuning after the first run.

### File size limit
- No explicit size limit is documented. The oversized-file test (25 MB) records
  the actual response in TEST_REPORT rather than failing hard.

### Negative validation
- Some negative tests use `pytest.xfail` when behaviour is ambiguous (e.g.
  server-side-only validation invisible in the DOM). These are flagged in the
  report so reviewers can distinguish "not implemented yet" from "site behaviour
  unclear".

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `SessionNotCreatedException` | Update ChromeDriver: `pip install -U webdriver-manager` |
| OAuth CAPTCHA / 2-FA | Use `--setup-auth` with an app-password or trusted device |
| Locators not finding elements | Run with `HEADLESS=false`, inspect DOM, update Page Objects |
| `SESSION_COOKIE_FILE` missing | Run `pytest --setup-auth` first |
| Oversized file test hangs | Reduce size in `.env` or skip: `pytest -k "not oversized"` |
