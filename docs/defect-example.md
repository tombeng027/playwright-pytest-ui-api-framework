# Controlled defect: skipping a work-order status

Goal 3 verified October 9, 2026. This is an intentional synthetic defect, not a reported production incident.

## Requirement and risk

A Pending order must become In Progress before Completed. Skipping this stage bypasses the documented workflow.

Expected API behavior: PATCH status to Completed on a Pending order returns 409 and preserves the order.

Injected behavior: the same request returns 200 and changes the order to Completed.

## Reproduce and verify

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\verify_defect.py
```

The verifier executes the unchanged regression test three times in separate pytest processes:

| Mode | HTTP response | Test result |
|---|---|---|
| Baseline | 409 | Pass |
| Mutated | 200 | Fail: `TRANSITION_GUARD: expected 409, got 200` |
| Restored default | 409 | Pass |

The verifier itself exits successfully only if the expected results, test identity, JUnit counts, transition logs and shutdown records all match. A startup error or unrelated assertion failure does not count as defect detection.

Reports, stdout/stderr and logs are retained separately under `artifacts/defect-demo/baseline`, `mutated` and `restored`.

## Defect control

`--demo-defect` explicitly enables the flag in the test fixture. Normal pytest runs and the manual demo leave it disabled. No environment variable, browser control or API endpoint enables it.

The flag permits only Pending -> Completed. It does not change test expectations or all other transition rules. The same application factory is used for normal and mutated tests.

## Observed outcome

All three modes verified successfully. The normal 55-case suite then passed in 51.83s with no retries/skips. The full suite is not run with the defect enabled; multiple transition checks would legitimately fail.

## Limitations

This proves the selected regression detects this one synthetic mutation. It is not a mutation coverage score or proof that all potential defects are caught.

The earlier browser diagnostic probe intentionally uses a wrong expectation to exercise evidence collection. This example instead changes application behavior and keeps the test expectation correct.
