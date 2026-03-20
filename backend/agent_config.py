"""Shared agent configuration and utility services.

This module hosts reusable configuration-oriented logic so `agents.py`
can focus on workflow orchestration.
"""
from __future__ import annotations
from langchain_core.messages import BaseMessage
from typing import Dict, List, Any, Optional
import logging
import json

from typing import Dict, List
import re
import random

from .agent_settings import _extract_numeric_trait_scores

# 知识图谱相关：基于病例 JSON + cognitive_orientation 构建图
from . import pbl_info
from .knowledge import build_agent_knowledge_graph
from .case_resolver import resolve_case_json_path
from pathlib import Path


KNOWLEDGE_LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2}
KNOWLEDGE_LEVELS = ["low", "medium", "high"]

# Base prior weights for non-silence actions. Silence prior is computed dynamically.
BASE_NON_SILENCE_PRIOR_WEIGHTS = {
    "accumulation": 0.63,
    "seeking_help_alignment": 0.10,
    "correction_challenge": 0.07,
}


class KnowledgeStateService:
    """Encapsulates knowledge-state parsing, initialization and aggregation logic."""

    @staticmethod
    def get_latest_internalized_note(state: Dict, agent_id: str, private_memory: Dict) -> str:
        """获取指定 Agent 最近的一条内化笔记。"""
        agent_memory = private_memory.get(agent_id, [])
        if not isinstance(agent_memory, list):
            return "暂无上一条可用内化信息。"

        for item in reversed(agent_memory[-8:]):
            if str(item.get("action", "")) == "internalize_message":
                source = str(item.get("source_speaker", "") or "unknown")
                note = str(item.get("internalized_note", "") or "").strip()
                if note:
                    return f"来源={source}; 内化={note}"
        return "暂无上一条可用内化信息。"

    @staticmethod
    def apply_knowledge_updates(
        agent_id: str,
        persona: Dict,
        agent_knowledge_state: Dict[str, Dict],
        payload: Dict,
        load_level: int,
        trigger_objectives: List[str] = None,
    ) -> Dict[str, Dict]:
        """根据内化结果更新知识状态。

        考虑因素：
        1. 学习可塑性 (learning_adaptivity): 影响掌握知识点的成功率 (high: 1.0, medium: 0.7, low: 0.4)
        2. 认知方式 (cognitive_orientation): 影响知识掌握的深度与关联性
        3. 触发问题目标 (trigger_objectives): 优先掌握目标范围内的知识
        """
        normalized = KnowledgeStateService._normalize_agent_state_schema(
            agent_knowledge_state)
        kb = dict(normalized.get("knowledge_background", {}) or {})
        for level in ("high", "medium", "low"):
            values = kb.get(level, [])
            kb[level] = list(values) if isinstance(values, list) else []
        before_mastered = list(normalized.get("mastered_points", []) or [])
        mastered_points = list(before_mastered)
        knowledge_graph = normalized.get("knowledge_graph")

        # 获取学生特性
        adaptivity = str(persona.get("learning_adaptivity", "medium")).lower()
        orientation = str(persona.get(
            "cognitive_orientation", "point_based")).lower()

        # 可塑性影响掌握门槛
        adaptivity_map = {"high": 1.0, "medium": 0.7, "low": 0.4}
        success_rate = adaptivity_map.get(adaptivity, 0.7)
        # 对于 point_based 学生，适当提升一次性“吃下”新点的概率，
        # 否则在低背景（initial_level=low）+ 中等可塑性时几乎不会记住任何点。
        if orientation == "point_based":
            success_rate = min(1.0, success_rate + 0.2)

        # 根据认知负荷决定本轮能处理的知识点上限
        max_mastered_points = 2 if load_level <= 6 else (
            1 if load_level <= 8 else 0)

        points_to_check = payload.get(
            "mastered_points", []) if isinstance(payload, dict) else []
        if not isinstance(points_to_check, list):
            points_to_check = []

        mastered_used = 0
        for point in points_to_check:
            if mastered_used >= max_mastered_points:
                break

            cleaned = str(point or "").strip()
            if not cleaned:
                continue

            # 学习可塑性校验：概率决定是否真正“掌握”
            if random.random() > success_rate:
                continue

            # 知识点关联性校验 (基于认知方式)
            # 点思维 (point_based) 只能掌握孤立点，线思维 (line_based) 可初步建立联系
            if orientation == "point_based" and len(cleaned) > 20:
                # 点思维可能难以一次性内化复杂的长知识链
                pass

            # 校验所属领域级别
            domain = KnowledgeStateService.extract_domain(cleaned)
            initial_level = KnowledgeStateService.normalize_level(
                KnowledgeStateService.persona_domain_level(persona, domain))

            # 低相关领域知识不轻易标记为已掌握，除非可塑性高；
            # 但对 point_based 学生放宽限制，否则他们在“低背景”领域几乎永远无法积累新点。
            if initial_level == "low" and adaptivity != "high" and orientation != "point_based":
                continue

            mastered_points.append(cleaned)
            mastered_used += 1

        for level in ("high", "medium", "low"):
            kb[level] = KnowledgeStateService._dedupe_keep_order(kb[level])
        mastered_points = KnowledgeStateService._dedupe_keep_order(
            mastered_points)

        # ---- 可观测性：输出每轮知识状态变化 ----
        try:
            before_set = set(str(p or "").strip() for p in before_mastered if str(p or "").strip())
            after_set = set(mastered_points)
            added = [p for p in mastered_points if p not in before_set]
            g_nodes = 0
            g_edges = 0
            graph_visual_lines: List[str] = []
            if isinstance(knowledge_graph, dict):
                nodes_obj = knowledge_graph.get("nodes", {})
                edges_obj = knowledge_graph.get("edges", [])
                g_nodes = len(nodes_obj) if isinstance(nodes_obj, dict) else 0
                g_edges = len(edges_obj) if isinstance(edges_obj, list) else 0

                # 构造一个小型“邻接视图”，帮助直观理解当前图谱结构
                if isinstance(nodes_obj, dict) and isinstance(edges_obj, list):
                    # 1) 列出新增掌握点对应的节点ID（精确用 point 匹配）
                    added_ids: List[str] = []
                    added_clean = [s for s in added if s]
                    for nid, node in nodes_obj.items():
                        try:
                            if not isinstance(node, dict):
                                continue
                            pt = str(node.get("point", "") or "").strip()
                            if pt and pt in added_clean:
                                added_ids.append(str(nid))
                        except Exception:
                            continue
                    added_ids = added_ids[:5]

                    # 2) 为这些节点构造一小段“邻接列表” ASCII 视图
                    if added_ids:
                        graph_visual_lines.append("新增掌握点局部邻接视图：")
                        for nid in added_ids:
                            node = nodes_obj.get(nid, {})
                            label = ""
                            try:
                                label = str(node.get("point", "") or "").strip()
                            except Exception:
                                pass
                            neighbors: List[str] = []
                            for e in edges_obj:
                                if not isinstance(e, dict):
                                    continue
                                src = str(e.get("source", "") or "")
                                dst = str(e.get("target", "") or "")
                                rel = str(e.get("relation", "") or "")
                                if src == nid:
                                    tgt_label = ""
                                    try:
                                        tgt_label = str(
                                            (nodes_obj.get(dst, {}) or {}).get("point", "") or ""
                                        ).strip()
                                    except Exception:
                                        tgt_label = ""
                                    neighbors.append(f"{nid} -[{rel}]-> {dst} ({tgt_label})")
                                elif dst == nid:
                                    src_label = ""
                                    try:
                                        src_label = str(
                                            (nodes_obj.get(src, {}) or {}).get("point", "") or ""
                                        ).strip()
                                    except Exception:
                                        src_label = ""
                                    neighbors.append(f"{src} -[{rel}]-> {nid} ({src_label})")
                            # 控制长度：每个点最多展示若干条边
                            neighbors = neighbors[:6]
                            graph_visual_lines.append(
                                f"  [{nid}] {label or 'N/A'}:"
                            )
                            if neighbors:
                                for line in neighbors:
                                    graph_visual_lines.append(f"    {line}")
                            else:
                                graph_visual_lines.append("    (无直接邻接边)")

                    # 若本轮没有新增掌握点，则给一个小的整体 preview
                    if not added_ids and g_nodes > 0 and g_edges > 0:
                        graph_visual_lines.append("图谱整体预览（前若干条边）：")
                        for e in edges_obj[:8]:
                            if not isinstance(e, dict):
                                continue
                            src = str(e.get("source", "") or "")
                            dst = str(e.get("target", "") or "")
                            rel = str(e.get("relation", "") or "")
                            src_label = str(
                                (nodes_obj.get(src, {}) or {}).get("point", "") or ""
                            ).strip()
                            dst_label = str(
                                (nodes_obj.get(dst, {}) or {}).get("point", "") or ""
                            ).strip()
                            graph_visual_lines.append(
                                f"  {src} ({src_label}) -[{rel}]-> {dst} ({dst_label})"
                            )

            graph_visual_block = "\n".join(graph_visual_lines) if graph_visual_lines else ""

            logger.info(
                "KNOWLEDGE_GRAPH_UPDATE agent=%s name=%s orientation=%s load=%s "
                "added_mastered=%s total_mastered=%s graph_nodes=%s graph_edges=%s\n%s",
                str(agent_id or "").strip() or "unknown",
                str(persona.get("name", "") or "").strip() or "unknown",
                str(persona.get("cognitive_orientation", "point_based") or "").strip(),
                int(load_level),
                added[:6],
                len(mastered_points),
                g_nodes,
                g_edges,
                graph_visual_block,
            )
        except Exception as e:
            logger.warning("KNOWLEDGE_GRAPH_UPDATE log failed: %s", e)

        # 保留/回写知识图谱（结构拓扑目前不在这里改变，只更新掌握点列表）
        new_state: Dict[str, Any] = {
            "knowledge_background": kb,
            "mastered_points": mastered_points,
        }
        if isinstance(knowledge_graph, dict):
            new_state["knowledge_graph"] = knowledge_graph
        return new_state

    @staticmethod
    def append_private_memory(
        state: Dict,
        agent_id: str,
        action_type: str,
        reason: str,
        load_level: int,
        self_efficacy_level: int,
        source_speaker: str = "",
        internalized_note: str = "",
    ) -> Dict[str, List[Dict]]:
        """向 Agent 的私有记忆中追加一条记录并保持最近 20 条。"""
        private_memory = dict(state.get("private_memory", {}) or {})
        agent_memory = list(private_memory.get(agent_id, []) or [])
        agent_state = ((state.get("knowledge_state", {})
                       or {}).get(agent_id, {}) or {})
        kb_snapshot = agent_state.get(
            "knowledge_background", {}) if isinstance(agent_state, dict) else {}

        import time
        knowledge_domains = {
            domain: level
            for level in ["high", "medium", "low"]
            for domain in (kb_snapshot.get(level, []) if isinstance(kb_snapshot, dict) else [])
        }
        agent_memory.append(
            {
                "timestamp": int(time.time()),
                "action": action_type,
                "reason": reason,
                "cognitive_load": load_level,
                "self_efficacy": self_efficacy_level,
                "topic": state.get("current_topic", ""),
                "source_speaker": source_speaker,
                "internalized_note": internalized_note,
                "knowledge_domains": knowledge_domains,
            }
        )
        private_memory[agent_id] = agent_memory[-20:]
        return private_memory

    @staticmethod
    def build_private_memory_brief(private_memory: Dict, agent_id: str, window: int = 5) -> List[Dict]:
        """构建私有记忆的简短摘要，用于 Prompt 上下文。"""
        agent_memory = private_memory.get(agent_id, [])
        if not isinstance(agent_memory, list):
            return []
        recent = agent_memory[-window:]
        brief: List[Dict] = []
        for item in recent:
            brief.append(
                {
                    "action": item.get("action", ""),
                    "reason": item.get("reason", ""),
                    "cognitive_load": item.get("cognitive_load", 6),
                    "self_efficacy": item.get("self_efficacy", 6),
                    "topic": item.get("topic", ""),
                    "source_speaker": item.get("source_speaker", ""),
                    "internalized_note": item.get("internalized_note", ""),
                }
            )
        return brief

    @staticmethod
    def _empty_knowledge_background() -> Dict[str, List[str]]:
        return {"high": [], "medium": [], "low": []}

    @staticmethod
    def _dedupe_keep_order(values: List[str]) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if value and value not in seen:
                seen.add(value)
                ordered.append(value)
        return ordered

    @staticmethod
    def _normalize_agent_state_schema(agent_state: Dict) -> Dict[str, Dict]:
        """Convert old and mixed schemas to canonical schema.

        Canonical schema:
        {
          "knowledge_background": {"high": [...], "medium": [...], "low": [...]},
          "mastered_points": [...]
        }
        """
        state = dict(agent_state or {})
        existing_graph = state.get("knowledge_graph")

        if "knowledge_background" in state and isinstance(state.get("knowledge_background"), dict):
            kb = state.get("knowledge_background", {}) or {}
            normalized_kb = KnowledgeStateService._empty_knowledge_background()
            for level in KNOWLEDGE_LEVELS:
                values = kb.get(level, [])
                if isinstance(values, list):
                    normalized_kb[level] = KnowledgeStateService._dedupe_keep_order(
                        values)
            mastered = state.get("mastered_points", [])
            if not isinstance(mastered, list):
                mastered = []
            result: Dict[str, Any] = {
                "knowledge_background": normalized_kb,
                "mastered_points": KnowledgeStateService._dedupe_keep_order(mastered),
            }
            # 透传已有知识图谱（如果已存在）
            if isinstance(existing_graph, dict):
                result["knowledge_graph"] = existing_graph
            return result

        # Backward compatibility: old shape {domains: {name:{level}}, details:{point:{level}}}
        domains = state.get("domains", {}) if isinstance(
            state.get("domains"), dict) else {}
        details = state.get("details", {}) if isinstance(
            state.get("details"), dict) else {}
        normalized_kb = KnowledgeStateService._empty_knowledge_background()
        for domain, meta in domains.items():
            level = KnowledgeStateService.normalize_level(
                (meta or {}).get("level", "low"))
            normalized_kb[level].append(str(domain or "").strip())
        for level in KNOWLEDGE_LEVELS:
            normalized_kb[level] = KnowledgeStateService._dedupe_keep_order(
                normalized_kb[level])

        mastered_points: List[str] = []
        for point, meta in details.items():
            if KnowledgeStateService.normalize_level((meta or {}).get("level", "low")) == "high":
                mastered_points.append(str(point or "").strip())

        result: Dict[str, Any] = {
            "knowledge_background": normalized_kb,
            "mastered_points": KnowledgeStateService._dedupe_keep_order(mastered_points),
        }
        if isinstance(existing_graph, dict):
            result["knowledge_graph"] = existing_graph
        return result

    @staticmethod
    def normalize_level(level: str, default: str = "low") -> str:
        value = str(level or "").strip().lower()
        if value in KNOWLEDGE_LEVEL_ORDER:
            return value
        return default

    @staticmethod
    def extract_domain(point: str) -> str:
        text = str(point or "").strip()
        if not text:
            return ""
        m = re.match(r"^([^（(]+)", text)
        return (m.group(1).strip() if m else text)

    @staticmethod
    def compute_level_ratio(persona: Dict) -> Dict[str, float]:
        """Compute high/medium/low ratio by high-level medical domains."""
        kb = persona.get("knowledge_background", {}) or {}
        domain_rank: Dict[str, int] = {}
        for level in KNOWLEDGE_LEVELS:
            values = kb.get(level, []) if isinstance(kb, dict) else []
            if not isinstance(values, list):
                continue
            rank = KNOWLEDGE_LEVEL_ORDER[level]
            for raw in values:
                domain = KnowledgeStateService.extract_domain(str(raw or ""))
                if not domain:
                    continue
                prev = domain_rank.get(domain, -1)
                if rank > prev:
                    domain_rank[domain] = rank

        counts = {"high": 0, "medium": 0, "low": 0}
        for rank in domain_rank.values():
            counts[KNOWLEDGE_LEVELS[rank]] += 1

        total = counts["high"] + counts["medium"] + counts["low"]
        if total <= 0:
            return {"high": 0.0, "medium": 0.0, "low": 1.0}
        return {
            "high": counts["high"] / total,
            "medium": counts["medium"] / total,
            "low": counts["low"] / total,
        }

    @staticmethod
    def derive_shared_domains(all_personas: Dict[str, Dict]) -> List[str]:
        """Build shared high-level domains used by all agents in current session."""
        ordered: List[str] = []
        seen = set()
        for persona in all_personas.values():
            kb = (persona or {}).get("knowledge_background", {}) or {}
            if not isinstance(kb, dict):
                continue
            for level in KNOWLEDGE_LEVELS:
                values = kb.get(level, [])
                if not isinstance(values, list):
                    continue
                for raw in values:
                    domain = KnowledgeStateService.extract_domain(
                        str(raw or ""))
                    if domain and domain not in seen:
                        seen.add(domain)
                        ordered.append(domain)
        return ordered

    @staticmethod
    def persona_domain_level(persona: Dict, domain: str) -> str:
        kb = persona.get("knowledge_background", {}) or {}
        best_rank = -1
        for level in KNOWLEDGE_LEVELS:
            values = kb.get(level, []) if isinstance(kb, dict) else []
            if not isinstance(values, list):
                continue
            for raw in values:
                if KnowledgeStateService.extract_domain(str(raw or "")) == domain:
                    best_rank = max(best_rank, KNOWLEDGE_LEVEL_ORDER[level])
        if best_rank < 0:
            return "low"
        return KNOWLEDGE_LEVELS[best_rank]

    @staticmethod
    def init_agent_state_from_persona(persona: Dict, shared_domains: List[str]) -> Dict[str, Dict]:
        """Initialize canonical state using persona knowledge_background + empty mastered_points
        并根据当前案例 + cognitive_orientation 构建该学生的知识图谱视图。
        """
        knowledge_background = KnowledgeStateService._empty_knowledge_background()
        for domain in shared_domains:
            level = KnowledgeStateService.persona_domain_level(persona, domain)
            knowledge_background[level].append(domain)
        for level in KNOWLEDGE_LEVELS:
            knowledge_background[level] = KnowledgeStateService._dedupe_keep_order(
                knowledge_background[level])

        # 尝试基于当前病例构建知识图谱（失败时安全降级为 None）
        knowledge_graph = None
        try:
            case_name = getattr(pbl_info, "current_case_name", "") or ""
            if case_name:
                case_path: Optional[Path] = resolve_case_json_path(case_name)
                if case_path and case_path.exists():
                    with open(case_path, "r", encoding="utf-8") as f:
                        case_data = json.load(f)
                    orientation = str(
                        persona.get("cognitive_orientation", "point_based")
                    ).lower()
                    knowledge_graph = build_agent_knowledge_graph(
                        case_data=case_data,
                        cognitive_orientation=orientation,
                    )

                    # 初始化可观测性：输出图谱规模 + 少量示例边
                    try:
                        nodes_obj = knowledge_graph.get("nodes", {}) if isinstance(knowledge_graph, dict) else {}
                        edges_obj = knowledge_graph.get("edges", []) if isinstance(knowledge_graph, dict) else []
                        node_count = len(nodes_obj) if isinstance(nodes_obj, dict) else 0
                        edge_count = len(edges_obj) if isinstance(edges_obj, list) else 0
                        edge_preview = []
                        if isinstance(edges_obj, list):
                            for e in edges_obj[:5]:
                                if isinstance(e, dict):
                                    edge_preview.append(
                                        {
                                            "source": e.get("source"),
                                            "target": e.get("target"),
                                            "relation": e.get("relation"),
                                            "scene_index": e.get("scene_index"),
                                            "question_index": e.get("question_index"),
                                        }
                                    )
                        logger.info(
                            "KNOWLEDGE_GRAPH_INIT name=%s orientation=%s case=%s graph_nodes=%s graph_edges=%s edge_preview=%s",
                            str(persona.get("name", "") or "").strip() or "unknown",
                            str(persona.get("cognitive_orientation", "point_based") or "").strip(),
                            str(case_name),
                            node_count,
                            edge_count,
                            edge_preview,
                        )
                    except Exception as e:
                        logger.warning("KNOWLEDGE_GRAPH_INIT log failed: %s", e)
        except Exception as e:
            # 仅记录日志，不影响主流程
            logging.getLogger(__name__).warning(
                "Init agent knowledge_graph failed: %s", e
            )

        state: Dict[str, Any] = {
            "knowledge_background": knowledge_background,
            "mastered_points": [],
        }
        if isinstance(knowledge_graph, dict):
            state["knowledge_graph"] = knowledge_graph
        return state

    @staticmethod
    def get_or_init_agent_state(
            state: Dict,
            agent_id: str,
            persona: Dict,
            all_personas: Dict[str, Dict],
    ) -> tuple[Dict[str, Dict], Dict[str, Dict]]:
        """Return (knowledge_state_all, agent_state)."""
        knowledge_state_all = dict(state.get("knowledge_state", {}) or {})
        shared_domains = knowledge_state_all.get("__shared_domains__")
        if not isinstance(shared_domains, list) or not shared_domains:
            shared_domains = KnowledgeStateService.derive_shared_domains(
                all_personas)
            knowledge_state_all["__shared_domains__"] = shared_domains

        agent_state = knowledge_state_all.get(agent_id)
        if not isinstance(agent_state, dict):
            agent_state = KnowledgeStateService.init_agent_state_from_persona(
                persona, shared_domains)
        else:
            agent_state = KnowledgeStateService._normalize_agent_state_schema(
                agent_state)

        # Ensure shared domains always exist in this agent's knowledge_background.
        kb = dict(agent_state.get("knowledge_background", {}) or {})
        for level in KNOWLEDGE_LEVELS:
            values = kb.get(level, [])
            kb[level] = values if isinstance(values, list) else []
        covered = set()
        for level in KNOWLEDGE_LEVELS:
            for domain in kb.get(level, []):
                covered.add(domain)
        for domain in shared_domains:
            if domain not in covered:
                kb[KnowledgeStateService.persona_domain_level(
                    persona, domain)].append(domain)
        for level in KNOWLEDGE_LEVELS:
            kb[level] = KnowledgeStateService._dedupe_keep_order(kb[level])

        agent_state = {
            "knowledge_background": kb,
            "mastered_points": KnowledgeStateService._dedupe_keep_order(agent_state.get("mastered_points", [])),
        }
        # 透传已存在的知识图谱
        existing_graph = state.get("knowledge_graph") if isinstance(
            state, dict) else None
        graph_in_agent = (agent_state or {}).get("knowledge_graph")
        if isinstance(graph_in_agent, dict):
            agent_state["knowledge_graph"] = graph_in_agent
        elif isinstance(existing_graph, dict):
            agent_state["knowledge_graph"] = existing_graph
        knowledge_state_all[agent_id] = agent_state
        return knowledge_state_all, agent_state

    @staticmethod
    def mastery_stats(agent_knowledge_state: Dict[str, Dict]) -> Dict[str, int]:
        counts = {"high": 0, "medium": 0, "low": 0}
        state = KnowledgeStateService._normalize_agent_state_schema(
            agent_knowledge_state)
        kb = state.get("knowledge_background", {}) or {}
        for level in KNOWLEDGE_LEVELS:
            values = kb.get(level, [])
            counts[level] = len(values) if isinstance(values, list) else 0
        return counts

    @staticmethod
    def mastery_brief(agent_knowledge_state: Dict[str, Dict], top_k: int = 8) -> str:
        if not isinstance(agent_knowledge_state, dict):
            return "暂无已掌握知识点。"
        state = KnowledgeStateService._normalize_agent_state_schema(
            agent_knowledge_state)
        kb = state.get("knowledge_background", {}) or {}
        d_high = sorted(kb.get("high", []) if isinstance(
            kb.get("high", []), list) else [])
        d_med = sorted(kb.get("medium", []) if isinstance(
            kb.get("medium", []), list) else [])
        d_low = sorted(kb.get("low", []) if isinstance(
            kb.get("low", []), list) else [])

        mastered_points = state.get("mastered_points", [])
        if not isinstance(mastered_points, list):
            mastered_points = []
        detail_preview = KnowledgeStateService._dedupe_keep_order(mastered_points)[
            :top_k]

        return (
            f"学科高: {', '.join(sorted(d_high)) or '无'} | "
            f"学科中: {', '.join(sorted(d_med)) or '无'} | "
            f"学科低: {', '.join(sorted(d_low)) or '无'} | "
            f"已掌握知识点: {', '.join(detail_preview) or '无'}"
        )

    @staticmethod
    def apply_level_update(prev_level: str, proposed_level: str) -> str:
        prev_rank = KNOWLEDGE_LEVEL_ORDER[KnowledgeStateService.normalize_level(
            prev_level)]
        target_rank = KNOWLEDGE_LEVEL_ORDER[KnowledgeStateService.normalize_level(
            proposed_level)]
        if target_rank > prev_rank + 1:
            target_rank = prev_rank + 1
        if target_rank < prev_rank - 1:
            target_rank = prev_rank - 1
        return KNOWLEDGE_LEVELS[target_rank]

    @staticmethod
    def sync_domain_levels_from_details(agent_state: Dict[str, Dict]) -> Dict[str, Dict]:
        # No-op for canonical schema; kept for compatibility with existing wrapper callsites.
        return KnowledgeStateService._normalize_agent_state_schema(agent_state)


class ActionDistributionService:
    """Encapsulates distribution normalization and action-prior construction."""

    @staticmethod
    def compute_router_trait_weight(agent_id: str, persona: Dict, self_efficacy_state: Dict) -> float:
        """基于人格特质计算路由偏好权重，优先选择外向、宜人、深度学习型成员。"""
        scores = _extract_numeric_trait_scores(persona)
        learning = scores["learning"]
        personality = scores["personality"]

        weight = 1.0  # 基础权重，确保每个人都有机会被选
        weight += 0.55 * max(0, learning["deep"] - 3)
        weight += 0.45 * max(0, personality["agreeableness"] - 3)
        weight += 0.55 * max(0, 3 - personality["neuroticism"])
        weight += 0.35 * max(0, 3 - learning["strategic"])

        # 自我效能感的微量调整
        se_level = self_efficacy_state.get(agent_id, 6)
        weight += 0.15 * max(0, (se_level - 3) / 3)
        return max(0.05, weight)

    @staticmethod
    def build_router_preference_summary(agent_ids: List[str], personas: Dict[str, Dict], self_efficacy_state: Dict) -> str:
        """生成描述性路由偏好摘要，供 LLM 参考。"""
        ranking = []
        for aid in agent_ids:
            persona = personas.get(aid, {})
            weight = ActionDistributionService.compute_router_trait_weight(
                aid, persona, self_efficacy_state)
            ranking.append((aid, weight))

        ranking.sort(key=lambda item: item[1], reverse=True)
        if not ranking:
            return "无可用学生偏好信息。"

        total = sum(weight for _, weight in ranking)
        if total <= 0:
            total = float(len(ranking))
            ranking = [(aid, 1.0) for aid, _ in ranking]

        natural_lines: List[str] = []
        for aid, weight in ranking:
            share = weight / total
            if share >= 0.40:
                band = "极高优先：积极主动，非常适合优先发言"
            elif share >= 0.28:
                band = "高优先：较为主动，适合作为候选"
            elif share >= 0.18:
                band = "中优先：正常发言节奏"
            else:
                band = "低优先：通常保持观察，除非必要不建议频繁点名"
            natural_lines.append(f"{aid} -> {band}")

        return "；".join(natural_lines)

    @staticmethod
    def deterministic_router_fallback(
        candidates: List[str],
        personas: Dict[str, Dict],
        self_efficacy_state: Dict,
        turn_counts: Dict[str, int],
        last_speaker: str,
    ) -> str:
        """启发式路由兜底逻辑：公平性第一（最少发言），人格权重第二，ID 稳定性第三。"""
        pool = [aid for aid in candidates if aid and aid !=
                last_speaker] or list(candidates)
        if not pool:
            return ""

        min_turn = min(turn_counts.get(aid, 0) for aid in pool)
        least_spoken = [
            aid for aid in pool if turn_counts.get(aid, 0) == min_turn]

        ranked = sorted(
            least_spoken,
            key=lambda aid: (-ActionDistributionService.compute_router_trait_weight(
                aid, personas.get(aid, {}), self_efficacy_state), aid),
        )
        return ranked[0]

    @staticmethod
    def normalize_distribution(
            raw_probs: Dict,
            allowed_keys: List[str],
            fallback: Dict[str, float],
    ) -> Dict[str, float]:
        cleaned: Dict[str, float] = {}
        for key in allowed_keys:
            value = raw_probs.get(key) if isinstance(raw_probs, dict) else None
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                numeric = 0.0
            cleaned[key] = max(0.0, numeric)

        total = sum(cleaned.values())
        if total <= 0:
            fallback_total = sum(max(0.0, float(v)) for v in fallback.values())
            if fallback_total <= 0:
                uniform = 1.0 / max(1, len(allowed_keys))
                return {k: uniform for k in allowed_keys}
            normalized = {
                k: max(0.0, float(fallback.get(k, 0.0))) / fallback_total
                for k in allowed_keys
            }
            total_norm = sum(normalized.values())
            if normalized and total_norm != 1.0:
                adjust_key = max(normalized, key=normalized.get)
                normalized[adjust_key] = max(
                    0.0,
                    min(1.0, normalized[adjust_key] + (1.0 - total_norm)),
                )
                total_norm = sum(normalized.values())
                if total_norm > 0:
                    normalized = {k: v / total_norm for k,
                                  v in normalized.items()}
            return normalized

        normalized = {k: cleaned[k] / total for k in allowed_keys}
        total_norm = sum(normalized.values())
        if normalized and total_norm != 1.0:
            adjust_key = max(normalized, key=normalized.get)
            normalized[adjust_key] = max(
                0.0,
                min(1.0, normalized[adjust_key] + (1.0 - total_norm)),
            )
            total_norm = sum(normalized.values())
            if total_norm > 0:
                normalized = {k: v / total_norm for k, v in normalized.items()}
        return normalized

    @staticmethod
    def sample(distribution: Dict[str, float], options: List[str]) -> str:
        weights = [max(0.0, float(distribution.get(opt, 0.0)))
                   for opt in options]
        total = sum(weights)
        if total <= 0:
            return random.choice(options)
        return random.choices(options, weights=weights, k=1)[0]

    @staticmethod
    def estimate_spa_band(persona: Dict) -> str:
        level_ratio = KnowledgeStateService.compute_level_ratio(persona)
        if level_ratio["high"] >= 0.55:
            return "high"
        if level_ratio["low"] >= 0.55:
            return "low"
        return "medium"

    @staticmethod
    def build_dynamic_non_silence_prior_weights(persona: Dict) -> Dict[str, float]:
        weights = dict(BASE_NON_SILENCE_PRIOR_WEIGHTS)
        scores = _extract_numeric_trait_scores(persona)
        personality = scores["personality"]

        agreeableness = int(personality.get("agreeableness", 3))
        conscientiousness = int(personality.get("conscientiousness", 3))
        extraversion = int(personality.get("extraversion", 3))
        openness = int(personality.get("openness", 3))
        spa_band = ActionDistributionService.estimate_spa_band(persona)

        if agreeableness > 3:
            weights["accumulation"] = max(weights["accumulation"], 0.78)
        if conscientiousness > 3:
            weights["accumulation"] *= 0.8

        if extraversion > 3 and openness > 3:
            weights["seeking_help_alignment"] = max(
                weights["seeking_help_alignment"], 0.20)
        elif extraversion > 3 or openness > 3:
            weights["seeking_help_alignment"] = max(
                weights["seeking_help_alignment"], 0.16)

        if spa_band == "high":
            weights["seeking_help_alignment"] = max(
                weights["seeking_help_alignment"], 0.18)

        if conscientiousness > 3:
            weights["correction_challenge"] = max(
                weights["correction_challenge"], 0.13)

        if spa_band == "high":
            weights["correction_challenge"] = max(
                weights["correction_challenge"], 0.10)

        if spa_band == "low":
            weights["correction_challenge"] = min(
                weights["correction_challenge"], 0.029)

        if agreeableness > 3:
            weights["correction_challenge"] = min(
                weights["correction_challenge"], 0.012)

        return {k: max(0.001, float(v)) for k, v in weights.items()}

    @staticmethod
    def build_action_prior_distribution(
            silence_prior: float,
            non_silence_weights: Dict[str, float],
            action_options: List[str],
    ) -> Dict[str, float]:
        silence_prior = max(0.0, min(1.0, float(silence_prior)))
        non_silence_mass = max(0.0, 1.0 - silence_prior)

        non_silence_total = sum(max(0.0, v)
                                for v in non_silence_weights.values())
        if non_silence_total <= 0:
            non_silence_total = 1.0

        prior = {
            "seeking_help_alignment": non_silence_mass * max(0.0, non_silence_weights["seeking_help_alignment"]) / non_silence_total,
            "correction_challenge": non_silence_mass * max(0.0, non_silence_weights["correction_challenge"]) / non_silence_total,
            "accumulation": non_silence_mass * max(0.0, non_silence_weights["accumulation"]) / non_silence_total,
            "silence": silence_prior,
        }
        return ActionDistributionService.normalize_distribution(prior, action_options, fallback=prior)


logger = logging.getLogger(__name__)


def is_silence_like_content(content: str) -> bool:
    """Return True when content is a silence marker such as '...' or '...（沉默）'."""
    text = str(content or "").strip()
    if not text:
        return False

    # Normalize full-width punctuation and ellipsis variants.
    text = text.replace("\u2026", "...").replace("。", ".")

    # Accepted examples:
    #   ...
    #   ...(沉默)
    #   ...（沉默）
    #   ...(silence)
    silence_pattern = r"^\.{3}\s*(?:[\(（]\s*(?:沉默|silence)\s*[\)）])?$"
    return re.match(silence_pattern, text, flags=re.IGNORECASE) is not None


def extract_json_object(text: str) -> Dict[str, Any]:
    """Best-effort JSON object extraction for LLM outputs."""
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


def find_recent_dominant_speaker(messages: List[BaseMessage], window: int = 6):
    recent = messages[-window:] if messages else []
    speaker_count: Dict[str, int] = {}
    for message in recent:
        speaker = getattr(message, "name", None)
        if speaker:
            speaker_count[speaker] = speaker_count.get(speaker, 0) + 1
    if not speaker_count:
        return None, 0
    dominant = max(speaker_count.items(), key=lambda x: x[1])
    return dominant[0], dominant[1]


def get_last_agent_utterance(messages: List[BaseMessage], agent_id: str) -> str:
    for message in reversed(messages):
        if getattr(message, "name", None) == agent_id:
            return str(getattr(message, "content", "") or "").strip()
    return ""


def build_recent_silence_context(messages: List[BaseMessage], window: int = 6) -> str:
    recent = messages[-window:] if messages else []
    silence_names: List[str] = []
    for message in recent:
        content = str(getattr(message, "content", "") or "").strip()
        name = str(getattr(message, "name", "") or "").strip()
        if content == "..." and name:
            silence_names.append(name)

    if not silence_names:
        return "No recent peer silence."

    return f"Recent peers who chose silence: {', '.join(silence_names)}"


def extract_teacher_nominated_agent(messages: List[BaseMessage], agent_ids: List[str]) -> str:
    if not messages or not agent_ids:
        return ""

    teacher_content = ""
    for message in reversed(messages):
        speaker = str(getattr(message, "name", "") or "").strip().lower()
        if speaker == "teacher":
            teacher_content = str(getattr(message, "content", "") or "")
            break

    if not teacher_content:
        return ""

    lowered = teacher_content.lower()
    for aid in agent_ids:
        aid_lower = aid.lower()
        if re.search(rf"\b{re.escape(aid_lower)}\b", lowered):
            return aid
    return ""


def has_high_knowledge_profile(persona: Dict) -> bool:
    kb = persona.get("knowledge_background", {}) or {}
    high_terms = kb.get("high", []) if isinstance(kb, dict) else []
    return isinstance(high_terms, list) and len(high_terms) > 0
