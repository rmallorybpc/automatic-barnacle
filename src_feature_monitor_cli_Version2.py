from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    # Initialize structured logging early
    from .logging_utils import setup_logging
except Exception:  # pragma: no cover - fallback if not present
    def setup_logging(*args, **kwargs):
        import logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

log = logging.getLogger(__name__)

def _load_config() -> Dict[str, Any]:
    """
    Loads config.yaml from the repository root or environment-configured path.
    """
    import yaml  # PyYAML expected to be available
    cfg_path = Path(os.getenv("FM_CONFIG_PATH", "config.yaml"))
    if not cfg_path.exists():
        raise FileNotFoundError(f"Could not find config.yaml at {cfg_path.resolve()}")
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _invoke_module(module_name: str, candidate_funcs: Optional[List[str]] = None, **kwargs) -> None:
    """
    Dynamically import a module and call the first available function in candidate_funcs.
    This keeps compatibility with different module shapes (main/run/execute/cli).
    """
    candidate_funcs = candidate_funcs or ["main", "run", "execute", "cli"]
    mod = importlib.import_module(module_name)
    for fn in candidate_funcs:
        if hasattr(mod, fn):
            log.info("Invoking %s.%s", module_name, fn)
            func = getattr(mod, fn)
            return func(**kwargs) if kwargs else func()
    raise AttributeError(f"No callable entry point found in {module_name}: tried {candidate_funcs}")

def _today_features_path(data_dir: Path) -> Path:
    # Prefer a dated file to avoid overwriting historical data
    dated_dir = data_dir / "features"
    dated_dir.mkdir(parents=True, exist_ok=True)
    return dated_dir / f"{datetime.utcnow().strftime('%Y-%m-%d')}.json"

def _merge_unique_features(base: List[Dict[str, Any]], extra: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = {f.get("id") for f in base if isinstance(f, dict)}
    merged = list(base)
    for f in extra:
        fid = f.get("id")
        if fid and fid not in seen:
            merged.append(f)
            seen.add(fid)
    return merged

def _ingest_graphql_if_enabled(config: Dict[str, Any], data_dir: Path) -> int:
    """
    If 'graphql_schema_diff' is enabled in feature_sources, call the ingestion hook and merge
    emitted records into today's features file. Returns number of records added.
    """
    sources: List[str] = (config.get("feature_sources") or [])
    if "graphql_schema_diff" not in sources:
        log.info("GraphQL schema diff not enabled in feature_sources; skipping")
        return 0

    try:
        from .ingestion_graphql_hook import ingest_graphql_schema_diff
    except Exception as e:
        log.error("Could not import GraphQL diff hook: %s", e)
        return 0

    added = ingest_graphql_schema_diff(data_dir=str(data_dir))
    if not added:
        log.info("GraphQL diff produced 0 records; nothing to merge")
        return 0

    # Determine the current features file (today’s)
    feats_path = _today_features_path(data_dir)
    existing: List[Dict[str, Any]] = []
    if feats_path.exists():
        try:
            existing = json.loads(feats_path.read_text(encoding="utf-8"))
        except Exception as e:
            log.error("Failed to read existing features file %s: %s", feats_path, e)

    merged = _merge_unique_features(existing, added)
    if merged != existing:
        feats_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        log.info("Merged %d GraphQL records into %s (total now %d)", len(added), feats_path, len(merged))
        return len(merged) - len(existing)

    log.info("No new GraphQL records to merge (deduplicated by id)")
    return 0

def cmd_run_all(config: Dict[str, Any]) -> None:
    # Command sequence based on the agreed pipeline
    for step, module in [
        ("ingest", "feature_monitor.ingestion"),
        ("index", "feature_monitor.modules_index"),
        ("embed", "feature_monitor.embeddings"),
        ("evaluate", "feature_monitor.coverage"),
        ("report", "feature_monitor.report"),
        ("issues", "feature_monitor.issues"),
        ("dashboard", "feature_monitor.dashboard"),
        ("notify", "feature_monitor.notifications"),
    ]:
        try:
            if step == "ingest":
                _invoke_module(module)
                # Augment with GraphQL schema diff results if enabled
                added = _ingest_graphql_if_enabled(config, data_dir=Path(config.get("data_dir", "data")))
                log.info("GraphQL ingest added records: %d", added)
            else:
                _invoke_module(module)
        except Exception as e:
            log.error("Step %s failed: %s", step, e)
            raise

def cmd_single_step(step_name: str, config: Dict[str, Any]) -> None:
    mapping = {
        "ingest": "feature_monitor.ingestion",
        "index": "feature_monitor.modules_index",
        "embed": "feature_monitor.embeddings",
        "evaluate": "feature_monitor.coverage",
        "report": "feature_monitor.report",
        "issues": "feature_monitor.issues",
        "notify": "feature_monitor.notifications",
        "dashboard": "feature_monitor.dashboard",
        "monthly-issues-report": "feature_monitor.monthly_report",
    }
    module = mapping.get(step_name)
    if not module:
        raise SystemExit(f"Unknown step: {step_name}")

    if step_name == "ingest":
        _invoke_module(module)
        added = _ingest_graphql_if_enabled(config, data_dir=Path(config.get("data_dir", "data")))
        log.info("GraphQL ingest added records: %d", added)
    else:
        _invoke_module(module)

def main(argv: Optional[List[str]] = None) -> None:
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    parser = argparse.ArgumentParser(prog="feature-monitor", description="GitHub Feature Coverage monitoring CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run-all", help="Run the full monitoring pipeline")
    for cmd in ["ingest", "index", "embed", "evaluate", "report", "issues", "notify", "dashboard", "monthly-issues-report"]:
        sub.add_parser(cmd, help=f"Run the {cmd} step")

    args = parser.parse_args(argv)
    config = _load_config()

    if args.command == "run-all":
        cmd_run_all(config)
    else:
        cmd_single_step(args.command, config)

if __name__ == "__main__":  # pragma: no cover
    main()