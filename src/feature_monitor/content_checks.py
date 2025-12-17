"""Content check module.

These checks are intentionally lightweight: they fetch a URL, validate basic
expectations, and compute a stable-ish fingerprint to detect changes over time.

State is stored locally under data/content_checks/ so subsequent runs can report
whether content changed since the last successful check.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

from .utils import safe_request, safe_write_file, setup_logging


logger = setup_logging(__name__)


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_text_for_fingerprint(text: str) -> str:
    # Normalize whitespace to reduce noise across runs.
    return _WHITESPACE_RE.sub(" ", (text or "").strip())


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _state_path(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name)
    return os.path.join("data", "content_checks", f"{safe}.json")


def _load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


@dataclass(frozen=True)
class ContentCheckResult:
    key: str
    name: str
    url: str
    ok: bool
    status_code: Optional[int]
    checked_at: str
    changed: Optional[bool]
    fingerprint: Optional[str]
    etag: Optional[str]
    last_modified: Optional[str]
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "url": self.url,
            "ok": self.ok,
            "status_code": self.status_code,
            "checked_at": self.checked_at,
            "changed": self.changed,
            "fingerprint": self.fingerprint,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "error": self.error,
        }


class ContentChecks:
    """Runs configured content checks."""

    def __init__(self, config_path: str = "config.yaml"):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
        except FileNotFoundError as exc:
            logger.error("ContentChecks configuration file not found: %s", config_path)
            raise FileNotFoundError(
                f"ContentChecks configuration file not found: {config_path}"
            ) from exc
        except (OSError, yaml.YAMLError) as exc:
            logger.error("Failed to load ContentChecks configuration from %s: %s", config_path, exc)
            raise RuntimeError(
                f"Failed to load ContentChecks configuration from {config_path}"
            ) from exc
        self.checks = (self.config.get("content_checks") or {})

    def run_all(self) -> List[ContentCheckResult]:
        results: List[ContentCheckResult] = []

        for key, cfg in self.checks.items():
            # Skip if config is malformed or disabled
            if not cfg or not isinstance(cfg, dict):
                logger.warning("Skipping content check %s: invalid configuration", key)
                continue
            if not cfg.get("enabled", False):
                continue
            
            url = cfg.get("url")
            if not url:
                results.append(
                    ContentCheckResult(
                        key=key,
                        name=cfg.get("display_name") or key,
                        url="",
                        ok=False,
                        status_code=None,
                        checked_at=datetime.now().isoformat(),
                        changed=None,
                        fingerprint=None,
                        etag=None,
                        last_modified=None,
                        error="Missing url in config",
                    )
                )
                continue

            contains = cfg.get("contains")
            display_name = cfg.get("display_name") or key
            results.append(self._run_one(key=key, name=display_name, url=url, contains=contains))

        return results

    def _run_one(self, key: str, name: str, url: str, contains: Optional[str]) -> ContentCheckResult:
        checked_at = datetime.now().isoformat()
        state_path = _state_path(key)
        prev = _load_state(state_path)
        prev_fp = prev.get("fingerprint")

        try:
            resp = safe_request(url, logger=logger, headers={"User-Agent": "automatic-barnacle/1.0"})
            if not resp:
                return ContentCheckResult(
                    key=key,
                    name=name,
                    url=url,
                    ok=False,
                    status_code=None,
                    checked_at=checked_at,
                    changed=None,
                    fingerprint=None,
                    etag=None,
                    last_modified=None,
                    error="Request failed",
                )

            text = resp.text or ""
            if contains and contains not in text:
                # Still compute fingerprint for debugging, but treat as not ok.
                normalized = _normalize_text_for_fingerprint(text)
                fp = _sha256(normalized)
                return ContentCheckResult(
                    key=key,
                    name=name,
                    url=url,
                    ok=False,
                    status_code=resp.status_code,
                    checked_at=checked_at,
                    changed=None,
                    fingerprint=fp,
                    etag=resp.headers.get("ETag"),
                    last_modified=resp.headers.get("Last-Modified"),
                    error=f"Response missing expected substring: {contains!r}",
                )

            normalized = _normalize_text_for_fingerprint(text)
            fp = _sha256(normalized)
            changed = (prev_fp is not None) and (prev_fp != fp)

            # Persist state only on a successful check.
            # Ensure the state directory exists before writing
            state_dir = os.path.dirname(state_path)
            os.makedirs(state_dir, exist_ok=True)
            
            success = safe_write_file(
                state_path,
                json.dumps(
                    {
                        "name": name,
                        "url": url,
                        "checked_at": checked_at,
                        "status_code": resp.status_code,
                        "fingerprint": fp,
                        "etag": resp.headers.get("ETag"),
                        "last_modified": resp.headers.get("Last-Modified"),
                    },
                    indent=2,
                ),
                logger,
            )
            
            if not success:
                logger.warning("Failed to persist state for check %s", key)

            return ContentCheckResult(
                key=key,
                name=name,
                url=url,
                ok=True,
                status_code=resp.status_code,
                checked_at=checked_at,
                changed=changed,
                fingerprint=fp,
                etag=resp.headers.get("ETag"),
                last_modified=resp.headers.get("Last-Modified"),
                error=None,
            )
        except Exception as e:
            return ContentCheckResult(
                key=key,
                name=name,
                url=url,
                ok=False,
                status_code=None,
                checked_at=checked_at,
                changed=None,
                fingerprint=None,
                etag=None,
                last_modified=None,
                error=str(e),
            )
