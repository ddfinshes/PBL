"""PBL.backend.server
使用 FastAPI 和 WebSocket 提供后端服务，支持动态 Agent 图构建。
"""
from os import name
import uvicorn
import json
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage

# 动态 Agent 注册与图构建相关
from . import graph  # 导入 graph 模块以访问和修改 app
from .agents import register_student_agent, student_nodes, student_personas
from .graph_builder import build_graph, GraphState

# 创建 FastAPI 应用实例
app_fastapi = FastAPI()

# --- CORS 中间件配置 ---
app_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产中应限制为前端域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app_fastapi.get("/")
def read_root():
    return {"message": "PBL Backend is running."}

@app_fastapi.post("/update_personas")
async def update_personas(request: Dict[str, Dict]):
    """接收前端配置，清空、注册所有 agent，并重新编译图。"""
    # 1. 清空现有的 agent 配置
    student_personas.clear()
    student_nodes.clear()
    print("Cleared existing agent configurations.")

    # 2. 根据请求注册新的 agent
    for agent_id, persona_data in request.items():
        register_student_agent(agent_id, persona_data)

    # 3. 重新编译 LangGraph
    agent_ids = list(student_nodes.keys())
    if not agent_ids:
        print("Warning: No agents provided. The graph will be empty.")
    
    graph.app = build_graph(agent_ids)
    print(f"Successfully rebuilt graph with agents: {agent_ids}")

    return {"status": "success", "message": f"Personas updated and graph rebuilt for {len(agent_ids)} agents."}


@app_fastapi.websocket("/ws/pbl/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """处理 PBL 讨论的 WebSocket 连接。"""
    await websocket.accept()
    print(f"WebSocket connection established for session: {session_id}")

    config = {"configurable": {"thread_id": session_id}}

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")
            print('-----------', action)

            if not graph.app:
                await websocket.send_json({"error": "Graph not initialized. Please configure agents first."})
                continue

            if action == "start_discussion":
                print(f"[{session_id}] Starting new discussion.")
                initial_case = message.get("initial_case", "")
                initial_message = HumanMessage(content=initial_case, name="case_introduction")
                initial_state: GraphState = {
                    "messages": [initial_message],
                    "summary": "",
                    "next_speaker": "router",
                    "is_teacher_interrupted": False,
                }
                async for event in graph.app.astream(initial_state, config=config):
                    for node_name, output in event.items():
                        if "messages" in output and output['messages']:
                            for msg in output['messages']:
                                if hasattr(msg, 'content'):
                                    await websocket.send_json({"node": node_name, "content": msg.content})

            elif action == "teacher_intervention":
                teacher_message_content = message.get("content", "")
                print(f"[{session_id}] Teacher intervention: {teacher_message_content}")
                teacher_message = HumanMessage(content=teacher_message_content, name="teacher")
                
                graph.app.update_state(
                    config,
                    {"messages": [teacher_message], "is_teacher_interrupted": True},
                )
                # 使用 {} 作为输入来继续图的执行
                async for event in graph.app.astream({}, config=config):
                    for node_name, output in event.items():
                        if "messages" in output and output['messages']:
                            for msg in output['messages']:
                                if hasattr(msg, 'content'):
                                    await websocket.send_json({"node": node_name, "content": msg.content})

    except WebSocketDisconnect:
        print(f"WebSocket connection closed for session: {session_id}")
    except Exception as e:
        print(f"An error occurred in session {session_id}: {e}")
        await websocket.close(code=1011, reason=str(e))


if __name__ == "__main__":
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000)
