"""PBL.backend.schemas
定义 PBL 案例的数据结构 (Pydantic Models)。
"""

from typing import List, Optional
from pydantic import BaseModel, Field

# --- 基础组件 ---


class TriggerQuestion(BaseModel):
    """
    对应 PDF 中的 "教师提示用问题" (Questions)
    或者 "主要讨论点" (Discussion Points)
    """
    question: str = Field(description="问题或讨论点的内容")
    type: str = Field("discussion", description="类型标记")
    learning_objectives: List[str] = Field(
        default=[],
        description="该触发问题对应的可评估学习目标；无法明确关联时应为空列表。",
    )
    knowledge_points: List[dict] = Field(
        default=[],
        description="回答该问题所需的细粒度医学知识点列表。每项建议包含 concept 和 explanation。",
    )


class BackgroundKnowledge(BaseModel):
    """对应 PDF 中的 "学习目的" """
    category: str = Field(description="分类，如：基础医学、临床医学")
    items: List[str] = Field(description="知识点列表")


class TriggerQuestionLearningObjective(BaseModel):
    """每个 trigger question 对应的学习目标。"""
    trigger_question: str = Field(description="对应的触发问题原文")
    learning_objectives: List[str] = Field(
        default=[],
        description="该问题下应达成的学习目标列表",
    )

# --- 新增：知识点溯源 ---


class KnowledgeEvidence(BaseModel):
    """知识点与原文的对应关系"""
    point: str = Field(description="背景知识点")
    evidence: List[str] = Field(description="原文中的证据片段（句子或短语）")
    explanation: str = Field(description="该片段如何体现了该知识点的必要性")


class KnowledgeAlignment(BaseModel):
    """全案知识点对齐结果"""
    alignments: List[KnowledgeEvidence] = Field(description="所有知识点的溯源列表")

# --- 核心场景结构 ---


class Scene(BaseModel):
    """
    单个情景模块 (Scene)
    """
    scene_number: int = Field(description="场景序号，从1开始")
    title: str = Field(description="场景标题，例如：第一部分-第一页")

    # --- 学生可见内容 ---
    story_content: str = Field(
        description="【学生可见】核心剧情。包含病历描述、对话、检查结果表格(Markdown格式)。"
    )

    # --- 教师/LLM 可见内容 ---
    teaching_guidance: Optional[str] = Field(
        None, description="对应 PDF 中的 '教师注意事项'。"
    )

    # 你提到的重点：主要讨论点
    key_discussion_points: List[str] = Field(
        default=[],
        description="对应 PDF 中的 '主要讨论点' (Main Discussion Points)。"
    )

    # 教师具体的提问
    trigger_questions: List[TriggerQuestion] = Field(
        default=[],
        description="对应 PDF 中的 '教师提示用问题'。"
    )

    trigger_question_learning_objectives: List[TriggerQuestionLearningObjective] = Field(
        default=[],
        description="按 trigger question 拆分的学习目标。每个问题至少应有一条对应目标。",
    )

    scene_reference_knowledge: Optional[str] = Field(
        None,
        description="对应 PDF 中的 '参考要点' (Reference Points)。"
    )

    # --- 图片处理 (核心修改) ---
    relevant_image_filenames: List[str] = Field(
        default=[],
        description="【LLM填写】从Markdown中提取的、该场景包含的**临床相关**图片文件名(如 'image-3.jpg')。忽略Logo或装饰图。"
    )

    images_base64: List[str] = Field(
        default=[],
        description="【后端回填】图片的Base64编码，前端可直接展示。"
    )

# --- 顶层案例结构 ---


class PBLCaseStructure(BaseModel):
    """完整的 PBL 案例结构"""
    case_title: str = Field(description="案例标题")
    theoretical_knowledge_points: List[str] = Field(
        description="【核心知识点】学习这个案例需要具备的背景知识、理论基础或临床学习要点。如果没有直接说明，请根据内容进行总结。"
    )

    learning_objectives: List[BackgroundKnowledge] = Field(
        default=[],
        description="总体学习目的（兼容字段）。若无法明确归属 trigger question，建议留空。"
    )

    scenes: List[Scene] = Field(description="场景列表")
