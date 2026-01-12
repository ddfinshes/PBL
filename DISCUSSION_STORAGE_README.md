# PBL 模拟讨论数据管理说明 (Data Management for PBL Discussions)

本文档说明了系统如何管理不同场景（Scene）和触发问题（Trigger Question）下的并行讨论数据及其存储机制。

## 1. 核心存储结构

### 后端存储 (Backend State)
- **Session History Mapping**: 在 `server.py` 中，使用 `session_histories` 字典存储每个会话的数据。
- **消息映射 (messages_map)**: 每个会话拥有一个扁平化的 `messages_map`，存储消息 ID 到消息对象的映射。
- **隔离标识**: 每一条消息都通过 `scene_index` 和 `question_index` 进行标记，从而在同一个 Session 中区分不同问题的讨论内容。

### 持久化存储 (LangGraph Checkpoints)
- **复合线程 ID (Thread ID)**: 为了实现不同问题之间的讨论状态隔离，系统采用了复合 Thread ID 机制：
  `{session_id}_{scene_index}_{question_index}_{branch_id}`
- **作用**: 这种 ID 设计确保了当你从“问题 A”切换到“问题 B”时，LangGraph 能够加载完全独立的状态上下文，避免对话内容混淆。

## 2. 前后端数据流转

### 数据标记 (Tagging)
1. **切换问题**: 当用户在 `ViewC` 点击“查看”按钮时，前端通过 `/api/set-active-scene` 通知后端更新当前的场景和问题索引。
2. **消息产出**: 后端 Agent 生成回复时，会从全局状态 `pbl_info` 获取当前的索引，并将其附加在 WebSocket 消息中。
3. **前端接收**: `usePBLSocket.js` 接收到消息后，将其存入全局 `messages` 数组。

### 过滤展示 (Filtering)
- **ViewD (演化图)**、**ViewE (故事线)**、**ViewF (对话框)** 并不直接展示所有消息。
- 它们通过监听全局状态 `activeQuestionInfo`，从 `messages` 数组中通过 `sceneIndex` 和 `questionIndex` 进行**实时过滤**。
- **动态 UI**: 如果当前选中的问题在 `messages` 中没有任何匹配项，`ViewF` 会自动判定为“尚未开始”并展示“开始讨论”按钮。

## 3. 讨论数据结构 (Message Schema)

每一条存储或传输的消息均包含以下关键字段：

```json
{
  "id": "uuid",
  "parent_id": "parent_uuid",  // 用于实现分支讨论 (Branching)
  "branch_id": "main",        // 分支标识
  "agent": "student_analyst",  // 发言角色
  "content": "消息正文",
  "scene_index": 0,           // 所属场景索引
  "question_index": 1          // 所属问题索引
}
```

## 4. 如何触发新讨论

当切换到一个全新的触发问题时：
1. 后端检测到该 `(scene, question)` 组合对应的 `thread_id` 尚无 Checkpoint。
2. 前端检测到 `filteredMessages` 为空，显示初始引导界面。
3. 点击“开始讨论”后，前端发送 `start_discussion` 指令，并携带当前的索引。
4. 后端初始化该特定路径下的 LangGraph 状态，开启全新的对话循环。

---
*注：该机制保证了即使在同一个浏览器标签页中，用户也可以通过切换 ViewC 的视角，在不同的 PBL 问题之间无缝跳转，且各自的讨论进度和逻辑分支均被完整保留。*
