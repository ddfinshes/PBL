"""PBL 案例信息存储（无阶段约束版本）。"""

from typing import List, Optional

# 病例文本与触发问题
pbl_story = "正在准备病例资料..."
pbl_triger_questions = ["正在加载问题列表..."]
current_trigger_question = ""
current_learning_objectives = []
current_case_name = ""

# 当前激活的场景 / 问题索引
active_scene_index = 0
active_question_index = 0

# 病例整体难度（1-9），用于与学生知识背景做差值
pbl_story_difficult = 3


def update_pbl_info(
    story: str,
    questions: list,
    story_difficult: int = 3,
    scene_idx: int = 0,
    q_idx: int = 0,
    learning_objectives: Optional[List[str]] = None,
    case_name: str = "",
) -> None:
    """更新全局案例信息，供 Agent 讨论使用。"""
    global pbl_story, pbl_triger_questions
    global current_trigger_question, current_learning_objectives
    global active_scene_index, active_question_index
    global current_case_name
    global pbl_story_difficult

    pbl_story = story
    pbl_triger_questions = questions
    current_trigger_question = str(questions[0]).strip() if questions else ""
    current_learning_objectives = learning_objectives or []
    current_case_name = (case_name or current_case_name or "").strip()
    active_scene_index = scene_idx
    active_question_index = q_idx
    pbl_story_difficult = story_difficult

    print(
        f"PBL Info Updated: case='{current_case_name}', Scene {scene_idx}, Question {q_idx}, story_difficult {story_difficult}, {len(questions)} questions loaded, {len(current_learning_objectives)} objectives loaded."
    )
