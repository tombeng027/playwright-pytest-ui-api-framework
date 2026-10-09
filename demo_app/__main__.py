"""Run the demo manually; tests create their own isolated app instances."""

import argparse
from pathlib import Path

import uvicorn

from demo_app.app import create_app
from demo_app.observability import EventLog


def main() -> None:
    parser = argparse.ArgumentParser(description="Local-only synthetic work-order demo")
    parser.add_argument("--database", type=Path, default=Path("demo.sqlite3"))
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log", type=Path, default=Path("artifacts/demo.jsonl"))
    args = parser.parse_args()
    uvicorn.run(
        create_app(args.database, EventLog(args.log)),
        host="127.0.0.1", port=args.port, access_log=False,
    )


if __name__ == "__main__":
    main()
