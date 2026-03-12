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
import copy
from contextlib import suppress
from typing import Any, Dict, Optional, Union, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
import asyncio
import re
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from .config import BASE_URL, DASHSCOPE_API_KEY, LLM_MODEL_NAME

# 动态 Agent 注册与图构建相关
from . import graph  # 导入 graph 模块以访问和修改 app
from .agents import (
    register_student_agent,
    student_nodes,
    student_personas,
    simplify_message,
    generate_learning_personality_sections,
)
from .agent_preview import generate_student_preview_response
from .graph_builder import build_graph, GraphState
from .graph import app, GraphState
# 导入解析函数
from .pdf_parser import parse_pbl_to_json, get_raw_pdf_images
from .schema import PBLCaseStructure
from .knowledge import (
    normalize_knowledge_points as _normalize_knowledge_points_impl,
    next_kp_id as _next_kp_id_impl,
    ensure_question_knowledge_points as _ensure_question_knowledge_points_impl,
    collect_case_question_knowledge_points as _collect_case_question_knowledge_points_impl,
    sync_agent_setting_knowledge_points as _sync_agent_setting_knowledge_points_impl,
    evaluate_progressive_coverage,
    build_discussion_content_from_leaf,
    get_historical_scores_from_leaf,
)

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
    personas: Dict[str, Any]


class AgentTagsRequest(BaseModel):
    agent_id: str
    persona: Dict[str, Any]
    trigger_question: str


class ActiveSceneRequest(BaseModel):
    story: str
    trigger_questions: List[str]
    scene_index: int = 0
    question_index: int = 0
    case_name: str = ""
    current_learning_objectives: List[str] = []


class InterventionSummaryRequest(BaseModel):
    session_id: str
    intervention_id: str
    scene_index: int
    question_index: int


class InterventionStrategyRequest(BaseModel):
    session_id: str
    last_message_id: str
    scene_index: int
    question_index: int


class SaveSummaryRequest(BaseModel):
    session_id: str
    scene_index: int
    question_index: int
    intervention_id: str
    summary_data: dict


class UpdateKnowledgeRequest(BaseModel):
    pdf_filename: str
    old_name: str
    new_name: str


class AddKnowledgeRequest(BaseModel):
    pdf_filename: str
    knowledge_point: str


class DeleteKnowledgeRequest(BaseModel):
    pdf_filename: str
    knowledge_point: str


class DeleteQuestionRequest(BaseModel):
    caseName: str
    sceneIndex: int
    questionIndex: int


class AddQuestionRequest(BaseModel):
    caseName: str
    sceneIndex: int
    questionText: str


class AddObjectiveRequest(BaseModel):
    caseName: str
    sceneIndex: int
    questionIndex: int
    objectiveText: str


class UpdateObjectiveRequest(BaseModel):
    caseName: str
    sceneIndex: int
    questionIndex: int
    objectiveIndex: int
    objectiveText: str


class OverrideObjectiveRequest(BaseModel):
    caseName: str
    sceneIndex: int
    questionIndex: int
    objectiveIndex: int
    # 【修改】支持新的override值：
    # None = clear override (automatic evaluation)
    # 'in_progress' = manually set to In Progress
    # 'achieved' = manually set to Achieved
    override: Optional[Union[str, bool]] = None


class AgentPreviewRequest(BaseModel):
    agent_id: str
    persona: Dict
    trigger_question: str


class ConfigLearningStyles(BaseModel):
    surface: Optional[int] = None
    deep: Optional[int] = None
    strategic: Optional[int] = None


class ConfigPersonality(BaseModel):
    openness: Optional[int] = None
    conscientiousness: Optional[int] = None
    extraversion: Optional[int] = None
    agreeableness: Optional[int] = None
    neuroticism: Optional[int] = None


class ConfigKnowledgeBackground(BaseModel):
    high: Optional[List[str]] = None
    medium: Optional[List[str]] = None
    low: Optional[List[str]] = None


class AgentConfigParseResult(BaseModel):
    name: Optional[str] = None
    age: Optional[str] = None
    major: Optional[str] = None
    learning_styles: Optional[ConfigLearningStyles] = None
    personality: Optional[ConfigPersonality] = None
    knowledge_background: Optional[ConfigKnowledgeBackground] = None
    cognitive_orientation: Optional[str] = None
    plasticity: Optional[str] = None


class AgentConfigChatRequest(BaseModel):
    instruction: str
    current_config: Dict[str, Any] = Field(default_factory=dict)
    chat_history: List[Dict[str, str]] = Field(default_factory=list)


class KnowledgeCoverageRequest(BaseModel):
    case_name: str
    scene_index: int
    question_index: int
    discussion_content: str


class QuestionKnowledgePointAddRequest(BaseModel):
    caseName: str
    sceneIndex: int
    questionIndex: int
    point: str
    explanation: str = ""


class QuestionKnowledgePointUpdateRequest(BaseModel):
    caseName: str
    sceneIndex: int
    questionIndex: int
    pointId: str
    point: str
    explanation: str = ""


class QuestionKnowledgePointDeleteRequest(BaseModel):
    caseName: str
    sceneIndex: int
    questionIndex: int
    pointId: str


class KnowledgeCoverageResponse(BaseModel):
    status: str
    total_points: int = 0
    covered_points: List[str] = []
    coverage_ratio: float = 0.0
    covered_point_details: List[Dict[str, str]] = []


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


def _collect_all_knowledge_points(current_cfg: Dict[str, Any]) -> List[str]:
    points: List[str] = []

    def append_unique(items: Any):
        if not isinstance(items, list):
            return
        for item in items:
            point = str(item or "").strip()
            if point and point not in points:
                points.append(point)

    kb = current_cfg.get("knowledge_background", {}) if isinstance(
        current_cfg, dict) else {}
    append_unique(current_cfg.get("all_knowledge_points", []))
    if isinstance(kb, dict):
        append_unique(kb.get("high", []))
        append_unique(kb.get("medium", []))
        append_unique(kb.get("low", []))

    return points


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


def resolve_case_json_path(case_name: str) -> Optional[Path]:
    """Resolve case JSON path by filename first, then by case_title fallback."""
    if not case_name:
        return None

    # 1) Direct filename match: /case/{case_name}.json
    direct = CASE_STORAGE_DIR / f"{case_name}.json"
    if direct.exists():
        return direct

    def _knowledge_point_count(case_data: Dict[str, Any]) -> int:
        count = 0
        scenes = case_data.get("scenes") or []
        if not isinstance(scenes, list):
            return 0
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            questions = scene.get("trigger_questions") or []
            if not isinstance(questions, list):
                continue
            for q in questions:
                if not isinstance(q, dict):
                    continue
                points = q.get("knowledge_points") or []
                if isinstance(points, list):
                    count += len(points)
        return count

    # 2) Title match in JSON content (handles filename/title mismatch).
    # If there are multiple candidates with the same title, prefer richer case files
    # that contain per-question knowledge points.
    target = case_name.strip()
    candidates: List[tuple] = []
    for f in CASE_STORAGE_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            if str(data.get("case_title", "")).strip() == target:
                kp_count = _knowledge_point_count(data)
                scene_count = len(data.get("scenes") or [])
                stem_exact = 1 if f.stem.strip() == target else 0
                candidates.append(
                    (stem_exact, kp_count, scene_count, int(f.stat().st_mtime), f)
                )
        except Exception:
            continue

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][4]

    return None


def resolve_objectives_from_case(case_name: str, scene_idx: int, question_idx: int) -> List[str]:
    """Read canonical per-question learning objectives directly from case JSON."""
    path = resolve_case_json_path(case_name)
    if not path:
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        scenes = case_data.get("scenes") or []
        if scene_idx < 0 or scene_idx >= len(scenes):
            return []

        rows = scenes[scene_idx].get(
            "trigger_question_learning_objectives") or []
        if question_idx < 0 or question_idx >= len(rows):
            return []

        objectives = rows[question_idx].get("learning_objectives") or []
        return [str(o).strip() for o in objectives if str(o).strip()]
    except Exception as e:
        logger.error(
            f"读取案例目标失败: case={case_name}, scene={scene_idx}, question={question_idx}, error={e}")
        return []


def resolve_objective_overrides_from_case(case_name: str, scene_idx: int, question_idx: int) -> Dict[str, bool]:
    """Read persisted teacher objective overrides for current question from case JSON."""
    path = resolve_case_json_path(case_name)
    if not path:
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        scenes = case_data.get("scenes") or []
        if scene_idx < 0 or scene_idx >= len(scenes):
            return {}

        rows = scenes[scene_idx].get(
            "trigger_question_learning_objectives") or []
        if question_idx < 0 or question_idx >= len(rows):
            return {}

        raw = rows[question_idx].get("objective_overrides") or {}
        if not isinstance(raw, dict):
            return {}

        normalized: Dict[str, bool] = {}
        for k, v in raw.items():
            key = str(k or "").strip()
            if not key:
                continue
            if v is True or v is False:
                normalized[key] = bool(v)
        return normalized
    except Exception as e:
        logger.error(
            f"读取案例目标覆盖失败: case={case_name}, scene={scene_idx}, question={question_idx}, error={e}")
        return {}


def _sync_runtime_objectives_if_active(case_name: str, scene_idx: int, question_idx: int) -> None:
    """If editing active question objectives, refresh runtime pbl_info immediately."""
    try:
        from . import pbl_info as pbl_state
        from .pbl_info import update_pbl_info

        active_case = str(
            getattr(pbl_state, "current_case_name", "") or "").strip()
        if not active_case or active_case != str(case_name or "").strip():
            return
        if int(getattr(pbl_state, "active_scene_index", -1) or -1) != int(scene_idx):
            return
        if int(getattr(pbl_state, "active_question_index", -1) or -1) != int(question_idx):
            return

        refreshed = resolve_objectives_from_case(
            case_name, scene_idx, question_idx)
        update_pbl_info(
            story=pbl_state.pbl_story,
            questions=pbl_state.pbl_triger_questions or (
                [pbl_state.current_trigger_question] if pbl_state.current_trigger_question else []),
            scene_idx=scene_idx,
            q_idx=question_idx,
            learning_objectives=refreshed,
            case_name=active_case,
        )
        rt_key = f"{scene_idx}_{question_idx}"
        # 【修改】刷新后不加载缓存的override，始终以干净状态开始
        # pbl_state.objective_overrides[rt_key] = resolve_objective_overrides_from_case(...)
        pbl_state.objective_overrides[rt_key] = {}
    except Exception as e:
        logger.warning("sync runtime objectives failed: %s", e)


def _normalize_knowledge_points(raw_points: Any) -> List[Dict[str, str]]:
    return _normalize_knowledge_points_impl(raw_points)


def _next_kp_id(points: List[Dict[str, str]]) -> str:
    return _next_kp_id_impl(points)


def _load_case_data_by_name(case_name: str) -> tuple[Optional[Path], Optional[Dict[str, Any]], Optional[dict]]:
    path = resolve_case_json_path(case_name)
    if not path:
        return None, None, ({"status": "error", "detail": f"案例文件不存在: {case_name}"}, 404)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return path, data, None
    except Exception as e:
        return None, None, ({"status": "error", "detail": f"读取案例失败: {e}"}, 500)


def _ensure_question_knowledge_points(case_data: Dict[str, Any], scene_idx: int, question_idx: int) -> tuple[Optional[List[Dict[str, str]]], Optional[str]]:
    return _ensure_question_knowledge_points_impl(case_data, scene_idx, question_idx)


def _collect_case_question_knowledge_points(case_data: Dict[str, Any]) -> List[str]:
    return _collect_case_question_knowledge_points_impl(case_data)


def _sync_agent_setting_knowledge_points(case_data: Dict[str, Any]) -> None:
    _sync_agent_setting_knowledge_points_impl(case_data, AGENT_SETTING_PATH)

# --- API 路由 ---


@app_fastapi.on_event("startup")
async def startup_event():
    """服务器启动时，从配置文件加载 Agents 并构建图。"""
    print("Initializing agents from agent_setting.json...")
    logger.info("Starting agent initialization...")

    def _default_persona() -> Dict[str, Any]:
        return {
            "name": "Student_1",
            "age": "",
            "major": "",
            "learning_styles": {"surface": 3, "deep": 3, "strategic": 3},
            "personality": {
                "openness": 3,
                "conscientiousness": 3,
                "extraversion": 3,
                "agreeableness": 3,
                "neuroticism": 3,
            },
            "knowledge_background": {"high": [], "medium": [], "low": []},
            "cognitive_orientation": "line_based",
            "learning_adaptivity": "medium",
        }

    try:
        personas: Dict[str, Dict] = {}
        if AGENT_SETTING_PATH.exists():
            with open(AGENT_SETTING_PATH, 'r', encoding='utf-8') as f:
                raw = f.read()

            # Startup steady-state handling: empty/invalid JSON should not fail startup.
            if not raw.strip():
                logger.warning(
                    "agent_setting.json is empty during startup, using fallback persona.")
                personas = {"Student_1": _default_persona()}
            else:
                try:
                    loaded = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning(
                        "agent_setting.json is invalid JSON during startup, using fallback persona.")
                    loaded = {}
                personas = loaded if isinstance(loaded, dict) and loaded else {
                    "Student_1": _default_persona()}
        else:
            logger.warning(
                f"agent_setting.json not found at {AGENT_SETTING_PATH}, using fallback persona.")
            personas = {"Student_1": _default_persona()}

        async def enrich_persona(agent_id: str, persona_data: Dict):
            enriched = dict(persona_data or {})
            generated_sections = await generate_learning_personality_sections(enriched)
            enriched.update(generated_sections)
            return agent_id, enriched

        if personas:
            try:
                enriched_pairs = await asyncio.gather(
                    *(enrich_persona(agent_id, persona_data) for agent_id, persona_data in personas.items())
                )
                personas = {agent_id: persona for agent_id,
                            persona in enriched_pairs}
            except Exception as enrich_error:
                # Keep startup resilient when LLM enrichment is unavailable.
                logger.warning(
                    f"Startup persona enrichment failed, fallback to raw personas: {enrich_error}")

        if not personas:
            personas = {"Student_1": _default_persona()}

        with open(AGENT_SETTING_PATH, 'w', encoding='utf-8') as f:
            json.dump(personas, f, ensure_ascii=False, indent=2)

        for agent_id, persona in personas.items():
            register_student_agent(agent_id, persona)

        agent_ids = list(student_nodes.keys())
        if not agent_ids:
            logger.warning(
                "No agents found in agent_setting.json after loading")
            print("⚠ Warning: No agents found to build graph")
            return

        graph.app = build_graph(agent_ids)
        logger.info(f"✓ Graph successfully built with agents: {agent_ids}")
        print(f"✓ Startup: Graph built with agents: {agent_ids}")
    except Exception as e:
        logger.error(
            f"✗ Startup: Error loading agents: {type(e).__name__}: {e}", exc_info=True)
        print(f"✗ Startup: Error loading agents: {type(e).__name__}: {e}")

        # Last-resort fallback to prevent WebSocket graph.app=None failures.
        try:
            student_personas.clear()
            student_nodes.clear()
            register_student_agent("Student_1", _default_persona())
            graph.app = build_graph(list(student_nodes.keys()))
            logger.warning(
                "Startup fallback graph initialized with default Student_1 persona.")
        except Exception as fallback_error:
            logger.error(
                f"Startup fallback graph initialization failed: {fallback_error}", exc_info=True)


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


@app_fastapi.get("/api/case-images/{case_name}")
def api_get_case_images(case_name: str):
    """获取案例文件夹中实际存在的图片列表"""
    case_img_dir = CASES_DATA_DIR / case_name / "img"
    if not case_img_dir.exists():
        return {"images": []}

    try:
        # 获取所有图片文件
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        existing_images = []

        for file_path in sorted(case_img_dir.iterdir()):
            if file_path.suffix.lower() in image_extensions:
                existing_images.append(file_path.name)

        return {"images": existing_images}
    except Exception as e:
        logger.error(f"获取案例图片列表失败: {e}")
        return {"detail": str(e)}, 500


@app_fastapi.post("/api/set-active-scene")
async def set_active_scene(request: ActiveSceneRequest):
    from .pbl_info import update_pbl_info

    # Prefer backend canonical objectives from case JSON to avoid stale frontend cache.
    resolved_objectives = resolve_objectives_from_case(
        case_name=request.case_name,
        scene_idx=request.scene_index,
        question_idx=request.question_index,
    )
    effective_objectives = resolved_objectives or request.current_learning_objectives

    update_pbl_info(
        story=request.story,
        questions=request.trigger_questions,
        scene_idx=request.scene_index,
        q_idx=request.question_index,
        learning_objectives=effective_objectives,
        case_name=request.case_name,
    )
    from . import pbl_info as pbl_state
    rt_key = f"{request.scene_index}_{request.question_index}"
    # 【修改】刷新后不加载缓存的override，始终以干净状态开始
    pbl_state.objective_overrides[rt_key] = {}
    return {
        "status": "success",
        "message": "Global PBL info updated.",
        "objectives_source": "case_json" if resolved_objectives else "request_payload",
        "objectives_count": len(effective_objectives),
    }


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

        # 同步更新对应的问题学习目标映射（若存在）
        per_q_objectives = scene.get(
            "trigger_question_learning_objectives", [])
        if isinstance(per_q_objectives, list) and question_idx < len(per_q_objectives):
            if isinstance(per_q_objectives[question_idx], dict):
                per_q_objectives[question_idx]["trigger_question"] = new_question

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


@app_fastapi.post("/api/delete-question")
async def api_delete_question(request: DeleteQuestionRequest):
    """从案例 JSON 中删除某个场景下的一条问题"""
    try:
        case_name = request.caseName
        scene_idx = request.sceneIndex
        question_idx = request.questionIndex

        # 改进：先尝试直接查找，失败则模糊匹配
        json_path = CASE_STORAGE_DIR / f"{case_name}.json"

        if not json_path.exists():
            # 模糊匹配
            matching_files = list(CASE_STORAGE_DIR.glob("*.json"))
            json_path = None
            for f in matching_files:
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        if data.get("case_title") == case_name:
                            json_path = f
                            break
                except Exception:
                    continue

            if not json_path:
                return {"status": "error", "detail": f"案例文件不存在: {case_name}"}, 404

        # 读取JSON文件
        with open(json_path, 'r', encoding='utf-8') as f:
            case_data = json.load(f)

        if scene_idx >= len(case_data.get("scenes", [])):
            return {"status": "error", "detail": f"场景索引越界: {scene_idx}"}, 400

        scene = case_data["scenes"][scene_idx]
        if question_idx >= len(scene.get("trigger_questions", [])):
            return {"status": "error", "detail": f"问题索引越界: {question_idx}"}, 400

        # 删除问题
        scene["trigger_questions"].pop(question_idx)

        # 同步删除对应的问题学习目标映射（若存在）
        per_q_objectives = scene.get(
            "trigger_question_learning_objectives", [])
        if isinstance(per_q_objectives, list) and question_idx < len(per_q_objectives):
            per_q_objectives.pop(question_idx)

        # 保存回JSON文件
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

        return {"status": "success", "message": "问题已删除"}

    except Exception as e:
        logger.error(f"删除问题失败: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/api/add-question")
async def api_add_question(request: AddQuestionRequest):
    """向某个场景添加一条引导问题"""
    try:
        case_name = request.caseName
        scene_idx = request.sceneIndex
        question_text = request.questionText

        json_path = CASE_STORAGE_DIR / f"{case_name}.json"

        if not json_path.exists():
            # 模糊匹配
            matching_files = list(CASE_STORAGE_DIR.glob("*.json"))
            json_path = None
            for f in matching_files:
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        if data.get("case_title", "").strip() == case_name.strip():
                            json_path = f
                            break
                except Exception:
                    continue

            if not json_path:
                return {"status": "error", "detail": f"案例文件不存在: {case_name}"}, 404

        with open(json_path, 'r', encoding='utf-8') as f:
            case_data = json.load(f)

        if scene_idx >= len(case_data.get("scenes", [])):
            return {"status": "error", "detail": "场景索引越界"}, 400

        scene = case_data["scenes"][scene_idx]
        if "trigger_questions" not in scene:
            scene["trigger_questions"] = []
        if "trigger_question_learning_objectives" not in scene:
            scene["trigger_question_learning_objectives"] = []

        # 添加新问题
        scene["trigger_questions"].append({"question": question_text})
        scene["trigger_question_learning_objectives"].append(
            {"trigger_question": question_text, "learning_objectives": []}
        )

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

        return {"status": "success", "message": "问题已添加"}

    except Exception as e:
        logger.error(f"添加问题失败: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/api/add-objective")
async def api_add_objective(request: AddObjectiveRequest):
    """向当前场景的当前 trigger question 添加一条学习目标。"""
    try:
        case_name = request.caseName
        scene_idx = request.sceneIndex
        question_idx = request.questionIndex
        objective_text = request.objectiveText.strip()

        if not objective_text:
            return {"status": "error", "detail": "objectiveText 不能为空"}, 400

        json_path = CASE_STORAGE_DIR / f"{case_name}.json"
        if not json_path.exists():
            matching_files = list(CASE_STORAGE_DIR.glob("*.json"))
            json_path = None
            for f in matching_files:
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        if data.get("case_title", "").strip() == case_name.strip():
                            json_path = f
                            break
                except Exception:
                    continue

            if not json_path:
                return {"status": "error", "detail": f"案例文件不存在: {case_name}"}, 404

        with open(json_path, 'r', encoding='utf-8') as f:
            case_data = json.load(f)

        scenes = case_data.get("scenes", [])
        if scene_idx >= len(scenes):
            return {"status": "error", "detail": "场景索引越界"}, 400

        scene = scenes[scene_idx]
        questions = scene.get("trigger_questions", [])
        if question_idx >= len(questions):
            return {"status": "error", "detail": "问题索引越界"}, 400

        q_text = str(questions[question_idx].get("question", "") or "").strip()

        if "trigger_question_learning_objectives" not in scene or not isinstance(scene.get("trigger_question_learning_objectives"), list):
            scene["trigger_question_learning_objectives"] = []

        rows = scene["trigger_question_learning_objectives"]
        while len(rows) <= question_idx:
            rows.append({"trigger_question": "", "learning_objectives": []})

        row = rows[question_idx]
        if not isinstance(row, dict):
            row = {"trigger_question": "", "learning_objectives": []}
            rows[question_idx] = row

        row["trigger_question"] = q_text
        if "learning_objectives" not in row or not isinstance(row.get("learning_objectives"), list):
            row["learning_objectives"] = []

        if objective_text not in row["learning_objectives"]:
            row["learning_objectives"].append(objective_text)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

        _sync_runtime_objectives_if_active(case_name, scene_idx, question_idx)

        return {"status": "success", "message": "objective 已添加"}
    except Exception as e:
        logger.error(f"添加 objective 失败: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/api/update-objective")
async def api_update_objective(request: UpdateObjectiveRequest):
    """编辑当前场景当前问题下的一条学习目标。"""
    try:
        case_name = request.caseName
        scene_idx = request.sceneIndex
        question_idx = request.questionIndex
        objective_idx = request.objectiveIndex
        objective_text = request.objectiveText.strip()

        if not objective_text:
            return {"status": "error", "detail": "objectiveText 不能为空"}, 400

        json_path = CASE_STORAGE_DIR / f"{case_name}.json"
        if not json_path.exists():
            matching_files = list(CASE_STORAGE_DIR.glob("*.json"))
            json_path = None
            for f in matching_files:
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        if data.get("case_title", "").strip() == case_name.strip():
                            json_path = f
                            break
                except Exception:
                    continue
            if not json_path:
                return {"status": "error", "detail": f"案例文件不存在: {case_name}"}, 404

        with open(json_path, 'r', encoding='utf-8') as f:
            case_data = json.load(f)

        scenes = case_data.get("scenes", [])
        if scene_idx >= len(scenes):
            return {"status": "error", "detail": "场景索引越界"}, 400

        scene = scenes[scene_idx]
        questions = scene.get("trigger_questions", [])
        if question_idx >= len(questions):
            return {"status": "error", "detail": "问题索引越界"}, 400

        q_text = str(questions[question_idx].get("question", "") or "").strip()
        rows = scene.get("trigger_question_learning_objectives")
        if not isinstance(rows, list):
            rows = []
            scene["trigger_question_learning_objectives"] = rows

        while len(rows) <= question_idx:
            rows.append({"trigger_question": "", "learning_objectives": []})

        row = rows[question_idx]
        if not isinstance(row, dict):
            row = {"trigger_question": "", "learning_objectives": []}
            rows[question_idx] = row

        row["trigger_question"] = q_text
        if not isinstance(row.get("learning_objectives"), list):
            row["learning_objectives"] = []

        if objective_idx < 0 or objective_idx >= len(row["learning_objectives"]):
            return {"status": "error", "detail": "objectiveIndex 越界"}, 400

        row["learning_objectives"][objective_idx] = objective_text

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

        _sync_runtime_objectives_if_active(case_name, scene_idx, question_idx)

        return {"status": "success", "message": "objective 已更新"}
    except Exception as e:
        logger.error(f"更新 objective 失败: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/api/override-objective")
async def api_override_objective(request: OverrideObjectiveRequest):
    """【修改】教师手动覆盖某条学习目标的达成状态。

    override 可以是：
    - None: 清除覆盖，使用自动评估
    - 'in_progress': 手动设置为进行中
    - 'achieved': 手动设置为完成
    - 布尔值（向后兼容）：true=achieved, false=not_achieved
    """
    try:
        json_path, case_data, err = _load_case_data_by_name(request.caseName)
        if err:
            return err

        scene_idx = request.sceneIndex
        question_idx = request.questionIndex
        objective_idx = request.objectiveIndex

        scenes = case_data.get("scenes", [])
        if scene_idx >= len(scenes):
            return {"status": "error", "detail": "场景索引越界"}, 400

        scene = scenes[scene_idx]
        rows = scene.setdefault("trigger_question_learning_objectives", [])
        while len(rows) <= question_idx:
            rows.append({"trigger_question": "",
                        "learning_objectives": [], "objective_overrides": {}})

        row = rows[question_idx]
        if not isinstance(row, dict):
            row = {"trigger_question": "",
                   "learning_objectives": [], "objective_overrides": {}}
            rows[question_idx] = row

        objectives = row.get("learning_objectives", [])
        if objective_idx < 0 or objective_idx >= len(objectives):
            return {"status": "error", "detail": "objectiveIndex 越界"}, 400

        obj_text = str(objectives[objective_idx])
        if not isinstance(row.get("objective_overrides"), dict):
            row["objective_overrides"] = {}

        # 【修改】处理新的override值类型
        if request.override is None:
            # 清除覆盖
            row["objective_overrides"].pop(obj_text, None)
            override_value = None
        elif isinstance(request.override, str):
            # 字符串值：'in_progress' 或 'achieved'
            if request.override in ('in_progress', 'achieved'):
                row["objective_overrides"][obj_text] = request.override
                override_value = request.override
            else:
                return {"status": "error", "detail": f"Invalid override value: {request.override}"}, 400
        else:
            # 布尔值（向后兼容）
            row["objective_overrides"][obj_text] = bool(request.override)
            override_value = bool(request.override)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

        # 同步到运行时覆盖表，供 router_node 实时读取
        from . import pbl_info as _pbl_info_mod
        rt_key = f"{scene_idx}_{question_idx}"
        if not isinstance(_pbl_info_mod.objective_overrides.get(rt_key), dict):
            _pbl_info_mod.objective_overrides[rt_key] = {}
        if request.override is None:
            _pbl_info_mod.objective_overrides[rt_key].pop(obj_text, None)
        else:
            _pbl_info_mod.objective_overrides[rt_key][obj_text] = override_value

        print(
            f"DEBUG: [Override API] Updated: rt_key={rt_key} obj_text={obj_text} to {override_value}")
        print(
            f"DEBUG: [Override API] Current overrides for {rt_key}: {_pbl_info_mod.objective_overrides[rt_key]}")

        return {"status": "success", "override": override_value}
    except Exception as e:
        logger.error(f"override-objective 失败: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.get("/api/question-knowledge-points")
async def api_get_question_knowledge_points(case_name: str, scene_index: int, question_index: int):
    """返回 ViewE 使用的当前问题知识点列表（统一来源）。"""
    path, case_data, err = _load_case_data_by_name(case_name)
    if err:
        return err

    points, msg = _ensure_question_knowledge_points(
        case_data, scene_index, question_index)
    if msg:
        return {"status": "error", "detail": msg}, 400

    return {
        "status": "success",
        "knowledge_points": points,
        "total": len(points or []),
        "case_path": str(path) if path else "",
    }


@app_fastapi.post("/api/question-knowledge-points/add")
async def api_add_question_knowledge_point(request: QuestionKnowledgePointAddRequest):
    """在 ViewE 的问题知识点列表中新增知识点，并同步 agent_setting.json。"""
    path, case_data, err = _load_case_data_by_name(request.caseName)
    if err:
        return err

    points, msg = _ensure_question_knowledge_points(
        case_data, request.sceneIndex, request.questionIndex)
    if msg:
        return {"status": "error", "detail": msg}, 400

    point = str(request.point or "").strip()
    explanation = str(request.explanation or "").strip()
    if not point:
        return {"status": "error", "detail": "point 不能为空"}, 400

    if any(p.get("point") == point for p in points):
        return {"status": "error", "detail": "该知识点已存在"}, 400

    points.append({
        "id": _next_kp_id(points),
        "point": point,
        "explanation": explanation,
    })

    # 写回双份字段，保证历史路径兼容。
    _ensure_question_knowledge_points(
        case_data, request.sceneIndex, request.questionIndex)
    scenes = case_data.get("scenes", [])
    scene = scenes[request.sceneIndex]
    scene["trigger_question_learning_objectives"][request.questionIndex]["knowledge_points"] = points
    scene["trigger_questions"][request.questionIndex]["knowledge_points"] = points

    with open(path, "w", encoding="utf-8") as f:
        json.dump(case_data, f, ensure_ascii=False, indent=2)

    _sync_agent_setting_knowledge_points(case_data)

    return {
        "status": "success",
        "knowledge_points": points,
        "total": len(points),
    }


@app_fastapi.post("/api/question-knowledge-points/update")
async def api_update_question_knowledge_point(request: QuestionKnowledgePointUpdateRequest):
    """编辑 ViewE 的问题知识点内容，并同步 agent_setting.json。"""
    path, case_data, err = _load_case_data_by_name(request.caseName)
    if err:
        return err

    points, msg = _ensure_question_knowledge_points(
        case_data, request.sceneIndex, request.questionIndex)
    if msg:
        return {"status": "error", "detail": msg}, 400

    point_id = str(request.pointId or "").strip()
    point = str(request.point or "").strip()
    explanation = str(request.explanation or "").strip()
    if not point_id:
        return {"status": "error", "detail": "pointId 不能为空"}, 400
    if not point:
        return {"status": "error", "detail": "point 不能为空"}, 400

    hit = None
    for item in points:
        if item.get("id") == point_id:
            hit = item
            break

    if not hit:
        return {"status": "error", "detail": "知识点不存在"}, 404

    # 除当前编辑对象外，不允许重名。
    if any(p.get("point") == point and p.get("id") != point_id for p in points):
        return {"status": "error", "detail": "该知识点名称已存在"}, 400

    hit["point"] = point
    hit["explanation"] = explanation

    scenes = case_data.get("scenes", [])
    scene = scenes[request.sceneIndex]
    scene["trigger_question_learning_objectives"][request.questionIndex]["knowledge_points"] = points
    scene["trigger_questions"][request.questionIndex]["knowledge_points"] = points

    with open(path, "w", encoding="utf-8") as f:
        json.dump(case_data, f, ensure_ascii=False, indent=2)

    _sync_agent_setting_knowledge_points(case_data)

    return {
        "status": "success",
        "knowledge_points": points,
        "total": len(points),
    }


@app_fastapi.post("/api/question-knowledge-points/delete")
async def api_delete_question_knowledge_point(request: QuestionKnowledgePointDeleteRequest):
    """删除 ViewE 的问题知识点，并同步 agent_setting.json。"""
    path, case_data, err = _load_case_data_by_name(request.caseName)
    if err:
        return err

    points, msg = _ensure_question_knowledge_points(
        case_data, request.sceneIndex, request.questionIndex)
    if msg:
        return {"status": "error", "detail": msg}, 400

    point_id = str(request.pointId or "").strip()
    if not point_id:
        return {"status": "error", "detail": "pointId 不能为空"}, 400

    filtered = [p for p in points if str(p.get("id", "")).strip() != point_id]
    if len(filtered) == len(points):
        return {"status": "error", "detail": "知识点不存在"}, 404

    scenes = case_data.get("scenes", [])
    scene = scenes[request.sceneIndex]
    scene["trigger_question_learning_objectives"][request.questionIndex]["knowledge_points"] = filtered
    scene["trigger_questions"][request.questionIndex]["knowledge_points"] = filtered

    with open(path, "w", encoding="utf-8") as f:
        json.dump(case_data, f, ensure_ascii=False, indent=2)

    _sync_agent_setting_knowledge_points(case_data)

    return {
        "status": "success",
        "knowledge_points": filtered,
        "total": len(filtered),
    }


@app_fastapi.post("/api/agent-preview")
async def api_agent_preview(request: AgentPreviewRequest):
    """Generate ViewB preview bubbles with one LLM call based on current panel settings."""
    try:
        result = await generate_student_preview_response(
            agent_id=str(request.agent_id or "preview_agent"),
            persona=dict(request.persona or {}),
            trigger_question=str(request.trigger_question or "").strip(),
        )
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Failed to generate agent preview: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/api/agent-tags")
async def api_agent_tags(request: AgentTagsRequest):
    """Generate 3-5 short tags for the agent based on persona and trigger question."""
    try:
        from .agent_preview import generate_agent_tags
        tags = await generate_agent_tags(
            persona=dict(request.persona or {}),
            trigger_question=str(request.trigger_question or "").strip(),
        )
        return {"status": "success", "tags": tags}
    except Exception as e:
        logger.error(f"Failed to generate agent tags: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/api/agent-config-chat")
async def api_agent_config_chat(request: AgentConfigChatRequest):
    """Parse natural-language instruction into partial agent config updates via structured LLM output."""
    instruction = str(request.instruction or "").strip()
    if not instruction:
        return {
            "status": "error",
            "detail": "instruction is required",
        }, 400

    try:
        llm = ChatOpenAI(
            model=LLM_MODEL_NAME,
            base_url=BASE_URL,
            api_key=DASHSCOPE_API_KEY,
            temperature=0,
            timeout=60.0,
            max_retries=2,
        )

        history = request.chat_history[-6:] if request.chat_history else []
        history_text = "\n".join(
            f"{str(item.get('role', 'user')).strip()}: {str(item.get('content', '')).strip()}"
            for item in history
            if str(item.get("content", "")).strip()
        ) or "无"

        prompt = (
            "你是一个 PBL 学生 Agent 配置解析器。\n"
            "你的任务是：把用户的自然语言描述解析为结构化的 Agent 配置更新。\n\n"

            "重要原则：\n"
            "1) 返回的是『增量更新建议』，不是完整配置；\n"
            "2) 只有在有把握时才填写字段；\n"
            "3) 如果无法确定某个字段，必须返回 null；\n"
            "4) personality 和 learning_styles 的评分范围是 1-5；\n"
            "5) cognitive_orientation 只能是：point_based / line_based / plane_based；\n"
            "6) plasticity 只能是：low / medium / high。\n\n"

            "语义解析要求（必须执行）：\n"
            "1) 对‘成绩好/中等生/基础薄弱’等水平描述，不要只改一个字段；要综合推断并尽量同时给出 learning_styles、cognitive_orientation、knowledge_background。\n"
            "2) 对‘X年级医学生’（例如：三年级医学生）要按医学课程进度推断能力层次：\n"
            "   - 推断学习风格与推理取向；\n"
            "   - 若给定知识点列表，则按 high/medium/low 对每个知识点分类，不要遗漏。\n"
            "3) knowledge_background 必须是 high/medium/low 三个数组；如果你决定更新该字段，尽量覆盖给定知识点全集。\n"
            "4) 若用户已有明确偏好（如‘线性推理’），优先尊重用户表达。\n\n"

            "字段说明：\n"
            "name: 学生姓名\n"
            "age: 学生年龄\n"
            "major: 专业\n"
            "learning_styles: 学习方式评分（surface / deep / strategic，范围1-5）\n"
            "personality: 大五人格评分（openness / conscientiousness / extraversion / agreeableness / neuroticism，范围1-5）\n"
            "knowledge_background: 知识基础，分为 high / medium / low 三个层级，每个是知识点列表\n"
            "cognitive_orientation: 认知取向（point_based / line_based / plane_based）\n"
            "plasticity: 学习可塑性（low / medium / high）\n\n"

            "示例：\n"
            "用户输入：\n"
            "“这是一个很内向但非常认真的医学生。”\n\n"
            "输出：\n"
            "{\n"
            '  "major": "medicine",\n'
            '  "personality": {\n'
            '    "extraversion": 1,\n'
            '    "conscientiousness": 5\n'
            "  }\n"
            "}\n\n"

            f"[当前配置]\n{json.dumps(request.current_config or {}, ensure_ascii=False)}\n\n"
            f"[可用于分类的知识点全集]\n{json.dumps(_collect_all_knowledge_points(request.current_config or {}), ensure_ascii=False)}\n\n"
            f"[近期对话]\n{history_text}\n\n"
            f"[用户指令]\n{instruction}\n\n"

            "请返回 JSON 格式的配置更新。"
        )

        structured_llm = llm.with_structured_output(AgentConfigParseResult)
        parsed = await structured_llm.ainvoke(prompt)

        if hasattr(parsed, "model_dump"):
            config_update = parsed.model_dump(exclude_none=True)
        else:
            config_update = parsed.dict(exclude_none=True)

        # Light normalization only: keep outputs inside schema constraints.
        if isinstance(config_update.get("learning_styles"), dict):
            for key in ["surface", "deep", "strategic"]:
                if key in config_update["learning_styles"]:
                    val = config_update["learning_styles"].get(key)
                    if isinstance(val, (int, float)):
                        config_update["learning_styles"][key] = max(
                            1, min(5, int(round(val))))

        if isinstance(config_update.get("personality"), dict):
            for key in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
                if key in config_update["personality"]:
                    val = config_update["personality"].get(key)
                    if isinstance(val, (int, float)):
                        config_update["personality"][key] = max(
                            1, min(5, int(round(val))))

        if config_update.get("cognitive_orientation") not in {None, "point_based", "line_based", "plane_based"}:
            config_update.pop("cognitive_orientation", None)

        if config_update.get("plasticity") not in {None, "low", "medium", "high"}:
            config_update.pop("plasticity", None)

        assistant_message = "已根据自然语言完成配置解析（由模型自动判断水平、推理风格与知识分层）。"

        return {
            "status": "success",
            "config_update": config_update,
            "assistant_message": assistant_message,
        }
    except Exception as e:
        logger.error(
            f"Failed to parse agent config instruction: {e}", exc_info=True)
        return {
            "status": "error",
            "detail": str(e),
            "config_update": {},
        }, 500


@app_fastapi.post("/api/evaluate-knowledge-coverage")
async def api_evaluate_knowledge_coverage(request: KnowledgeCoverageRequest):
    """
    评估当前讨论路径对 trigger question 的知识点覆盖程度。

    输入：
    - case_name: 案例名称
    - scene_index: 场景索引
    - question_index: 问题索引
    - discussion_content: 当前路径的完整讨论内容

    输出：
    - total_points: 该问题总知识点数
    - covered_points: 已覆盖的知识点名称列表
    - coverage_ratio: 覆盖比例 (0-1)
    - covered_point_details: 每个知识点的详细信息 (point, explanation)
    """
    try:
        case_path = resolve_case_json_path(request.case_name)
        if not case_path:
            return {"status": "error", "message": "Case not found"}, 404

        with open(case_path, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        result = await evaluate_progressive_coverage(
            case_data=case_data,
            scene_index=request.scene_index,
            question_index=request.question_index,
            discussion_content=request.discussion_content,
        )

        if result.get("status") == "error":
            return result, 400

        # 将 ViewE 主来源回填后的结构持久化，保证后续稳定。
        with open(case_path, "w", encoding="utf-8") as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

        return result
    except Exception as e:
        logger.error(
            f"Failed to evaluate knowledge coverage: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/update_personas")
async def update_personas_v1(request: Dict[str, Dict]):
    """接收前端配置，保存到 JSON 文件，清空并重新注册所有 agent，并重新构建图。"""
    try:
        async def enrich_persona(agent_id: str, persona_data: Dict):
            enriched = dict(persona_data or {})
            generated_sections = await generate_learning_personality_sections(enriched)
            enriched.update(generated_sections)
            return agent_id, enriched

        enriched_pairs = await asyncio.gather(
            *(enrich_persona(agent_id, persona_data) for agent_id, persona_data in request.items())
        )
        enriched_request = {agent_id: persona for agent_id,
                            persona in enriched_pairs}

        # 1. 保存到 agent_setting.json
        with open(AGENT_SETTING_PATH, 'w', encoding='utf-8') as f:
            json.dump(enriched_request, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved personas to {AGENT_SETTING_PATH}")

        # 2. 清空现有的 agent 配置
        student_personas.clear()
        student_nodes.clear()
        logger.info("Cleared existing agent configurations.")

        # 3. 注册新的 agent
        for agent_id, persona_data in enriched_request.items():
            register_student_agent(agent_id, persona_data)

        # 4. 重新编译 LangGraph
        agent_ids = list(student_nodes.keys())
        graph.app = build_graph(agent_ids)
        logger.info(f"Successfully rebuilt graph with agents: {agent_ids}")

        return {
            "status": "success",
            "message": f"Personas updated, generated prompts, saved to file, and graph rebuilt for {len(agent_ids)} agents.",
            "generated_prompt_count": len(enriched_request),
        }
    except Exception as e:
        logger.error(f"Failed to update personas: {e}")
        return {"status": "error", "detail": str(e)}, 500


@app_fastapi.post("/api/update-knowledge")
async def api_update_knowledge(request: UpdateKnowledgeRequest):
    """更新案例 JSON 中的知识点名称"""
    base_name = extract_base_filename(request.pdf_filename)
    json_path = CASE_STORAGE_DIR / f"{base_name}.json"
    if not json_path.exists():
        return {"status": "error", "message": "Case not found"}, 404

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. 更新 theoretical_knowledge_points
        if "theoretical_knowledge_points" in data:
            data["theoretical_knowledge_points"] = [
                request.new_name if p == request.old_name else p
                for p in data["theoretical_knowledge_points"]
            ]

        # 2. 更新 knowledge_alignments
        if "knowledge_alignments" in data:
            for alignment in data["knowledge_alignments"]:
                if alignment.get("point") == request.old_name:
                    alignment["point"] = request.new_name

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to update knowledge: {e}")
        return {"status": "error", "message": str(e)}, 500


@app_fastapi.post("/api/add-knowledge")
async def api_add_knowledge(request: AddKnowledgeRequest):
    """在案例 JSON 中新增知识点"""
    base_name = extract_base_filename(request.pdf_filename)
    json_path = CASE_STORAGE_DIR / f"{base_name}.json"
    if not json_path.exists():
        return {"status": "error", "message": "Case not found"}, 404

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "theoretical_knowledge_points" not in data:
            data["theoretical_knowledge_points"] = []

        if request.knowledge_point not in data["theoretical_knowledge_points"]:
            data["theoretical_knowledge_points"].append(
                request.knowledge_point)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to add knowledge: {e}")
        return {"status": "error", "message": str(e)}, 500


@app_fastapi.post("/api/delete-knowledge")
async def api_delete_knowledge(request: DeleteKnowledgeRequest):
    """从案例 JSON 中删除知识点"""
    base_name = extract_base_filename(request.pdf_filename)
    json_path = CASE_STORAGE_DIR / f"{base_name}.json"
    if not json_path.exists():
        return {"status": "error", "message": "Case not found"}, 404

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. 从 theoretical_knowledge_points 删除
        if "theoretical_knowledge_points" in data:
            data["theoretical_knowledge_points"] = [
                p for p in data["theoretical_knowledge_points"] if p != request.knowledge_point
            ]

        # 2. 从 knowledge_alignments 删除
        if "knowledge_alignments" in data:
            data["knowledge_alignments"] = [
                a for a in data["knowledge_alignments"] if a.get("point") != request.knowledge_point
            ]

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to delete knowledge: {e}")
        return {"status": "error", "message": str(e)}, 500


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
                session_data[block_key] = {
                    "messages": [],
                    "intervention_summaries": {}
                }

            # 检查是否已存在 (优化: 只检查该 block 内部)
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

        prompt_context = f"你是一名 PBL 教育专家。请根据提供的学生讨论上下文，总结在此教师介入前的讨论状态（包含主题趋势、学生观点分布、是否存在僵局或不均等）。\n上下文：\n{context_text}\n要求：客观、简练，直接输出总结，不要包含开头。输出英文"
        prompt_action = f"你是一名 PBL 教育专家。请对以下教师的干预行为进行客观的‘形式性描述’（如：提问、复述、指出证据、点名等）。\n干预内容：\n{intervention_msg['content']}\n要求：去意图化，仅描述事实，直接输出。输出英文"
        prompt_consequence = f"你是一名 PBL 教育专家。请根据教师介入后的后续讨论，总结即时的互动变化（是否产生了新假设、讨论是否聚焦、语气变化等）。\n后续讨论：\n{consequence_text}\n要求：客观简练，直接输出。输出英文"

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


@app_fastapi.post("/api/generate-intervention-suggestions")
async def api_generate_intervention_suggestions(request: InterventionStrategyRequest):
    """并行调用 LLM 生成四种类型的教师干预策略建议"""
    try:
        logger.info(
            f"=== Generating intervention suggestions for session {request.session_id} ===")

        # 1. 获取消息地图和上下文
        messages_map = {}
        if request.session_id in session_histories:
            messages_map = session_histories[request.session_id]["messages_map"]
        else:
            # 兼容性处理：尝试从磁盘获取
            if DISCUSSION_FILE.exists():
                with open(DISCUSSION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if request.session_id in data:
                        # 扫描所有 block_key 以填充 messages_map
                        full_history = data[request.session_id]
                        for q_key, q_data in full_history.items():
                            if isinstance(q_data, dict):
                                for m in q_data.get("messages", []):
                                    if m["id"] not in messages_map:
                                        messages_map[m["id"]] = m

        if not messages_map:
            return {"status": "error", "message": "Discussion history not found"}

        # 构建讨论上下文
        discussion_history = build_discussion_content_from_leaf(
            messages_map, request.last_message_id)

        # 2. 定义四种类型及其 Prompt
        types = [
            {"type": "提问", "desc": "最常见，推进整个讨论的流程"},
            {"type": "解释", "desc": "解释自己提问的意图等"},
            {"type": "回答", "desc": "扮演病人回答，需要提示LLM生成的策略包含“我现在要扮演病人请你回答我”"},
            {"type": "点评", "desc": "one of my favorite questions"}
        ]

        # 3. 并行调用 (Qwen-3-Max)
        llm = ChatOpenAI(
            model=LLM_MODEL_NAME,
            openai_api_key=DASHSCOPE_API_KEY,
            openai_api_base=BASE_URL,
            temperature=0.7
        )

        async def generate_one(t_info):
            prompt = f"""你是一名资深的医学 PBL 导师（或者是参与 PBL 讨论的标准化病人/家属）。当前讨论背景（最近的消息在最后）如下：
{discussion_history}

请根据当前讨论进度，生成一条建议的教师/导师干预内容。
类型：{t_info['type']} ({t_info['desc']})

要求：
1. 语言专业、亲切，符合医学教育场景。
2. 简明扼要，直接输出干预内容，不要包含任何前缀（如“教师建议内容：”）。
3. 如果是“回答”类型且当前没有待答复的问题，可以提供一条关于病情的补充信息。
4. 确保与上述讨论上下文紧密相关。
"""
            msg = HumanMessage(content=prompt)
            # 注意：ainvoke 是异步的
            try:
                resp = await llm.ainvoke([msg])
                return {"type": t_info['type'], "content": resp.content.strip()}
            except Exception as e:
                logger.error(f"Error invoking LLM for {t_info['type']}: {e}")
                return {"type": t_info['type'], "content": f"无法生成该建议：{e}"}

        tasks = [generate_one(t) for t in types]
        suggestions = await asyncio.gather(*tasks)

        return {
            "status": "success",
            "suggestions": suggestions
        }
    except Exception as e:
        logger.error(f"Error generating intervention suggestions: {e}")
        return {"status": "error", "message": str(e)}


@app_fastapi.get("/get_personas")
async def get_personas():
    """从 agent_setting.json 读取所有 agent 的配置并返回。"""
    try:
        if not AGENT_SETTING_PATH.exists():
            return {}
        with open(AGENT_SETTING_PATH, 'r', encoding='utf-8') as f:
            raw = f.read()

        # 稳态处理：空文件不作为错误，直接返回空配置，前端无需展示。
        if not raw.strip():
            logger.info(
                "agent_setting.json is empty, returning empty personas.")
            return {}

        try:
            personas = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "agent_setting.json is invalid JSON, returning empty personas.")
            return {}

        if not isinstance(personas, dict):
            return {}
        return personas
    except Exception as e:
        logger.error(f"Error reading personas: {e}")
        return {"detail": str(e)}, 500

# 移除冗余或过时的 Pydantic 定义


@app_fastapi.websocket("/ws/pbl/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connection established for session: {session_id}")

    # Check if graph is initialized
    if graph.app is None:
        logger.error(
            f"WebSocket connection rejected for {session_id}: graph.app is None - agents not initialized")
        await websocket.send_json({
            "error": "System Error: Agent graph not initialized. Please check server logs and ensure agents were loaded during startup.",
            "type": "system_error"
        })
        await websocket.close()
        return

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

    def _build_state_snapshot(state_like: Optional[Dict]) -> Dict:
        """Build a compact, rollback-safe runtime snapshot from graph state."""
        base = state_like or {}
        return {
            "private_memory": copy.deepcopy(base.get("private_memory", {}) or {}),
            "knowledge_state": copy.deepcopy(base.get("knowledge_state", {}) or {}),
            "cognitive_load": copy.deepcopy(base.get("cognitive_load", {}) or {}),
            "self_efficacy": copy.deepcopy(base.get("self_efficacy", {}) or {}),
            "total_messages": int(base.get("total_messages", 0) or 0),
            "current_topic": str(base.get("current_topic", "Undefined") or "Undefined"),
            "discussion_active": bool(base.get("discussion_active", True)),
            "is_teacher_interrupted": bool(base.get("is_teacher_interrupted", False)),
            "force_no_silence_once": bool(base.get("force_no_silence_once", False)),
            "next_speaker": str(base.get("next_speaker", "router") or "router"),
            "trigger_question": str(base.get("trigger_question", "") or ""),
            "objective_evaluations": copy.deepcopy(base.get("objective_evaluations", []) or []),
            "achieved_all": bool(base.get("achieved_all", False)),
            "end_reason": str(base.get("end_reason", "") or ""),
        }

    def _snapshot_for_message(message_id: Optional[str]) -> Dict:
        if not message_id:
            return _build_state_snapshot(None)
        # Fallback to nearest ancestor snapshot for compatibility with old history rows.
        curr = message_id
        safety = 0
        while curr and safety < 2000:
            msg_data = sh["messages_map"].get(curr, {}) or {}
            stored = msg_data.get("state_snapshot", {}) if isinstance(
                msg_data, dict) else {}
            if isinstance(stored, dict) and stored:
                return _build_state_snapshot(stored)
            curr = msg_data.get("parent_id") if isinstance(
                msg_data, dict) else None
            safety += 1
        return _build_state_snapshot(None)

    def _apply_out_to_runtime_state(runtime_state: Dict, out: Dict) -> Dict:
        """Apply node incremental outputs onto session runtime state."""
        if not isinstance(out, dict):
            return runtime_state

        # total_messages is an additive channel in LangGraph.
        if "total_messages" in out:
            runtime_state["total_messages"] = int(runtime_state.get(
                "total_messages", 0) or 0) + int(out.get("total_messages", 0) or 0)

        for key in [
            "private_memory",
            "knowledge_state",
            "cognitive_load",
            "self_efficacy",
            "current_topic",
            "discussion_active",
            "is_teacher_interrupted",
            "force_no_silence_once",
            "next_speaker",
            "trigger_question",
            "objective_evaluations",
            "achieved_all",
            "end_reason",
        ]:
            if key in out:
                runtime_state[key] = copy.deepcopy(out.get(key))

        return runtime_state

    def _clear_output_queue() -> None:
        """Drop stale queued events so resumed branches don't consume old outputs."""
        while not output_queue.empty():
            try:
                output_queue.get_nowait()
                output_queue.task_done()
            except asyncio.QueueEmpty:
                break

    async def _stop_graph_tasks(drain_pending: bool, clear_queue: bool = True) -> None:
        """Stop current graph tasks safely.

        - drain_pending=True: let output_processor finish queued events (internalization/topic/objective updates).
        - clear_queue=True: remove any stale leftovers after stop.
        """
        nonlocal graph_task, output_task, pause_requested, discussion_paused

        if drain_pending and graph_task:
            # Ask output_processor to pause at next safe event boundary.
            pause_requested = True
            try:
                await asyncio.wait_for(_wait_until_paused(), timeout=8.0)
            except asyncio.TimeoutError:
                logger.warning(
                    "Graceful pause timed out; forcing task cancellation.")

        if graph_task:
            graph_task.cancel()
            with suppress(asyncio.CancelledError):
                await graph_task
            graph_task = None

        if output_task:
            if drain_pending:
                try:
                    await asyncio.wait_for(output_queue.join(), timeout=3.0)
                except asyncio.TimeoutError:
                    logger.warning(
                        "Timed out draining pending output queue before task switch.")
            output_task.cancel()
            with suppress(asyncio.CancelledError):
                await output_task
            output_task = None

        if clear_queue:
            _clear_output_queue()

        pause_requested = False
        discussion_paused = False

    async def _wait_until_paused() -> None:
        while not discussion_paused:
            await asyncio.sleep(0.05)

    async def _emit_state_restore(scene_idx: int, question_idx: int, snapshot: Optional[Dict]) -> None:
        """Push restored objective/end-state so frontend can sync ViewE when switching branch/context."""
        snap = _build_state_snapshot(snapshot or {})
        rows = snap.get("objective_evaluations", []) or []
        if not isinstance(rows, list):
            rows = []

        # 获取当前活跃 leaf 关联的预缓存知识覆盖度
        leaf_id = sh.get("active_id")
        cached_coverage = None
        if leaf_id and leaf_id in sh["messages_map"]:
            cached_coverage = sh["messages_map"][leaf_id].get(
                "knowledge_coverage")

        await websocket.send_json({
            "type": "state_restored",
            "scene_index": int(scene_idx),
            "question_index": int(question_idx),
            "trigger_question": snap.get("trigger_question", ""),
            "objective_evaluations": rows,
            "achieved_all": bool(snap.get("achieved_all", False)),
            "end_reason": snap.get("end_reason", ""),
            "state_snapshot": snap,
            "knowledge_coverage": cached_coverage,  # 【新增】返回历史快照中记录的评估结果
        })

    async def _recompute_and_emit_context_evaluations(scene_idx: int, question_idx: int, leaf_id: Optional[str], emit_ws: bool = True) -> Dict[str, Any]:
        """Re-evaluate knowledge coverage from current branch leaf context."""
        from . import pbl_info

        case_name = str(
            getattr(pbl_info, "current_case_name", "") or "").strip()
        if not case_name or not leaf_id:
            return {}

        case_path = resolve_case_json_path(case_name)
        if not case_path or not case_path.exists():
            return {}

        discussion_content = build_discussion_content_from_leaf(
            sh["messages_map"], leaf_id)
        if not discussion_content.strip():
            return {}

        with open(case_path, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        # 【新增】获取历史分数和消息轮数以支撑增量评估和动态严格度约束
        historical_scores, message_count = get_historical_scores_from_leaf(
            sh["messages_map"], leaf_id)

        coverage_payload = await evaluate_progressive_coverage(
            case_data=case_data,
            scene_index=int(scene_idx),
            question_index=int(question_idx),
            discussion_content=discussion_content,
            historical_scores=historical_scores,
            message_count=message_count
        )

        # 【新增】将最新的覆盖率结果保存到 messages_map 中，实现回退后的即时恢复
        if leaf_id in sh["messages_map"]:
            sh["messages_map"][leaf_id]["knowledge_coverage"] = coverage_payload
            persist_discussion(session_id, sh["messages_map"])

        # 持久化一次可能发生的知识点回填。
        with open(case_path, "w", encoding="utf-8") as f:
            json.dump(case_data, f, ensure_ascii=False, indent=2)

        if emit_ws:
            await websocket.send_json({
                "type": "knowledge_coverage_update",
                "scene_index": int(scene_idx),
                "question_index": int(question_idx),
                "node_id": leaf_id,
                "coverage": coverage_payload,
            })

        return {
            "coverage": coverage_payload,
        }

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

                        # 【新增】自动推断每个问题的最后活跃状态
                        if q_val.get("messages"):
                            last_msg = q_val["messages"][-1]
                            sh["q_states"][f"{s_idx}_{q_idx}"] = {
                                "active_id": last_msg["id"],
                                "current_branch": last_msg.get("branch_id", "main")
                            }
                            # 顺便设置全局 active_id 保证初始上下文可见
                            sh["active_id"] = last_msg["id"]
                            sh["current_branch"] = last_msg.get(
                                "branch_id", "main")
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

    def ensure_branch_for_new_message(s_idx, q_idx, parent_id):
        """If parent already has children, create a new branch to avoid merging paths."""
        if not parent_id:
            return sh.get("current_branch", "main")

        has_children = any(
            m.get("parent_id") == parent_id for m in sh["messages_map"].values()
        )
        if has_children:
            new_branch_name = f"branch_{str(uuid.uuid4())[:4]}"
            update_q_state(s_idx, q_idx, parent_id, new_branch_name)
            logger.info(
                f"Auto-branching: parent {parent_id} already has children, switching to {new_branch_name}"
            )
            return new_branch_name

        return sh.get("current_branch", "main")

    # 状态管理
    current_state = None
    graph_task = None
    output_queue = asyncio.Queue()
    runtime_state: Dict = _build_state_snapshot(None)
    pause_requested = False
    discussion_paused = False

    async def stream_langgraph(state, s_idx, q_idx):
        """后台流式输出任务，携带当前任务的场景和问题索引"""
        if graph.app is None:
            logger.error(
                "Error in stream_langgraph: graph.app is None - the agent graph was not initialized during startup")
            await websocket.send_json({"error": "Agent graph not initialized. Please ensure agents are loaded and retry."})
            return

        current_config = {
            "configurable": {"thread_id": f"{session_id}_{s_idx}_{q_idx}_{sh.get('current_branch', 'main')}"},
            "recursion_limit": 60
        }
        logger.info(
            f"Starting stream for {s_idx}_{q_idx} with thread_id: {current_config.get('configurable').get('thread_id')}")
        try:
            async for event in graph.app.astream(state, config=current_config):
                # 【优化】检查暂停请求：如果暂停被请求，立即停止处理新事件
                if pause_requested:
                    logger.info(
                        "Pause requested in stream_langgraph; stopping event processing.")
                    break
                # 将输出放入队列，附带 context 索引
                await output_queue.put((event, s_idx, q_idx))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in stream_langgraph: {e}")
            await websocket.send_json({"error": str(e)})

    async def output_processor():
        """处理输出队列的任务"""
        nonlocal runtime_state, graph_task, pause_requested, discussion_paused
        # 【优化】追踪上一次发送的topic和objectives，用于检测变化并立即更新
        previous_topic = None
        previous_objectives = None

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
                    # 处理知识覆盖率评估结果 (由 knowledge_evaluator 节点产生)
                    if node == "knowledge_evaluator" and out:
                        kb_data = out.get("knowledge_state")
                        if kb_data and kb_data.get("status") == "success":
                            # 将知识覆盖率直接推送到前端，这会触发 ViewD 的更新
                            # 携带 leaf_id，使其能精确对应到 graphData 的节点
                            leaf_id = sh.get("active_id")
                            if leaf_id:
                                # 【核心同步修复】不仅发送到前端，还要立即更新内存中的 messages_map，
                                # 否则下一条消息评估时 get_historical_scores 拿不到这个值。
                                if leaf_id in sh["messages_map"]:
                                    sh["messages_map"][leaf_id]["knowledge_coverage"] = kb_data
                                    # 如果有 persist_discussion 需求也建议在这里触发
                                    persist_discussion(
                                        session_id, sh["messages_map"])

                                await websocket.send_json({
                                    "type": "message_update",
                                    "id": leaf_id,
                                    "knowledge_coverage": kb_data,
                                    "scene_index": s_idx,
                                    "question_index": q_idx
                                })
                                logger.info(
                                    f"DEBUG: [Server] Pushed sync coverage for {leaf_id} (Ratio: {kb_data.get('coverage_ratio')})")

                    runtime_state = _apply_out_to_runtime_state(
                        runtime_state, out)

                    # 处理消息输出
                    if "messages" in out:
                        for m in out["messages"]:
                            # 识别发言者
                            sender = getattr(m, "name", node)

                            # 分支管理：生成 ID
                            msg_id = str(uuid.uuid4())[:8]
                            parent_id = sh["active_id"]
                            branch_id = ensure_branch_for_new_message(
                                s_idx, q_idx, parent_id
                            )

                            # 存储到历史
                            msg_data = {
                                "id": msg_id,
                                "parent_id": parent_id,
                                "branch_id": branch_id,
                                "agent": sender,
                                "content": m.content,
                                "langchain_msg": m,
                                "state_snapshot": _build_state_snapshot(runtime_state),
                                "scene_index": s_idx,
                                "question_index": q_idx,
                                "is_convention": False
                            }
                            sh["messages_map"][msg_id] = msg_data

                            # 持久化到 json 文件
                            persist_discussion(session_id, sh["messages_map"])

                            # 更新特定问题的指针
                            update_q_state(s_idx, q_idx, msg_id, branch_id)

                            # 【优化】立即发送消息到前端，不等待简化和评估
                            # 简化和评估改为异步后台任务，完成后通过单独消息更新前端
                            await websocket.send_json({
                                "id": msg_id,
                                "parent_id": parent_id,
                                "branch_id": branch_id,
                                "node": node,
                                "agent": sender,
                                "content": m.content,
                                "summary": m.content,  # 暂时为原文，异步更新
                                "type": "agent_output",
                                "scene_index": s_idx,
                                "question_index": q_idx,
                                "state_snapshot": msg_data.get("state_snapshot", {}),
                                "knowledge_coverage": {},  # 暂时为空，异步更新
                            })

                            # 【后台任务】异步进行消息简化
                            async def _async_postprocess_message():
                                """后台异步处理消息的简化，完成后通过WS更新前端"""
                                try:
                                    simplified = m.content
                                    # 只有学生 Agent 的长发言才需要精简显示在 Storyline 中
                                    if sender and sender not in ["case_introduction", "teacher", "host", "system"]:
                                        simplified = await simplify_message(m.content)

                                    # 【优化】覆盖评估已在 summarizer 节点后同步执行，这里只做消息简化
                                    # 异步更新前端
                                    if simplified != m.content:
                                        await websocket.send_json({
                                            "type": "message_update",
                                            "id": msg_id,
                                            "summary": simplified,
                                        })

                                    # 更新内存中的消息数据
                                    if msg_id in sh["messages_map"]:
                                        sh["messages_map"][msg_id]["summary"] = simplified
                                except Exception as e:
                                    logger.error(
                                        f"Error in async message postprocessing: {e}")

                            # 提交后台任务，不阻塞当前流程
                            asyncio.create_task(_async_postprocess_message())

                    # 【优化】处理主题更新：检测变化并立即发送，不等待其他处理
                    current_topic = runtime_state.get(
                        "current_topic", "Undefined")
                    if current_topic and current_topic != previous_topic:
                        # 主题发生变化，立即通知前端
                        await websocket.send_json({
                            "id": sh["active_id"],  # 关联到最后一条消息
                            "node": node,
                            "topic": current_topic,
                            "type": "topic_update"
                        })
                        previous_topic = current_topic

                    # Keep the active message snapshot aligned with latest state updates
                    # from non-message nodes (topic_manager/summarizer/router).
                    active_id = sh.get("active_id")
                    if active_id and active_id in sh["messages_map"]:
                        sh["messages_map"][active_id]["state_snapshot"] = _build_state_snapshot(
                            runtime_state)
                        await websocket.send_json({
                            "type": "state_snapshot_update",
                            "scene_index": s_idx,
                            "question_index": q_idx,
                            "active_id": active_id,
                            "state_snapshot": sh["messages_map"][active_id].get("state_snapshot", {}),
                        })

                    # 【优化】目标达成状态更新：检测变化并立即发送到前端
                    current_objectives = runtime_state.get(
                        "objective_evaluations", [])
                    if current_objectives and current_objectives != previous_objectives:
                        # 目标评估发生变化，立即通知前端
                        logger.info(
                            "WS objective_update send scene=%s question=%s rows=%s",
                            s_idx,
                            q_idx,
                            len(current_objectives or []),
                        )
                        await websocket.send_json({
                            "type": "objective_update",
                            "scene_index": s_idx,
                            "question_index": q_idx,
                            "trigger_question": runtime_state.get("trigger_question", ""),
                            "objective_evaluations": current_objectives,
                        })
                        previous_objectives = copy.deepcopy(current_objectives)

                    # 讨论结束事件（用于前端提示 END 原因）
                    if out.get("next_speaker") == "END":
                        logger.info(
                            "WS discussion_end send scene=%s question=%s reason=%s rows=%s",
                            s_idx,
                            q_idx,
                            out.get("end_reason", "unknown"),
                            len(out.get("objective_evaluations", []) or []),
                        )
                        await websocket.send_json({
                            "type": "discussion_end",
                            "scene_index": s_idx,
                            "question_index": q_idx,
                            "reason": out.get("end_reason", "unknown"),
                            "achieved_all": bool(out.get("achieved_all", False)),
                            "trigger_question": out.get("trigger_question", ""),
                            "objective_evaluations": out.get("objective_evaluations", []),
                        })
                output_queue.task_done()

                if pause_requested and not discussion_paused:
                    logger.info(
                        "Pause barrier reached: stopping stream after current event is fully persisted."
                    )
                    if graph_task:
                        graph_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await graph_task
                        graph_task = None

                    # 【核心修复】在真正进入暂停状态前，由 server 主核触发一次最终评估。
                    # LangGraph 节点内部可能因 teacher_interrupted/silence 跳过，
                    # 这里的触发确保了即使学生保持沉默被暂停，知识点覆盖也能刷新。
                    from . import pbl_info
                    await _recompute_and_emit_context_evaluations(
                        scene_idx=int(pbl_info.active_scene_index),
                        question_index=int(pbl_info.active_question_index),
                        leaf_id=sh.get("active_id"),
                        emit_ws=True
                    )

                    _clear_output_queue()
                    pause_requested = False
                    discussion_paused = True
                    await websocket.send_json({"type": "discussion_paused"})
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
                # 1. 仅清除当前 block 在内存中的历史消息（保留其他情景的消息）
                sh["messages_map"] = {k: v for k, v in sh["messages_map"].items()
                                      if v.get('scene_index') != scene_idx or v.get('question_index') != question_idx}

                # 重置该问题的状态指针
                if block_key in sh["q_states"]:
                    del sh["q_states"][block_key]
                sh["active_id"] = None
                sh["current_branch"] = "main"

                # 2. 从持久化文件中移除该 block 的记录，强制从新开始写入
                if DISCUSSION_FILE.exists():
                    try:
                        with open(DISCUSSION_FILE, "r", encoding="utf-8") as f:
                            disk_data = json.load(f)
                        if session_id in disk_data:
                            if block_key in disk_data[session_id]:
                                del disk_data[session_id][block_key]
                                logger.info(
                                    f"Cleared existing block records for {block_key} in session {session_id}")

                            with open(DISCUSSION_FILE, "w", encoding="utf-8") as f:
                                json.dump(disk_data, f,
                                          ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.error(
                            f"Failed to clear specific block in discussion file: {e}")

                # 同步更新全局 pbl_info
                from . import pbl_info as pbl_state
                from .pbl_info import update_pbl_info
                # 保留已由 /api/set-active-scene 注入的当前问题与目标，避免在 start_discussion 时被清空。
                preserved_questions = pbl_state.pbl_triger_questions or []
                preserved_case_name = getattr(
                    pbl_state, "current_case_name", "") or ""
                refreshed_objectives = resolve_objectives_from_case(
                    case_name=preserved_case_name,
                    scene_idx=scene_idx,
                    question_idx=question_idx,
                )
                preserved_objectives = refreshed_objectives or pbl_state.current_learning_objectives or []
                update_pbl_info(
                    story=initial_case,
                    questions=preserved_questions,
                    scene_idx=scene_idx,
                    q_idx=question_idx,
                    learning_objectives=preserved_objectives,
                    case_name=preserved_case_name,
                )
                rt_key = f"{scene_idx}_{question_idx}"
                # 【修改】刷新后不加载缓存的override，始终以干净状态开始
                pbl_state.objective_overrides[rt_key] = {}

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
                    "total_messages": 0,
                    "private_memory": {},
                    "knowledge_state": {},
                    "cognitive_load": {},
                    "self_efficacy": {},
                    "next_speaker": "router",
                    "is_teacher_interrupted": False,
                    "discussion_active": True,
                    "force_no_silence_once": False,
                    "current_topic": "开始讨论"
                }
                runtime_state = _build_state_snapshot(current_state)

                sh["messages_map"][msg_id]["state_snapshot"] = _build_state_snapshot(
                    runtime_state)

                # 取消旧任务
                await _stop_graph_tasks(drain_pending=False, clear_queue=True)

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
                    runtime_state = _snapshot_for_message(sh["active_id"])
                    await _emit_state_restore(s_idx, q_idx, runtime_state)
                    await _recompute_and_emit_context_evaluations(
                        scene_idx=int(s_idx),
                        question_idx=int(q_idx),
                        leaf_id=sh.get("active_id"),
                    )
                    logger.info(
                        f"Context switched to {q_key}: active_id={sh['active_id']}, branch={sh['current_branch']}")
                else:
                    logger.info(
                        f"Context switched to new question {q_key}, pointers not yet initialized")

            elif action == "rollback_to":
                target_id = msg.get("target_id")
                if target_id in sh["messages_map"]:
                    logger.info(f"Rolling back to message: {target_id}")

                    # Finish in-flight queue events first so memory/objective states are not lost.
                    await _stop_graph_tasks(drain_pending=True, clear_queue=True)

                    target_branch = sh["messages_map"][target_id].get(
                        "branch_id", "main")
                    target_scene_idx = int(
                        sh["messages_map"][target_id].get("scene_index", 0) or 0)
                    target_question_idx = int(
                        sh["messages_map"][target_id].get("question_index", 0) or 0)
                    from . import pbl_info
                    update_q_state(target_scene_idx,
                                   target_question_idx, target_id, target_branch)
                    runtime_state = _snapshot_for_message(target_id)
                    await _emit_state_restore(target_scene_idx, target_question_idx, runtime_state)
                    await _recompute_and_emit_context_evaluations(
                        scene_idx=int(target_scene_idx),
                        question_idx=int(target_question_idx),
                        leaf_id=target_id,
                    )

                    logger.info(
                        f"Context switched to branch: {sh['current_branch']}")

                    await websocket.send_json({"type": "rollback_ack", "target_id": target_id})

            elif action == "switch_node_focus":
                """【新增】在暂停期间切换节点焦点，用于切换分支后恢复讨论"""
                target_id = msg.get("target_id")
                branch_id = msg.get("branch_id", "main")

                if target_id and target_id in sh["messages_map"]:
                    sh["active_id"] = target_id
                    sh["current_branch"] = branch_id
                    runtime_state = _snapshot_for_message(target_id)
                    target_scene_idx = int(
                        sh["messages_map"][target_id].get("scene_index", 0) or 0)
                    target_question_idx = int(
                        sh["messages_map"][target_id].get("question_index", 0) or 0)

                    from . import pbl_info
                    update_q_state(target_scene_idx,
                                   target_question_idx, target_id, branch_id)
                    await _emit_state_restore(target_scene_idx, target_question_idx, runtime_state)
                    await _recompute_and_emit_context_evaluations(
                        scene_idx=int(target_scene_idx),
                        question_idx=int(target_question_idx),
                        leaf_id=target_id,
                    )

                    logger.info(
                        f"✓ Switched node focus to: {target_id} on branch: {branch_id}")
                    await websocket.send_json({
                        "type": "node_focus_switched",
                        "target_id": target_id,
                        "branch_id": branch_id
                    })
                else:
                    logger.warning(
                        f"✗ Failed to switch focus: target_id {target_id} not found")

            elif action == "teacher_intervention":
                teacher_content = msg.get("content", "")

                # 【修改】趁着暂停把暂停前的 agent 更新执行完，但不调用 host
                # 设置 pause_requested 为 True，让 output_processor 在处理完当前排队事件后自动进入暂停状态，
                # 但不强行 cancel graph_task，直到我们手动重新启动它。
                # 这样可以确保之前的 topic/objective/coverage 等异步评估在教师消息发出前更有可能完成。
                await _stop_graph_tasks(drain_pending=True, clear_queue=True)

                # 优先使用前端传入的 parent_id，实现点击节点后分支
                target_parent_id = msg.get("parent_id")
                from . import pbl_info
                if target_parent_id and target_parent_id in sh["messages_map"]:
                    target_branch = sh["messages_map"][target_parent_id].get(
                        "branch_id", "main")
                    update_q_state(pbl_info.active_scene_index,
                                   pbl_info.active_question_index, target_parent_id, target_branch)
                    runtime_state = _snapshot_for_message(target_parent_id)
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
                    "state_snapshot": _build_state_snapshot(runtime_state),
                    "topic": "Teacher Intervention",
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
                    "topic": "Teacher Intervention",
                    "scene_index": pbl_info.active_scene_index,
                    "question_index": pbl_info.active_question_index,
                    "state_snapshot": teacher_msg_data.get("state_snapshot", {}),
                })

                # 准备更新 Payload
                update_payload = {
                    "messages": chain + [teacher_msg],  # 传入完整链条以重置状态
                    "total_messages": int(runtime_state.get("total_messages", 0) or 0),
                    "private_memory": copy.deepcopy(runtime_state.get("private_memory", {}) or {}),
                    "knowledge_state": copy.deepcopy(runtime_state.get("knowledge_state", {}) or {}),
                    "cognitive_load": copy.deepcopy(runtime_state.get("cognitive_load", {}) or {}),
                    "self_efficacy": copy.deepcopy(runtime_state.get("self_efficacy", {}) or {}),
                    "is_teacher_interrupted": False,    # 设为 False 以跳过主持人干预回复，直接让学生讨论
                    "next_speaker": "router",           # 直接去路由
                    "discussion_active": True,
                    "force_no_silence_once": True,
                    "current_topic": None               # 强制重置主题识别，由 topic_manager 重新生成
                }
                runtime_state = _build_state_snapshot(update_payload)

                # 取消旧任务并重新启动讨论流
                # 这里的 stream_langgraph 现在由于我们之前的修改，会使用包含 branch_id 的新 thread_id
                await _stop_graph_tasks(drain_pending=False, clear_queue=True)

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
                if not graph_task and not output_task:
                    discussion_paused = True
                    # 【新增】暂停时立即触发一次异步评估，确保前端显示最新

                    async def _pause_eval():
                        from . import pbl_info
                        await _recompute_and_emit_context_evaluations(
                            scene_idx=int(pbl_info.active_scene_index),
                            question_index=int(pbl_info.active_question_index),
                            leaf_id=sh.get("active_id"),
                        )
                    asyncio.create_task(_pause_eval())
                    await websocket.send_json({"type": "discussion_paused"})
                else:
                    # Defer stopping until current event is fully processed and persisted.
                    pause_requested = True
                    logger.info(
                        "Pause requested; waiting for current in-flight event to finish.")

            elif action == "resume_discussion" or action == "force_resume":
                logger.info(f"教师指令：恢复讨论 (Action: {action})。")
                if pause_requested and not discussion_paused:
                    try:
                        await asyncio.wait_for(_wait_until_paused(), timeout=8.0)
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Resume requested before pause barrier completed; forcing stop.")

                await _stop_graph_tasks(drain_pending=False, clear_queue=True)

                from . import pbl_info

                chain = []
                curr_ptr = sh["active_id"]
                while curr_ptr:
                    m_data = sh["messages_map"].get(curr_ptr)
                    if not m_data:
                        break
                    chain.append(m_data["langchain_msg"])
                    curr_ptr = m_data.get("parent_id")
                chain.reverse()

                resume_state = None
                if chain:
                    # 【修复】使用当前runtime_state中的total_messages，而不是snapshot中的静态值
                    historical_turns = int(
                        runtime_state.get("total_messages", 0) or 0)
                    resume_state = {
                        "messages": chain,
                        "total_messages": historical_turns,
                        "private_memory": copy.deepcopy(runtime_state.get("private_memory", {}) or {}),
                        "knowledge_state": copy.deepcopy(runtime_state.get("knowledge_state", {}) or {}),
                        "cognitive_load": copy.deepcopy(runtime_state.get("cognitive_load", {}) or {}),
                        "self_efficacy": copy.deepcopy(runtime_state.get("self_efficacy", {}) or {}),
                        "discussion_active": True,
                        "is_teacher_interrupted": False,
                        "force_no_silence_once": False,
                        "current_topic": runtime_state.get("current_topic", "Undefined"),
                        "next_speaker": "router"
                    }
                    runtime_state = _build_state_snapshot(resume_state)
                else:
                    runtime_state = _build_state_snapshot(runtime_state)

                graph_task = asyncio.create_task(stream_langgraph(
                    resume_state, pbl_info.active_scene_index, pbl_info.active_question_index))
                output_task = asyncio.create_task(output_processor())
                discussion_paused = False
                logger.info("教师强制恢复讨论（override-triggered）")
                await websocket.send_json({"type": "discussion_resumed"})

            elif action == "force_resume":
                logger.info("教师强制恢复讨论（override触发，不受 isPaused 限制）")
                if pause_requested and not discussion_paused:
                    try:
                        await asyncio.wait_for(_wait_until_paused(), timeout=8.0)
                    except asyncio.TimeoutError:
                        logger.warning(
                            "Resume requested before pause barrier completed; forcing stop.")

                await _stop_graph_tasks(drain_pending=False, clear_queue=True)

                # 【修复】恢复时，需要重新构建到当前 active_id 的完整链条
                # 这样能保证即使切换了分支，LangGraph 也能从正确的消息链恢复
                from . import pbl_info

                # 构建完整的消息链
                chain = []
                curr_ptr = sh["active_id"]
                while curr_ptr:
                    m_data = sh["messages_map"].get(curr_ptr)
                    if not m_data:
                        logger.warning(
                            f"Message {curr_ptr} not found in map during resume")
                        break
                    chain.append(m_data["langchain_msg"])
                    curr_ptr = m_data.get("parent_id")
                chain.reverse()

                # 如果链条为空，说明只有初始消息，使用 None 让 checkpoint 恢复
                resume_state = None
                if chain:
                    # 【修复】使用当前runtime_state中的total_messages，而不是snapshot中的静态值
                    historical_turns = int(
                        runtime_state.get("total_messages", 0) or 0)
                    resume_state = {
                        "messages": chain,
                        "total_messages": historical_turns,
                        "private_memory": copy.deepcopy(runtime_state.get("private_memory", {}) or {}),
                        "knowledge_state": copy.deepcopy(runtime_state.get("knowledge_state", {}) or {}),
                        "cognitive_load": copy.deepcopy(runtime_state.get("cognitive_load", {}) or {}),
                        "self_efficacy": copy.deepcopy(runtime_state.get("self_efficacy", {}) or {}),
                        "discussion_active": bool(runtime_state.get("discussion_active", True)),
                        "is_teacher_interrupted": bool(runtime_state.get("is_teacher_interrupted", False)),
                        "force_no_silence_once": bool(runtime_state.get("force_no_silence_once", False)),
                        "current_topic": runtime_state.get("current_topic", "Undefined"),
                        "next_speaker": "router"
                    }
                    runtime_state = _build_state_snapshot(resume_state)
                    logger.info(
                        f"Resuming with {len(chain)} historical messages from {sh['active_id']} on branch {sh['current_branch']}")
                else:
                    runtime_state = _build_state_snapshot(runtime_state)
                    logger.info(
                        f"No messages to resume, using checkpoint recovery on branch {sh['current_branch']}")

                graph_task = asyncio.create_task(stream_langgraph(
                    resume_state, pbl_info.active_scene_index, pbl_info.active_question_index))
                output_task = asyncio.create_task(output_processor())
                discussion_paused = False
                await websocket.send_json({"type": "discussion_resumed"})

    except WebSocketDisconnect:
        # 清理资源
        if graph_task:
            graph_task.cancel()
        if output_task:
            output_task.cancel()

if __name__ == "__main__":
    uvicorn.run(app_fastapi, host="0.0.0.0", port=8000)
