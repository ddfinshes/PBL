# PBL Project

This project is a Problem-Based Learning (PBL) application featuring an AI-powered student agent discussion panel. It consists of a Vue.js frontend and a Python FastAPI backend using LangChain.

## Project Structure

```
PBL/
├── backend/      # FastAPI backend application
│   ├── agents.py
│   ├── server.py
│   ├── graph.py
│   └── requirements.txt
├── frontend/     # Vue.js frontend application
│   ├── src/
│   └── package.json
└── Readme.md
```

## Setup

### Backend

1. Navigate to the backend directory:
   ```bash
   cd PBL/backend
   ```
2. Create a Python virtual environment and activate it. For example, using Conda with Python 3.9:
   ```bash
   conda create --name pbl-env python=3.9 -y
   conda activate pbl-env
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd PBL/frontend
   ```
2. Install the required Node.js dependencies:
   ```bash
   npm install
   ```

## Running the Application

You will need two separate terminals to run the backend and frontend servers.

1. **Run the Backend Server**

   * From the `PBL/` root directory, run:
     ```bash
     vicorn backend.server:app_fastapi --reload
     ```
   * The backend will be available at `http://127.0.0.1:8000`.
2. **Run the Frontend Development Server**

   * From the `PBL/frontend/` directory, run:
     ```bash
     npm run dev
     ```
   * The frontend will typically be available at `http://localhost:5173`.

## Testing

1. “认知时钟” Glyph (Cognitive Rhythm Ring)
   目前的环形图只反映了总量。PBL 更看重讨论的“轮转”和“动态”。

设计思路：将外圈设计成从 12 点钟方向开始顺时针排列的小刻度线或色块，每一个刻度代表一次发言。
编码维度：
颜色：发言 Agent 的颜色。
刻度长度：单次发言的 Token 长度。
刻度间隔：如果两次发言之间时间跨度大，可以留出间隙。
价值：一眼就能看出这个主题是某个 Agent 的“一言堂”，还是大家高频往复的“头脑风暴”。
2. “认知偏向”雷达图 (Cognitive Balance Radar)
PBL 的核心是引导学生从“临床表现”转向“病理机制”。

设计思路：在节点圆心中嵌入一个极简的三角形或四边形雷达图。
编码维度：
三个轴分别代表：现象描述（Symptoms）、机制推理（Mechanism）、疑问质疑（Questioning）。
根据该主题下消息的关键词命中所占比例，调整雷达图形状。
价值：让教师看缩略图就能发现：“这个主题大家一直在聊症状，没有深入到机制”。
这两个我同意。

To run the backend agent tests, navigate to the `PBL/` root directory and run:

```bash
python -m unittest backend/test_agents.py
```
