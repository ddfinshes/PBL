"""PBL.backend.graph
占位模块：提供 GraphState 类型，并在运行时持有动态生成的 LangGraph app 实例。

server.py 在收到 /update_personas 请求后会调用
    graph_builder.build_graph(agent_ids)
并把返回的 app 赋值给本模块的全局变量 `app`。
"""
from .graph_builder import GraphState, build_graph  # noqa: F401  (GraphState 供类型检查使用)

# 在启动阶段先置为 None；更新 persona 时由 server.py 赋值
app = None  # type: ignore