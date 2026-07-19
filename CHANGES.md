# CHANGES — Citizen/Bot/Staff Dashboard Integration

Everything from the integration plan, actually implemented against your
repo. Read this before deploying — the "Verification status" section at
the bottom is important since I could not run the app live in this
environment (no network access to install dependencies).

## New files

- `app/services/citizen_service.py` — shared identity/dedup logic (used by
  the bot, web registration, and Field Officer registration)
- `app/services/checkin_service.py` — "are you safe?" campaign logic
- `app/services/beneficiary_service.py` — search/filter backing the new
  verification directory screens
- `app/models/checkin.py` — `CheckIn` / `CheckInResponse` models
- `app/routes/api.py` — `/api/lookup/beneficiaries`, `/api/lookup/users`
  (backs the person-picker widget)
- `app/static/js/entity-picker.js` — reusable typeahead component
- `app/templates/gov_officer/aid_requests.html` + `field_officer/aid_requests.html`
- `app/templates/gov_officer/beneficiaries.html` + `super_admin/beneficiaries.html`
- `app/templates/super_admin/checkins.html` + `checkin_detail.html`
- `migrations/versions/f3a8c1d2e6b7_add_user_location_fields_and_checkin_.py`

## Changed files (by feature)

**Bug fix — registration approval data loss**
- `app/routes/gov_officer.py`: `approve_registration`/`reject_registration`
  now delegate to `approval_service` instead of a second, drifted
  implementation that never linked the new `Beneficiary` to
  `citizen_user_id`.

**Identity/dedup consolidation**
- `app/services/citizen_service.py` (new): `register_or_link_citizen()`
  is the one place "does this ID already have a record" gets decided.
- `app/bot/handlers.py`: `continue_register`'s confirm step now calls the
  shared service instead of its own inline User/Beneficiary creation.
- `app/routes/citizen.py`: `register()` now collects full name + optional
  ID and runs the same dedup check as the bot; `profile()` no longer
  risks a unique-constraint collision if a Field-Officer-created record
  already exists for that ID.
- `app/routes/field_officer.py`: `register_citizen_to_shelter()` now
  **always creates a real `User`** (previously created a `Beneficiary`
  with no login at all — the reason those citizens could never be
  notified of approval/rejection, since they had no account to notify).

**`/requestshelter` bot command**
- `app/bot/handlers.py`: new flow, distance-sorted via
  `geo_service.haversine_distance` when the citizen has a saved location,
  reuses the existing `apr_reg`/`rej_reg` approval buttons unchanged.

**Aid-request dashboards** (previously `CitizenAidRequest` had zero web
routes or templates anywhere — bot-only)
- `app/routes/gov_officer.py` + `field_officer.py`: new `aid_requests`,
  `aid_request_in_progress`, `aid_request_resolve` routes, all delegating
  to the existing `approval_service.mark_aid_in_progress/resolved` so the
  web buttons and Telegram buttons share one state machine.

**Location capture**
- `app/models/user.py`: added `latitude`, `longitude`, `location_updated_at`.
- `app/bot/handlers.py`: `process_update()` now handles Telegram
  `message.location` (previously silently dropped — it only checked for
  `'text' in message`).
- `app/routes/citizen.py`: new `POST /citizen/location` endpoint.
- `app/templates/citizen/dashboard.html`: "Share my location" button using
  the browser Geolocation API.
- `app/routes/citizen.py` `shelter_request()`: sorts the shelter list by
  distance when the citizen has a saved location.

**Check-in campaigns**
- `app/models/checkin.py`, `app/services/checkin_service.py` (new).
- `app/services/notification_service.py`: `notify_segment()` now accepts
  `reply_markup` and an explicit `users` list (previously had no way to
  attach inline buttons to a broadcast at all).
- `app/bot/handlers.py`: `chk_safe`/`chk_help` callback actions; tapping
  "Need help" auto-creates a `CitizenAidRequest` (feeds the aid-request
  dashboard above) rather than being a fourth parallel request type.
- `app/routes/super_admin.py`: `checkins()` (launch) and `checkin_detail()`
  (per-campaign response map) routes.

**Analytics map — citizen layer**
- `app/services/geo_service.py`: new `get_citizen_points()`, extended
  `get_all_locations_geojson()`; deduplicated `geo_services.py` into a
  thin re-export (it was a byte-for-byte copy before).
- `app/routes/super_admin.py` `analytics()`: added `citizens_geo` to the
  existing map data and `recent_checkins` to the page context.
- `app/templates/super_admin/analytics.html`: citizen markers + legend
  entry, recent check-ins summary block.

**Beneficiary/verification directory**
- `app/services/beneficiary_service.py` (new), routes + templates for
  both Gov Officer and Super Admin.

**Reusable person/place picker**
- `app/routes/api.py`, `app/static/js/entity-picker.js`, wired into
  `field_officer/register_citizen.html` as the first consumer — searching
  before submitting is what actually prevents the duplicate-record
  problem `citizen_service.py` was built to close.

**Template plumbing**
- `app/templates/base.html`: added a `{% block scripts %}` — didn't exist
  before, needed so per-page JS (the picker, the geolocation button)
  loads without stuffing it into `content`.

## Verification status — please read before deploying

This sandbox has **no network access**, so I could not `pip install` the
project's dependencies or actually boot the Flask app. What I *did* do
instead:

1. **Syntax-checked every changed/new `.py` file** with `py_compile` —
   all clean.
2. **Traced the logic by hand** for the riskier spots (found and fixed
   two real bugs this way before you'd have hit them: a double-tap on
   "Need help" would have created a duplicate aid request each time, and
   a repeat tap was showing the wrong confirmation message — both fixed
   in `checkin_service.py`).
3. **Hand-wrote the Alembic migration** to match the exact defensive
   style (`if 'x' not in existing_columns`) of your existing head
   migration, then **tested the actual SQL against a throwaway copy of
   your real `sahananeth_local.db`** (not the live file) — confirmed the
   new columns and tables create cleanly and round-trip an insert/select.
4. **Unit-tested the distance-sorting logic** (used in `/requestshelter`
   and the web shelter-request page) standalone in pure Python — confirms
   it picks the genuinely nearest shelter given real coordinates.

What I could **not** do: actually run `flask db migrate --autogenerate`
(to have Alembic confirm my hand-written migration matches the models
exactly), start the dev server, click through the new pages, or send a
real Telegram update through the webhook. Before deploying:

```bash
pip install -r requirements.txt
flask db upgrade          # applies migrations/versions/f3a8c1d2e6b7_...
flask run                 # or your usual run command
```

Then smoke-test in this order (most-likely-to-break first): Field Officer
→ Register Citizen (search box should suggest matches as you type) →
Gov Officer → Beneficiary Directory (should show it) → Gov/Field →
Citizen Aid Requests → bot `/requestshelter` → Super Admin → Safety
Check-in → launch one to yourself → tap the buttons in Telegram → check
`/admin/checkins/<id>` shows your response on the map.

## Known remaining item (documented, not fixed)

`continue_register`'s `link_confirm` step in `handlers.py` (the "we found
an existing record, reply LINK to connect" branch) still has its own
inline `User` creation rather than calling `citizen_service.py` — I left
it alone because it's Telegram-specific confirmation-flow logic that
isn't obviously reusable, and touching it wasn't necessary to fix the
duplicate-record problem (that's now caught earlier, at the point of
registration, everywhere). Worth consolidating later for consistency, not
urgent.
