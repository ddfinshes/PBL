# PBL 前端可视化大屏

基于 Vue 3 的多 Agent 讨论可视化大屏前端界面。

## 功能特性

- 🎨 **三栏布局设计**：30% - 40% - 30% 的响应式布局
- 💬 **实时讨论交互**：View E 核心交互区支持实时消息显示和用户参与
- 🤖 **多 Agent 展示**：展示四个学生 Agent 的讨论内容
- 📊 **多视图展示**：8 个不同的视图组件展示各类信息
- 🔄 **实时通信**：通过 REST API 连接后端讨论系统

## 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── DashboardLayout.vue    # 主布局组件
│   │   └── views/
│   │       ├── ViewA.vue          # 左栏顶部视图
│   │       ├── ViewB.vue          # 左栏中部视图
│   │       ├── ViewC.vue          # 左栏底部视图
│   │       ├── ViewD.vue          # 中栏顶部视图
│   │       ├── ViewE.vue          # 中栏核心交互区
│   │       ├── ViewF.vue          # 右栏顶部视图
│   │       ├── ViewG.vue          # 右栏中部视图
│   │       └── ViewH.vue          # 右栏底部视图
│   ├── stores/
│   │   └── discussion.js          # Pinia 状态管理
│   ├── api/
│   │   └── discussion.js          # API 服务层
│   ├── App.vue                    # 根组件
│   ├── main.js                    # 入口文件
│   └── style.css                  # 全局样式
├── index.html                     # HTML 模板
├── vite.config.js                 # Vite 配置
└── package.json                   # 项目配置
```

## 安装和运行

### 1. 安装依赖

```bash
npm install
# 或
yarn install
# 或
pnpm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动。

### 3. 构建生产版本

```bash
npm run build
```

### 4. 预览生产构建

```bash
npm run preview
```

## 布局说明

### 左栏 (30%)
- **View A**: 系统概览
- **View B**: 数据分析
- **View C**: 信息面板

### 中栏 (40%)
- **View D**: 统计概览
- **View E**: 讨论交互区（核心功能）
  - 实时消息显示
  - Agent 身份标识
  - 消息时间戳
  - 用户输入和发送
  - 连接状态指示

### 右栏 (30%)
- **View F**: 实时指标
- **View G**: 活动日志
- **View H**: 系统状态

## View E 核心功能

### 消息显示
- Agent 消息：显示四个学生 Agent（小明、小红、小李、小张）的发言
- 用户消息：区分显示用户输入的消息
- 消息类型：支持陈述、提问、建议等类型标识
- 时间戳：每条消息显示发送时间
- 自动滚动：新消息自动滚动到底部

### 用户交互
- 文本输入框：支持多行文本输入
- 发送按钮：点击发送消息
- 回车快捷：按 Enter 键快速发送
- 发送状态：显示发送中、成功、失败状态

### 连接管理
- 连接状态：实时显示后端连接状态
- 自动重连：连接断开时提示用户

## API 集成

前端通过 REST API 与后端通信：

- `GET /api/health` - 健康检查
- `GET /api/agents` - 获取所有 Agent
- `POST /api/discussion/start` - 开始讨论
- `POST /api/discussion/user-message` - 发送用户消息
- `POST /api/discussion/agent-response` - 获取 Agent 回复
- `POST /api/discussion/reset` - 重置讨论

## 技术栈

- **Vue 3**: 渐进式 JavaScript 框架
- **Vite**: 下一代前端构建工具
- **Pinia**: Vue 状态管理
- **Axios**: HTTP 客户端
- **CSS3**: 现代化样式设计

## 样式特点

- 深色主题：适合大屏展示的深色配色方案
- 渐变背景：现代化的渐变效果
- 响应式设计：适配不同屏幕尺寸
- 动画效果：流畅的交互动画
- 加载状态：优雅的加载指示器

## 开发说明

### 添加新视图

1. 在 `src/components/views/` 目录下创建新的视图组件
2. 在 `DashboardLayout.vue` 中引入并使用
3. 添加相应的样式和功能

### 自定义样式

全局样式在 `src/style.css` 中定义，组件样式在各组件的 `<style>` 标签中。

### 状态管理

使用 Pinia 管理讨论状态，相关逻辑在 `src/stores/discussion.js` 中。

## 注意事项

1. 确保后端服务运行在 `http://localhost:5001`（默认端口已改为 5001，避免与 macOS AirPlay Receiver 冲突）
2. 如需修改 API 地址，请更新 `vite.config.js` 中的 proxy 配置
3. 建议使用现代浏览器（Chrome、Firefox、Safari、Edge）

## 后续改进

- [ ] 添加 WebSocket 支持实现真正的实时通信
- [ ] 添加消息搜索和过滤功能
- [ ] 添加 Agent 配置界面
- [ ] 添加讨论主题选择功能
- [ ] 添加消息导出功能
- [ ] 优化移动端适配

