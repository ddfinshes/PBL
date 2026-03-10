"""Preview generation for ViewB agent panel.

This module centralizes all backend logic related to agent preview generation,
including before/after response simulation and behavior description synthesis.
"""

from __future__ import annotations

from typing import Dict, List

from langchain_core.messages import AIMessage, BaseMessage

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
    describe_cognitive_load_level,
    init_cognitive_load,
    self_efficacy_init,
)


_LIMITATION_CUES = (
    "局限", "不足", "偏差", "忽略", "过早", "犹豫", "不够", "欠缺", "单一", "保守"
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
        hints.append("分析深度不足")
    if strategic <= 2:
        hints.append("只积累信息不易收束")
    if openness <= 2:
        hints.append("容易忽略替代解释和反例")
    if conscientiousness <= 2:
        hints.append("证据核查不充分，可能过早下结论")
    if extraversion <= 2:
        hints.append("不太主动寻求同伴帮助")
    if agreeableness >= 4:
        hints.append("为避免冲突而挑战力度偏弱")
    if neuroticism >= 4:
        hints.append("不确定时更易犹豫")

    if not hints:
        hints.append("关键节点可能收敛偏快")

    return hints[0]


def _preview_baseline_text(trigger_question: str, action: str) -> str:
    """Construct baseline bubble text without hard-coded trait conclusions."""
    action_hint = {
        "seeking_help_alignment": "我会先和同伴对齐问题范围，再补充关键线索。",
        "correction_challenge": "我会先指出可能的逻辑缺口，再给出更稳妥的鉴别方向。",
        "accumulation": "我会先承接现有信息，再补充必要的鉴别与检查建议。",
    }.get(action, "我会先承接现有信息，再补充必要的鉴别与检查建议。")
    return f"针对“{trigger_question}”，{action_hint}"


async def _generate_behavior_description(persona: Dict, action_plan: Dict, after_text: str) -> str:
    """Generate a concise and balanced behavior description for preview panel footer."""
    persona_str = _format_persona_to_string_safe(persona)
    action = str(action_plan.get("action", "accumulation") or "accumulation")
    action_desc = str(action_plan.get("action_description", "") or "").strip()
    reply_focus = str(action_plan.get("reply_focus", "") or "").strip()
    limitation_hint = _local_limitation_hint(persona)

    prompt = (
        "你是医学PBL课堂中的行为画像生成器。\n"
        "请根据学生配置和本轮动作规划，生成1句平衡的行为描述（26-52字）。\n"
        "要求：\n"
        "1) 必须同时包含一个相对优势和一个明确局限（缺点/偏差）；\n"
        "2) 局限需可观察，如过早下结论、忽略反例、求助不足、分析不深、只积累不收束等；\n"
        "3) 不要复述问题，不要输出步骤编号；\n"
        "4) 禁止只写正面评价。\n"
        "5) 只输出这一句话。\n\n"
        "3) 语气客观、可读；\n"
        f"[局限提示]\n{limitation_hint}\n\n"
        f"[人设]\n{persona_str}\n\n"
        f"[动作]\naction={action}; action_description={action_desc}; reply_focus={reply_focus}\n\n"
        f"[当前回答]\n{after_text}"
    )

    fallback = f"该同学能够承接讨论推进分析，但{limitation_hint}。"

    try:
        result = await _ainvoke_with_log(SUM_LLM, prompt, "preview_behavior_description")
        text = str(getattr(result, "content", "") or "").strip()
        if not text:
            return fallback
        if _contains_limitation_cue(text):
            return text
        return f"{text}，但{limitation_hint}。"
    except Exception:
        return fallback


async def generate_student_preview_response(agent_id: str, persona: Dict, trigger_question: str) -> Dict[str, str]:
    """Generate ViewB preview with the same two-step runtime flow.

    Step 1: call action planner LLM (_plan_agent_action) to choose strategy.
    Step 2: call STUDENT_PROMPT LLM to generate final answer from that strategy.
    Step 3: call summary LLM to generate concise behavior description.

    Returns before/after bubble content and behavior metadata.
    """
    safe_question = str(trigger_question or "").strip() or "请先上传案例后再生成预览。"
    safe_persona = dict(persona or {})

    preview_messages: List[BaseMessage] = [
        AIMessage(
            content=f"当前讨论刚开始，请围绕第一幕第一个 trigger question 展开：{safe_question}",
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
    load_label = describe_cognitive_load_level(load_level)

    active_contribution_behavior_rule = (
        "你需遵循动作规划并保持既有互动风格，动作包括："
        "(1) 探索性提问：学生批判性地、建设性地参与彼此的想法，或是提出问题以寻求对齐；"
        "(2) 纠错/挑战：当他人逻辑与你内在推理冲突时进行辩论；仅仅是观点碰撞，没有深度加工或共同构建"
        "(3) 累积/补充：学生在不挑战他人的情况下，互相重复或确认彼此的论点即：简单支持、证据叠加）。"
    )

    degradation_instruction = "认知负荷中等。"
    interaction_bias = "优先简洁、可证据化表达。"
    if load_level >= 9:
        degradation_instruction = "认知负荷高，避免复杂并行推理，先给单步结论。"
        interaction_bias = "减少挑战，优先澄清或求助对齐。"
    elif load_level <= 3:
        degradation_instruction = "认知负荷低，可进行机制级解释。"
        interaction_bias = "可进行适度挑战与证据整合。"

    persona_str = _format_persona_to_string_safe(safe_persona)
    persona_str += f"""

						- **当前认知负荷水平（3-6-9）**：{load_level}（{load_label}）。
						- **认知负荷对推理的影响**：{degradation_instruction}
						- **认知负荷对互动行为的影响**：{interaction_bias}
						- **教师回应约束**：老师刚刚介入：优先进行明确口头回应，除非绝对必要否则不要沉默。
						- **主动贡献互动规则**：{active_contribution_behavior_rule}
                        - **回答约束**：本轮回答需自然暴露至少一个局限或偏差，不要追求完美正确。
						- **当前为 ViewB 参数预览模式，语气更清亮、简洁、自然，长度控制在 80 字以内。**
			"""

    kb = safe_persona.get("knowledge_background", {}) if isinstance(
        safe_persona, dict) else {}
    high = ",".join(kb.get("high", []) if isinstance(kb, dict) else []) or "无"
    medium = ",".join(kb.get("medium", [])
                      if isinstance(kb, dict) else []) or "无"
    low = ",".join(kb.get("low", []) if isinstance(kb, dict) else []) or "无"
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
            "latest_processed_info": f"第一幕首题：{safe_question}",
            "knowledge_state_brief": knowledge_state_brief,
        }
    )

    result = await _ainvoke_with_log(STUDENT_LLM, prompt, f"student_preview:{agent_id}")
    after_text = str(getattr(result, "content", "") or "").strip()
    if _is_silence_like_content(after_text):
        after_text = "我先聚焦关键证据和鉴别方向，再给出可执行的下一步判断。"

    action_type = str(plan.get("action", "accumulation")
                      or "accumulation").strip()
    action_label = ACTION_DISPLAY_LABELS.get(action_type, action_type)
    if after_text:
        after_text = f"【动作类型:{action_label}】{after_text}"

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
