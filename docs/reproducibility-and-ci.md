# Reproducibility and CI

Goal 4 local and hosted verification completed October 9, 2026. Parent-workspace editor alignment remains an environment-specific follow-up, not a claim of verified discovery.

## Dependency policy

- `pyproject.toml` describes compatible dependencies and pins the build backend to setuptools 80.9.0.
- `constraints.txt` pins the runtime/test dependencies from the verified Windows/Python 3.14 environment.
- Install with `pip install -c constraints.txt ".[test]"` (non-editable) or `pip install -c constraints.txt -e ".[test]"` (development).
- Constraints do not force platform-conditional dependencies to install. They are a version snapshot, not a hash-verified universal lockfile.
- Browser binaries are selected by the pinned Playwright release.
- Refresh pins deliberately and rerun clean-install, normal-suite and defect checks. Do not replace the snapshot with unrelated packages from a global interpreter.
- Python 3.12-3.14 is permitted by metadata; only 3.14.3 has been verified locally. The initial CI matrix uses 3.14, not an unverified Python-version matrix.

## Fresh-install evidence

Created a separate empty virtual environment, installed the non-editable project with constraints and ran `pip check`.

From a working directory outside the source package:

1. Verified `demo_app` loaded from the fresh environment's `site-packages`, not the source checkout.
2. Checked packaged HTML, JavaScript and CSS files and instantiated the installed application.
3. Ran all tests with `--import-mode=importlib`.
4. Result: **56 passed in 53.74s**, no retries/skips, Windows/Python 3.14.3/Chromium.

Evidence remains in `artifacts/fresh-check/report.html` and `results.xml`. The temporary verification environment is removed after testing; the development `.venv` remains.

To reproduce manually, install non-editably in a new venv, change to a directory outside the checkout, then use its Python:

```powershell
$root = 'D:\path\to\playwright-pytest-ui-api-framework'
python "$root\scripts\check_package.py"
python -m pytest "$root\tests" -c "$root\pyproject.toml" --import-mode=importlib --browser chromium --output "$root\artifacts\clean-browser" --app-log-dir "$root\artifacts\clean-logs"
```

Replace `python` with the new venv executable. This avoids a source checkout masking missing package assets.

## GitHub Actions workflow

`.github/workflows/qa.yml` is configured for push, pull request and manual dispatch:

- Python 3.14 on Windows and Ubuntu.
- Non-editable installation with the same constraints; `pip check`.
- Chromium installation, including Linux system dependencies.
- Installed package/assets check and tests run outside the checkout.
- Controlled-defect verifier after a successful normal suite.
- HTML/JUnit, logs, browser failure artifacts, dependency snapshot and defect evidence uploaded even if a prior step fails.
- Read-only repository permissions, 15-minute timeout, seven-day artifact retention and no test retries.

The intentional browser diagnostic probe is not included in default CI. It is documented for explicit local execution. The controlled-defect verifier treats only the precise expected mutation failure as success.

### First hosted execution

[Run 37889100220](https://github.com/tombeng027/playwright-pytest-ui-api-framework/actions/runs/37889100220), source commit `0d09aae63530533ae5f754f3d5b73ab52f6f83d1`, succeeded on both runners:

| Runner | Actual Python | Default suite |
|---|---|---|
| Ubuntu | 3.14.8 | 56 passed in 33.85s |
| Windows | 3.14.7 | 56 passed in 65.91s |

Both jobs verified the non-editable package/assets outside the checkout and the controlled-defect baseline/mutated/restored sequence. The mutation failed for `TRANSITION_GUARD: expected 409, got 200`, not an unrelated failure.

Downloaded both evidence ZIPs and verified their SHA-256 digests against GitHub's artifact metadata. Inspected default JUnit XML (56 cases, zero failures/errors/skips), separate defect XML, HTML report presence and all 55 server-backed log endings per runner (`app_stopped`). Local copies are ignored under `artifacts/hosted-ci/`; hosted retention is seven days.

Passing normal runs do not generate failure-only browser traces/screenshots. Those were separately verified using the explicit local diagnostic probe, not this CI run.

## Editor setup

Repository-local `.vscode/settings.json` provides a venv default and pytest discovery configuration.

Open this repository folder directly in VS Code, then select `.venv\Scripts\python.exe`. A previously selected interpreter can override the default, and the parent labs workspace may retain another project's selection.

The settings file is valid, but this does not establish that the already-open parent workspace has switched interpreters or rediscovered tests.

## Publication boundary

The local reproducibility step did not publish anything. Subsequently, the user supplied and approved [the GitHub repository](https://github.com/tombeng027/playwright-pytest-ui-api-framework). Its remote was inspected and empty before configuring `origin`, committing and pushing `main`. The first hosted run and uploaded evidence were then verified as recorded above.

Review synthetic traces before sharing: they can contain demo credentials and payloads despite structured log allowlisting. Do not add real accounts or employer data.
