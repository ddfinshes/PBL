from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from .config import BASE_URL, DASHSCOPE_API_KEY, LLM_MODEL_NAME

logger = logging.getLogger(__name__)


def normalize_knowledge_points(raw_points: Any) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for idx, item in enumerate(raw_points or []):
        point_id = ""
        point = ""
        explanation = ""

        if isinstance(item, dict):
            point_id = str(item.get("id", "") or "").strip()
            point = str(item.get("point", item.get(
                "concept", "")) or "").strip()
            explanation = str(item.get("explanation", "") or "").strip()
        else:
            point = str(item or "").strip()

        if not point:
            continue

        if not point_id:
            point_id = f"kp_{idx + 1}"

        normalized.append({
            "id": point_id,
            "point": point,
            "explanation": explanation,
        })

    seen = set()
    deduped: List[Dict[str, str]] = []
    for item in normalized:
        key = item["point"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def next_kp_id(points: List[Dict[str, str]]) -> str:
    used = {str(p.get("id", "")).strip()
            for p in points if isinstance(p, dict)}
    idx = 1
    while f"kp_{idx}" in used:
        idx += 1
    return f"kp_{idx}"


def ensure_question_knowledge_points(
        case_data: Dict[str, Any],
        scene_idx: int,
        question_idx: int,
) -> Tuple[Optional[List[Dict[str, str]]], Optional[str]]:
    scenes = case_data.get("scenes", [])
    if scene_idx < 0 or scene_idx >= len(scenes):
        return None, "场景索引越界"

    scene = scenes[scene_idx]
    questions = scene.get("trigger_questions", [])
    if question_idx < 0 or question_idx >= len(questions):
        return None, "问题索引越界"

    question = questions[question_idx]
    q_text = str(question.get("question", "") or "").strip()

    rows = scene.get("trigger_question_learning_objectives")
    if not isinstance(rows, list):
        rows = []
        scene["trigger_question_learning_objectives"] = rows

    while len(rows) <= question_idx:
        rows.append({"trigger_question": "",
                    "learning_objectives": [], "knowledge_points": []})

    row = rows[question_idx]
    if not isinstance(row, dict):
        row = {"trigger_question": "",
               "learning_objectives": [], "knowledge_points": []}
        rows[question_idx] = row

    row["trigger_question"] = q_text
    if not isinstance(row.get("learning_objectives"), list):
        row["learning_objectives"] = []

    row_points = normalize_knowledge_points(row.get("knowledge_points", []))
    question_points = normalize_knowledge_points(
        question.get("knowledge_points", []))

    canonical = row_points if row_points else question_points
    row["knowledge_points"] = canonical
    question["knowledge_points"] = canonical

    return canonical, None


def collect_case_question_knowledge_points(case_data: Dict[str, Any]) -> List[str]:
    points: List[str] = []

    def append_unique(raw: Any):
        for item in normalize_knowledge_points(raw):
            p = item.get("point", "").strip()
            if p and p not in points:
                points.append(p)

    for scene in case_data.get("scenes", []) or []:
        if not isinstance(scene, dict):
            continue
        for q in scene.get("trigger_questions", []) or []:
            if isinstance(q, dict):
                append_unique(q.get("knowledge_points", []))
        for row in scene.get("trigger_question_learning_objectives", []) or []:
            if isinstance(row, dict):
                append_unique(row.get("knowledge_points", []))

    return points


def sync_agent_setting_knowledge_points(case_data: Dict[str, Any], agent_setting_path: Path) -> None:
    if not agent_setting_path.exists():
        return

    try:
        with open(agent_setting_path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return
            personas = json.loads(content)

        if not isinstance(personas, dict):
            return

        all_points = collect_case_question_knowledge_points(case_data)
        for _, persona in personas.items():
            if isinstance(persona, dict):
                persona["all_knowledge_points"] = list(all_points)

        with open(agent_setting_path, "w", encoding="utf-8") as f:
            json.dump(personas, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("同步 agent_setting.json 知识点失败: %s", e)


def build_discussion_content_from_leaf(messages_map: Dict[str, Dict[str, Any]], leaf_id: str) -> str:
    if not leaf_id or leaf_id not in messages_map:
        return ""

    lines: List[str] = []
    curr = messages_map.get(leaf_id)
    safety = 0

    while curr and safety < 2000:
        agent = str(curr.get("agent", "") or "").strip()
        content = str(curr.get("content", "") or "").strip()
        if content and agent not in {"case_introduction", "Start Discussion"}:
            lines.append(f"[{agent}]: {content}")
        parent_id = curr.get("parent_id")
        curr = messages_map.get(parent_id) if parent_id else None
        safety += 1

    lines.reverse()
    return "\n\n".join(lines)


def _safe_parse_json(raw_text: str) -> Dict[str, Any]:
    text = str(raw_text or "").strip()
    if not text:
        return {}

    fenced = re.search(
        r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, flags=re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    obj = re.search(r"\{[\s\S]*\}", text)
    if obj:
        try:
            return json.loads(obj.group(0))
        except Exception:
            return {}
    return {}


def _normalize_score(v: Any) -> float:
    try:
        fv = float(v)
    except Exception:
        return 0.0
    if fv >= 0.95:
        return 1.0
    if fv >= 0.55:
        return 0.6
    if fv >= 0.15:
        return 0.3
    return 0.0


async def evaluate_progressive_coverage(
        case_data: Dict[str, Any],
        scene_index: int,
        question_index: int,
        discussion_content: str,
) -> Dict[str, Any]:
    knowledge_points, err = ensure_question_knowledge_points(
        case_data, scene_index, question_index)
    if err:
        return {"status": "error", "message": err}

    if not knowledge_points:
        return {
            "status": "success",
            "total_points": 0,
            "covered_points": [],
            "coverage_ratio": 0.0,
            "coverage_score": 0.0,
            "point_scores": [],
            "covered_point_details": [],
        }

    normalized_points = normalize_knowledge_points(knowledge_points)
    if not normalized_points:
        return {
            "status": "success",
            "total_points": 0,
            "covered_points": [],
            "coverage_ratio": 0.0,
            "coverage_score": 0.0,
            "point_scores": [],
            "covered_point_details": [],
        }

    knowledge_points_str = "\n".join([
        f"- id: {kp['id']}\n  point: {kp['point']}\n  explanation: {kp['explanation']}"
        for kp in normalized_points
    ])

    prompt = f"""请分析以下讨论内容，判断每个知识点的覆盖深度分数。

【知识点列表】
{knowledge_points_str}

【讨论内容】
{discussion_content}

【任务】
请逐个检查每个知识点，输出一个 coverage_score，分值只能是以下四档之一：
- 0.0: 未涉及
- 0.3: 初步提及概念（点到为止，无机制）
- 0.6: 解释机制或原理（有一定因果/过程）
- 1.0: 结合临床或推理应用（用于诊断、鉴别、治疗决策等）

【输出格式】
请以 JSON 格式输出：
{{
  "point_scores": [
	{{"id": "kp_1", "coverage_score": 0.6, "evidence": "讨论中提到了..."}}
  ]
}}

严格要求：
1) 只能返回【知识点列表】中已有 id；
2) coverage_score 只能是 0.0 / 0.3 / 0.6 / 1.0；
3) 只输出 JSON。
"""

    score_by_id: Dict[str, float] = {}
    evidence_by_id: Dict[str, str] = {}

    try:
        llm = ChatOpenAI(
            api_key=DASHSCOPE_API_KEY,
            model=LLM_MODEL_NAME,
            base_url=BASE_URL,
            temperature=0,
        )
        logger.info("[coverage] Requesting LLM evaluation for question %d, scene %d. Discussion length: %d chars",
                    question_index, scene_index, len(discussion_content))

        response = await llm.ainvoke([HumanMessage(content=prompt)])

        logger.info("[coverage] LLM response received: %s",
                    str(response.content)[:200] + "...")

        covered_data = _safe_parse_json(str(response.content or ""))

        valid_ids = {kp["id"] for kp in normalized_points}
        raw_scores = covered_data.get("point_scores", [])
        if not isinstance(raw_scores, list):
            raw_scores = []

        for item in raw_scores:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("id", "") or "").strip()
            if cid not in valid_ids:
                continue
            score_by_id[cid] = _normalize_score(item.get("coverage_score", 0))
            evidence_by_id[cid] = str(item.get("evidence", "") or "").strip()
    except Exception as e:
        logger.warning("[coverage] LLM evaluation failed: %s", e)

    # 优先保持“LLM 作为评分器”的单一策略：解析失败时保持 0 分，等待后续轮次重评。

    point_scores: List[Dict[str, Any]] = []
    covered_point_names: List[str] = []
    covered_point_details: List[Dict[str, Any]] = []

    for kp in normalized_points:
        pid = kp["id"]
        score = float(score_by_id.get(pid, 0.0))
        score = 1.0 if score > 1.0 else (0.0 if score < 0 else score)
        evidence = str(evidence_by_id.get(pid, "") or "").strip()

        row = {
            "id": pid,
            "point": kp["point"],
            "coverage_score": round(score, 3),
            "evidence": evidence,
            "explanation": kp.get("explanation", ""),
        }
        point_scores.append(row)

        if score > 0:
            covered_point_names.append(kp["point"])
            covered_point_details.append(dict(row))

    total_points = len(normalized_points)
    coverage_score = sum(item["coverage_score"] for item in point_scores)
    coverage_ratio = (
        coverage_score / total_points) if total_points > 0 else 0.0

    return {
        "status": "success",
        "total_points": total_points,
        "covered_point_ids": [item["id"] for item in point_scores if item["coverage_score"] > 0],
        "covered_points": covered_point_names,
        "point_scores": point_scores,
        "coverage_score": round(coverage_score, 3),
        "coverage_ratio": round(coverage_ratio, 3),
        "covered_point_details": covered_point_details,
    }


async def evaluate_objectives_from_discussion(
    trigger_question: str,
    learning_objectives: List[str],
    discussion_content: str,
) -> Dict[str, Any]:
    cleaned_objectives = [str(o or "").strip()
                          for o in learning_objectives if str(o or "").strip()]
    if not cleaned_objectives:
        return {
            "achieved_all": False,
            "trigger_question": trigger_question,
            "objective_evaluations": [],
        }

    if len(str(discussion_content or "").strip()) < 20:
        return {
            "achieved_all": False,
            "trigger_question": trigger_question,
            "objective_evaluations": [
                {
                    "objective": obj,
                    "achieved": False,
                    "status": "not_discussed",
                    "evidence": "讨论内容不足，暂无法判定。",
                }
                for obj in cleaned_objectives
            ],
        }

    objective_text = "\n".join(f"- {obj}" for obj in cleaned_objectives)
    judge_prompt = (
        "你是医学PBL讨论的学习目标评估器。\n"
        "请判断当前触发问题下的学习目标是否已经达到可结束讨论的程度。\n\n"
        f"当前触发问题：{trigger_question or '未提供'}\n"
        f"学习目标：\n{objective_text}\n\n"
        "讨论记录：\n"
        f"{discussion_content}\n\n"
        "判定规则：\n"
        "1. 若绝大多数关键目标已明确讨论并形成稳定结论，可判定 achieved；\n"
        "2. 仅表面提及或存在明显未解决分歧，判定 not_achieved；\n"
        "3. 不确定时保守返回未达成。\n\n"
        "请严格输出 JSON，不要附加其他文字。JSON 格式：\n"
        "{\n"
        "  \"achieved_all\": true/false,\n"
        "  \"objective_evaluations\": [\n"
        "    {\n"
        "      \"objective\": \"...\",\n"
        "      \"achieved\": true/false,\n"
        "      \"status\": \"achieved|in_progress|not_discussed\",\n"
        "      \"evidence\": \"一句证据描述\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    try:
        llm = ChatOpenAI(
            api_key=DASHSCOPE_API_KEY,
            model=LLM_MODEL_NAME,
            base_url=BASE_URL,
            temperature=0,
        )
        result = await llm.ainvoke([HumanMessage(content=judge_prompt)])
        parsed = _safe_parse_json(str(result.content or ""))

        objective_rows = parsed.get("objective_evaluations", [])
        if not isinstance(objective_rows, list):
            objective_rows = []

        normalized_rows: List[Dict[str, Any]] = []
        for row in objective_rows:
            objective = str((row or {}).get("objective", "")).strip()
            if not objective:
                continue
            status = str((row or {}).get("status", "")).strip().lower()
            if status not in {"achieved", "in_progress", "not_discussed"}:
                status = "achieved" if bool(
                    (row or {}).get("achieved")) else "not_discussed"
            normalized_rows.append({
                "objective": objective,
                "achieved": bool((row or {}).get("achieved", False)),
                "status": status,
                "evidence": str((row or {}).get("evidence", "")).strip(),
            })

        existing = {item["objective"] for item in normalized_rows}
        for obj in cleaned_objectives:
            if obj not in existing:
                normalized_rows.append({
                    "objective": obj,
                    "achieved": False,
                    "status": "not_discussed",
                    "evidence": "",
                })

        achieved_all = all(bool(item.get("achieved"))
                           for item in normalized_rows) if normalized_rows else False
        return {
            "achieved_all": achieved_all,
            "trigger_question": trigger_question,
            "objective_evaluations": normalized_rows,
        }
    except Exception as e:
        logger.warning("objective evaluation failed: %s", e)
        return {
            "achieved_all": False,
            "trigger_question": trigger_question,
            "objective_evaluations": [
                {
                    "objective": obj,
                    "achieved": False,
                    "status": "not_discussed",
                    "evidence": "目标评估失败，保守视为未达成。",
                }
                for obj in cleaned_objectives
            ],
        }
