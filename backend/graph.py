"""PBL2.backend.graph
定义 LangGraph 的状态和图的结构。
"""
from typing import List, Annotated
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from . import agents


class GraphState(TypedDict):
    """
    表示图的状态。

    Attributes:
        messages: 讨论中交换的消息列表。
        discussion_stage: PBL 讨论的当前阶段。
        summary: 到目前为止的讨论摘要。
        next_speaker: 预定下一个发言的 Agent。
        is_teacher_interrupted: 标志位，指示老师是否已介入。
    """
    messages: Annotated[List[BaseMessage], operator.add]
    discussion_stage: str
    summary: str
    next_speaker: str
    is_teacher_interrupted: bool


# --------- 构建图 --------- 
wf = StateGraph(GraphState)

# 添加所有节点
wf.add_node("student_analyst", agents.STUDENT_ANALYST)
wf.add_node("student_observer", agents.STUDENT_OBSERVER)
wf.add_node("student_skeptic", agents.STUDENT_SKEPTIC)
wf.add_node("teacher_handler", agents.teacher_handler_node)
wf.add_node("summarizer", agents.summarizer_node)
wf.add_node("router", agents.router_node)

# 设置入口点
wf.set_entry_point("router")

# 定义条件路由
def _conditional_router(state: GraphState):
    """根据 next_speaker 决定下一个节点。"""
    return state["next_speaker"]

wf.add_conditional_edges(
    "router",
    _conditional_router,
    {
        "student_analyst": "student_analyst",
        "student_observer": "student_observer",
        "student_skeptic": "student_skeptic",
        "teacher_handler": "teacher_handler",
        "summarizer": "summarizer",
        "END": END,
    },
)

# 其他节点运行后都回到 router
wf.add_edge("student_analyst", "router")
wf.add_edge("student_observer", "router")
wf.add_edge("student_skeptic", "router")
wf.add_edge("teacher_handler", "router")
wf.add_edge("summarizer", "router")

# --------- 添加检查点并编译 ---------
# 使用内存检查点来保存状态
checkpointer = MemorySaver()

# 编译图，并附加检查点
app = wf.compile(checkpointer=checkpointer)
