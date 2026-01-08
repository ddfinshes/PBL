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


class BackgroundKnowledge(BaseModel):
    """对应 PDF 中的 "学习目的" """
    category: str = Field(description="分类，如：基础医学、临床医学")
    items: List[str] = Field(description="知识点列表")

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
    summary: str = Field(description="案例摘要")

    learning_objectives: List[BackgroundKnowledge] = Field(
        description="总体学习目的"
    )

    scenes: List[Scene] = Field(description="场景列表")
