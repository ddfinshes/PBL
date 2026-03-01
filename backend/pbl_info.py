
# PBL 案例信息存储
# 初始为空，由前端通过 API 动态更新

pbl_story = "正在准备病例资料..."

pbl_triger_questions = [
    "正在加载问题列表..."
]

active_scene_index = 0
active_question_index = 0

active_stage_index = 0
stage_tasks = [
    "【Phase 1: Problem Identification】Students speak freely and list the key known information in the case(such as symptoms, signs, and examination or test results). They propose a “question list” that requires further exploration(e.g., What could be the cause of the patient’s fever? Why do specific signs appear?).",
    "【Phase 2: Preliminary Hypotheses】Students propose possible causes, diagnoses, or mechanisms based on existing knowledge (e.g., “It might be an infectious disease,” “Consider autoimmune diseases”). Hypotheses do not need to be entirely correct; the focus is on stimulating thinking.",
    "【Phase 3: Knowledge Gap Analysis】Students discuss the limitations of current knowledge and identify new content that needs to be learned (e.g., “We need to review the etiology of pneumonia,” “Need to understand the mechanism of a certain drug”). They list “Learning Issues,” which are key questions to be investigated.",
    "【Phase 4: Assignment of Learning Tasks】Within the group, tasks are divided, with each student responsible for 1-2 learning issues (e.g., Student A researches relevant anatomy, Student B researches the significance of laboratory tests). Clarify the content and resources for self-study after class (textbooks, literature, databases, etc.).",
]

def update_pbl_info(story: str, questions: list, scene_idx: int = 0, q_idx: int = 0):
    """更新全局 PBL 案例信息，供 Agent 讨论使用"""
    global pbl_story, pbl_triger_questions, active_scene_index, active_question_index
    pbl_story = story
    pbl_triger_questions = questions
    active_scene_index = scene_idx
    active_question_index = q_idx
    print(
        f"PBL Info Updated: Scene {scene_idx}, Question {q_idx}, {len(questions)} questions loaded.")
