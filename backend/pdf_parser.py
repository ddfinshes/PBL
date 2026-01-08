"""PBL.backend.pdf_parser
完整版：
1. PBLFastParser: 用于 LLM 解析，支持图片提取持久化。
2. get_raw_pdf_images: 用于前端快速预览原始 PDF 图片。
"""

import time
import asyncio
import logging
import base64
import os
import io
import pymupdf4llm
import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .schema import PBLCaseStructure
from .config import DASHSCOPE_API_KEY, BASE_URL, LLM_MODEL_NAME

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 1. LLM 解析器 ---


class PBLFastParser:
    def __init__(self):
        if not DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY is missing.")
        # 图片存储目录
        self.base_storage_dir = Path(__file__).parent / "cases_img"
        if not self.base_storage_dir.exists():
            self.base_storage_dir.mkdir(parents=True)

        self.llm = ChatOpenAI(
            model=LLM_MODEL_NAME, temperature=0.1, api_key=DASHSCOPE_API_KEY,
            base_url=BASE_URL, timeout=300.0, max_retries=2
        )

    def _image_to_base64(self, image_path: str) -> str:
        """读取图片并转为 Base64，同时进行质量检查"""
        try:
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()
                # 过滤过小的图片（小于 5KB 的通常是Logo或装饰图）
                if len(img_data) < 5120:  # 5KB
                    logger.debug(
                        f"跳过过小的图片: {image_path} ({len(img_data)} bytes)")
                    return ""
                b64_data = base64.b64encode(img_data).decode('utf-8')
                return f"data:image/jpeg;base64,{b64_data}"
        except Exception as e:
            logger.debug(f"图片转Base64失败: {e}")
            return ""

    async def parse(self, pdf_path: str) -> Dict[str, Any]:
        total_start = time.time()
        pdf_name = Path(pdf_path).stem
        # 使用PDF名称直接创建目录
        case_root_dir = self.base_storage_dir / pdf_name
        img_dir = case_root_dir / "img"
        img_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"🚀 [PDF解析] 开始提取: {pdf_name}，图片存至: {img_dir}")

        try:
            # 1. 提取 Markdown 和 图片
            md_text = await asyncio.to_thread(
                pymupdf4llm.to_markdown, pdf_path, write_images=True,
                image_path=str(img_dir), image_format="jpg"
            )

            # 2. 构造 Prompt
            system_prompt = """
            你是一个医学PBL教案解析专家。请将Markdown教案解析为结构化数据。
            
            【场景拆分】请根据剧情推进（如"第一页"、"第二页"）将教案拆分为细粒度的 Scene。
            每个Scene对应教案中的一个独立病情阶段或检查阶段。
            
            【内容提取】对每个Scene，提取：
            - story_content：该场景的病历描述、临床表现、检查结果等
            - key_discussion_points：核心讨论要点
            - trigger_questions：引导问题
            
            【图片处理 - 关键规则】
            1. 只在 Markdown 中寻找 `![](img/xxx.jpg)` 格式的图片
            2. 【准确定位】：将图片关联到它最近的/最相关的文字内容所属的Scene
            3. 【质量筛选】：
               - 忽略所有Logo、页眉、页脚、装饰性图片
               - 只选择【医学相关】的图片：患者身体部位、医学检查图、X光、CT、超声等
               - 忽略【纯文字图片】或【表格图片】
            4. 【准确归类】：
               - 同一个Scene内的多个相关图片才能一起列出
               - 不属于当前Scene的图片一定不要列出
            
            返回每个Scene的 relevant_image_filenames 列表，只包含真正相关的医学图片。
            """
            prompt = ChatPromptTemplate.from_messages(
                [("system", system_prompt), ("human", "{text}")])

            logger.info("🚀 [LLM解析] 正在进行结构化提取...")
            chain = prompt | self.llm.with_structured_output(PBLCaseStructure)
            result = await chain.ainvoke({"text": md_text})

            # 3. 后处理：强制重命名标题 & 回填图片
            final_scenes = []
            for scene_idx, scene in enumerate(result.scenes):
                scene_dict = scene.model_dump()

                # --- 【关键修改】强制统一命名为 "第x幕" ---
                new_title = f"第{scene_idx + 1}幕"
                scene_dict['title'] = new_title
                # ---------------------------------------

                images_b64, local_paths = [], []

                logger.info(
                    f"  处理场景 {scene_idx + 1}: {new_title}")

                # 图片处理逻辑
                for img_idx, filename in enumerate(scene.relevant_image_filenames):
                    clean_name = Path(filename).name
                    full_img_path = img_dir / clean_name

                    # 先尝试精确匹配
                    if not full_img_path.exists():
                        # 模糊匹配：处理文件名变化
                        for f in img_dir.glob(f"{clean_name}*"):
                            full_img_path = f
                            break

                    if full_img_path.exists():
                        b64_str = self._image_to_base64(str(full_img_path))
                        if b64_str:
                            images_b64.append(b64_str)
                            local_paths.append(str(full_img_path))
                    else:
                        logger.warning(
                            f"    图片未找到: {clean_name}")

                scene_dict['images_base64'] = images_b64
                scene_dict['local_image_paths'] = local_paths
                if 'relevant_image_filenames' in scene_dict:
                    del scene_dict['relevant_image_filenames']

                final_scenes.append(scene_dict)

            logger.info(f"✓ 解析完成，共生成 {len(final_scenes)} 幕场景")

            return {
                "case_title": result.case_title,
                "summary": result.summary,
                "learning_objectives": [obj.model_dump() for obj in result.learning_objectives],
                "total_scenes": len(final_scenes),
                "scenes": final_scenes,
                "case_folder": str(case_root_dir),
                "parse_time_seconds": round(time.time() - total_start, 2)
            }
        except Exception as e:
            logger.error(f"解析异常: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "status": "failed"}


async def parse_pbl_to_json(pdf_path: str):
    parser = PBLFastParser()
    return await parser.parse(pdf_path)

# --- 2. 原始图片提取器 ---


def get_raw_pdf_images(pdf_path: str) -> Dict[str, Any]:
    """
    使用 fitz (PyMuPDF) 快速提取所有页面图片。
    用于前端 View B (Raw PDF View)。
    """
    try:
        doc = fitz.open(pdf_path)
        full_text_buffer = []
        pages_content = []

        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            full_text_buffer.append(text)
            page_images = []

            for img_index, img in enumerate(page.get_images()):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n - pix.alpha < 4:
                        pass
                    else:
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    img_data = pix.tobytes("png")
                    # 使用 PIL 处理透明度并压缩
                    pil_image = Image.open(io.BytesIO(img_data))
                    if pil_image.mode in ('RGBA', 'LA') or (pil_image.mode == 'P' and 'transparency' in pil_image.info):
                        bg = Image.new('RGB', pil_image.size, (255, 255, 255))
                        if pil_image.mode == 'P':
                            pil_image = pil_image.convert('RGBA')
                        bg.paste(pil_image, mask=pil_image.split()[
                                 3] if len(pil_image.split()) > 3 else None)
                        pil_image = bg
                    elif pil_image.mode != 'RGB':
                        pil_image = pil_image.convert('RGB')

                    # 缩放
                    if max(pil_image.size) > 1024:
                        pil_image.thumbnail((1024, 1024))

                    buffered = io.BytesIO()
                    pil_image.save(buffered, format="JPEG", quality=75)
                    img_b64 = base64.b64encode(
                        buffered.getvalue()).decode('utf-8')

                    page_images.append({
                        'page_num': page_num + 1,
                        'img_index': img_index,
                        'base64': f"data:image/jpeg;base64,{img_b64}",
                        'width': pil_image.width,
                        'height': pil_image.height
                    })
                except Exception:
                    continue

            pages_content.append({
                'page_number': page_num + 1,
                'images': page_images
            })

        doc.close()
        return {
            'status': 'success',
            'data': {
                'total_pages': len(pages_content),
                'pages': pages_content
            }
        }
    except Exception as e:
        logger.error(f"Raw图片提取失败: {e}")
        return {'status': 'error', 'detail': str(e)}
