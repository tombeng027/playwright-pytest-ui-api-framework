# Raw access-log investigation

Resolved October 9, 2026 with installed pytest 9.1.1 and Uvicorn 0.54.0.

## Observation

The browser failure report contained raw `uvicorn.access` records despite `access_log=False`. Raw access records can include query strings, unlike the structured request log's allowlisted route template.

## Confirmed mechanism

1. Uvicorn configuration clears the access logger's handlers and disables propagation when access logging is off.
2. pytest's logging capture attaches handlers to non-propagating loggers at the start of a phase.
3. Uvicorn's HTTP protocol checks `access_logger.hasHandlers()` when a connection is constructed.
4. Connections opened during the call phase therefore enable access records again. API connections established during fixture setup can retain the earlier disabled state.

A regression test opening a fresh HTTP client during the call phase reproduced a raw record containing a synthetic query sentinel. Using the existing setup-time client alone passed and did not exercise the cause.

## Fix

The application fixture explicitly disables only `uvicorn.access` while its server is active, using pytest's monkeypatch fixture to restore the previous value afterward.

Structured application logs and Uvicorn error/lifecycle logging remain enabled. No dependency source was modified and no broad logging suppression was added.

This is a sequential-suite solution. Shared global logger configuration needs reconsideration before simultaneous in-process application servers are introduced.

## Verification

- Fresh-connection regression failed before the fix and passed afterward.
- Both logging API tests passed.
- Full default suite passed: 56 cases in 51.83s.
- Regression also confirms structured correlation remains present and the synthetic query value is absent from structured logs.

Traces and framework exception output still require separate privacy review; disabling access records does not sanitize all artifacts.
