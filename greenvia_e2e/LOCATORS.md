# GreenVia Live-Site Locator Reference

Captured 2026-05-08 via Chrome MCP read-only DOM inspection.
Pages requiring user interaction (gated by login) are marked `[NEEDS LIVE RUN]`.

---

## 0. Site shell (every page)

- Main nav menu items (anchor `href`):
  - `/` — Home (logo link)
  - `/border-trip` — Border Trip
  - `/private-transfers` — Private Transfers
  - `/arrival-airport-assistance` — Arrival Airport Assistance
  - `/about-us`, `/faq`, `/legal-policy`, `/contactus`
- Currency button: `button` with text `"THB"`
- Login control: `button` with text `"Log in/Sign up"`, `href="#"` — opens via JS (modal or in-page)

---

## 1. Homepage (`/`)

- **Title:** `"Transport Home Page | Greenvia"`
- **Login button:** desktop and mobile both have `button[text()="Log in/Sign up"]` (`href="#"`)
- **Direct login URL exists:** `/web/login`
- **Direct signup URL exists:** `/web/signup`
- **Logged-in indicator:** TBD — when not logged in, "Log in/Sign up" button is present. When logged in, this presumably becomes a profile menu/avatar. **[NEEDS LIVE RUN to confirm]**

---

## 2. Login (`/web/login`)

- **Title:** `"Login | Greenvia"`
- **Email field:** `input[type="text"][placeholder="Email"]` (also `name="login"` per Odoo convention — to verify)
- **Password field:** `input[type="password"][placeholder="Password"]`
- **Submit button:** `button[type="submit"]` with text `"Log in"`
- **Google OAuth link:** `a` with text `"Log in with Google"`. URL:
  `https://accounts.google.com/o/oauth2/auth?response_type=token&client_id=1052198960819-buuhtaufd8jmhgm6q9lvqq7mufcnrt5a.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fwww.greenviathai.com%2Fauth_oauth%2Fsignin&scope=openid+profile+email&state=...`
  - OAuth redirect URI: `/auth_oauth/signin`
  - Scopes: `openid profile email`
- **Reset password link:** `a[href="/web/reset_password"]`
- **Sign-up link:** `a[href="/web/signup"]` text `"Don't have an account?"`

**Note:** Site is built on Odoo (URL pattern `/web/login`, `/auth_oauth/signin` are Odoo conventions). This means the underlying form likely uses Odoo's standard HTML — `input[name="login"]` for email, `input[name="password"]` for password.

---

## 3. Sign-up (`/web/signup`)

**Important:** The task spec says "Internal registration is disabled" but the form is fully present and accepts input. Treat this as a **discrepancy** to record in TEST_REPORT.

Form fields (in order):
1. **Email:** `input[type="text"][placeholder="Your Email"]`
2. **First name:** `input[type="text"][placeholder="e.g. John"]`
3. **Last name:** `input[type="text"][placeholder="e.g. Doe"]`
4. **Date of birth:** `input[type="date"]` (native HTML5 date picker, ISO format)
5. **Contact phone:** `input` (no type/placeholder seen — likely `type="tel"`)
6. **Citizenship/Nationality:** `<select>` with first option `"Select Nationality"`. **Georgia value="78"** (alphabetical, NOT a country code).
7. **Password:** `input[type="password"]`
8. **Confirm password:** `input[type="password"]`
9. **Submit:** button with text `"Sign up"`
10. **Google OAuth alternative:** same as on login page

**Same form likely appears post-OAuth-signin** for first-time Google users to complete profile (with Georgia nationality required per the task spec). **[NEEDS LIVE RUN to confirm post-OAuth registration form path]**

---

## 4. Border Trip Catalog + Search Results (`/border-trip`)

**Architecture finding:** This is a single-page app. The search form, filters, and results are **all on the same URL** (`/border-trip`). There is no separate `/catalog` and `/search-results` URL.

URL query params (`?origin=1&destination=2&date=...&passengers=3`) are **NOT** read by the page — form state is JS-driven.

### Search form

- **Origin:** `<select>` (combobox) — currently shows only `"Phuket"` (value=1) selected. Other options hidden until clicked.
- **Destination:** `<select>` (combobox), placeholder `"Destination"`. Visible options:
  - value=2 → `"Ranong"` (THE TARGET)
  - value=3 → `"Satun"`
- **Swap button:** `button[type="button"]` with aria-label `"Swap origin and destination"`
- **Date display:** generic element (ref_15) showing currently-selected date label, e.g. `"Sat, May 9"`
- **Passenger count display:** generic showing `"1 Passenger"`. Clicking opens a panel with heading `"Passengers"` (ref_149 in some renders). **[NEEDS LIVE RUN to confirm increment/decrement controls]**
- **Submit button:** `button[type="button"]` with text `"Update"` (NOT "Search").

### Date selection

The form has a row of pre-rendered date buttons (single-day buttons), e.g.:
- `"Tomorrow"`, `"Sun, May 10"`, `"Mon, May 11"`, ..., `"Fri, May 15"`

For arbitrary dates (e.g., **May 17**), use:
- **`button` with text `"Pick a Date"`** — opens calendar widget. **[NEEDS LIVE RUN to confirm calendar markup]**

### Filters (sidebar)

- Sort: `"Recommended"` heading + radios
- **Departure time:** checkboxes — `"00:05"`, `"01:00"`, `"04:00"`, `"05:00"`
- **Transport type:** filter labels include `"VAN"`, `"Alphard"`

### Trip results (inline cards below filters)

Each trip card shows: date, departure time, seats-left badge, amenity icons (Wi-fi/Charge/Meals/Blanket), origin → destination, price (e.g., `"4,500.00 ฿"`), and a CTA.

CTA varies by trip type:
- **Simple (single-destination) trip:** `link` text `"Book now"`, `href="#"` — JS-driven.
- **Multi-stop trip:** `button "Configure Trip"` and `button "Trip details"`.

Result count hint: at least 3 trips visible without specifying any params (default state).

---

## 5. Seat Selection — `[NEEDS LIVE RUN]`

Reachable only after clicking `"Book now"` on a trip card (cannot reach via direct URL).

To discover during Phase C:
- URL slug after Book Now (likely `/booking/<id>` or modal stays on `/border-trip`)
- Seat element class names — `comfort` vs `regular`, selected-state class
- Seat counter / total display
- "Continue" / next-step button

---

## 6. Passenger Form — `[NEEDS LIVE RUN]`

Per spec, must contain N=passenger-count form sections, each with:
- First name, Last name (likely)
- Nationality dropdown — should be the same widget as on /web/signup (Georgia=78)
- Visa type dropdown — must include option `"DTV 180"` (verify exact spelling)
- Passport number, Passport expiry date
- Entry stamp / current-stay expiry date
- File upload(s) — type `<input type="file">` ideally; `accept` attribute will tell us allowed MIME types

To discover: per-passenger field locator pattern (likely `[data-passenger-index="N"]` or indexed), date-input format, file-input `accept` attribute, validation behaviour.

---

## 7. Checkout — `[NEEDS LIVE RUN]`

Reachable only after submitting the passenger form. Per task spec, payment is disabled — checkout is the final stop.

To discover: URL slug, heading text, booking-summary fields (route, date, passenger count), absence of working payment button.

---

## 8. Open questions / assumptions

| Item | Assumption | Confirmation needed |
|---|---|---|
| Internal signup actually works | Form is present, but task spec says "disabled" | Try submitting → check for error |
| Logged-in indicator | Profile menu replaces "Log in/Sign up" | Live run after OAuth |
| Date format on passenger form | ISO `YYYY-MM-DD` (matching /web/signup DOB) | Live run |
| File upload accept | Likely `image/*,application/pdf` | Inspect `accept` attribute |
| File size limit | None documented in task spec | Try 25 MB upload |
| Document upload mandatory | Task spec implies yes; needs verification | Try submitting without upload |
| Visa type "DTV 180" exact string | Match dropdown option | Live run |
