1. 测试agent：
python -m unittest PBL2/backend/test_agents.py
2. PBL目录下打开终端运行：
    uvicorn backend.server:app_fastapi --reload
3. PBL/frontend目录下执行： npm run dev