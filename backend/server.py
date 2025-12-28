"""PBL2.backend.server
使用 FastAPI 和 WebSocket 提供后端服务。
"""
import asyncio
import uvicorn
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage

from .graph import app, GraphState

# 创建 FastAPI 应用实例
app_fastapi = FastAPI()

@app_fastapi.get("/")
def read_root():
    return {"message": "PBL Backend is running."}

@app_fastapi.websocket("/ws/pbl/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """处理 PBL 讨论的 WebSocket 连接。"""
    await websocket.accept()
    print(f"WebSocket connection established for session: {session_id}")

    # 为每个会话配置一个唯一的 thread_id
    config = {"configurable": {"thread_id": session_id}}

    try:
        # 循环等待前端消息
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")

            if action == "start_discussion":
                # --- 开始新的讨论 ---
                print(f"[{session_id}] Starting new discussion.")
                initial_case = message.get("initial_case", "")
                initial_message = HumanMessage(content=initial_case, name="case_introduction")
                initial_state: GraphState = {
                    "messages": [initial_message],
                    "discussion_stage": "初步诊断与鉴别诊断",
                    "summary": "",
                    "next_speaker": "router",
                    "is_teacher_interrupted": False,
                }
                # 流式运行图，并将结果发送到前端
                async for event in app.astream(initial_state, config=config):
                    for node_name, output in event.items():
                        if "messages" in output and output['messages']:
                            for msg in output['messages']:
                                if hasattr(msg, 'content'):
                                    await websocket.send_json({
                                        "node": node_name,
                                        "content": msg.content
                                    })

            elif action == "teacher_intervention":
                # --- 处理老师干预 ---
                teacher_message_content = message.get("content", "")
                print(f"[{session_id}] Teacher intervention: {teacher_message_content}")
                teacher_message = HumanMessage(content=teacher_message_content, role="teacher")
                
                # 更新状态，插入老师消息并设置中断标志
                await app.update_state(
                    config,
                    {
                        "messages": [teacher_message],
                        "is_teacher_interrupted": True,
                    },
                )
                # 老师发言后，图会自动从下一个节点（router -> teacher_handler）继续
                # 我们需要继续流式传输后续的响应
                async for event in app.astream(None, config=config):
                    for node_name, output in event.items():
                        if "messages" in output and output['messages']:
                            for msg in output['messages']:
                                if hasattr(msg, 'content'):
                                    await websocket.send_json({
                                        "node": node_name,
                                        "content": msg.content
                                    })

    except WebSocketDisconnect:
        print(f"WebSocket connection closed for session: {session_id}")
    except Exception as e:
        print(f"An error occurred in session {session_id}: {e}")
        await websocket.close(code=1011, reason=str(e))


# 运行服务器的入口
if __name__ == "__main__":
    # 建议在终端中使用 uvicorn 命令启动，便于调试和热重载
    # uvicorn PBL2.backend.server:app_fastapi --reload
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000)
