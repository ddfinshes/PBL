"""Shared agent configuration and utility services.

This module hosts reusable configuration-oriented logic so `agents.py`
can focus on workflow orchestration.
"""
from __future__ import annotations

from typing import Dict, List
import re
import random

from .agent_settings import _extract_numeric_trait_scores


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
            return {
                "knowledge_background": normalized_kb,
                "mastered_points": KnowledgeStateService._dedupe_keep_order(mastered),
            }

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

        return {
            "knowledge_background": normalized_kb,
            "mastered_points": KnowledgeStateService._dedupe_keep_order(mastered_points),
        }

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
        """Initialize canonical state using persona knowledge_background + empty mastered_points."""
        knowledge_background = KnowledgeStateService._empty_knowledge_background()
        for domain in shared_domains:
            level = KnowledgeStateService.persona_domain_level(persona, domain)
            knowledge_background[level].append(domain)
        for level in KNOWLEDGE_LEVELS:
            knowledge_background[level] = KnowledgeStateService._dedupe_keep_order(
                knowledge_background[level])
        return {
            "knowledge_background": knowledge_background,
            "mastered_points": [],
        }

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
