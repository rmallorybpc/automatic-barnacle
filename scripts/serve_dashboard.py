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
import mimetypes
from pathlib import Path
from typing import Optional


def _register_common_mime_types() -> None:
    # Some environments (and some servers) can end up serving text assets as
    # application/octet-stream, which Safari may interpret as a download.
    mimetypes.add_type("text/html; charset=utf-8", ".html")
    mimetypes.add_type("text/css; charset=utf-8", ".css")
    mimetypes.add_type("text/javascript; charset=utf-8", ".js")
    mimetypes.add_type("application/json; charset=utf-8", ".json")
    mimetypes.add_type("text/markdown; charset=utf-8", ".md")
    mimetypes.add_type("image/svg+xml", ".svg")


def _serve_simple(root: Path, host: str, port: int) -> None:
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, directory: Optional[str] = None, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def end_headers(self) -> None:
            # Reduce caching surprises during local/codespaces preview.
            self.send_header("Cache-Control", "no-store")
            # Hint to the browser that common text assets should render inline.
            # (If Safari sees octet-stream it may prompt for download.)
            self.send_header("Content-Disposition", "inline")
            super().end_headers()

    httpd = ThreadingHTTPServer((host, port), lambda *a, **kw: Handler(*a, directory=str(root), **kw))
    sa = httpd.socket.getsockname()
    print(f"Serving {root} at http://{sa[0]}:{sa[1]}/ (simple mode)")
    httpd.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve docs/ with live reload")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--root", default="docs", help="Directory to serve")
    parser.add_argument(
        "--mode",
        choices=["auto", "livereload", "simple"],
        default="auto",
        help="Server mode. 'auto' uses livereload if installed, else falls back to a simple static server.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"Root directory not found: {root.resolve()}")

    _register_common_mime_types()

    if args.mode == "simple":
        try:
            _serve_simple(root=root, host=args.host, port=args.port)
        except OSError as exc:
            raise SystemExit(
                f"Unable to start preview server on {args.host}:{args.port} ({exc}).\n"
                f"Free the port and try again (example):\n"
                f"  lsof -iTCP:{args.port} -sTCP:LISTEN -Pn\n"
                f"  kill <PID>\n"
            ) from exc
        return 0

    try:
        from livereload import Server  # type: ignore
    except Exception as exc:  # pragma: no cover
        if args.mode == "livereload":
            raise SystemExit(
                "Missing dev dependency 'livereload'. Install it with:\n"
                "  /workspaces/automatic-barnacle/.venv/bin/python -m pip install -r requirements-dev.txt"
            ) from exc

        # auto mode fallback
        try:
            _serve_simple(root=root, host=args.host, port=args.port)
        except OSError as ose:
            raise SystemExit(
                f"Unable to start preview server on {args.host}:{args.port} ({ose}).\n"
                f"Free the port and try again (example):\n"
                f"  lsof -iTCP:{args.port} -sTCP:LISTEN -Pn\n"
                f"  kill <PID>\n"
            ) from ose
        return 0

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
