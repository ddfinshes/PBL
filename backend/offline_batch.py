"""Offline batch runner for PBL discussions.

Run all trigger questions in all scenes without frontend participation,
reusing existing backend agent and graph workflow.

Usage:
    python -m backend.offline_batch
    python -m backend.offline_batch --case "2024秋-泌尿系统PBL-肾脏中的“宝石”"
    python -m backend.offline_batch --case-file backend/case/example.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage

from .agents import register_student_agent, student_nodes, student_personas
from .graph_builder import build_graph
from .pbl_info import update_pbl_info


BASE_DIR = Path(__file__).parent
CASE_DIR = BASE_DIR / "case"
AGENT_SETTING_PATH = BASE_DIR / "agent_setting.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "test_bench"


def _load_agent_personas() -> Dict[str, Dict[str, Any]]:
    if not AGENT_SETTING_PATH.exists():
        raise FileNotFoundError(
            f"Missing agent setting file: {AGENT_SETTING_PATH}")

    with open(AGENT_SETTING_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or not data:
        raise ValueError("agent_setting.json is empty or invalid.")

    return data


def _reset_and_build_graph(personas: Dict[str, Dict[str, Any]]):
    # Re-initialize all student agents for each trigger question run.
    student_personas.clear()
    student_nodes.clear()

    for agent_id, persona in personas.items():
        register_student_agent(agent_id, persona)

    agent_ids = list(student_nodes.keys())
    if not agent_ids:
        raise RuntimeError("No student agents registered.")

    return build_graph(agent_ids)


def _iter_case_files(case_name: Optional[str], case_file: Optional[str]) -> List[Path]:
    if case_file:
        p = Path(case_file)
        if not p.is_absolute():
            p = Path.cwd() / p
        if not p.exists() or p.suffix.lower() != ".json":
            raise FileNotFoundError(f"Invalid --case-file: {case_file}")
        return [p]

    if case_name:
        direct = CASE_DIR / f"{case_name}.json"
        if direct.exists():
            return [direct]

        matched: List[Path] = []
        for f in CASE_DIR.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                if str(data.get("case_title", "")).strip() == case_name.strip():
                    matched.append(f)
            except Exception:
                continue

        if matched:
            return sorted(matched)
        raise FileNotFoundError(f"Case not found for --case: {case_name}")

    return sorted(CASE_DIR.glob("*.json"))


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _extract_scene_questions(scene: Dict[str, Any]) -> List[Tuple[int, str, List[str]]]:
    """Return tuples: (question_id_1_based, question_text, learning_objectives)."""
    trigger_questions = scene.get("trigger_questions") or []
    rows = scene.get("trigger_question_learning_objectives") or []

    result: List[Tuple[int, str, List[str]]] = []
    for idx, q in enumerate(trigger_questions, start=1):
        if isinstance(q, dict):
            question_text = _safe_str(q.get("question"))
        else:
            question_text = _safe_str(q)

        objectives: List[str] = []
        if isinstance(rows, list) and idx - 1 < len(rows) and isinstance(rows[idx - 1], dict):
            raw = rows[idx - 1].get("learning_objectives") or []
            if isinstance(raw, list):
                objectives = [_safe_str(item)
                              for item in raw if _safe_str(item)]

        # Fallback: some case files may store objectives directly in trigger question.
        if not objectives and isinstance(q, dict):
            raw_inline = q.get("learning_objectives") or []
            if isinstance(raw_inline, list):
                objectives = [_safe_str(item)
                              for item in raw_inline if _safe_str(item)]

        result.append((idx, question_text, objectives))

    return result


def _build_initial_case_text(scene: Dict[str, Any], trigger_question: str) -> str:
    story = _safe_str(scene.get("story_content"))
    return (
        f"{story}\n"
        f" Trigger Question: {trigger_question}\n"
        "Please start your discussion."
    )


async def _run_single_trigger_question(
    app,
    case_title: str,
    scene: Dict[str, Any],
    scene_index_0: int,
    question_index_0: int,
    trigger_question: str,
    objectives: List[str],
    out_file: Path,
) -> None:
    scene_idx_1 = scene_index_0 + 1
    question_idx_1 = question_index_0 + 1

    update_pbl_info(
        story=_safe_str(scene.get("story_content")),
        questions=[trigger_question],
        scene_idx=scene_index_0,
        q_idx=question_index_0,
        learning_objectives=objectives,
        case_name=case_title,
    )

    initial_case = _build_initial_case_text(scene, trigger_question)
    init_msg = HumanMessage(content=initial_case, name="case_introduction")

    state: Dict[str, Any] = {
        "messages": [init_msg],
        "total_messages": 0,
        "private_memory": {},
        "knowledge_state": {},
        "cognitive_load": {},
        "self_efficacy": {},
        "next_speaker": "router",
        "is_teacher_interrupted": False,
        "discussion_active": True,
        "force_no_silence_once": False,
        "current_topic": "开始讨论",
        "trigger_question": trigger_question,
        "objective_evaluations": [],
        "achieved_all": False,
        "end_reason": "",
    }

    config = {
        "configurable": {
            "thread_id": f"offline_{scene_idx_1}_{question_idx_1}_{uuid.uuid4().hex[:8]}"
        },
        "recursion_limit": 60,
    }

    conversation: List[Dict[str, str]] = [
        {
            "content": initial_case,
            "role": "case_introduction",
        }
    ]
    _flush_conversation(out_file, conversation)

    async for event in app.astream(state, config=config):
        for node, out in event.items():
            if not isinstance(out, dict):
                continue

            # 【关键修复】从每个节点的输出中更新状态，确保 cognitive_load 和 self_efficacy 能持续累积
            if "cognitive_load" in out:
                state["cognitive_load"] = dict(
                    state.get("cognitive_load", {}) or {})
                state["cognitive_load"].update(out.get("cognitive_load", {}))
            if "self_efficacy" in out:
                state["self_efficacy"] = dict(
                    state.get("self_efficacy", {}) or {})
                state["self_efficacy"].update(out.get("self_efficacy", {}))

            for message in out.get("messages", []) or []:
                content = _safe_str(getattr(message, "content", ""))
                if not content:
                    continue
                role = _safe_str(getattr(message, "name", "")
                                 ) or _safe_str(node) or "unknown"

                # 获取发言者的认知负荷和自我效能感
                msg_item = {
                    "content": content,
                    "role": role,
                }

                # 如果是学生发言（学生节点名称在state中），获取其动态状态
                if role in student_nodes:
                    cognitive_load = state.get(
                        "cognitive_load", {}).get(role, 3)  # 改为默认3而不是6
                    self_efficacy = state.get("self_efficacy", {}).get(role, 6)
                    msg_item["cognitive_load"] = int(cognitive_load)
                    msg_item["self_efficacy"] = int(self_efficacy)

                conversation.append(msg_item)
                _flush_conversation(out_file, conversation)


def _write_output(output_dir: Path, scene_idx_1: int, question_idx_1: int, payload: Dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / \
        f"trigger_question_scene_{scene_idx_1}_{question_idx_1}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_file


def _flush_conversation(out_file: Path, conversation: List[Dict[str, str]]) -> None:
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"conversation": conversation},
                  f, ensure_ascii=False, indent=2)


async def run_batch(case_name: Optional[str], case_file: Optional[str], output_root: Path) -> None:
    personas = _load_agent_personas()
    case_files = _iter_case_files(case_name=case_name, case_file=case_file)

    if not case_files:
        raise RuntimeError(f"No case files found under {CASE_DIR}")

    total_jobs = 0
    written_files: List[Path] = []

    for case_path in case_files:
        with open(case_path, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        case_title = _safe_str(case_data.get("case_title")) or case_path.stem
        scenes = case_data.get("scenes") or []
        if not isinstance(scenes, list):
            continue

        # Use case-specific folder to avoid filename collisions when processing multiple cases.
        case_output_dir = output_root / case_path.stem

        for scene_index_0, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                continue

            questions = _extract_scene_questions(scene)
            for question_idx_1, trigger_question, objectives in questions:
                if not trigger_question:
                    continue

                question_index_0 = question_idx_1 - 1
                app = _reset_and_build_graph(personas)

                out_file = _write_output(
                    output_dir=case_output_dir,
                    scene_idx_1=scene_index_0 + 1,
                    question_idx_1=question_idx_1,
                    payload={"conversation": []},
                )

                await _run_single_trigger_question(
                    app=app,
                    case_title=case_title,
                    scene=scene,
                    scene_index_0=scene_index_0,
                    question_index_0=question_index_0,
                    trigger_question=trigger_question,
                    objectives=objectives,
                    out_file=out_file,
                )
                written_files.append(out_file)
                total_jobs += 1
                print(f"[offline-batch] wrote: {out_file}")

    print(f"[offline-batch] completed jobs: {total_jobs}")
    print(f"[offline-batch] output files: {len(written_files)}")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run offline PBL discussion batch for all scenes and trigger questions."
    )
    parser.add_argument(
        "--case",
        type=str,
        default=None,
        help="Case stem or case_title to run. If omitted, process all case/*.json files.",
    )
    parser.add_argument(
        "--case-file",
        type=str,
        default=None,
        help="Explicit case JSON file path. Overrides --case.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory root. Default: backend/test_bench",
    )
    return parser


def main() -> None:
    # Fix for Windows: Avoid "Event loop is closed" warning
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = _build_arg_parser()
    args = parser.parse_args()
    output_root = Path(args.output_dir)

    asyncio.run(
        run_batch(
            case_name=args.case,
            case_file=args.case_file,
            output_root=output_root,
        )
    )


if __name__ == "__main__":
    main()
