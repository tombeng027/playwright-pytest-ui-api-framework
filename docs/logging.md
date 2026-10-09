# Logging and correlation

Application and test-lifecycle logs use newline-delimited JSON. This is local diagnostic evidence, not production monitoring.

## Locations

- Tests: `artifacts/logs/<test-id-hash>.jsonl`; the pytest setup report identifies the file. The lifecycle records identify the test.
- Manual app: `artifacts/demo.jsonl`; override with `python -m demo_app --log <path>`.
- Artifacts are ignored by Git. Test files are overwritten for each rerun of the same test; copy evidence you want to retain.
- Parallel execution is not yet supported or verified for artifact naming.

## Request records

Each request gets a generated `X-Request-ID` response header. The same ID is recorded with UTC timestamp, level, method, matched route template, status and elapsed milliseconds.

Illustrative synthetic record (not a benchmark):

```json
{"timestamp":"2026-10-09T05:00:00+00:00","level":"WARNING","event":"http_request","request_id":"example-id","method":"PATCH","route":"/api/orders/{order_id}/status","status":409,"duration_ms":2.1}
```

2xx/3xx requests are INFO; 4xx are WARNING; 5xx are ERROR. A warning may be an expected negative test, not a defect. Unmatched routes are represented by `<unmatched>` rather than raw user-controlled paths.

Unexpected exceptions record only their type and are re-raised, not converted into successful responses. If a response has already started, status reflects the emitted status; `exception_type` still identifies an interrupted request. Failures before response start may be rendered by the server's outer error handler without the correlation header.

## Lifecycle records

`app_starting`, `app_ready`, `app_stopped` identify the test. `app_stop_failed` is an ERROR and fails teardown.

## Privacy and limitations

- No request/response bodies, passwords, session tokens, cookies, authorization headers, query strings or order text in structured records.
- Exception messages are deliberately omitted because they can contain sensitive values.
- Existing framework stderr/tracebacks and future Playwright traces are separate evidence sources; this allowlist does not sanitize every third-party artifact.
- File-write errors surface rather than silently disabling logging.
- Browser observations, screenshots and trace verification are now implemented; see [failure diagnostics](failure-diagnostics.md).
- No cloud logging, log rotation or multi-process writer support.

## Verification

Tests verify response/log correlation for a 201 and 409, route templates, timestamps, timings and exclusion of credential/token/payload/header/query sentinel values. A middleware test verifies unexpected failures are logged and propagated without copying exception messages.

After the full 55-case run, all 54 application-backed test log files ended with `app_stopped`. The remaining test exercises middleware directly without a server. Failure-path cleanup still needs a deliberate failing browser run.

Goal 2 subsequently verified `app_stopped` after an intentional browser assertion failure, with no teardown errors. Structured browser events exclude free-text messages; traces remain richer, synthetic-only evidence requiring separate privacy review.
