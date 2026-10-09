# Demo business rules

All accounts, customers and orders are synthetic. This contract is intentionally small.

| Area | Rule |
|---|---|
| Login | `demo` / `demo-password` establishes a cookie session; invalid credentials return 401 |
| Logout | Returns 204 and revokes the server-side session |
| Protected endpoints | Missing or revoked sessions return 401 |
| Customer | Must refer to one of the two seeded customers |
| Create | Nonblank title and description, trimmed by the server, maximum 500 characters each; starts Pending |
| Edit | Title and description can change while Pending or In Progress; customer is fixed |
| Status | Pending -> In Progress -> Completed only; repeats, skipping and reopening return 409 |
| Completed | No edits allowed (409) |
| Listing | Filter by status; empty list is valid |
| Unknown order | Returns 404 |
| Invalid input | Returns 422; unexpected fields in order-write payloads are rejected |
| Error shape | `{"error": {"message": "..."}}`, with field issues on model validation errors |
| Successful writes | Create returns 201; edit/status updates return 200 with the stored order |

No deletion, role matrix, inventory, payments or multi-tenant permissions.

## Milestone 1 coverage

| Test | Evidence |
|---|---|
| Cross-layer workflow | Create through API, Pending -> In Progress -> Completed through UI, verify each state through API |
| Invalid transition | Pending -> Completed returns 409 and leaves the order unchanged |
| Blank title | Server rejects whitespace-only input; no order is stored |
| Anonymous/logout | Anonymous request denied; copied pre-logout session also denied after logout |

## Goal 1 coverage additions

| Requirement/risk | Scenario coverage |
|---|---|
| Login/logout | UI invalid login/recovery, sign out/reload; API invalid login and copied-session revocation |
| Create | UI customer selection and trimmed fields; API required fields, 1/500/501-character boundaries, unknown customer and forbidden server-owned fields |
| Edit | UI edits verified through API; API Pending/In Progress edits, Completed rejection, invalid edits and customer immutability |
| Status | Cross-layer happy path; seven invalid transition combinations with unchanged-state assertions |
| Listing | UI mixed statuses, empty result and reset; API filtered exact response values |
| Access | Anonymous customers, order read/create/edit/status and logout rejected; existing order remains unchanged |
| Missing order | API read, edit and status actions return 404 |
| Invalid input | UI required fields and server whitespace errors; API invalid status/filter values |
| Text rendering | Markup-looking title/description remain literal text; no corresponding markup nodes created |

Total: 53 collected cases including parameterized variations, not 53 unique business features. See [progress](progress.md) for run evidence.

Not covered: exhaustive malformed-body/error-shape checks, session expiry (not implemented), concurrency, accessibility compliance, load, mobile/browser matrix or a security audit. Failure artifacts and the controlled defect remain separate pending goals.
