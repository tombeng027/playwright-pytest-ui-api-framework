"""Run the same regression test normally and against an explicit synthetic defect."""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = "tests/api/test_order_rules.py::test_invalid_transition_preserves_order"


def run_case(name: str, defect: bool) -> None:
    directory = ROOT / "artifacts" / "defect-demo" / name
    directory.mkdir(parents=True, exist_ok=True)
    report = directory / "results.xml"
    if report.exists():
        report.unlink()
    command = [
        sys.executable, "-m", "pytest", TEST, "-q", "--tb=short",
        f"--junitxml={report}", f"--app-log-dir={directory / 'logs'}",
        f"--output={directory / 'browser'}",
    ]
    if defect:
        command.append("--demo-defect")
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    (directory / "pytest.txt").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    if result.returncode != (1 if defect else 0):
        raise RuntimeError(f"{name}: unexpected exit {result.returncode}; see {directory}")
    suite = ET.parse(report).getroot().find("testsuite")
    if suite is None:
        raise RuntimeError(f"{name}: missing test suite")
    if (
        suite.get("tests") != "1" or suite.get("errors") != "0"
        or suite.get("skipped") != "0"
        or suite.get("failures") != ("1" if defect else "0")
    ):
        raise RuntimeError(f"{name}: unexpected report counts")
    case = suite.find("testcase")
    if case is None or case.get("name") != "test_invalid_transition_preserves_order":
        raise RuntimeError(f"{name}: wrong test executed")
    failure = case.find("failure")
    if defect and (
        failure is None
        or "TRANSITION_GUARD: expected 409, got 200" not in failure.get("message", "")
    ):
        raise RuntimeError("Mutated run failed for an unrelated reason")
    logs = list((directory / "logs").glob("*.jsonl"))
    if len(logs) != 1:
        raise RuntimeError(f"{name}: expected one application log")
    events = [json.loads(line) for line in logs[0].read_text().splitlines()]
    if events[-1]["event"] != "app_stopped":
        raise RuntimeError(f"{name}: server cleanup not confirmed")
    transitions = [
        event for event in events
        if event["event"] == "http_request"
        and event["route"] == "/api/orders/{order_id}/status"
    ]
    if len(transitions) != 1 or transitions[0]["status"] != (200 if defect else 409):
        raise RuntimeError(f"{name}: unexpected transition evidence")
    print(f"PASS: {name}; expected test result, transition response and cleanup verified.")


def main() -> None:
    run_case("baseline", defect=False)
    run_case("mutated", defect=True)
    run_case("restored", defect=False)
    print("Verified: unchanged regression detects the defect; default behavior remains correct.")


if __name__ == "__main__":
    main()
