#!/usr/bin/env python3
"""Live-reload dev server for the GitHub Pages dashboard.

Serves the static site from ./docs and reloads the browser when:
- docs/index.html changes
- any JSON in docs/reports changes

Usage:
  /workspaces/automatic-barnacle/.venv/bin/python scripts/serve_dashboard.py

Then open:
  http://localhost:8000/
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve docs/ with live reload")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--root", default="docs", help="Directory to serve")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"Root directory not found: {root.resolve()}")

    try:
        from livereload import Server  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Missing dev dependency 'livereload'. Install it with:\n"
            "  /workspaces/automatic-barnacle/.venv/bin/python -m pip install -r requirements-dev.txt"
        ) from exc

    server = Server()
    server.watch(str(root / "index.html"))
    server.watch(str(root / "reports" / "*.json"))

    # host/port are for the HTTP server; livereload uses an internal websocket.
    try:
        server.serve(root=str(root), host=args.host, port=args.port)
    except OSError as exc:
        raise SystemExit(
            f"Unable to start preview server on {args.host}:{args.port} ({exc}).\n"
            f"Free the port and try again (example):\n"
            f"  lsof -iTCP:{args.port} -sTCP:LISTEN -Pn\n"
            f"  kill <PID>\n"
        ) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
