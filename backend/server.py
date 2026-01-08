"""PBL.backend.server
最终修复版：
1. 包含所有必要的 API 路由 (/api/pdf-images/, /api/parse-case/ 等)。
2. 静态资源挂载。
3. WebSocket 支持。
"""
import asyncio
import uvicorn
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List

from langchain_core.messages import HumanMessage
from .graph import app, GraphState
from .agents import student_personas
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


app_fastapi = FastAPI()

# --- 目录配置 ---
BASE_DIR = Path(__file__).parent
PDF_STORAGE_DIR = BASE_DIR / "pdfs"
PDF_STORAGE_DIR.mkdir(exist_ok=True)

CASE_STORAGE_DIR = BASE_DIR / "case"
CASE_STORAGE_DIR.mkdir(exist_ok=True)

CASES_DATA_DIR = BASE_DIR / "cases_img"
CASES_DATA_DIR.mkdir(exist_ok=True)

# 挂载静态资源
app_fastapi.mount(
    "/static/cases", StaticFiles(directory=CASES_DATA_DIR), name="cases_img")

app_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
async def update_personas(request: UpdatePersonasRequest):
    new_personas = request.dict()
    for agent_id, persona_data in new_personas.items():
        if agent_id in student_personas:
            student_personas[agent_id] = persona_data
    return {"status": "success"}


@app_fastapi.websocket("/ws/pbl/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    config = {"configurable": {"thread_id": session_id}}
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")

            if action == "start_discussion":
                initial_case = message.get("initial_case", "")
                initial_message = HumanMessage(
                    content=initial_case, name="case_introduction")
                initial_state: GraphState = {
                    "messages": [initial_message],
                    "discussion_stage": "初步诊断与鉴别诊断",
                    "summary": "",
                    "next_speaker": "router",
                    "is_teacher_interrupted": False,
                }
                async for event in app.astream(initial_state, config=config):
                    for node_name, output in event.items():
                        if "messages" in output and output['messages']:
                            for msg in output['messages']:
                                if hasattr(msg, 'content'):
                                    await websocket.send_json({"node": node_name, "content": msg.content})

            elif action == "teacher_intervention":
                teacher_content = message.get("content", "")
                teacher_message = HumanMessage(
                    content=teacher_content, role="teacher")
                await app.update_state(config, {"messages": [teacher_message], "is_teacher_interrupted": True})
                async for event in app.astream(None, config=config):
                    for node_name, output in event.items():
                        if "messages" in output and output['messages']:
                            for msg in output['messages']:
                                if hasattr(msg, 'content'):
                                    await websocket.send_json({"node": node_name, "content": msg.content})
    except Exception:
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000)
