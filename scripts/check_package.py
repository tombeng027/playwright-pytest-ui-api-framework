"""Confirm the non-editable installation includes the demo and its static assets."""

from pathlib import Path
from tempfile import TemporaryDirectory

import demo_app

from demo_app.app import create_app

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if demo_app.__file__ is None:
        raise RuntimeError("Installed demo_app has no package file")
    package = Path(demo_app.__file__).resolve().parent
    if package == ROOT / "demo_app":
        raise RuntimeError("Source checkout shadows installed package; run outside repo")
    for name in ("index.html", "app.js", "style.css"):
        asset = package / "static" / name
        if not asset.is_file() or asset.stat().st_size == 0:
            raise RuntimeError(f"Missing packaged asset: {name}")
    with TemporaryDirectory() as directory:
        app = create_app(Path(directory) / "packaged.sqlite3")
        if not any(getattr(route, "path", None) == "/api/orders" for route in app.routes):
            raise RuntimeError("Installed application is missing order routes")
    print(f"PASS: non-editable package and all static assets verified at {package}")


if __name__ == "__main__":
    main()
