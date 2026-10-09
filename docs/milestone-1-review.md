# Milestone 1 Review

Completed October 9, 2026.

## Implemented

- FastAPI/SQLite application, synthetic login, server-side logout revocation and seeded customers.
- Plain browser UI for order creation, editing, status advancement and filtering.
- Server-enforced validation and Pending -> In Progress -> Completed transitions.
- Function-scoped application/database fixtures and separate browser/API sessions.
- One cross-layer test and three API rule checks.
- Dependency manifest, ignore rules, setup instructions and business-rule coverage map.

## Execution evidence

Windows, Python 3.14.3, pytest 9.1.1, pytest-playwright 0.10.0 and Playwright 1.63.0:

| Run | Result | Duration |
|---|---|---|
| 1 (HTML/JUnit reports) | 4 passed | 4.45s |
| 2 | 4 passed | 4.06s |
| 3 | 4 passed | 4.07s |

JavaScript syntax and installed dependency consistency checks passed. Application Python syntax was checked through Pylance. Manual browser verification covered login, initial empty state and UI order creation.

The editor test runner did not discover the tests, so verification used pytest in the explicit project venv. Pylance still reported missing pytest/Playwright imports while its environment query continued to show the parent workspace's different interpreter, despite a switch attempt. This is an unresolved editor configuration issue, not a claim that the selected editor environment is correct. Open the repo independently and select its venv.

## Deliberate implementation choices

- Tests run the server in a dedicated thread on a socket bound to an OS-selected port. This avoids port-selection races and Windows subprocess/socket-sharing complexity.
- Each test owns its app and temporary SQLite database. Fixtures request bounded shutdown and report cleanup failures.
- No page-object abstraction yet: the single browser workflow is readable directly. Introduce a small reusable page object when UI coverage expands.
- API fixtures and tests use Playwright's request client. They do not import the application's expected-transition rules.
- The logout test copies the session before logout, then verifies that copy is rejected afterward. This checks server-side revocation rather than merely cookie deletion.

## Not complete yet

- Broad UI and API negative/boundary coverage.
- Screenshot/trace generation verified through an intentional failure.
- Controlled-defect demonstration.
- Fresh-environment installation verification.
- GitHub Actions execution, GitHub publication and pinning.
- Multiple browsers, parallel execution and testing on other Python versions.

The manual demo has intentionally limited authentication and must not be deployed publicly.

## Next review decisions

1. Keep the minimal application as the test target rather than expanding features.
2. Prioritize invalid login, UI creation/editing, filtering and completed-order restrictions.
3. Verify rejected API writes preserve state and extend boundary cases.
4. Add failure artifacts before introducing CI.
