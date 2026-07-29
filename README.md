# HR Management System

A small internal tool for employee records, leave management, and payroll, built for the Vunoh coding challenge.

## Stack
- Backend: Flask + Flask-SQLAlchemy
- DB: SQLite locally (auto-created, zero setup), PostgreSQL in production (Render)
- Frontend: vanilla HTML/CSS/JS, single dashboard page, no build step, no framework

## How to run locally

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

python seed.py      # optional: populate sample data
python run.py
```
Visit `http://localhost:5000`.

Locally the app uses SQLite automatically — no `DATABASE_URL` needed. In production
(Render), setting the `DATABASE_URL` environment variable switches it to PostgreSQL
with no code changes required (see `app/__init__.py`).

Run tests:
```bash
pytest -v
```
Unit tests cover payroll math and leave rules in isolation; integration tests cover
the full API including approvals, withdrawals, reversible decisions, the payroll lock,
overlapping-request validation, and payroll generation/export. Tests always run
against an in-memory SQLite DB regardless of `DATABASE_URL`, so they're unaffected by
the production database.

## Live demo
https://hr-management-system-os6q.onrender.com/

## What I prioritized, and why

The brief said it's better to do one or two modules properly than three shallowly.
I prioritized in this order:

1. **Payroll calculation logic** — the most testable, most "real business logic" part
   of the brief: tax brackets, pro-ration, mid-month joiners, the leave→payroll link.
2. **Leave management rules and lifecycle** — going beyond a simple request/approve
   form to handle the realistic cases below.
3. **Employee records / org view** — simple CRUD, manager-based org view,
   soft-deactivate, with team/manager assignment exposed in the UI.

## Leave management: problems identified and what I built

1. **Short-notice requests slip through unnoticed.** Requests submitted with less than
   `MIN_NOTICE_DAYS = 3` days' notice are flagged (not blocked) so they're visible to
   the manager instead of being a surprise.
2. **Team under-coverage.** If approving a request would push concurrent approved
   leave for that team above `TEAM_COVERAGE_THRESHOLD = 40%`, it's flagged — a warning
   surfaced to the manager, not a hard block.
3. **Requests sitting unanswered.** Anything pending more than `STALE_HOURS = 48` is
   flagged as stale everywhere it appears, so nothing quietly rots in a queue.
4. **Leave balance overruns.** Requests exceeding remaining balance aren't blocked —
   the excess is marked unpaid at approval time. This is the leave→payroll link:
   `unpaid_days` on an approved request flows directly into that employee's next
   payslip, reducing gross pay pro-rata.
5. **Duplicate/overlapping requests.** A new request is rejected outright at
   submission if the same employee already has a pending or approved request
   covering any of the same dates — a hard validation error, since this is a
   data-integrity problem rather than a judgment call for a manager to weigh.

### Reversible decisions, withdrawal, and the payroll lock

Real leave decisions get reversed — an employee's plans change, or a manager
reconsiders. So beyond the four states (`pending`, `approved`, `rejected`,
`withdrawn`):

- **Withdraw** is allowed on `pending` or `approved` requests. Withdrawing an
  approved request gives back whatever balance it had consumed.
- **Decisions are reversible** — an approved request can be rejected after the fact,
  and a rejected one can be approved after the fact. Whichever direction it flips,
  the prior financial effect (balance consumed or not) is undone before the new
  effect is applied.
- **Payroll lock:** none of the above is allowed if a payroll run already exists for
  any month the request's dates fall into. Without this, an already-generated payslip
  could silently become wrong the moment a leave decision changed after the fact —
  exactly the kind of quiet payroll error a real system has to guard against. The
  error message names the specific locked period so it's clear why the action was
  refused, not just that it failed.

All thresholds live as named constants at the top of `app/rules.py`.

## Payroll formula and assumptions

Documented in `app/payroll_calc.py`, summarized here:

- **Working days** = calendar days minus Sundays (simple 6-day week assumption, no
  holiday calendar — noted under improvements below).
- **Gross pay:**
  `gross_pay = (monthly_salary / working_days_in_month) × (working_days_in_month − unpaid_days)`
  `unpaid_days` includes both approved unpaid leave and days before a mid-month
  joiner's start date.
- **Tax:** marginal bracket scheme, each bracket taxed only on income within it:
  | Bracket | Rate |
  |---|---|
  | 0 – 24,000 | 10% |
  | 24,000 – 32,333 | 25% |
  | 32,333+ | 30% |
  Illustrative figures, not a real country's actual brackets, as instructed.
- **Social security:** flat 6% of gross, capped at 2,160/month.
- **Net pay:** gross − tax − social security, floored at 0 as a safety check.

### Edge cases handled (and tested)
- Mid-month joiner: pro-rated from `start_date`.
- Joining entirely after the payroll period: correctly resolves to 0 pay.
- Salary at/near a bracket boundary: confirmed marginal, not cliff, taxation.
- Zero-deduction low salary and zero salary: no negative net, no divide-by-zero.
- Approved unpaid leave reduces gross pay proportionally, including when a leave
  request spans two payroll periods (unpaid days are split by day-overlap).
- Payroll can't be generated twice for the same period.

## Frontend

Single vanilla-JS page (`frontend/app.js`), no framework, no build step. Built as a
ledger/registry-themed dashboard — tabbed navigation, tabular numerals for all
figures, a rubber-stamp animation on approve/reject actions — since a payroll tool's
own visual vocabulary (ledgers, stamps, pay stubs) fit the subject better than a
generic dashboard template.

**Architecture notes:**
- All user-supplied text (employee names, roles, team names, search input) is passed
  through an `escapeHTML()` helper before being inserted into the page, since it's
  injected via `innerHTML`. Without this, a name typed into the Add Employee form
  could contain executable markup that would run in another user's browser when they
  later view that data — a stored XSS risk given this app has no authentication
  separating who can enter data from who views it.
- Interactivity uses event delegation (a handful of listeners on `document`, keyed off
  `data-action`/`data-sort-*` attributes) rather than inline `onclick` handlers, so
  markup stays free of embedded behavior and listeners don't need re-attaching on
  every re-render.
- Search boxes update only their own table container on `input`, not the whole tab,
  so the input never loses focus mid-keystroke.

## API overview
- `GET/POST /api/employees`, `PATCH /api/employees/<id>`, `POST /api/employees/<id>/deactivate`
- `GET /api/employees/org-chart`, `GET/POST /api/employees/teams`
- `GET/POST /api/leave`, `POST /api/leave/<id>/approve|reject|withdraw`
- `GET /api/leave/balances/<employee_id>`, `GET /api/leave/balances` (all employees)
- `GET /api/leave/who-is-out`
- `GET /api/payroll` (list every run ever generated)
- `POST /api/payroll/generate`, `GET /api/payroll/<year>/<month>`
- `GET /api/payroll/<year>/<month>/export` (CSV download)

## Stretch features added

1. **Leave balances dashboard panel** and **notification banner** for flagged/stale
   pending requests — surfaces risk at a glance rather than requiring a manager to
   read every row's flags column.
2. **CSV export of any payroll run**, plus a persistent "Past Payroll Runs" list —
   since a period can only be generated once, this is how generated payslips stay
   accessible indefinitely afterward.
3. **Search, sort, and confirmation dialogs** on the Employees and Leave tables, and
   the withdraw/reversible-decision system described above with its payroll-lock
   safeguard.

## SQL dump
`schema_and_data.sql` contains the PostgreSQL schema plus sample teams, employees,
leave requests (including an over-balance/unpaid case and a short-notice case), and
one generated payroll run — all produced by `seed.py`, which generates that payroll
period using the same tested `calculate_payslip()` logic the live API uses, so the
seeded numbers are guaranteed correct rather than hand-typed. Regenerate with:
```bash
python seed.py
pg_dump "<DATABASE_URL>" > schema_and_data.sql
```

## What I'd improve with more time
- Real authentication/roles — `decided_by` is currently free text, not tied to a
  logged-in manager account.
- A public holiday calendar instead of the Sunday-only working-days assumption.
- Partial-day leave (currently whole days only).
- Multiple leave types (annual/sick/unpaid) with separate balances, and accrual over
  time instead of a flat 21-day upfront allocation.
- A similar lock/history safeguard for salary changes, mirroring the payroll lock
  already built for leave.
- Payslip PDF export alongside the CSV.
- Server-side date checks (e.g. "who's out today") use UTC; a production deployment
  serving a specific timezone would need to account for that explicitly.