"""Content checks module.

Runs lightweight checks against configured URLs, storing the latest result for each
check under data/content_checks/<key>.json.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

from .utils import create_session_with_retry, safe_write_file, setup_logging


logger = setup_logging(__name__)


@dataclass(frozen=True)
class ContentCheckConfig:
    key: str
    name: str
    url: str


def _fingerprint_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _load_previous_fingerprint(path: str) -> Optional[str]:
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            prev = json.load(f)
        fp = prev.get("fingerprint")
        return str(fp) if fp else None
    except Exception:
        return None


class ContentCheckRunner:
    def __init__(
        self,
        config_path: str = "config.yaml",
        output_dir: str = "data/content_checks",
    ) -> None:
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}
        self.output_dir = output_dir

    def _load_checks(self) -> List[ContentCheckConfig]:
        raw = self.config.get("content_checks")
        if not isinstance(raw, list):
            return []

        checks: List[ContentCheckConfig] = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                logger.warning("Skipping invalid content check (not a mapping) at index %s", idx)
                continue
            key = str(item.get("key") or "").strip()
            url = str(item.get("url") or "").strip()
            name = str(item.get("name") or key).strip()
            if not key or not url:
                logger.warning("Skipping content check missing key/url at index %s", idx)
                continue
            checks.append(ContentCheckConfig(key=key, name=name or key, url=url))
        return checks

    def run(self) -> List[Dict[str, Any]]:
        checks = self._load_checks()
        if not checks:
            logger.info("No content checks configured")
            return []

        os.makedirs(self.output_dir, exist_ok=True)

        session = create_session_with_retry()
        results: List[Dict[str, Any]] = []

        try:
            for ch in checks:
                out_path = os.path.join(self.output_dir, f"{ch.key}.json")
                prev_fp = _load_previous_fingerprint(out_path)
                checked_at = datetime.now().isoformat()

                status_code: Optional[int] = None
                ok = False
                fingerprint: Optional[str] = None
                etag: Optional[str] = None
                last_modified: Optional[str] = None
                changed: Optional[bool] = None

                try:
                    logger.info("Content check: %s (%s)", ch.key, ch.url)
                    res = session.get(ch.url, timeout=30)
                    status_code = int(res.status_code)
                    ok = 200 <= status_code < 400
                    etag = res.headers.get("ETag")
                    last_modified = res.headers.get("Last-Modified")

                    content = res.content or b""
                    fingerprint = _fingerprint_bytes(content)
                    if prev_fp is None:
                        changed = None
                    else:
                        changed = (prev_fp != fingerprint)
                except Exception as e:
                    logger.error("Content check failed for %s: %s", ch.key, e)
                    ok = False

                payload: Dict[str, Any] = {
                    "key": ch.key,
                    "name": ch.name,
                    "url": ch.url,
                    "checked_at": checked_at,
                    "status_code": status_code,
                    "ok": ok,
                    "changed": changed,
                    "fingerprint": fingerprint,
                    "etag": etag,
                    "last_modified": last_modified,
                }

                safe_write_file(out_path, json.dumps(payload, indent=2), logger=logger)
                results.append(payload)
        finally:
            session.close()

        return results


def main() -> int:
    runner = ContentCheckRunner()
    results = runner.run()
    print(f"\nContent checks complete: {len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
