"""PBL backend agent 配置和人格画像预览

This module isolates persona/profile configuration and prompt-generation helpers
to keep agents.py focused on runtime orchestration.
"""

from __future__ import annotations

from typing import Any, Dict, List
import json

from langchain_core.prompts import ChatPromptTemplate


TRAIT_MIN = 1
TRAIT_MAX = 5
TRAIT_MID = 3
TRAIT_HIGH_THRESHOLD = 3
TRAIT_LOW_THRESHOLD = 3


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

    def _score(raw: Dict, key: str, default: int = TRAIT_MID) -> int:
        value = raw.get(key, default)
        try:
            numeric = int(value)
            return max(TRAIT_MIN, min(TRAIT_MAX, numeric))
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

    if ls["deep"] > TRAIT_HIGH_THRESHOLD:
        learning_patterns.append(
            PERSONA_PATTERN_LIBRARY["learning_mechanisms"]["deep_high"]
        )
    if ls["surface"] > TRAIT_HIGH_THRESHOLD:
        learning_patterns.append(
            PERSONA_PATTERN_LIBRARY["learning_mechanisms"]["surface_high"]
        )
    if ls["strategic"] > TRAIT_HIGH_THRESHOLD:
        learning_patterns.append(
            PERSONA_PATTERN_LIBRARY["learning_mechanisms"]["strategic_high"]
        )

    if p["neuroticism"] > TRAIT_HIGH_THRESHOLD:
        personality_patterns.append(
            PERSONA_PATTERN_LIBRARY["personality_mechanisms"]["neuroticism_high"]
        )
    if p["neuroticism"] < TRAIT_LOW_THRESHOLD:
        personality_patterns.append(
            PERSONA_PATTERN_LIBRARY["personality_mechanisms"]["neuroticism_low"]
        )
    if p["conscientiousness"] > TRAIT_HIGH_THRESHOLD or p["openness"] > TRAIT_HIGH_THRESHOLD:
        personality_patterns.append(
            PERSONA_PATTERN_LIBRARY["personality_mechanisms"]["co_openness_high"]
        )

    if ls["deep"] > TRAIT_HIGH_THRESHOLD and p["neuroticism"] > TRAIT_HIGH_THRESHOLD:
        archetypes.append(
            PERSONA_PATTERN_LIBRARY["archetypes"]["anxious_high_achiever"])
    if ls["surface"] > TRAIT_HIGH_THRESHOLD and p["neuroticism"] < TRAIT_LOW_THRESHOLD:
        archetypes.append(
            PERSONA_PATTERN_LIBRARY["archetypes"]["social_but_shallow"])
    if ls["deep"] > TRAIT_HIGH_THRESHOLD and p["neuroticism"] < TRAIT_LOW_THRESHOLD:
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
        "特质量表：1-5（1-2=低，3=中，4-5=高）。\n"
        f"学习风格：surface={ls['surface']}, deep={ls['deep']}, strategic={ls['strategic']}。\n"
        f"人格特质：openness={p['openness']}, conscientiousness={p['conscientiousness']}, extraversion={p['extraversion']}, "
        f"agreeableness={p['agreeableness']}, neuroticism={p['neuroticism']}。\n"
        f"模式字典（参考）：{json.dumps(PERSONA_PATTERN_LIBRARY, ensure_ascii=False)}\n"
        f"该学生激活的学习模式：{json.dumps(active_patterns['learning_patterns'], ensure_ascii=False)}\n"
        f"该学生激活的人格模式：{json.dumps(active_patterns['personality_patterns'], ensure_ascii=False)}\n"
        f"该学生激活的原型映射：{json.dumps(active_patterns['archetypes'], ensure_ascii=False)}\n"
        "生成要求（必须遵循上述激活模式）：\n"
        "1) learning_style_prompt（60-140字）：基于Biggs理论描述该学生的学习动机与策略（Deep/Surface/Strategic），"
        "并明确在PBL中会如何表现（是否主动追问机制、是否偏向标准答案、是否按绩效选择性参与）。"
        "必须逐一包含 surface/deep/strategic 的原始分值与其行为含义。\n"
        "2) personality_prompt（80-170字）：基于大五描述社交与情绪机制，重点解释Neuroticism如何改变发言阈值与贡献意愿，"
        "并补充Conscientiousness与Openness如何增强或削弱对PBL价值的主观判断。"
        "必须逐一包含 openness/conscientiousness/extraversion/agreeableness/neuroticism 的原始分值与对应特质解释。\n"
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

    if not learning_style_prompt or not personality_prompt:
        raise ValueError(
            "LLM did not return valid learning_style_prompt/personality_prompt")

    return {
        "learning_style_prompt": learning_style_prompt,
        "personality_prompt": personality_prompt,
    }


async def generate_learning_personality_prompt(persona: Dict, llm: Any) -> str:
    """Generate a natural-language role prompt from numeric learning-style + personality traits."""
    sections = await generate_learning_personality_sections(persona, llm)
    return sections.get("learning_personality_prompt", "")


def format_persona_to_string(persona: Dict) -> str:
    """将 persona 字典格式化为字符串，注入到 prompt 中。"""

    # 1. 认知地图保持不变（非常棒的设计）
    cognitive_map = {
        "point_based": "你的逻辑能力被限制在‘孤立检索’。你只能回答‘是什么’，无法将两个不同知识点关联。行为准则：1.只能给出字面定义或单一病因。2.严禁进行复杂的因果链推理。3.发言通常简短且缺乏深度。",
        "line_based": "你具备‘单一链条推理’能力。你倾向于锁定一个最明显的因果路径并一条路走到黑。行为准则：1.迅速锁定一个最可能的诊断，并只寻找支持它的证据。2.容易产生‘隧道视野’，忽略反常线索。3.极度依赖权威指南和标准答案。",
        "plane_based": "你具备‘全局网状推理’和‘多重假设验证’能力。行为准则：1.能同时激活多个差异诊断，对比权重。2.能敏锐捕捉反常线索（如大量吃维C）并推导病理机制。3.发言包含‘虽然...但是...’等整合性逻辑。",
    }

    learning_adaptivity = {
        "low": "即使被提示也坚持原观点或盲从权威，无法真正理解新逻辑。",
        "medium": "如果别人的观点符合考核标准或书本权威，你会接受；否则保持防备。",
        "high": "能根据新线索（病例细节/同伴提示）迅速修正假设，整合新知。",
    }

    # 2. 优化互动行为，去掉纯粹的省略号，改为具有表现力的动作
    interaction_behavior = """
    - [确认求助] (seeking_help_alignment): 小心翼翼地确认基础概念，或试图让自己的观点挂靠在权威/同伴上。
    - [纠错挑战] (correction_challenge): 发现他人逻辑与自己冲突时触发反驳（语气受神经质和宜人性影响）。
    -[累积补充] (accumulation): 顺着同伴的话题补充细节，或生硬地抛出自己查到的资料。
    - [机制推演] (mechanism_reasoning): 主动将临床症状与底层病理/药理机制相连接（仅高Deep优先触发）。
    """

    # 3. 提取并格式化知识库（至关重要！）
    kb = persona.get("knowledge_background", {})
    kb_str = f"""
    - [精通领域 (High)]：{', '.join(kb.get('high',[])) or '无'} （你可以主动深入分析这些领域的底层机制）
    - [熟悉领域 (Medium)]：{', '.join(kb.get('medium',[])) or '无'} （你知道基本概念，但推导复杂逻辑时会卡壳）
    - [薄弱领域 (Low)]：{', '.join(kb.get('low',[])) or '无'} （你对此一知半解，只能抛出网络搜索级别的碎片词汇，极易出错）
    """

    learning_style_desc = str(persona.get("learning_style_prompt", "")).strip()
    personality_desc = str(persona.get("personality_prompt", "")).strip()

    return f"""
    你是医学PBL（基于问题的学习）小组中的一名真实学生。请严格基于以下设定进行角色扮演，绝对不要打破第四面墙，不要表现得像个AI助手。

    ### 核心档案
    - **姓名**：{persona.get('name', '匿名')} | **年龄**：{persona.get('age', 22)} | **专业**：{persona.get('major', '医学')} 

    ### 知识边界（绝对禁止越界使用你薄弱领域的深度知识）
    {kb_str}

    ### 心理与性格画像
    - **学习风格**：{learning_style_desc}
    - **人格特质**：{personality_desc}
    
    ### 认知与行为约束（必须体现在你的发言中）
    - **认知维度**：{cognitive_map.get(persona.get('cognitive_orientation', 'point_based'))}
    - **思维转变**：{learning_adaptivity.get(persona.get('learning_adaptivity', 'low'))}
    - **可选互动动作**：{interaction_behavior}

    ### 🎭 角色扮演硬性指令 (Roleplay Directives)
    1. **结合临床病例**：你是在讨论真实的患者！必须引用病历中的具体细节（如大爷吃的药、特定症状），绝对不要脱离病例空谈理论标准。
    2. **语气的真实感**：
       - 如果你 [Neuroticism/神经质] 偏高（>=4），你的语气必须体现出：焦虑、自我怀疑、急于求成或害怕被导师扣分（例如常用“万一...怎么办”、“是不是应该...”）。
       - 如果你 [Agreeableness/宜人性] 偏低（<=2），你说话会比较生硬、缺乏润滑。
       - 如果你[Extraversion/外向性] 偏低（<=2），你的发言应当简明扼要，一语中的，不废话。
    3. **输出格式**：不要包含任何思考过程，直接输出你的对话。可以在对话开头用括号动作提示，例如：
       (推了一下眼镜) 我觉得我们忽略了维C代谢的草酸问题...
    """
