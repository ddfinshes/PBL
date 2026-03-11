"""PBL.backend.graph_builder
提供动态构建 LangGraph 实例的功能。
"""
from typing import List, Annotated, TypedDict
import operator

from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from . import agents


class GraphState(TypedDict):
    """
    表示图的状态。

    Attributes:
        messages: 讨论中交换的消息列表。
        discussion_stage: PBL 讨论的当前阶段。
        next_speaker: 预定下一个发言的 Agent。
        is_teacher_interrupted: 标志位，指示老师是否已介入。
        current_topic: 当前讨论的主题。
    """
    messages: Annotated[List[BaseMessage], operator.add]
    discussion_stage: str
    next_speaker: str
    is_teacher_interrupted: bool
    discussion_active: bool
    current_topic: str
    # 新增：累积消息计数器，每返回 {"total_messages": 1} 即自增
    total_messages: Annotated[int, operator.add]
    private_memory: dict
    knowledge_state: dict
    cognitive_load: dict
    self_efficacy: dict
    last_action_plan: dict
    force_no_silence_once: bool
    teacher_nominated_agent: str
    # Router objective-judge outputs (must be declared, otherwise dropped by state schema).
    trigger_question: str
    objective_evaluations: list
    achieved_all: bool
    end_reason: str


def build_graph(agent_ids: List[str]):
    """根据提供的 agent_ids 列表，动态构建并编译一个 LangGraph。"""
    wf = StateGraph(GraphState)

    # 1. 动态添加所有学生节点
    for agent_id in agent_ids:
        wf.add_node(agent_id, agents.student_nodes[agent_id])
        # 每位学生发言后进入 topic_manager 进行主题识别
        wf.add_edge(agent_id, "topic_manager")

    # 2. 添加固定的辅助节点
    wf.add_node("teacher_handler", agents.teacher_handler_node)
    wf.add_node("topic_manager", agents.topic_manager_node)
    wf.add_node("knowledge_evaluator", agents.knowledge_eval_node)
    wf.add_node("summarizer", agents.summarizer_node)
    wf.add_node("router", agents.router_node)

    # 3. 设置边关系
    wf.add_edge("teacher_handler", "router")
    # 【优化】线性流水线：识别主题 -> 评估知识覆盖 -> 记忆内化 -> 路由
    wf.add_edge("topic_manager", "knowledge_evaluator")
    wf.add_edge("knowledge_evaluator", "summarizer")
    wf.add_edge("summarizer", "router")

    # 4. 设置入口点
    wf.set_entry_point("router")

    # 4. 定义条件路由
    def _conditional_router(state: GraphState):
        return state["next_speaker"]

    # 将动态的学生节点和固定节点合并到路由映射中
    dynamic_mapping = {agent_id: agent_id for agent_id in agent_ids}
    static_mapping = {
        "teacher_handler": "teacher_handler",
        "END": END,
    }
    wf.add_conditional_edges(
        "router",
        _conditional_router,
        {**dynamic_mapping, **static_mapping},
    )

    # 5. 编译图并附加检查点
    checkpointer = MemorySaver()
    app = wf.compile(checkpointer=checkpointer)
    return app
