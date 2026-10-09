# Failure diagnostics

Goal 2 verified October 9, 2026 on Windows/Python 3.14.3/Chromium.

## Default behavior

pytest-playwright retains traces and full-page screenshots only for failed browser tests, under `artifacts/browser/`. Application/browser observation logs are retained per test under `artifacts/logs/`. The setup report identifies the matching log path.

Browser observations record:

- `browser_console_error`: an error-level console event, without message text.
- `browser_page_error`: an uncaught page error, without its message or stack.
- `browser_network_failure`: transport failure, with method but no URL or error text.
- `browser_http_error`: HTTP status >= 400, method and response request ID.

HTTP errors are distinct from network failures. Some HTTP errors (initial anonymous requests and invalid-input tests) are expected. These observations do not automatically fail tests; scenario assertions determine pass/fail.

Logs deliberately omit console text and URLs; use the synthetic-only trace for richer context. Browser listeners are removed during fixture teardown.

## Reproduce the verified diagnostic failure

From the repository root in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\diagnostic_probe.py --browser chromium --output artifacts\diagnostic-probe --junitxml=artifacts\probe.xml --tb=short
```

**Expected exit code: 1**, with exactly one failed assertion:

```text
Expected: INTENTIONAL_FAILURE_EXPECTED
Actual: Pending
```

The probe is excluded from default discovery because its filename does not start with `test_`. It is not an application defect test: its purpose is to validate evidence collection. Goal 3 will separately demonstrate a real controlled business-rule defect.

The probe logs in, creates a synthetic order, generates console/page/network errors, then intentionally expects the wrong status.

## Evidence inspected

- JUnit contained the expected assertion failure and no setup/teardown error.
- Screenshot was opened and visually showed the order in Pending state. Full-page capture was enabled after the first viewport-only screenshot omitted the order.
- Trace ZIP integrity was checked; its records contained the exact failed assertion and DOM snapshots.
- Logs contained all four browser event categories.
- Browser HTTP request IDs matched application request records and response statuses.
- Console/page-error sentinels and demo password were absent from structured logs.
- Final lifecycle event was `app_stopped`; fixture teardown reported no live server thread.
- The ordinary suite subsequently passed: 55 tests in 50.59s, with no skips/retries.

These checks establish failure-path fixture cleanup for this probe, not every possible startup/teardown failure.

## Inspect a trace locally

```powershell
.\.venv\Scripts\python.exe -m playwright show-trace artifacts\diagnostic-probe\tests-diagnostic-probe-py-test-intentional-browser-failure-chromium\trace.zip
```

Use the local viewer, not an online upload. The path changes if the probe name/browser changes.

## Artifact handling

- Traces can include synthetic credentials, request payloads, DOM content and console messages. Structured log allowlisting does not sanitize traces or screenshots.
- Never use real credentials/data in the demo or upload raw artifacts publicly without review.
- Artifacts are ignored by Git. Copy diagnostic-probe evidence before rerunning it if you want to retain an earlier run.
- Passing-run trace/screenshot output is discarded. pytest-playwright manages its output directory per run; the separate probe directory preserves demonstration evidence during ordinary runs.
- CI artifact retention and fresh installation remain Goal 4 work.
