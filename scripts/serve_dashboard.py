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
import socket
import sys
from pathlib import Path


def _is_port_available(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
        return True
    except OSError:
        return False


def _pick_port(host: str, preferred_port: int, max_tries: int = 50) -> int:
    for p in range(preferred_port, preferred_port + max_tries):
        if _is_port_available(host, p):
            return p
    raise SystemExit(
        f"No available port found in range {preferred_port}-{preferred_port + max_tries - 1} for host {host!r}"
    )


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

    port = _pick_port(args.host, args.port)
    if port != args.port:
        print(f"Port {args.port} is in use; serving on {port} instead.", file=sys.stderr)

    # host/port are for the HTTP server; livereload uses an internal websocket.
    server.serve(root=str(root), host=args.host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
