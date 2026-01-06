"""Generate an executive-friendly delta between two dashboard snapshots.

This is intended to make change-over-time review easy without requiring
manual GitHub file-history comparisons.

Typical usage in CI:
  python -m src.feature_monitor.dashboard_delta \
    --old docs/reports/dashboard.json \
    --new data/dashboard/dashboard_latest.json \
    --out-json docs/reports/dashboard_delta.json \
    --out-md docs/reports/dashboard_delta.md

If the --old file does not exist (first run), the delta reports all current
items as "added".
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .utils import setup_logging


logger = setup_logging(__name__)


@dataclass(frozen=True)
class FeatureLite:
    id: str
    title: str
    source_type: Optional[str]
    product_area: Optional[str]
    source_url: Optional[str]
    date_discovered: Optional[str]

    @staticmethod
    def from_obj(obj: Dict[str, Any]) -> "FeatureLite":
        return FeatureLite(
            id=str(obj.get("id") or "").strip(),
            title=str(obj.get("title") or "").strip(),
            source_type=(str(obj.get("source_type")).strip() if obj.get("source_type") is not None else None),
            product_area=(str(obj.get("product_area")).strip() if obj.get("product_area") is not None else None),
            source_url=(str(obj.get("source_url")).strip() if obj.get("source_url") is not None else None),
            date_discovered=(
                str(obj.get("date_discovered")).strip() if obj.get("date_discovered") is not None else None
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source_type": self.source_type,
            "product_area": self.product_area,
            "source_url": self.source_url,
            "date_discovered": self.date_discovered,
        }


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f) or {}


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _extract_features(dashboard: Dict[str, Any]) -> Dict[str, FeatureLite]:
    features_raw = _safe_list(dashboard.get("features"))
    out: Dict[str, FeatureLite] = {}
    for item in features_raw:
        if not isinstance(item, dict):
            continue
        feature = FeatureLite.from_obj(item)
        if feature.id:
            out[feature.id] = feature
    return out


def _extract_gap_counts(dashboard: Dict[str, Any]) -> Dict[str, int]:
    gaps = _safe_list(dashboard.get("gaps"))
    counts = {"total": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
    for g in gaps:
        if not isinstance(g, dict):
            continue
        counts["total"] += 1
        impact = str(g.get("impact") or "unknown").strip().lower()
        if impact not in counts:
            impact = "unknown"
        counts[impact] += 1
    return counts


def _diff_features(
    old_by_id: Dict[str, FeatureLite],
    new_by_id: Dict[str, FeatureLite],
) -> Tuple[List[FeatureLite], List[FeatureLite], List[Dict[str, Any]]]:
    added: List[FeatureLite] = []
    removed: List[FeatureLite] = []
    changed: List[Dict[str, Any]] = []

    old_ids = set(old_by_id.keys())
    new_ids = set(new_by_id.keys())

    for feature_id in sorted(new_ids - old_ids):
        added.append(new_by_id[feature_id])

    for feature_id in sorted(old_ids - new_ids):
        removed.append(old_by_id[feature_id])

    common = sorted(old_ids & new_ids)
    for feature_id in common:
        old_f = old_by_id[feature_id]
        new_f = new_by_id[feature_id]
        if old_f == new_f:
            continue

        field_changes: Dict[str, Dict[str, Any]] = {}
        for field in ["title", "source_type", "product_area", "source_url", "date_discovered"]:
            old_v = getattr(old_f, field)
            new_v = getattr(new_f, field)
            if old_v != new_v:
                field_changes[field] = {"old": old_v, "new": new_v}

        changed.append(
            {
                "id": feature_id,
                "title": new_f.title or old_f.title,
                "fields": field_changes,
            }
        )

    return added, removed, changed


def _top_items(items: Iterable[FeatureLite], limit: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for f in items:
        out.append(f.to_dict())
        if len(out) >= limit:
            break
    return out


def _render_markdown(delta: Dict[str, Any]) -> str:
    counts = delta.get("counts", {}) if isinstance(delta.get("counts"), dict) else {}
    gaps = delta.get("gaps", {}) if isinstance(delta.get("gaps"), dict) else {}

    lines: List[str] = []
    lines.append("# Dashboard Delta (Executive Summary)")
    lines.append("")
    lines.append(f"**Generated:** {delta.get('generated_at')}")
    lines.append(f"**Baseline:** {delta.get('baseline_generated_at') or 'n/a'}")
    lines.append(f"**New snapshot:** {delta.get('new_generated_at') or 'n/a'}")
    lines.append("")

    lines.append("## Key changes")
    lines.append("")
    lines.append(f"- **Features added:** {counts.get('features_added', 0)}")
    lines.append(f"- **Features removed:** {counts.get('features_removed', 0)}")
    lines.append(f"- **Features changed:** {counts.get('features_changed', 0)}")
    lines.append("")

    if isinstance(gaps, dict) and gaps:
        old_g = gaps.get("old", {}) if isinstance(gaps.get("old"), dict) else {}
        new_g = gaps.get("new", {}) if isinstance(gaps.get("new"), dict) else {}
        lines.append("## Gaps")
        lines.append("")
        lines.append(
            f"- **Total gaps:** {old_g.get('total', 0)} → {new_g.get('total', 0)}"
        )
        lines.append(
            f"- **High-impact gaps:** {old_g.get('high', 0)} → {new_g.get('high', 0)}"
        )
        lines.append("")

    added = _safe_list(delta.get("top_added"))
    if added:
        lines.append("## Newly added (sample)")
        lines.append("")
        for item in added:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("id") or "").strip()
            url = str(item.get("source_url") or "").strip()
            if url:
                lines.append(f"- {title} ({url})")
            else:
                lines.append(f"- {title}")
        lines.append("")

    removed = _safe_list(delta.get("top_removed"))
    if removed:
        lines.append("## Removed (sample)")
        lines.append("")
        for item in removed:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("id") or "").strip()
            lines.append(f"- {title}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_delta(old_path: Optional[Path], new_path: Path, top_n: int = 8) -> Dict[str, Any]:
    new_dash = _read_json(new_path)
    new_features = _extract_features(new_dash)

    old_dash: Dict[str, Any] = {}
    old_features: Dict[str, FeatureLite] = {}
    if old_path is not None and old_path.exists():
        old_dash = _read_json(old_path)
        old_features = _extract_features(old_dash)

    added, removed, changed = _diff_features(old_features, new_features)

    delta: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "baseline_generated_at": old_dash.get("generated_at") if old_dash else None,
        "new_generated_at": new_dash.get("generated_at"),
        "counts": {
            "total_old": len(old_features),
            "total_new": len(new_features),
            "features_added": len(added) if old_dash else len(new_features),
            "features_removed": len(removed) if old_dash else 0,
            "features_changed": len(changed) if old_dash else 0,
        },
        "gaps": {
            "old": _extract_gap_counts(old_dash) if old_dash else {"total": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0},
            "new": _extract_gap_counts(new_dash),
        },
        "top_added": _top_items(added if old_dash else new_features.values(), top_n),
        "top_removed": _top_items(removed, top_n),
        "changed": changed[:top_n],
        "note": None if old_dash else "No baseline dashboard.json found; treating all current items as newly added.",
    }

    return delta


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a delta between two dashboard snapshots")
    parser.add_argument("--old", default="docs/reports/dashboard.json", help="Path to previous published dashboard")
    parser.add_argument("--new", default="data/dashboard/dashboard_latest.json", help="Path to newly generated dashboard")
    parser.add_argument("--out-json", default="docs/reports/dashboard_delta.json", help="Output JSON path")
    parser.add_argument("--out-md", default="docs/reports/dashboard_delta.md", help="Output Markdown path")
    parser.add_argument("--top", type=int, default=8, help="Max items to include in samples")
    args = parser.parse_args()

    old_path = Path(args.old) if args.old else None
    new_path = Path(args.new)

    if not new_path.exists():
        logger.error(f"New dashboard snapshot not found: {new_path}")
        return 2

    out_json = Path(args.out_json)
    out_md = Path(args.out_md)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    delta = generate_delta(old_path=old_path, new_path=new_path, top_n=args.top)

    out_json.write_text(json.dumps(delta, indent=2), encoding="utf-8")
    out_md.write_text(_render_markdown(delta), encoding="utf-8")

    logger.info(f"Wrote delta JSON: {out_json}")
    logger.info(f"Wrote delta Markdown: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
