
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
    "【阶段一：问题识别】学生自由发言，列出病例中已知的关键信息（如症状、体征、检查结果）。提出需要进一步探究的“问题清单”（例如：患者发热的原因可能是什么？为什么会出现特定体征？）。",
    "【阶段二：初步假设】学生基于已有知识，提出可能的病因、诊断或机制假设（如“可能是感染性疾病”“需考虑自身免疫病”）。假设无需完全正确，重点是激发思考。",
    "【阶段三：知识缺口分析】学生讨论现有知识的不足，明确需要学习的新内容（如“我们需要复习肺炎的病原学”“需了解某种药物的作用机制”）。列出“学习议题”（Learning Issues），即待查证的关键问题。",
    "【阶段四：分配学习任务​】小组内部分工，每位学生负责1-2个学习议题（例如：A同学查相关解剖学知识，B同学查实验室检查意义）。明确课后自主学习的内容和资源（教材、文献、数据库等）。",
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
