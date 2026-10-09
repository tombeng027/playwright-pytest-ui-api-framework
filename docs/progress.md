# Repository Progress

Updated October 9, 2026. This tracks verified work, not merely planned features.

## Milestone 1 baseline

Complete: local FastAPI/SQLite app, synthetic authentication, seeded customers, independent test databases/servers, documented rules, one cross-layer workflow and three API checks.

Four tests passed on three consecutive Windows/Python 3.14.3/Chromium runs without retries. HTML and JUnit reports generated. JavaScript syntax and dependency consistency checks passed.

Review: [Milestone 1](milestone-1-review.md).

## Next goals

| Goal | Status | Completion criteria |
|---|---|---|
| 1. Risk-focused UI/API coverage | Complete for agreed scope | UI creation/editing, login errors, validation, filtering, completed restrictions and safe text; API boundary/negative cases and rejected-write state checks verified |
| 2. Failure diagnostics | Complete for agreed scope | Correlated logs, browser observations, full-page screenshot/trace and server teardown verified through intentional failure |
| 3. Defect detection | Complete for agreed scope | Unchanged transition test passed baseline/restored runs and failed mutated behavior for the precise 200-versus-409 assertion |
| 4. Portability and CI | In progress | Pinned dependency snapshot and fresh installed-package run verified; editor guidance/workflow written; hosted Actions and parent editor alignment pending |
| 5. Portfolio release | Pending | README, coverage map, defect example and interview walkthrough complete; publication approved and CI inspected |

## Review decisions

- Keep the application small; no inventory, payments or extra business modules.
- Use focused page objects only for repeated UI interactions. Keep assertions in tests.
- Verify response fields and persisted state, not just status codes.
- Tests do not import the application's expected-transition logic.
- Per-test server threads and pre-bound sockets avoid port-selection races. Exercise cleanup on failures in Goal 2.
- Three passing runs establish current repeatability, not complete coverage or long-term stability.
- No retry-based masking, silent skips or claims of unexecuted CI.

## Outstanding limitations

- Editor discovery and Pylance interpreter alignment remain unresolved in the parent workspace.
- Only Windows, Python 3.14.3 and Chromium have been executed.
- Version ranges currently permit dependency changes; fresh setup and reproducibility remain Goal 4 work.
- No commits, GitHub remotes or publication yet.

## Goal 1 execution

53 collected test cases (including parameterized variations): 44 API, 8 UI and 1 cross-layer.

| Run | Result | Duration |
|---|---|---|
| Expanded suite with reports | 53 passed | 45.76s |
| Repeat 1 | 53 passed | 46.36s |
| Repeat 2 | 53 passed | 45.33s |

No retries or skips. HTML/JUnit reports regenerated. Pylance syntax checks passed for both new test modules.

The first browser run uncovered a locator mismatch: a wrapping customer label with dynamic option text did not match `get_by_label("Customer", exact=True)`. A focused Playwright reproduction returned zero exact matches before and one after explicit label association. The application now uses explicit `for`/`id` associations for customer and status filter. No timeout extensions or weakened locators were used.

A focused `WorkOrdersPage` helper now shares interactions between UI and cross-layer tests; assertions remain in the scenarios.

Next: Goal 2, failure diagnostics and cleanup verification. Current passing reports are not proof that failure artifacts work.

## Goal 2 logging scope

Review confirmed that existing output is mainly Uvicorn lifecycle messages; request access logging is disabled. Persistent, correlated application logs have not been implemented.

Add focused observability, not a monitoring platform:

- Structured application request records: UTC timestamp, level, generated request ID, method, route template (not raw query strings), response status and duration.
- Correlate requests with a response request-ID header; log unexpected failures and propagate them rather than returning success.
- Test lifecycle records: test identity, app ready/stopped and diagnostic artifact location. Keep application logging isolated per app/test.
- Browser console errors and failed requests retained as failure evidence. Distinguish HTTP error responses from network failures and expected negative-test responses.
- Never log passwords, cookies, authorization headers, session tokens, request/response bodies or user-entered order text.
- Keep generated logs in ignored artifact directories; provide only sanitized representative samples in documentation.
- Verify successful requests, rejected requests, correlation and absence of sensitive values. Logging must not change API business behavior.
- Inspect the deliberate browser failure's screenshot, trace and logs together; verify server cleanup afterward.

Do not add cloud logging, Splunk integration, a log dashboard or claims of production monitoring. Logs show what was observed; they do not alone prove correctness or defect-free operation.

## Logging execution

- Implemented allowlisted JSON request events, generated response request IDs and per-test lifecycle records.
- Added correlation/privacy and exception-propagation tests.
- Two focused logging tests passed; full suite passed: 55 cases in 48.79s, no retries or skips.
- Inspected all 54 application-backed test logs: every file ended with `app_stopped`.
- Pylance reported no diagnostics for the observability module.
- Middleware test runs its async exercise on a dedicated thread because Playwright's sync session owns a running loop on the pytest thread.
- Browser console/network capture and failure artifacts are not yet implemented. Passing-run shutdown records do not establish failure-path cleanup.

Details: [Logging](logging.md).

## Goal 2 completion

- Added browser console/page error, HTTP error and network-failure observations without message text, URLs or bodies.
- Enabled failure-only full-page screenshots and retained traces through pytest-playwright.
- Explicit-only diagnostic probe failed for the exact expected assertion; no setup/teardown errors.
- Opened the screenshot and inspected ZIP integrity, exact assertion and DOM snapshot records in the trace.
- Verified browser-to-application request correlation, sensitive-sentinel exclusion and `app_stopped` after failure.
- Full normal suite passed afterward: 55 tests in 50.59s without retries/skips.
- Editor Problems reported no errors in the updated fixture and observability files.

Evidence, commands and privacy limitations: [Failure diagnostics](failure-diagnostics.md).

Next: Goal 3, controlled business-rule defect detection. The diagnostic probe's intentionally wrong expectation is not a substitute for a test catching an application defect.

## Goal 3 review and completion

Quick review found no urgent blocker to the scoped demonstration. Existing state assertions, per-test isolation and diagnostic evidence remain intact. CI, fresh setup and publication are still pending; do not describe the project as release-ready.

- Added a default-off test-only flag allowing Pending -> Completed.
- Verified baseline pass, exact mutated failure and restored-default pass using the same regression test.
- Verifier rejects unrelated failures, skips, setup/teardown errors or missing shutdown/transition evidence.
- Separate baseline/mutated/restored reports and logs preserve comparison evidence.
- Full default suite passed afterward: 55 cases in 51.83s without retries/skips.
- Editor Problems reported no errors in changed application, fixture and verifier files.

Example and reproduction: [Controlled defect](defect-example.md).

Next: Goal 4, fresh-environment reproducibility, editor setup and CI. GitHub publication still needs approval.

Review note for Goal 4: the diagnostic probe output showed Uvicorn access records despite `access_log=False` in its config. Structured logs are allowlisted, but framework stderr is not covered by that privacy guarantee. Investigate framework/pytest logging configuration before presenting all artifacts as sanitized.

## Access-log investigation resolved

pytest capture reattached access-logger handlers; new Uvicorn connections enabled raw access records based on handler presence. A fresh-client regression reproduced this, then passed after scoped access-logger disabling in the fixture. Structured/error logs remain active.

Full suite: 56 passed in 51.83s. See [investigation](access-log-investigation.md).

Goal 4 still requires reproducible dependencies, fresh setup, editor alignment and real CI execution.

## Goal 4 local execution

- Added a dependency constraint snapshot and pinned setuptools build backend.
- Installed non-editably into an empty verification venv; `pip check` passed.
- Confirmed package loaded from site-packages and included all static assets.
- Ran tests outside the source checkout with importlib mode: 56 passed in 53.74s.
- Added repository-local VS Code pytest/venv defaults; current parent workspace selection is not claimed fixed.
- Added Windows/Ubuntu Python 3.14 workflow with package verification, tests, defect checks and failure artifact retention.
- Editor Problems reported no errors for workflow, settings and package-check script.
- No remote, commits or pushes; actual GitHub jobs remain pending.

Details and limitations: [Reproducibility and CI](reproducibility-and-ci.md).
