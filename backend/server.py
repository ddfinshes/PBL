"""PBL.backend.server
使用 FastAPI 和 WebSocket 提供后端服务，支持动态 Agent 图构建。
最终修复版：
1. 包含所有必要的 API 路由 (/api/pdf-images/, /api/parse-case/ 等)。
2. 静态资源挂载。
3. WebSocket 支持。
"""
from os import name
import uvicorn
import json
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
import asyncio
import re
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List

from langchain_core.messages import HumanMessage

# 动态 Agent 注册与图构建相关
from . import graph  # 导入 graph 模块以访问和修改 app
from .agents import register_student_agent, student_nodes, student_personas
from .graph_builder import build_graph, GraphState
from .graph import app, GraphState
# 导入解析函数
from .pdf_parser import parse_pbl_to_json, get_raw_pdf_images
from .schema import PBLCaseStructure

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic 模型 ---


class Persona(BaseModel):
    reasoning_path: str
    knowledge_integration: str
    core_biases: List[str]
    sensitivity: int
    proficiency: int


class UpdatePersonasRequest(BaseModel):
    student_analyst: Persona
    student_observer: Persona
    student_skeptic: Persona


class ActiveSceneRequest(BaseModel):
    story: str
    trigger_questions: List[str]


app_fastapi = FastAPI()

# --- CORS 中间件配置 ---
# --- 目录配置 ---
BASE_DIR = Path(__file__).parent
PDF_STORAGE_DIR = BASE_DIR / "pdfs"
PDF_STORAGE_DIR.mkdir(exist_ok=True)

CASE_STORAGE_DIR = BASE_DIR / "case"
CASE_STORAGE_DIR.mkdir(exist_ok=True)

CASES_DATA_DIR = BASE_DIR / "cases_img"
CASES_DATA_DIR.mkdir(exist_ok=True)

AGENT_SETTING_PATH = BASE_DIR / "agent_setting.json"

# 挂载静态资源
app_fastapi.mount(
    "/static/cases", StaticFiles(directory=CASES_DATA_DIR), name="cases_img")

app_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产中应限制为前端域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- 工具函数 ---


def extract_base_filename(pdf_filename: str) -> str:
    """从PDF文件名提取基础名称（不带时间戳或扩展名）"""
    # 支持两种格式：新格式（无时间戳）和兼容旧格式（有时间戳）
    match = re.match(r'(.+?)_\d{8}_\d{6}\.pdf$', pdf_filename)
    if match:
        return match.group(1)  # 旧格式：提取时间戳前部分
    return pdf_filename.rsplit('.', 1)[0]  # 新格式：直接去掉.pdf


def save_case_json(base_name: str, data: dict) -> bool:
    json_path = CASE_STORAGE_DIR / f"{base_name}.json"
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def process_response_urls(result_dict: dict) -> dict:
    """将本地路径转换为Web URL，并移除Base64"""
    case_folder_abs_path = result_dict.get("case_folder")
    if not case_folder_abs_path:
        return result_dict

    case_folder_name = Path(case_folder_abs_path).name
    scenes = result_dict.get("scenes", [])
    for scene in scenes:
        local_paths = scene.get("local_image_paths", [])
        image_urls = []
        for local_path in local_paths:
            filename = Path(local_path).name
            url = f"/static/cases/{case_folder_name}/img/{filename}"
            image_urls.append(url)
        scene["image_urls"] = image_urls
        if "images_base64" in scene:
            del scene["images_base64"]
        if "local_image_paths" in scene:
            del scene["local_image_paths"]
    return result_dict

# --- API 路由 ---

@app_fastapi.on_event("startup")
async def startup_event():
    """服务器启动时，从配置文件加载 Agents 并构建图。"""
    print("Initializing agents from agent_setting.json...")
    
    if not AGENT_SETTING_PATH.exists():
        print("✗ Startup: agent_setting.json not found. No agents loaded.")
        return

    try:
        with open(AGENT_SETTING_PATH, 'r', encoding='utf-8') as f:
            personas = json.load(f)
        
        for agent_id, persona in personas.items():
            register_student_agent(agent_id, persona)
        
        agent_ids = list(student_nodes.keys())
        graph.app = build_graph(agent_ids)
        print(f"✓ Startup: Graph built with agents: {agent_ids}")
    except Exception as e:
        print(f"✗ Startup: Error loading agents: {e}")


@app_fastapi.get("/")
def read_root():
    return {"message": "PBL Backend is running."}


@app_fastapi.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        if file.content_type != "application/pdf" or not file.filename.endswith(".pdf"):
            return {"detail": "只支持PDF格式的文件"}, 400

        # 改进：不添加时间戳，直接用原始文件名，实现同名PDF自动覆盖和缓存复用
        file_stem = file.filename.rsplit(".", 1)[0]
        unique_filename = f"{file_stem}.pdf"
        file_path = PDF_STORAGE_DIR / unique_filename

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        return {
            "status": "success",
            "message": "文件上传成功",
            "file_name": unique_filename,
            "file_path": str(file_path.relative_to(BASE_DIR.parent)),
            "file_size": len(contents)
        }
    except Exception as e:
        logger.error(f"PDF上传失败: {e}")
        return {"detail": str(e)}, 500

# 1. AI 解析接口


@app_fastapi.post("/api/parse-case/{filename}")
async def api_parse_case(filename: str, force_reparse: bool = False):
    """
    解析PDF文件为PBL案例。
    - 如果缓存存在且 force_reparse=False，直接返回缓存
    - 否则调用LLM进行完整解析
    """
    logger.info(f"[解析请求] {filename}, force_reparse={force_reparse}")
    file_path = PDF_STORAGE_DIR / filename
    if not file_path.exists():
        return {"detail": "文件不存在"}, 404

    base_name = extract_base_filename(filename)

    # 检查缓存
    if not force_reparse:
        json_path = CASE_STORAGE_DIR / f"{base_name}.json"
        if json_path.exists():
            logger.info(f"✓ 使用缓存: {json_path}")
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                return cached_data
            except Exception as e:
                logger.warning(f"缓存读取失败: {e}，将重新解析")

    # 缓存不存在或force_reparse=True，执行LLM解析
    try:
        logger.info(f"[开始LLM解析] {filename}")
        result_dict = await parse_pbl_to_json(str(file_path))
        if result_dict.get("status") == "failed":
            return {"detail": result_dict.get("error", "解析失败")}, 500

        result_dict = process_response_urls(result_dict)
        save_case_json(base_name, result_dict)
        logger.info(f"✓ 解析完成并已缓存: {base_name}")
        return result_dict
    except Exception as e:
        logger.error(f"解析失败: {e}", exc_info=True)
        return {"detail": str(e)}, 500


@app_fastapi.get("/api/pdf-images/{filename}")
def api_get_images(filename: str):
    """获取PDF中的原始图片（不进行LLM处理，快速返回）"""
    logger.info(f"[图片提取请求] {filename}")
    file_path = PDF_STORAGE_DIR / filename
    if not file_path.exists():
        return {"detail": "文件不存在"}, 404

    try:
        # 调用 pdf_parser.py 中的 get_raw_pdf_images
        result = get_raw_pdf_images(str(file_path))
        return result
    except Exception as e:
        logger.error(f"图片提取失败: {e}", exc_info=True)
        return {"detail": str(e)}, 500

# 3. 缓存列表接口


@app_fastapi.get("/api/cached-cases")
def api_get_cached_cases():
    try:
        cached_files = list(CASE_STORAGE_DIR.glob("*.json"))
        cases = []
        for json_file in cached_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cases.append({
                        "filename": json_file.stem,
                        "title": data.get("case_title", "未命名案例"),
                        "scenes_count": len(data.get("scenes", [])),
                        "modified_time": datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
                    })
            except Exception:
                continue
        return {"status": "success", "cases": cases}
    except Exception as e:
        return {"detail": str(e)}, 500

# 4. 获取单个缓存接口


@app_fastapi.get("/api/case/{case_name}")
def api_get_case_by_name(case_name: str):
    json_path = CASE_STORAGE_DIR / f"{case_name}.json"
    if not json_path.exists():
        return {"detail": "案例不存在"}, 404
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"detail": str(e)}, 500


@app_fastapi.post("/api/set-active-scene")
async def set_active_scene(request: ActiveSceneRequest):
    from .pbl_info import update_pbl_info
    update_pbl_info(request.story, request.trigger_questions)
    return {"status": "success", "message": "Global PBL info updated."}


# 5. 【新增】保存编辑后的case数据
@app_fastapi.post("/api/save-case")
async def api_save_case(request_data: dict):
    """
    保存编辑后的case数据到JSON文件

    请求体格式:
    {
      "caseName": "案例标题",
      "sceneIndex": 0,
      "questionIndex": 0,
      "newQuestion": "编辑后的问题内容"
    }
    """
    try:
        case_name = request_data.get("caseName")
        scene_idx = request_data.get("sceneIndex")
        question_idx = request_data.get("questionIndex")
        new_question = request_data.get("newQuestion")

        if not all([case_name, isinstance(scene_idx, int), isinstance(question_idx, int), new_question]):
            return {"status": "error", "detail": "参数不完整"}, 400

        # 改进：先尝试直接查找，失败则模糊匹配
        json_path = CASE_STORAGE_DIR / f"{case_name}.json"

        if not json_path.exists():
            # 模糊匹配：根据case_name包含关系查找
            logger.debug(f"精确匹配失败，开始模糊匹配: {case_name}")
            matching_files = list(CASE_STORAGE_DIR.glob("*.json"))
            json_path = None

            for f in matching_files:
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        if data.get("case_title") == case_name:
                            json_path = f
                            logger.debug(f"模糊匹配成功: {f.name}")
                            break
                except Exception:
                    continue

            if not json_path:
                logger.error(f"找不到对应的case文件: {case_name}")
                return {"status": "error", "detail": f"案例文件不存在: {case_name}"}, 404

        logger.info(f"找到case文件: {json_path}")

        # 读取JSON文件
        with open(json_path, 'r', encoding='utf-8') as f:
            case_data = json.load(f)

        # 更新对应的问题
        if scene_idx >= len(case_data.get("scenes", [])):
            return {"status": "error", "detail": f"场景索引越界: {scene_idx}"}, 400

        scene = case_data["scenes"][scene_idx]
        if question_idx >= len(scene.get("trigger_questions", [])):
            return {"status": "error", "detail": f"问题索引越界: {question_idx}"}, 400

        # 记录旧问题内容用于日志
        old_question = scene["trigger_questions"][question_idx]["question"]

        # 更新问题内容
        scene["trigger_questions"][question_idx]["question"] = new_question

        # 保存回JSON文件
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 已保存: {json_path.name}")
        logger.info(f"  场景 {scene_idx + 1}, 问题 {question_idx + 1}")
        logger.info(f"  旧内容: {old_question[:50]}...")
        logger.info(f"  新内容: {new_question[:50]}...")

        return {"status": "success", "message": "问题已保存"}

    except Exception as e:
        logger.error(f"保存case失败: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/update_personas")
# async def update_personas(request: Dict[str, Dict]):
#     """接收前端配置，清空、注册所有 agent，并重新编译图。"""
#     # 1. 清空现有的 agent 配置
#     student_personas.clear()
#     student_nodes.clear()
#     print("Cleared existing agent configurations.")

#     # 2. 根据请求注册新的 agent
#     request = {
#         "Alice": {     
#             "name": "Alice",
#             "age": 22,
#             "major": "female",
#             "knowledge_background": {
#                 "high": ["hypertension"],
#                 "medium": ["haemodynamics"],
#                 "low": ["diabete"] 
#                 },
#             "cognitive_orientation": 
#                 {
#                     "attentional_anchor":[
#                         "patient_events",
#                         "symptoms",
#                         "social_cues",
#                     ],
#                     "reasoning_entry": ["mechanism"],
#                     "causal_structure": ["linear_causality"]
#                 },
#             "social_interaction_style": {
#                 "verbal_confidence": "high",
#                 "language_register": "medium",
#                 "interaction_role": "leader"     
#                  },    
#             "learning_adaptivity": "high"
#         },
#         "Bob": {     
#             "name": "Bob",
#             "age": 23,
#             "major": "male",
#             "knowledge_background": {
#                 "high": ["hypertension"],
#                 "medium": ["haemodynamics"],
#                 "low": ["diabete"] 
#                 },
#             "cognitive_orientation": 
#                 {
#                     "attentional_anchor":[
#                         "symptoms",
#                         "social_cues",
#                     ],
#                     "reasoning_entry": ["external_factors"],
#                     "causal_structure": ["linear_causality", "multi_concurrent"]
#                 },
#             "social_interaction_style": {
#                 "verbal_confidence": "low",
#                 "language_register": "low",
#                 "interaction_role": "follower"     
#                  },    
#             "learning_adaptivity": "medium"
#         },
#         "Lily": {     
#             "name": "Lily",
#             "age": 22,
#             "major": "female",
#             "knowledge_background": {
#                 "high": ["hypertension"],
#                 "medium": ["haemodynamics"],
#                 "low": ["diabete"] 
#                 },
#             "cognitive_orientation": 
#                 {
#                     "attentional_anchor":[
#                         "social_cues",
#                     ],
#                     "reasoning_entry": ["external_factors"],
#                     "causal_structure": ["multi_concurrent"]
#                 },
#             "social_interaction_style": {
#                 "verbal_confidence": "high",
#                 "language_register": "high",
#                 "interaction_role": "follower"     
#                  },    
#             "learning_adaptivity": "medium"
#         },
#     }

#     for agent_id, persona_data in request.items():
#         register_student_agent(agent_id, persona_data)

#     return {"status": "success", "message": f"Personas updated and graph rebuilt for {len(agent_ids)} agents."}

async def update_personas_v1(request: Dict[str, Dict]):
    """接收前端配置，保存到 JSON 文件，清空并重新注册所有 agent，并重新构建图。"""
    try:
        # 1. 保存到 agent_setting.json
        with open(AGENT_SETTING_PATH, 'w', encoding='utf-8') as f:
            json.dump(request, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved personas to {AGENT_SETTING_PATH}")

        # 2. 清空现有的 agent 配置
        student_personas.clear()
        student_nodes.clear()
        logger.info("Cleared existing agent configurations.")

        # 3. 注册新的 agent
        for agent_id, persona_data in request.items():
            register_student_agent(agent_id, persona_data)

        # 4. 重新编译 LangGraph
        agent_ids = list(student_nodes.keys())
        graph.app = build_graph(agent_ids)
        logger.info(f"Successfully rebuilt graph with agents: {agent_ids}")

        return {"status": "success", "message": f"Personas updated, saved to file, and graph rebuilt for {len(agent_ids)} agents."}
    except Exception as e:
        logger.error(f"Failed to update personas: {e}")
        return {"status": "error", "detail": str(e)}, 500
        
# 存储每个 session 的后台任务，用于处理 LangGraph 流输出
session_tasks = {}
@app_fastapi.get("/get_personas")
async def get_personas():
    """从 agent_setting.json 读取所有 agent 的配置并返回。"""
    try:
        if not AGENT_SETTING_PATH.exists():
            return {}
        with open(AGENT_SETTING_PATH, 'r', encoding='utf-8') as f:
            personas = json.load(f)
        return personas
    except Exception as e:
        logger.error(f"Error reading personas: {e}")
        return {"detail": str(e)}, 500

# 移除冗余或过时的 Pydantic 定义


@app_fastapi.websocket("/ws/pbl/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connection established for session: {session_id}")

    config = {"configurable": {"thread_id": session_id}}
    
    # 状态管理
    current_state = None
    graph_task = None
    output_queue = asyncio.Queue()
    
    async def stream_langgraph(state):
        """后台流式输出任务"""
        try:
            async for event in graph.app.astream(state, config=config):
                # 将输出放入队列，避免阻塞 astream
                await output_queue.put(event)
        except asyncio.CancelledError:
            # 正常任务取消
            pass
        except Exception as e:
            # 发送错误信息到前端
            await websocket.send_json({"error": str(e)})
    
    async def output_processor():
        """处理输出队列的任务"""
        while True:
            try:
                event = await output_queue.get()
                for node, out in event.items():
                    if "messages" in out:
                        for m in out["messages"]:
                            await websocket.send_json({
                                "node": node, 
                                "content": m.content,
                                "type": "agent_output"
                            })
                output_queue.task_done()
            except asyncio.CancelledError:
                break
    
    output_task = None
    
    try:
        while True:
            # 主循环只负责接收消息
            data = await websocket.receive_text()
            msg = json.loads(data)
            action = msg.get("action")
            
            if action == "start_discussion":
                # 初始化状态
                initial_case = msg.get("initial_case", "")
                current_state = {
                    "messages": [HumanMessage(content=initial_case, name="case_introduction")],
                    "summary": "",
                    "next_speaker": "router",
                    "is_teacher_interrupted": False,
                    "discussion_active": True,  # 显式初始化讨论状态
                }
                
                # 取消旧任务
                if graph_task:
                    graph_task.cancel()
                if output_task:
                    output_task.cancel()
                
                # 启动新任务
                graph_task = asyncio.create_task(stream_langgraph(current_state))
                output_task = asyncio.create_task(output_processor())
                
            elif action == "teacher_intervention":
                teacher_content = msg.get("content", "")
                print(f"teacher_content: {teacher_content}")
                teacher_msg = HumanMessage(content=teacher_content, name="teacher")
                print(f"current_state: {current_state}")
                # 更新状态以触发干预
                if current_state:
                    # 检查教师指令并相应地更新状态
                    update_payload = {"messages": [teacher_msg]}
                    # 教师希望终止讨论的关键字列表，可以根据需要扩展
                    stop_keywords = ["停止讨论", "结束讨论", "stop", "end"]
                    if any(kw in teacher_content for kw in stop_keywords):
                        logger.info("教师指令：停止讨论。更新状态以终止图。")
                        update_payload["discussion_active"] = False
                        update_payload["next_speaker"] = "END"  # 直接终止图，避免 KeyError
                        # 先更新状态，然后取消后台任务，防止学生继续发言
                        graph.app.update_state(config, update_payload)
                        if graph_task:
                            graph_task.cancel()
                        if output_task:
                            output_task.cancel()
                        # 更新状态后无需再次调用 update_state
                        continue  # 跳过后续统一的 update_state 调用
                    else:
                        logger.info("教师干预：常规消息。")
                        update_payload["is_teacher_interrupted"] = True
                        update_payload["next_speaker"] = "teacher_handler"

                        # graph.app.update_state(config, update_payload)
                        # 1) 立即写入 LangGraph 状态
                        graph.app.update_state(config, update_payload)
                        # 2) 更新本地 current_state（让后续 restart 用最新值）
                        current_state["messages"].append(teacher_msg)
                        current_state["is_teacher_interrupted"] = True
                        current_state["next_speaker"] = "teacher_handler"

                        # 3) 抢占：重启流任务
                        if graph_task:
                            graph_task.cancel()
                        if output_task:
                            output_task.cancel()

                        graph_task  = asyncio.create_task(stream_langgraph(current_state))
                        output_task = asyncio.create_task(output_processor())
                    
                    
                    # 通知前端教师干预已接收
                    await websocket.send_json({
                        "type": "teacher_intervention_ack",
                        "content": teacher_content
                    })
                
    except WebSocketDisconnect:
        # 清理资源
        if graph_task:
            graph_task.cancel()
        if output_task:
            output_task.cancel()

if __name__ == "__main__":
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000)
