import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """应用配置类"""
    # OpenAI 模型配置：可选值 "gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'sk-de225921dd58479887c1f14d8249b337')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'qwen3-32b')
    # base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')


    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # API 配置
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    # 默认使用 5001 端口，避免与 macOS AirPlay Receiver 冲突
    API_PORT = int(os.getenv('API_PORT', 5002))
    
    # Agent 配置
    MAX_CONVERSATION_TURNS = int(os.getenv('MAX_CONVERSATION_TURNS', 50))
    TEMPERATURE = float(os.getenv('TEMPERATURE', 0.7))
    # 是否启用流式输出（stream），默认 False（非流式，更稳定）
    ENABLE_STREAM = os.getenv('ENABLE_STREAM', 'False').lower() == 'true'
    