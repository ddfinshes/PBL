"""PBL2.backend.config
统一管理模型配置信息。
"""
import os

# 从环境变量读取 DashScope API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", 'sk-de225921dd58479887c1f14d8249b337')  # 请确保已 export

# DashScope OpenAI-Compatible endpoint (北京地域)
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 模型名称（可改成 qwen3-32b 等）
LLM_MODEL_NAME = "qwen-plus"

# --- 额外请求体参数 ---
# 通义千问支持 enable_thinking，可按需扩展
EXTRA_BODY = {"enable_thinking": False}

# 若还有其他 OpenAI 参数，可放在此处；保持为空即可
MODEL_KWARGS: dict = {}
