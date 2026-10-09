# Playwright Python UI/API Framework

[![QA verification](https://github.com/tombeng027/playwright-pytest-ui-api-framework/actions/workflows/qa.yml/badge.svg)](https://github.com/tombeng027/playwright-pytest-ui-api-framework/actions/workflows/qa.yml)

Personal QA portfolio project: test a local, synthetic work-order application through its UI and API.

**Current status:** milestone 1 and Goals 1-4 complete for the agreed scope; published with verified Windows/Ubuntu CI. The default suite contains 46 API, 8 UI, 1 cross-layer and 1 middleware case, including parameterized variations. Portfolio walkthrough/presentation polish remains next.

## What this demonstrates

- API setup -> browser status changes -> API verification of persisted results.
- Server-side validation and invalid transitions that preserve existing state.
- Functional authentication, including server-side logout invalidation.
- Per-test SQLite databases and application instances.

This is not professional Playwright experience, a security audit or a production-ready application.

## Setup (Windows PowerShell)

Use Python 3.12-3.14; only versions actually executed will be listed as verified below.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -e ".[test]"
.\.venv\Scripts\python.exe -m playwright install chromium
```

On Linux/macOS, create `.venv` with `python3 -m venv .venv` and use `.venv/bin/python`. Linux browser installation may require `python -m playwright install --with-deps chromium`.

Run the current suite:

```powershell
.\.venv\Scripts\python.exe -m pytest --browser chromium --html=artifacts/report.html --self-contained-html --junitxml=artifacts/results.xml
```

Select critical paths with `-m smoke`. No external demo websites, Docker or cloud credentials are required at test runtime.

## Try the application

```powershell
.\.venv\Scripts\python.exe -m demo_app
```

Open `http://127.0.0.1:8000`. Synthetic credentials: `demo` / `demo-password`.

Stop with Ctrl+C. Manual execution persists data in `demo.sqlite3` (ignored by Git); tests use temporary databases instead.

## Application contract

See [the business rules](docs/business-rules.md). Tests assert expected values independently of the application's transition logic.

## Architecture and limitations

- FastAPI serves plain HTML/JavaScript and a REST API; SQLite stores customers, orders and sessions.
- Tests use Playwright's HTTP client for API calls and Chromium for browser interactions.
- Each test starts a Uvicorn server on a pre-bound ephemeral localhost socket, in a dedicated thread. This avoids a port-selection race and supports Windows without sharing state.
- Fixtures check readiness with bounded polling and close their server/socket after each test; pytest owns temporary directories.
- Sessions use a synthetic fixed account, have no expiry and use non-secure cookies for localhost HTTP. Do not deploy this app publicly.
- UI coverage includes login errors/recovery, creation/editing/logout, required and whitespace fields, filtering, completed restrictions and literal text rendering. A focused page object shares interactions while tests retain assertions.
- API checks include boundary values, missing fields, protected endpoints, unknown customers/orders, edit restrictions and the invalid-transition matrix. Rejected writes are checked for unchanged state.
- GitHub Actions runs on Windows/Ubuntu with Python 3.14 and Chromium; both hosted jobs are verified. Other Python versions, browsers and parallel execution are not yet verified.

## Verification

Verified on Windows with Python 3.14.3 and Playwright Chromium:

- Four tests passed on three consecutive runs: 4.45s, 4.06s and 4.07s.
- pytest-html and JUnit XML reports generated in `artifacts/`.
- JavaScript syntax check and `pip check` passed.
- Manual browser login and UI order creation verified.

These are milestone results, not a claim of complete coverage or CI success. See [milestone 1 review](docs/milestone-1-review.md).

After Goal 1 expansion, all 53 cases passed on three consecutive runs (45.76s, 46.36s, 45.33s) without retries or skips. Updated HTML/JUnit reports are in `artifacts/`. See [progress and remaining goals](docs/progress.md).

With logging added, all 55 cases passed in 48.79s. Request correlation and sensitive-field exclusion are tested; all 54 server-backed tests logged successful shutdown. See [logging locations, fields and limitations](docs/logging.md).

Goal 2's separate failing probe verified browser observations, full-page screenshots, traces and cleanup. The default 55-case suite then passed in 50.59s. See [failure diagnostics and reproduction](docs/failure-diagnostics.md). Raw traces contain synthetic data and must be reviewed before sharing.

Goal 3 verified baseline pass, a precise failure against an explicitly injected transition defect, and restored-default pass. The full suite then passed in 51.83s. See [the defect example](docs/defect-example.md) and run `python scripts/verify_defect.py` with the project venv to reproduce it.

An additional regression reproduces and prevents pytest capture from re-enabling raw Uvicorn access records. The updated 56-case suite passed in 51.83s. See [access-log investigation](docs/access-log-investigation.md).

A fresh non-editable install passed all 56 tests in 53.74s from outside the checkout. Installed static assets and dependency consistency were verified. See [reproducibility, CI and editor setup](docs/reproducibility-and-ci.md).

The [first hosted CI run](https://github.com/tombeng027/playwright-pytest-ui-api-framework/actions/runs/37889100220) passed on both runners:

| Runner | Python | Default suite | Controlled defect |
|---|---|---|---|
| Ubuntu | 3.14.8 | 56 passed in 33.85s | Baseline pass, exact mutation failure, restored pass |
| Windows | 3.14.7 | 56 passed in 65.91s | Baseline pass, exact mutation failure, restored pass |

Downloaded artifacts were checked against their published SHA-256 digests. Both JUnit reports have zero failures, errors or skips in the default suite; all 55 server-backed logs per runner end with `app_stopped`. HTML reports, dependency snapshots and separate defect evidence were retained. Artifact retention is seven days; the deliberate browser failure probe remains a separate local demonstration.

If VS Code reports missing pytest/Playwright imports, open this repository as a workspace and select `.venv\Scripts\python.exe`. The parent labs workspace may still have another project's interpreter selected. Tests run with the explicit venv command above.
