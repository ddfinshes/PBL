
# PBL 案例信息存储
# 初始为空，由前端通过 API 动态更新

pbl_story = "正在准备病例资料..."

pbl_triger_questions = [
    "正在加载问题列表..."
]


def update_pbl_info(story: str, questions: list):
    """更新全局 PBL 案例信息，供 Agent 讨论使用"""
    global pbl_story, pbl_triger_questions
    pbl_story = story
    pbl_triger_questions = questions
    print(f"PBL Info Updated: {len(questions)} questions loaded.")
