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
import uuid
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
from langchain_openai import ChatOpenAI
from .config import BASE_URL, DASHSCOPE_API_KEY, LLM_MODEL_NAME

# 动态 Agent 注册与图构建相关
from . import graph  # 导入 graph 模块以访问和修改 app
from .agents import register_student_agent, student_nodes, student_personas, simplify_message
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
    scene_index: int = 0
    question_index: int = 0


class InterventionSummaryRequest(BaseModel):
    session_id: str
    intervention_id: str
    scene_index: int
    question_index: int


class SaveSummaryRequest(BaseModel):
    session_id: str
    scene_index: int
    question_index: int
    intervention_id: str
    summary_data: dict


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
    update_pbl_info(request.story, request.trigger_questions,
                    request.scene_index, request.question_index)
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
# 存储每个 session 的消息历史（用于分支管理）
# 结构: { session_id: { "messages": [...], "active_id": "none" } }
session_histories = {}

DISCUSSION_FILE = BASE_DIR / "discussion.json"


def persist_discussion(session_id, messages_map):
    """将讨论历史持久化到 discussion.json，按 trigger question 分块存储"""
    try:
        data = {}
        if DISCUSSION_FILE.exists():
            with open(DISCUSSION_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    data = json.loads(content)

        session_data = data.get(session_id, {})

        # 按 scene_index 和 question_index 进行分组
        for msg_id, msg in messages_map.items():
            s_idx = msg.get("scene_index", 0)
            q_idx = msg.get("question_index", 0)
            block_key = f"q_{s_idx}_{q_idx}"

            if block_key not in session_data:
                session_data[block_key] = {"messages": []}

            # 检查是否已存在
            if not any(m["id"] == msg_id for m in session_data[block_key]["messages"]):
                # 序列化副本 (去掉不可序列化的 langchain_msg)
                store_msg = {k: v for k, v in msg.items() if k !=
                             "langchain_msg"}
                session_data[block_key]["messages"].append(store_msg)

        data[session_id] = session_data

        with open(DISCUSSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error persisting discussion: {e}")


@app_fastapi.post("/api/generate-intervention-summary")
async def api_generate_intervention_summary(request: InterventionSummaryRequest):
    """根据教师干预点，优先检查已归档总结，否则并行调用 Qwen 生成"""
    try:
        logger.info(
            f"=== Summary generation requested for {request.intervention_id} ===")

        # 1. 优先从磁盘（归档文件）检查是否已有总结
        block_key = f"q_{request.scene_index}_{request.question_index}"
        if DISCUSSION_FILE.exists():
            with open(DISCUSSION_FILE, "r", encoding="utf-8") as f:
                disk_data = json.load(f)
                cached = disk_data.get(request.session_id, {}).get(block_key, {}).get(
                    "intervention_summaries", {}).get(request.intervention_id)
                if cached and "parts" in cached:
                    logger.info(
                        f"Found archived summary for {request.intervention_id}. Skipping LLM.")
                    return {
                        "status": "success",
                        "summary_parts": cached["parts"],
                        "is_archived": True
                    }

        # 2. 获取消息地图：优先内存，缺失则查文件
        messages_map = {}
        if request.session_id in session_histories:
            messages_map = session_histories[request.session_id]["messages_map"].copy(
            )
            logger.info("Accessing session from memory.")

        target_id = request.intervention_id
        # 如果内存中找不到该干预点，尝试从本地文件补全（可能是旧会话或刚重启）
        if target_id not in messages_map:
            logger.info(
                f"Target {target_id} not in memory, checking discussion.json...")
            if DISCUSSION_FILE.exists():
                with open(DISCUSSION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if request.session_id in data:
                        full_history = data[request.session_id]
                        for q_key, q_data in full_history.items():
                            for m in q_data.get("messages", []):
                                if m["id"] not in messages_map:
                                    messages_map[m["id"]] = m
                        logger.info(
                            f"Updated messages_map from file. Total: {len(messages_map)}")

        if not messages_map or target_id not in messages_map:
            logger.error(
                f"Message {target_id} not found in memory or session file.")
            return {"status": "error", "detail": "Intervention message not found"}, 404

        intervention_msg = messages_map[target_id]
        parent_id = intervention_msg.get("parent_id")

        # 2. 搜集介入前的上下文
        logger.info(f"Collecting context for parent_id: {parent_id}")
        context_msgs = []
        curr = parent_id
        count = 0
        while curr and count < 10:
            m = messages_map.get(curr)
            if m:
                context_msgs.append(f"{m['agent']}: {m['content']}")
                curr = m.get("parent_id")
                count += 1
            else:
                break
        context_msgs.reverse()
        context_text = "\n".join(context_msgs)

        # 3. 搜集介入后的即时反应
        logger.info(
            f"Collecting consequences for intervention_id: {target_id}")
        consequence_msgs = []
        children = [m for m in messages_map.values() if m.get(
            "parent_id") == target_id]
        children.sort(key=lambda x: x.get("timestamp", 0))
        for c in children[:5]:
            consequence_msgs.append(f"{c['agent']}: {c['content']}")
        consequence_text = "\n".join(
            consequence_msgs) if consequence_msgs else "暂无后续讨论"

        logger.info(f"Calling LLM ({LLM_MODEL_NAME}) parallelly...")
        llm = ChatOpenAI(
            model_name=LLM_MODEL_NAME,
            openai_api_base=BASE_URL,
            openai_api_key=DASHSCOPE_API_KEY,
            temperature=0,
            timeout=60  # 设置 60s 超时防止一直挂起
        )

        async def get_part(prompt_content):
            resp = await llm.ainvoke(prompt_content)
            return resp.content

        prompt_context = f"你是一名 PBL 教育专家。请根据提供的学生讨论上下文，总结在此教师介入前的讨论状态（包含主题趋势、学生观点分布、是否存在僵局或不均等）。\n上下文：\n{context_text}\n要求：客观、简练，直接输出总结，不要包含开头。"
        prompt_action = f"你是一名 PBL 教育专家。请对以下教师的干预行为进行客观的‘形式性描述’（如：提问、复述、指出证据、点名等）。\n干预内容：\n{intervention_msg['content']}\n要求：去意图化，仅描述事实，直接输出。"
        prompt_consequence = f"你是一名 PBL 教育专家。请根据教师介入后的后续讨论，总结即时的互动变化（是否产生了新假设、讨论是否聚焦、语气变化等）。\n后续讨论：\n{consequence_text}\n要求：客观简练，直接输出。"

        # 并行执行
        results = await asyncio.gather(
            get_part(prompt_context),
            get_part(prompt_action),
            get_part(prompt_consequence)
        )

        logger.info("LLM summary generation completed successfully.")

        return {
            "status": "success",
            "summary_parts": {
                "context": results[0],
                "action": results[1],
                "consequence": results[2]
            }
        }
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/api/save-intervention-summary")
async def api_save_intervention_summary(request: SaveSummaryRequest):
    """将编辑后的总结保存回 discussion.json"""
    try:
        if not DISCUSSION_FILE.exists():
            return {"status": "error", "detail": "File not found"}, 404

        with open(DISCUSSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        session_id = request.session_id
        block_key = f"q_{request.scene_index}_{request.question_index}"

        if session_id not in data:
            data[session_id] = {}
        if block_key not in data[session_id]:
            data[session_id][block_key] = {
                "messages": [], "intervention_summaries": {}}

        if "intervention_summaries" not in data[session_id][block_key]:
            data[session_id][block_key]["intervention_summaries"] = {}

        data[session_id][block_key]["intervention_summaries"][request.intervention_id] = request.summary_data

        with open(DISCUSSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving summary: {e}")
        return {"status": "error", "detail": str(e)}, 500


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

    config = {"configurable": {"thread_id": session_id}, "recursion_limit": 60}

    # 初始化该 session 的历史记录
    if session_id not in session_histories:
        session_histories[session_id] = {
            "messages_map": {},  # id -> message_data
            "active_id": None,
            "current_branch": "main",
            # (scene, q) -> {"active_id": ..., "current_branch": ...}
            "q_states": {},
            "branches": {"main": {"parent": None, "messages": []}}
        }

    sh = session_histories[session_id]

    # 【新增】连接时自动从文件恢复历史，防止重启后内存丢失
    if not sh["messages_map"] and DISCUSSION_FILE.exists():
        try:
            with open(DISCUSSION_FILE, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                if session_id in history_data:
                    logger.info(
                        f"Restoring history for {session_id} from file...")
                    session_data = history_data[session_id]
                    for q_key, q_val in session_data.items():
                        # 格式示例 "q_0_0"
                        if not q_key.startswith("q_"):
                            continue
                        try:
                            s_idx, q_idx = q_key.split("_")[1:3]
                            s_idx, q_idx = int(s_idx), int(q_idx)
                        except:
                            continue

                        for m in q_val.get("messages", []):
                            m_id = m.get("id")
                            if m_id:
                                sh["messages_map"][m_id] = m
                    logger.info(
                        f"Restored {len(sh['messages_map'])} messages to memory.")

                    # 同步历史消息到前端
                    msgs_list = []
                    for m_id, m in sh["messages_map"].items():
                        # 去掉不可序列化的 langchain_msg
                        msgs_list.append(
                            {k: v for k, v in m.items() if k != "langchain_msg"})

                    # 【新增】搜集并连带发送已归档的干预总结
                    all_summaries = {}
                    for q_key, q_val in session_data.items():
                        if q_key.startswith("q_"):
                            block_summaries = q_val.get(
                                "intervention_summaries", {})
                            for int_id, s_data in block_summaries.items():
                                all_summaries[int_id] = s_data

                    await websocket.send_json({
                        "type": "history_sync",
                        "messages": msgs_list,
                        "intervention_summaries": all_summaries
                    })
        except Exception as e:
            logger.error(f"Failed to restore history from file: {e}")

    def update_q_state(s_idx, q_idx, active_id, branch):
        """Helper to save question-specific pointers"""
        key = f"{s_idx}_{q_idx}"
        sh["q_states"][key] = {
            "active_id": active_id,
            "current_branch": branch
        }
        # Update global pointers as well for backward compatibility in current session
        sh["active_id"] = active_id
        sh["current_branch"] = branch

    # 状态管理
    current_state = None
    graph_task = None
    output_queue = asyncio.Queue()

    async def stream_langgraph(state, s_idx, q_idx):
        """后台流式输出任务，携带当前任务的场景和问题索引"""
        current_config = {
            "configurable": {"thread_id": f"{session_id}_{s_idx}_{q_idx}_{sh.get('current_branch', 'main')}"},
            "recursion_limit": 60
        }
        logger.info(
            f"Starting stream for {s_idx}_{q_idx} with thread_id: {current_config.get('configurable').get('thread_id')}")
        try:
            async for event in graph.app.astream(state, config=current_config):
                # 将输出放入队列，附带 context 索引
                await output_queue.put((event, s_idx, q_idx))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in stream_langgraph: {e}")
            await websocket.send_json({"error": str(e)})

    async def output_processor():
        """处理输出队列的任务"""
        while True:
            try:
                item = await output_queue.get()
                if not isinstance(item, tuple):
                    # 兼容旧逻辑或错误数据
                    event = item
                    from . import pbl_info
                    s_idx, q_idx = pbl_info.active_scene_index, pbl_info.active_question_index
                else:
                    event, s_idx, q_idx = item

                for node, out in event.items():
                    # 处理消息输出
                    if "messages" in out:
                        for m in out["messages"]:
                            # 识别发言者
                            sender = getattr(m, "name", node)

                            # 分支管理：生成 ID
                            msg_id = str(uuid.uuid4())[:8]
                            parent_id = sh["active_id"]
                            branch_id = sh["current_branch"]

                            # 存储到历史
                            msg_data = {
                                "id": msg_id,
                                "parent_id": parent_id,
                                "branch_id": branch_id,
                                "agent": sender,
                                "content": m.content,
                                "langchain_msg": m,
                                "scene_index": s_idx,
                                "question_index": q_idx,
                                "is_convention": False
                            }
                            sh["messages_map"][msg_id] = msg_data

                            # 持久化到 json 文件
                            persist_discussion(session_id, sh["messages_map"])

                            # 更新特定问题的指针
                            update_q_state(s_idx, q_idx, msg_id, branch_id)

                            simplified = m.content
                            # 只有学生 Agent 的长发言才需要精简显示在 Storyline 中
                            if sender and sender not in ["case_introduction", "teacher", "host", "system"]:
                                simplified = await simplify_message(m.content)

                            await websocket.send_json({
                                "id": msg_id,
                                "parent_id": parent_id,
                                "branch_id": branch_id,
                                "node": node,
                                "agent": sender,
                                "content": m.content,
                                "summary": simplified,
                                "type": "agent_output",
                                "scene_index": s_idx,
                                "question_index": q_idx
                            })

                    # 处理主题更新
                    if "current_topic" in out:
                        # 主题更新通常发生在消息之后，我们也带上当前的 active_id
                        await websocket.send_json({
                            "id": sh["active_id"],  # 关联到最后一条消息
                            "node": node,
                            "topic": out["current_topic"],
                            "type": "topic_update"
                        })
                output_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in output_processor: {e}")

    output_task = None

    try:
        while True:
            # 主循环只负责接收消息
            data = await websocket.receive_text()
            msg = json.loads(data)
            action = msg.get("action")

            if action == "start_discussion":
                initial_case = msg.get("initial_case", "")
                scene_idx = msg.get("scene_index", 0)
                question_idx = msg.get("question_index", 0)
                block_key = f"q_{scene_idx}_{question_idx}"

                # 【重要】用户点击开始讨论，视为该情景问题下的“硬重置”
                # 1. 清除当前 block 在内存中的历史消息（保留其他情景的消息 map，或者全量清空根据需求定，这里全量清空符合大部分 PBL 重置逻辑）
                sh["messages_map"] = {}
                sh["active_id"] = None
                sh["current_branch"] = "main"
                sh["q_states"] = {}

                # 2. 从持久化文件中移除该 session 的记录，强制从新开始写入
                if DISCUSSION_FILE.exists():
                    try:
                        with open(DISCUSSION_FILE, "r", encoding="utf-8") as f:
                            disk_data = json.load(f)
                        if session_id in disk_data:
                            # 如果希望只清除当前 block：
                            # if block_key in disk_data[session_id]:
                            #     del disk_data[session_id][block_key]
                            # 如果希望清除整个 session：
                            del disk_data[session_id]

                            with open(DISCUSSION_FILE, "w", encoding="utf-8") as f:
                                json.dump(disk_data, f,
                                          ensure_ascii=False, indent=2)
                        logger.info(
                            f"Cleared existing disk records for session {session_id} upon start_discussion.")
                    except Exception as e:
                        logger.error(f"Failed to clear discussion file: {e}")

                # 同步更新全局 pbl_info
                from .pbl_info import update_pbl_info
                update_pbl_info(initial_case, [], scene_idx, question_idx)

                # 为初始消息生成 ID 并记录
                msg_id = f"init_{scene_idx}_{question_idx}_{str(uuid.uuid4())[:4]}"

                # 更新当前问题的活跃指针
                update_q_state(scene_idx, question_idx, msg_id, "main")

                init_msg = HumanMessage(
                    content=initial_case, name="case_introduction")
                sh["messages_map"][msg_id] = {
                    "id": msg_id,
                    "parent_id": None,
                    "branch_id": "main",
                    "agent": "case_introduction",
                    "content": initial_case,
                    "langchain_msg": init_msg,
                    "scene_index": scene_idx,
                    "question_index": question_idx,
                    "is_convention": False
                }

                # 持久化初始讨论状态
                persist_discussion(session_id, sh["messages_map"])

                current_state = {
                    "messages": [init_msg],
                    "summary": "",
                    "next_speaker": "router",
                    "is_teacher_interrupted": False,
                    "discussion_active": True,
                    "current_topic": "开始讨论"
                }

                # 取消旧任务
                if graph_task:
                    graph_task.cancel()
                if output_task:
                    output_task.cancel()

                # 启动新任务
                graph_task = asyncio.create_task(
                    stream_langgraph(current_state, scene_idx, question_idx))
                output_task = asyncio.create_task(output_processor())

            elif action == "switch_context":
                s_idx = msg.get("scene_index", 0)
                q_idx = msg.get("question_index", 0)
                q_key = f"{s_idx}_{q_idx}"
                if q_key in sh.get("q_states", {}):
                    state = sh["q_states"][q_key]
                    sh["active_id"] = state["active_id"]
                    sh["current_branch"] = state["current_branch"]
                    logger.info(
                        f"Context switched to {q_key}: active_id={sh['active_id']}, branch={sh['current_branch']}")
                else:
                    logger.info(
                        f"Context switched to new question {q_key}, pointers not yet initialized")

            elif action == "rollback_to":
                target_id = msg.get("target_id")
                if target_id in sh["messages_map"]:
                    logger.info(f"Rolling back to message: {target_id}")

                    target_branch = sh["messages_map"][target_id].get(
                        "branch_id", "main")
                    from . import pbl_info
                    update_q_state(pbl_info.active_scene_index,
                                   pbl_info.active_question_index, target_id, target_branch)

                    logger.info(
                        f"Context switched to branch: {sh['current_branch']}")

                    # 停止当前讨论
                    if graph_task:
                        graph_task.cancel()
                    if output_task:
                        output_task.cancel()

                    await websocket.send_json({"type": "rollback_ack", "target_id": target_id})

            elif action == "teacher_intervention":
                teacher_content = msg.get("content", "")
                # 优先使用前端传入的 parent_id，实现点击节点后分支
                target_parent_id = msg.get("parent_id")
                from . import pbl_info
                if target_parent_id and target_parent_id in sh["messages_map"]:
                    target_branch = sh["messages_map"][target_parent_id].get(
                        "branch_id", "main")
                    update_q_state(pbl_info.active_scene_index,
                                   pbl_info.active_question_index, target_parent_id, target_branch)
                    logger.info(
                        f"Teacher intervention branching from focus: {target_parent_id} on branch: {sh['current_branch']}")

                # 分支判断：如果当前 active_id 已经有子节点，说明是在开辟新分支
                has_children = any(m["parent_id"] == sh["active_id"]
                                   for m in sh["messages_map"].values())
                if has_children:
                    new_branch_name = f"branch_{str(uuid.uuid4())[:4]}"
                    update_q_state(pbl_info.active_scene_index,
                                   pbl_info.active_question_index, sh["active_id"], new_branch_name)
                    logger.info(f"Switching to new branch: {new_branch_name}")

                # 构建回退后的消息列表
                chain = []
                curr_ptr = sh["active_id"]
                while curr_ptr:
                    m_data = sh["messages_map"][curr_ptr]
                    chain.append(m_data["langchain_msg"])
                    curr_ptr = m_data["parent_id"]
                chain.reverse()

                teacher_msg = HumanMessage(
                    content=teacher_content, name="teacher")

                # zyc新增：记录教师干预消息到历史图谱中
                from . import pbl_info
                teacher_msg_id = f"teacher_{str(uuid.uuid4())[:6]}"
                teacher_msg_data = {
                    "id": teacher_msg_id,
                    "parent_id": sh["active_id"],
                    "branch_id": sh["current_branch"],
                    "agent": "teacher",
                    "content": teacher_content,
                    "summary": teacher_content[:30],
                    "langchain_msg": teacher_msg,
                    "topic": "教师干预",
                    "scene_index": pbl_info.active_scene_index,
                    "question_index": pbl_info.active_question_index,
                    "is_convention": True
                }
                sh["messages_map"][teacher_msg_id] = teacher_msg_data

                # 持久化教师干预后的状态
                persist_discussion(session_id, sh["messages_map"])

                update_q_state(pbl_info.active_scene_index,
                               pbl_info.active_question_index, teacher_msg_id, sh["current_branch"])

                # 发送教师消息回显到前端，增加 type 和 node 以便前端直接识别为图节点
                await websocket.send_json({
                    "type": "agent_output",
                    "id": teacher_msg_id,
                    "parent_id": teacher_msg_data["parent_id"],
                    "branch_id": teacher_msg_data["branch_id"],
                    "agent": "teacher",
                    "node": "teacher",
                    "content": teacher_content,
                    "summary": teacher_content[:30],
                    "topic": "教师干预",
                    "scene_index": pbl_info.active_scene_index,
                    "question_index": pbl_info.active_question_index
                })

                # 准备更新 Payload
                update_payload = {
                    "messages": chain + [teacher_msg],  # 传入完整链条以重置状态
                    "is_teacher_interrupted": False,    # 设为 False 以跳过主持人干预回复，直接让学生讨论
                    "next_speaker": "router",           # 直接去路由
                    "discussion_active": True,
                    "current_topic": None               # 强制重置主题识别，由 topic_manager 重新生成
                }

                # 取消旧任务并重新启动讨论流
                # 这里的 stream_langgraph 现在由于我们之前的修改，会使用包含 branch_id 的新 thread_id
                if graph_task:
                    graph_task.cancel()
                if output_task:
                    output_task.cancel()

                logger.info(
                    f"Restarting graph with new branch: {sh['current_branch']}")
                graph_task = asyncio.create_task(
                    stream_langgraph(update_payload, pbl_info.active_scene_index, pbl_info.active_question_index))
                output_task = asyncio.create_task(output_processor())

                await websocket.send_json({
                    "type": "teacher_intervention_ack",
                    "content": teacher_content,
                    "topic": None
                })

            elif action == "pause_discussion":
                logger.info("教师指令：暂停讨论。")
                if graph_task:
                    graph_task.cancel()
                if output_task:
                    output_task.cancel()

                # 尽量清空输出队列，实现“憋回去”
                while not output_queue.empty():
                    try:
                        output_queue.get_nowait()
                        output_queue.task_done()
                    except asyncio.QueueEmpty:
                        break

                await websocket.send_json({"type": "discussion_paused"})

            elif action == "resume_discussion":
                logger.info("教师指令：恢复讨论。")
                if graph_task:
                    graph_task.cancel()
                if output_task:
                    output_task.cancel()

                # 恢复时传入 None，astream 会自动从 checkpoint 恢复
                from . import pbl_info
                graph_task = asyncio.create_task(stream_langgraph(
                    None, pbl_info.active_scene_index, pbl_info.active_question_index))
                output_task = asyncio.create_task(output_processor())
                await websocket.send_json({"type": "discussion_resumed"})

    except WebSocketDisconnect:
        # 清理资源
        if graph_task:
            graph_task.cancel()
        if output_task:
            output_task.cancel()

if __name__ == "__main__":
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000)
