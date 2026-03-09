"""PBL backend agent settings and persona utilities.

This module isolates persona/profile configuration and prompt-generation helpers
to keep agents.py focused on runtime orchestration.
"""

from __future__ import annotations

from typing import Any, Dict, List
import json

from langchain_core.prompts import ChatPromptTemplate


PERSONA_PATTERN_LIBRARY = {
    "learning_mechanisms": {
        "deep_high": "深度学习倾向是PBL中‘个人学习效能感’（概念澄清与新知记忆）的最强预测因子。",
        "surface_high": "高表层学习倾向通常意味着对非结构化PBL效率评价较低，更偏好标准答案与任务完成。",
        "strategic_high": "高策略型倾向会驱动以绩效为导向的参与方式，依据目标/评价标准进行选择性投入。",
    },
    "personality_mechanisms": {
        "neuroticism_high": "高神经质会因社交压力与犯错担忧显著抑制案例讨论中的发言意愿。",
        "neuroticism_low": "低神经质有助于在不确定讨论中保持社交舒适感、互动愉悦度和持续参与。",
        "co_openness_high": "高尽责性与高开放性会增强对PBL有效性的认可，并支持更深入、持续的投入。",
    },
    "archetypes": {
        "anxious_high_achiever": "高Deep + 高Neuroticism：‘焦虑的高成就者’，认知上认可PBL价值，但因社交焦虑而发言犹豫。",
        "social_but_shallow": "高Surface + 低Neuroticism：‘社交活跃但浅层贡献者’，愿意说话但贡献深度不足。",
        "ideal_beneficiary": "高Deep + 低Neuroticism：PBL理想受益者，兼具学习获益与讨论贡献意愿。",
        "hybrid": "混合型画像：学习效能与讨论贡献意愿存在拉扯，需要体现情境依赖与内在冲突。",
    },
}


def _extract_numeric_trait_scores(persona: Dict) -> Dict[str, Dict[str, int]]:
    learning_raw = persona.get("learning_styles", {})
    personality_raw = persona.get("personality", {})

    def _score(raw: Dict, key: str, default: int = 2) -> int:
        value = raw.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    learning = {
        "surface": _score(learning_raw, "surface"),
        "deep": _score(learning_raw, "deep"),
        "strategic": _score(learning_raw, "strategic"),
    }
    personality = {
        "openness": _score(personality_raw, "openness"),
        "conscientiousness": _score(personality_raw, "conscientiousness"),
        "extraversion": _score(personality_raw, "extraversion"),
        "agreeableness": _score(personality_raw, "agreeableness"),
        "neuroticism": _score(personality_raw, "neuroticism"),
    }
    return {"learning": learning, "personality": personality}


def _build_active_pattern_context(scores: Dict[str, Dict[str, int]]) -> Dict[str, List[str]]:
    ls = scores["learning"]
    p = scores["personality"]

    learning_patterns: List[str] = []
    personality_patterns: List[str] = []
    archetypes: List[str] = []

    if ls["deep"] >= 3:
        learning_patterns.append(
            PERSONA_PATTERN_LIBRARY["learning_mechanisms"]["deep_high"]
        )
    if ls["surface"] >= 3:
        learning_patterns.append(
            PERSONA_PATTERN_LIBRARY["learning_mechanisms"]["surface_high"]
        )
    if ls["strategic"] >= 3:
        learning_patterns.append(
            PERSONA_PATTERN_LIBRARY["learning_mechanisms"]["strategic_high"]
        )

    if p["neuroticism"] >= 3:
        personality_patterns.append(
            PERSONA_PATTERN_LIBRARY["personality_mechanisms"]["neuroticism_high"]
        )
    if p["neuroticism"] <= 1:
        personality_patterns.append(
            PERSONA_PATTERN_LIBRARY["personality_mechanisms"]["neuroticism_low"]
        )
    if p["conscientiousness"] >= 3 or p["openness"] >= 3:
        personality_patterns.append(
            PERSONA_PATTERN_LIBRARY["personality_mechanisms"]["co_openness_high"]
        )

    if ls["deep"] >= 3 and p["neuroticism"] >= 3:
        archetypes.append(
            PERSONA_PATTERN_LIBRARY["archetypes"]["anxious_high_achiever"])
    if ls["surface"] >= 3 and p["neuroticism"] <= 1:
        archetypes.append(
            PERSONA_PATTERN_LIBRARY["archetypes"]["social_but_shallow"])
    if ls["deep"] >= 3 and p["neuroticism"] <= 1:
        archetypes.append(
            PERSONA_PATTERN_LIBRARY["archetypes"]["ideal_beneficiary"])
    if not archetypes:
        archetypes.append(PERSONA_PATTERN_LIBRARY["archetypes"]["hybrid"])

    if not learning_patterns:
        learning_patterns = [
            "当前没有单一极端学习机制主导；应按Deep/Surface/Strategic的加权组合进行描述。"]
    if not personality_patterns:
        personality_patterns = ["当前没有单一极端人格机制主导；应描述中等强度的社交-情绪画像。"]

    return {
        "learning_patterns": learning_patterns,
        "personality_patterns": personality_patterns,
        "archetypes": archetypes,
    }


async def generate_learning_personality_sections(persona: Dict, llm: Any) -> Dict[str, str]:
    """Generate separated learning-style and personality prompt sections from numeric traits."""
    scores = _extract_numeric_trait_scores(persona)
    ls = scores["learning"]
    p = scores["personality"]
    active_patterns = _build_active_pattern_context(scores)

    system_prompt = (
        "你是医学PBL学生智能体的人格画像合成引擎。"
        "你必须结合以下理论框架生成："
        "（1）PBL特质：病例驱动、问题非结构化、协作讨论、假设-证据迭代、反思修正；"
        "（2）Biggs学习风格：Deep/Surface/Strategic对应不同学习动机与策略；"
        "（3）大五人格：尤其Neuroticism影响发言压力与讨论贡献意愿，Conscientiousness与Openness影响投入质量与PBL价值认可。"
        "请将‘模式字典’与‘当前激活模式’作为硬约束进行生成，"
        "输出内容必须映射到激活模式，并体现‘学习效能（learning efficacy）’与‘讨论贡献意愿（contribution willingness）’两个维度，"
        "不得写成泛泛的人格描述或空泛鸡汤。"
        "请严格只返回JSON，键名必须是 learning_style_prompt、personality_prompt、integrated_prompt。"
        "所有值都用中文字符串，不要使用Markdown。"
    )

    user_prompt = (
        "特质量表：1=低，2=中，3=高。\n"
        f"学习风格：surface={ls['surface']}, deep={ls['deep']}, strategic={ls['strategic']}。\n"
        f"人格特质：openness={p['openness']}, conscientiousness={p['conscientiousness']}, extraversion={p['extraversion']}, "
        f"agreeableness={p['agreeableness']}, neuroticism={p['neuroticism']}。\n"
        f"模式字典（参考）：{json.dumps(PERSONA_PATTERN_LIBRARY, ensure_ascii=False)}\n"
        f"该学生激活的学习模式：{json.dumps(active_patterns['learning_patterns'], ensure_ascii=False)}\n"
        f"该学生激活的人格模式：{json.dumps(active_patterns['personality_patterns'], ensure_ascii=False)}\n"
        f"该学生激活的原型映射：{json.dumps(active_patterns['archetypes'], ensure_ascii=False)}\n"
        "生成要求（必须遵循上述激活模式）：\n"
        "1) learning_style_prompt（60-140字）：基于Biggs理论描述该学生的学习动机与策略（Deep/Surface/Strategic），"
        "并明确在PBL中会如何表现（是否主动追问机制、是否偏向标准答案、是否按绩效选择性参与）。\n"
        "2) personality_prompt（80-170字）：基于大五描述社交与情绪机制，重点解释Neuroticism如何改变发言阈值与贡献意愿，"
        "并补充Conscientiousness与Openness如何增强或削弱对PBL价值的主观判断。\n"
        "3) integrated_prompt（130-230字）：在PBL‘不确定+协作+持续修正’情境下，整合学习风格与人格机制，"
        "写出内在冲突、可观察行为、发言策略与转变条件；需映射到一个或多个原型（焦虑高成就者/社交活跃但浅层贡献者/理想受益者/混合型）。\n"
        "写作风格要求：角色指令风格，强调可执行行为，不要写成文献综述。\n"
        "只输出JSON。"
    )

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{user_prompt_text}")]
    ).invoke({"user_prompt_text": user_prompt})
    result = await llm.ainvoke(prompt)
    content = (result.content or "").strip()
    parsed = json.loads(content)

    learning_style_prompt = str(parsed.get(
        "learning_style_prompt", "")).strip()
    personality_prompt = str(parsed.get("personality_prompt", "")).strip()
    integrated_prompt = str(parsed.get("integrated_prompt", "")).strip()

    if not learning_style_prompt or not personality_prompt:
        raise ValueError(
            "LLM did not return valid learning_style_prompt/personality_prompt")

    return {
        "learning_style_prompt": learning_style_prompt,
        "personality_prompt": personality_prompt,
        "learning_personality_prompt": integrated_prompt,
    }


async def generate_learning_personality_prompt(persona: Dict, llm: Any) -> str:
    """Generate a natural-language role prompt from numeric learning-style + personality traits."""
    sections = await generate_learning_personality_sections(persona, llm)
    return sections.get("learning_personality_prompt", "")


def format_persona_to_string(persona: Dict) -> str:
    """将 persona 字典格式化为字符串，注入到 prompt 中。"""
    cognitive_map = {
        "point_based": """
			你的逻辑能力被限制在‘孤立检索’。在讨论中，你只能回答‘是什么’类的问题。即使你掌握了相关的医学知识，你也无法将两个不同的知识点进行关联。
			行为准则：
			1.如果队友问‘这个症状的原因是什么？’，你只能给出教材上的标准定义或单一病因。
			2.严禁进行‘因为 A 导致 B，所以推测 C’的推理。
			3.当讨论涉及复杂因果链时，请表现出困惑，或坚持回归到基本定义的确认上。”
		""",
        "line_based": """
			你具备‘单一链条推理’能力。你倾向于锁定一个最明显的因果路径（$A \rightarrow B \rightarrow C$）并一条路走到黑。
			行为准则：
			1. 在分析案例时，迅速锁定一个你认为最可能的诊断，并沿着这个诊断寻找支持证据。
			2. 你容易产生‘隧道视野’，忽略与你当前逻辑链不符的其他线索。
			3. 如果队友提出其他路径，除非当前路径被彻底证伪，否则你会坚持原有的逻辑闭环。
		""",
        "plane_based": """
			你具备‘全局网状推理’和‘多重假设验证’能力。你是 PBL 讨论中的高阶思考者。
			行为准则：
			1. 你能同时激活多个可能的诊断（差异诊断），并对比它们的权重 。
			2. 当面对冲突的检查结果（如：症状支持 A，但化验支持 B）时，你需要尝试通过更深层的生理机制来解释这种矛盾。
			3. 你的发言应包含‘虽然...但是...’或‘考虑到...我们需要排除...’这类整合性逻辑 。
		""",
    }

    learning_adaptivity = {
        "low": "即使被提示也坚持原观点",
        "medium": "讨论中其他agent观点更加合理则修正观点，不合理则保持原观点",
        "high": "能根据新线索快速修正",
    }

    interaction_behavior = {
        "seeking_help_alignment": "确认他人的医学术语是否与自己理解的一致。",
        "correction_challenge": "发现他人逻辑与自己内部推理冲突时触发辩论。",
        "accumulation": "简单认同并补充相似的案例证据。",
        "reiteration": "只复述主要观点，不再做任何推理、联想、分析。",
        "silence": "保持沉默。返回省略号",
    }

    learning_style_desc = str(persona.get(
        "learning_style_prompt", "") or "").strip()
    personality_desc = str(persona.get("personality_prompt", "") or "").strip()

    if not learning_style_desc:
        raise ValueError(
            "Missing learning_style_prompt. Please click Save to generate prompts via LLM.")
    if not personality_desc:
        raise ValueError(
            "Missing personality_prompt. Please click Save to generate prompts via LLM.")

    return f"""
	请务必用中文输出
	- **姓名**：{persona.get('name', '匿名')} \n
	- **年龄**：{persona.get('age', 22)} \n
	- **性别/专业**：{persona.get('major', '医学')} \n

	- **学习风格**：
		- {learning_style_desc}

	- **人格因素（作用：不同的人格特质显著影响学生在 PBL 中的表现与感受 。）**：
		- {personality_desc}

	- **认知维度**（作用：决定 agent“从哪里开始想、怎么想，发言保留可能存在的缺陷”）：
		- {cognitive_map.get(persona.get('cognitive_orientation', 'point_based'), '无明确偏好')}

	- **动态学习维度**（作用：决定在讨论中吸收知识的速度，“能否被教会”）\n
		- 随着讨论的深度思维的转变情况：{learning_adaptivity.get(persona.get('learning_adaptivity'), '中等稳定')}

	- **学生可进行的互动行为** (作用： 根据学生特征，选择其中一种进行学生与学生、学生与老师之间的互动行为)
		- {interaction_behavior}
	"""
