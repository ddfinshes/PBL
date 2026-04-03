"""Preview generation for ViewB agent panel.

This module centralizes all backend logic related to agent preview generation,
including before/after response simulation and behavior description synthesis.
"""

from __future__ import annotations

from typing import Dict, List

from langchain_core.messages import AIMessage, BaseMessage

import json
from .agents import (
    ACTION_DISPLAY_LABELS,
    STUDENT_LLM,
    STUDENT_PROMPT,
    SUM_LLM,
    _ainvoke_with_log,
    _build_recent_silence_context,
    _format_persona_to_string_safe,
    _is_silence_like_content,
    _plan_agent_action,
    init_cognitive_load,
    self_efficacy_init,
)


_LIMITATION_CUES = (
    "limitation", "insufficiency", "bias", "overlooked", "premature", "hesitant", "inadequate", "lacking", "narrow", "conservative"
)


def _contains_limitation_cue(text: str) -> bool:
    content = str(text or "").strip()
    return any(cue in content for cue in _LIMITATION_CUES)


def _local_limitation_hint(persona: Dict) -> str:
    """Build a lightweight limitation hint from current persona fields."""
    learning = persona.get("learning_styles", {}) if isinstance(
        persona, dict) else {}
    traits = persona.get("personality", {}) if isinstance(
        persona, dict) else {}

    deep = int(learning.get("deep", 3) or 3)
    strategic = int(learning.get("strategic", 3) or 3)
    openness = int(traits.get("openness", 3) or 3)
    conscientiousness = int(traits.get("conscientiousness", 3) or 3)
    extraversion = int(traits.get("extraversion", 3) or 3)
    agreeableness = int(traits.get("agreeableness", 3) or 3)
    neuroticism = int(traits.get("neuroticism", 3) or 3)

    hints: List[str] = []
    if deep <= 2:
        hints.append("Insufficient analysis depth")
    if strategic <= 2:
        hints.append("Tends to accumulate without synthesis")
    if openness <= 2:
        hints.append(
            "May overlook alternative explanations and counterexamples")
    if conscientiousness <= 2:
        hints.append(
            "Evidence verification insufficient, may draw premature conclusions")
    if extraversion <= 2:
        hints.append("Less proactive in seeking peer collaboration")
    if agreeableness >= 4:
        hints.append("Avoids conflict, which weakens challenge and debate")
    if neuroticism >= 4:
        hints.append("More prone to hesitation when uncertain")

    if not hints:
        hints.append("Tendency for rapid convergence at key decision points")

    return hints[0]


def _preview_baseline_text(trigger_question: str, action: str) -> str:
    """Construct baseline bubble text without hard-coded trait conclusions."""
    action_hint = {
        "seeking_help_alignment": "I'll align on problem scope with peers first, then supplement key evidence.",
        "correction_challenge": "I'll first point out potential logical gaps, then offer a more robust diagnostic direction.",
        "accumulation": "I'll build on existing information, then add necessary diagnostic and assessment recommendations.",
    }.get(action, "I'll build on existing information, then add necessary diagnostic and assessment recommendations.")
    return f"Regarding {trigger_question}, {action_hint}"


async def _generate_behavior_description(persona: Dict, action_plan: Dict, after_text: str) -> str:
    """Generate a structured behavior explanation with dimension-by-dimension impact."""
    persona_str = _format_persona_to_string_safe(persona)
    action = str(action_plan.get("action", "accumulation") or "accumulation")
    action_desc = str(action_plan.get("action_description", "") or "").strip()
    reply_focus = str(action_plan.get("reply_focus", "") or "").strip()
    limitation_hint = _local_limitation_hint(persona)

    prompt = (
        "You are a behavior analyzer for medical PBL classroom discussions.\n"
        "Task: Do not write a single-sentence summary. Instead, write 'dimension-by-dimension impact analysis' explaining how each dimension affects this student agent.\n"
        "Output Requirements:\n"
        "1) Output exactly 4 lines, one dimension per line, with strict format:\n"
        "Learning Style Impact: ...\n"
        "Personality Impact: ...\n"
        "Cognitive Orientation Impact: ...\n"
        "Current Interaction Behavior: ...\n"
        "2) Each line must contain three components: 'mechanism -> observable behavior -> risk/limitation';\n"
        "3) Must show both relative strengths and clear limitations; avoid purely positive evaluation;\n"
        "4) Be specific and concrete, do not rephrase the question, avoid numbered steps, no Markdown.\n\n"
        f"[Limitation Hint]\n{limitation_hint}\n\n"
        f"[Student Profile]\n{persona_str}\n\n"
        f"[Action]\naction={action}; action_description={action_desc}; reply_focus={reply_focus}\n\n"
        f"[Current Response]\n{after_text}"
    )

    fallback = (
        "Learning Style Impact: The student organizes information per their learning preferences and advances discussion, but may still show insufficient depth in complex mechanism integration.\n"
        "Personality Impact: Personality traits determine speaking initiative and interaction style; strengths include maintaining discussion continuity, while limitations emerge under pressure through avoidance of high-conflict viewpoints.\n"
        "Cognitive Orientation Impact: The student's reasoning tends toward fixed structures for stability but may overlook alternative hypotheses and counterexamples, leading to rapid conclusion convergence.\n"
        f"Current Interaction Behavior: This response addresses the question and provides direction, but {limitation_hint} — subsequent follow-up and evidence comparison are needed for correction."
    )

    try:
        result = await _ainvoke_with_log(SUM_LLM, prompt, "preview_behavior_description")
        text = str(getattr(result, "content", "") or "").strip()
        if not text:
            return fallback

        required_prefixes = (
            "Learning Style Impact:",
            "Personality Impact:",
            "Cognitive Orientation Impact:",
            "Current Interaction Behavior:",
        )
        if all(prefix in text for prefix in required_prefixes):
            if _contains_limitation_cue(text):
                return text
            return f"{text}\nCurrent Interaction Behavior: While demonstrating some capability to advance discussion, {limitation_hint}."
        return fallback
    except Exception:
        return fallback


async def generate_agent_tags(persona: Dict, trigger_question: str) -> List[str]:
    """Generate 3-5 short tags characterizing the agent's behavior style for the given question."""
    persona_str = _format_persona_to_string_safe(persona)
    prompt = (
        "You are a PBL teaching observer tasked with assessing student learning performance and contribution characteristics during discussion.\n"
        "Task: Based on the student's profile and the current discussion question, generate 3-5 short tags that reflect the student's behavior patterns in PBL classroom, learning participation characteristics, collaborative style, and potential learning support points.\n\n"
        "Dimensional Guidance (Consider these perspectives, not just psychological traits):\n"
        "【Problem Analysis】How does the student understand the problem? Deep exploration vs quick summary? Systematic analysis vs intuitive judgment?\n"
        "【Knowledge Construction】Tendency to pursue root causes & mechanism understanding, or quick application & surface understanding? Knowledge transfer ability?\n"
        "【Group Interaction】Listening to others vs dominating discussion? Can tolerate different perspectives? Advance group thinking or persist in own views?\n"
        "【Argument Quality】Strong evidence vs hasty conclusions? Logical rigor vs jumping conclusions? Can identify counterexamples or weak points?\n"
        "【Learning Participation】Active questioning vs passive responding? Reflective criticism vs blind acceptance? Effective self-correction?\n\n"
        "Requirements:\n"
        "1) Tags must be 1-3 word phrases, specific rather than generic (e.g., 'Mechanism Questioner' better than 'Serious', 'Rapid Synthesizer' better than 'Intelligent').\n"
        "2) Balance strength and challenge: identify both limitations (e.g., 'Single-Source Evidence', 'Premature Closure') and positive qualities (e.g., 'Deep Questioning', 'Interdisciplinary Links').\n"
        "3) Tags should relate to current problem's learning context, reflecting student's immediate learning state.\n"
        "4) Prioritize observable behaviors in PBL discussion over abstract psychological categories.\n"
        "5) Output in English.\n"
        "6) Return format must be JSON string array, e.g. [\"Tag1\", \"Tag2\", \"Tag3\"].\n\n"
        f"[Student Profile]\n{persona_str}\n\n"
        f"[Current Discussion Question]\n{trigger_question}\n\n"
        "JSON Output:"
    )

    try:
        result = await _ainvoke_with_log(SUM_LLM, prompt, "generate_agent_tags")
        content = str(getattr(result, "content", "") or "").strip()
        # Clean up possible markdown code blocks
        if "```json" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[-1].split("```")[0].strip()

        tags = json.loads(content)
        if isinstance(tags, list):
            return [str(t)[:20] for t in tags[:5]]
        return ["Observant", "Knowledgeable"]
    except Exception as e:
        print(f"Error generating tags: {e}")
        return ["Inquisitive", "Reflective"]


async def generate_student_preview_response(agent_id: str, persona: Dict, trigger_question: str) -> Dict[str, str]:
    """Generate ViewB preview with the same two-step runtime flow.

    Step 1: call action planner LLM (_plan_agent_action) to choose strategy.
    Step 2: call STUDENT_PROMPT LLM to generate final answer from that strategy.
    Step 3: call summary LLM to generate concise behavior description.

    Returns before/after bubble content and behavior metadata.
    """
    safe_question = str(trigger_question or "").strip(
    ) or "Please upload a case first before generating preview."
    safe_persona = dict(persona or {})

    preview_messages: List[BaseMessage] = [
        AIMessage(
            content=f"Current discussion begins. Focus on the first trigger question: {safe_question}",
            name="case_introduction",
        )
    ]
    preview_state: Dict = {
        "messages": preview_messages,
        "current_topic": "Undefined",
        "private_memory": {},
        "cognitive_load": {agent_id: init_cognitive_load(safe_persona)},
        "self_efficacy": {agent_id: self_efficacy_init(safe_persona)},
        "knowledge_state": {},
        "force_no_silence_once": True,
    }

    plan = await _plan_agent_action(
        agent_id=agent_id,
        persona=safe_persona,
        state=preview_state,
        messages=preview_messages,
        preview_mode=True,
    )

    load_level = int(plan.get("load_level", init_cognitive_load(
        safe_persona)) or init_cognitive_load(safe_persona))
    load_label = "Low" if load_level <= 3 else (
        "High" if load_level >= 8 else "Medium")

    active_contribution_behavior_rule = (
        "Follow action planning and maintain existing interaction style. Actions include:\n"
        "(1) Exploratory Questions: Student participates critically and constructively in shared thinking, or asks questions to seek alignment;\n"
        "(2) Correction/Challenge: Debate when others' logic conflicts with your reasoning; simply collision of views without deep elaboration or co-construction\n"
        "(3) Accumulation/Supplement: Students repeat or confirm each other's arguments without challenging; simple support and evidence stacking."
    )

    degradation_instruction = "Medium cognitive load."
    interaction_bias = "Prioritize concise, evidence-supported expression."
    if load_level >= 9:
        degradation_instruction = "High cognitive load: avoid complex parallel reasoning, provide single-step conclusions first."
        interaction_bias = "Reduce challenges, prioritize clarification or seek alignment."
    elif load_level <= 3:
        degradation_instruction = "Low cognitive load: can provide mechanism-level explanations."
        interaction_bias = "Can engage in moderate challenges and evidence integration."

    persona_str = _format_persona_to_string_safe(safe_persona)
    persona_str += f"""
						- **Current Cognitive Load Level (3-6-9)**: {load_level} ({load_label}).
						- **Cognitive Load Impact on Reasoning**: {degradation_instruction}
						- **Cognitive Load Impact on Interaction Behavior**: {interaction_bias}
						- **Teacher Response Constraints**: Teacher just intervened: prioritize explicit verbal response, avoid silence unless absolutely necessary.
						- **Active Contribution Interaction Rules**: {active_contribution_behavior_rule}
                        - **Answer Constraints**: This response should naturally reveal at least one limitation or bias, do not pursuit perfect correctness.
						- **Currently in ViewB parameter preview mode: tone should be clear, concise, natural; length limit 80 characters.**
	"""

    kb = safe_persona.get("knowledge_background", {}) if isinstance(
        safe_persona, dict) else {}
    high = ",".join(kb.get("high", []) if isinstance(
        kb, dict) else []) or "None"
    medium = ",".join(kb.get("medium", [])
                      if isinstance(kb, dict) else []) or "None"
    low = ",".join(kb.get("low", []) if isinstance(kb, dict) else []) or "None"
    knowledge_state_brief = f"high:{high}; medium:{medium}; low:{low}"

    plan_text = (
        f"action={plan['action']}; "
        f"action_description={plan.get('action_description', '')}; "
        f"reply_focus={plan.get('reply_focus', '')}; "
        f"reason={plan.get('reason', '')}"
    )

    silence_social_context = _build_recent_silence_context(
        preview_messages, window=6)

    prompt = STUDENT_PROMPT.invoke(
        {
            "persona": persona_str,
            "messages": preview_messages,
            "silence_social_context": silence_social_context,
            "action_plan": plan_text,
            "latest_processed_info": f"Scene 1 First Question: {safe_question}",
            "knowledge_state_brief": knowledge_state_brief,
        }
    )

    result = await _ainvoke_with_log(STUDENT_LLM, prompt, f"student_preview:{agent_id}")
    after_text = str(getattr(result, "content", "") or "").strip()
    if _is_silence_like_content(after_text):
        after_text = "I'll focus on key evidence and diagnostic direction first, then provide actionable next-step judgment."

    action_type = str(plan.get("action", "accumulation")
                      or "accumulation").strip()
    action_label = ACTION_DISPLAY_LABELS.get(action_type, action_type)
    if after_text:
        after_text = f"[Action Type: {action_label}] {after_text}"

    behavior_description = await _generate_behavior_description(
        persona=safe_persona,
        action_plan=plan,
        after_text=after_text,
    )

    rendered_messages = prompt.to_messages()
    prompt_preview = "\n\n".join(
        f"[{getattr(msg, 'type', 'message')}] {str(getattr(msg, 'content', '') or '').strip()}"
        for msg in rendered_messages
    )

    return {
        "before_text": _preview_baseline_text(safe_question, plan["action"]),
        "after_text": after_text,
        "action": plan["action"],
        "action_display": plan.get("action_description", ACTION_DISPLAY_LABELS.get(plan["action"], plan["action"])),
        "behavior_description": behavior_description,
        "prompt_preview": prompt_preview,
    }
