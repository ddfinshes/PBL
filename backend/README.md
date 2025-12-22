# PBL Multi-Agent 讨论系统

基于 LangGraph 和 Flask 的多 Agent 讨论系统，支持四个学生 Agent 之间的互动讨论，以及真实用户的参与。

## 功能特性

- 🤖 **四个学生 Agent**：每个 Agent 具有独特的性格、背景和专业领域
- 💬 **多 Agent 讨论**：Agent 之间可以自然互动和讨论
- 👤 **用户参与**：真实用户可以插入讨论，Agent 会响应用户的消息
- ⚙️ **可配置**：支持通过 API 自定义 Agent 的特征和属性
- 🔄 **LangGraph 管理**：使用 LangGraph 管理多 Agent 对话流程

## 技术栈

- **Flask**: Web 框架
- **LangGraph**: 多 Agent 对话流程管理
- **LangChain**: LLM 集成
- **OpenAI GPT-4**: 语言模型

## 项目结构

```
backend/
├── app.py                 # Flask 应用主文件
├── config.py              # 配置文件（包含默认配置）
├── requirements.txt       # 依赖包
├── run.sh                 # 启动脚本
├── test_api.py            # API 测试脚本
├── models/               # 数据模型
│   ├── __init__.py
│   └── agent.py          # Agent 模型定义
└── services/             # 业务逻辑服务
    ├── __init__.py
    ├── agent_manager.py  # Agent 管理器
    └── discussion_service.py  # 讨论服务
```

## 安装和运行

### 1. 激活 Conda 环境

```bash
conda activate pbl
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（可选）

`config.py` 中已包含默认配置，可以直接使用。如果需要自定义配置，可以创建 `.env` 文件：

创建 `.env` 文件（可选）：
```bash
touch .env
```

编辑 `.env` 文件（可选）：
```
OPENAI_API_KEY=your_openai_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True
API_PORT=5001
```

**注意**：如果使用默认端口 5000，macOS 系统可能会与 AirPlay Receiver 冲突，建议使用其他端口（如 5001）。

### 4. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动（如果端口未被占用）。

**注意**：如果端口 5000 被占用（macOS 的 AirPlay Receiver 默认使用此端口），可以通过环境变量修改端口：
```bash
export API_PORT=5001
python app.py
```

## API 接口

### 健康检查
```
GET /api/health
```

### 获取所有 Agent
```
GET /api/agents
```

### 获取指定 Agent
```
GET /api/agents/<agent_name>
```

### 更新 Agent 配置
```
PUT /api/agents/<agent_name>
Body: {
  "name": "小明",
  "personality": "积极乐观",
  "background": "计算机科学专业",
  "expertise": "软件开发",
  "speaking_style": "直接、热情"
}
```

### 开始讨论
```
POST /api/discussion/start
Body: {
  "topic": "讨论主题",
  "max_turns": 10
}
```

### 获取 Agent 回复
```
POST /api/discussion/agent-response
Body: {
  "agent_name": "小明",
  "topic": "讨论主题",
  "conversation_history": [...]
}
```

### 添加用户消息
```
POST /api/discussion/user-message
Body: {
  "message": "用户消息",
  "topic": "讨论主题",
  "conversation_history": [...]
}
```

### 重置讨论
```
POST /api/discussion/reset
```

## 默认 Agent 配置

系统预定义了四个学生 Agent：

1. **小明** - 计算机科学专业，积极乐观，擅长软件开发
2. **小红** - 心理学专业，细心谨慎，擅长用户研究
3. **小李** - 数学专业，理性冷静，擅长数据分析
4. **小张** - 设计专业，创意丰富，擅长用户体验设计

## 开发说明

- Agent 的特征可以通过前端自定义，通过 API 更新
- 讨论流程由 LangGraph 管理，确保对话的自然流畅
- 支持用户随时插入讨论，Agent 会响应用户的消息
- 所有对话历史都会被保存，用于上下文理解

## 注意事项

- 需要有效的 OpenAI API Key
- 建议使用 GPT-4 模型以获得更好的对话质量
- 可以根据需要调整 `MAX_CONVERSATION_TURNS` 和 `TEMPERATURE` 参数

