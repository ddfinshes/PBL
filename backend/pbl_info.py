
# PBL 案例信息存储
# 初始为空，由前端通过 API 动态更新

pbl_story = "正在准备病例资料..."

pbl_triger_questions = [
    "正在加载问题列表..."
]

active_scene_index = 0
active_question_index = 0


def update_pbl_info(story: str, questions: list, scene_idx: int = 0, q_idx: int = 0):
    """更新全局 PBL 案例信息，供 Agent 讨论使用"""
    global pbl_story, pbl_triger_questions, active_scene_index, active_question_index
    pbl_story = story
    pbl_triger_questions = questions
    active_scene_index = scene_idx
    active_question_index = q_idx
    print(
        f"PBL Info Updated: Scene {scene_idx}, Question {q_idx}, {len(questions)} questions loaded.")
