"""Case JSON path resolver.

This module is intentionally dependency-light to avoid circular imports.
It can be imported by both `server.py` and runtime agent modules.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Keep directory convention identical to `server.py`.
BASE_DIR = Path(__file__).parent
CASE_STORAGE_DIR = BASE_DIR / "case"


def resolve_case_json_path(case_name: str) -> Optional[Path]:
    """Resolve case JSON path by filename first, then by case_title fallback.

    This mirrors the logic in `server.py` but is isolated here to avoid
    circular imports (server -> graph -> agents -> agent_config -> server).
    """
    if not case_name:
        return None

    # 1) Direct filename match: /case/{case_name}.json
    direct = CASE_STORAGE_DIR / f"{case_name}.json"
    if direct.exists():
        return direct

    def _knowledge_point_count(case_data: Dict[str, Any]) -> int:
        count = 0
        scenes = case_data.get("scenes") or []
        if not isinstance(scenes, list):
            return 0
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            questions = scene.get("trigger_questions") or []
            if not isinstance(questions, list):
                continue
            for q in questions:
                if not isinstance(q, dict):
                    continue
                points = q.get("knowledge_points") or []
                if isinstance(points, list):
                    count += len(points)
        return count

    # 2) Title match in JSON content (handles filename/title mismatch).
    # Prefer richer case files when duplicates exist.
    target = case_name.strip()
    candidates: List[tuple] = []
    try:
        for f in CASE_STORAGE_DIR.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                if str(data.get("case_title", "")).strip() == target:
                    kp_count = _knowledge_point_count(data)
                    scene_count = len(data.get("scenes") or [])
                    stem_exact = 1 if f.stem.strip() == target else 0
                    candidates.append(
                        (stem_exact, kp_count, scene_count, int(f.stat().st_mtime), f)
                    )
            except Exception:
                continue
    except Exception as e:
        logger.warning("resolve_case_json_path scan failed: %s", e)
        return None

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][4]

    return None

