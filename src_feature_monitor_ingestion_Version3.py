"""
Ingestion entrypoint.

This module is updated to initialize structured logging on import and ensure that
the ingest step provides a stable place for the CLI to augment with GraphQL
schema diff results (handled in the CLI after the base ingest completes).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    from .logging_utils import setup_logging
    setup_logging()
except Exception:
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

log = logging.getLogger(__name__)

def _load_config() -> Dict[str, Any]:
    import os, yaml
    cfg = Path(os.getenv("FM_CONFIG_PATH", "config.yaml"))
    with cfg.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _today_features_path(data_dir: Path) -> Path:
    d = data_dir / "features"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{datetime.utcnow().strftime('%Y-%m-%d')}.json"

def _write_features(features: List[Dict[str, Any]], path: Path) -> None:
    path.write_text(json.dumps(features, indent=2), encoding="utf-8")
    log.info("Wrote %d features to %s", len(features), path)

def main() -> None:
    """
    Base ingestion routine. Keep as-is if your repo already has an ingestion flow.
    This is a minimal no-op placeholder if your previous implementation is elsewhere.
    Replace the body with your existing ingestion logic that outputs today's features
    to data/features/YYYY-MM-DD.json.
    """
    cfg = _load_config()
    data_dir = Path(cfg.get("data_dir", "data"))

    # If your project already implements ingestion, call it here instead.
    # Example (if implemented):
    # from .ingestion_sources import ingest_from_sources
    # features = ingest_from_sources(cfg)
    # Otherwise, we keep a safe default that does not overwrite existing files.
    features: List[Dict[str, Any]] = []

    out = _today_features_path(data_dir)
    if out.exists():
        log.info("Features file already exists for today; leaving it in place: %s", out)
        return

    _write_features(features, out)