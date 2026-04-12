# XuanJi (玄机) 全栈项目创建方案

## Context

用户需要从零创建一个基于Web的本地-云端协同AI智能体系统。项目目录 `c:\Code\XuanJi` 当前为空（仅有 `.qoder/skills/` 开发规范文档）。需要搭建完整的前后端工程、数据库、AI集成、沙箱执行系统，并确保可直接启动运行。

## 推荐方案：7阶段渐进式构建

### Phase 0 — 项目脚手架 & 基础设施

**目标**: 前后端均可启动，health check 通过。

创建文件：
- `/.gitignore` — 忽略 node_modules, __pycache__, .env, dist 等
- `/.env` — 数据库凭证(root/root)、Ollama配置、在线API占位
- `/backend/environment.yml` — Conda环境定义 (name: xuanji, python=3.11)
- `/backend/app/__init__.py`
- `/backend/app/main.py` — FastAPI入口，CORS，/health端点
- `/backend/app/core/__init__.py`
- `/backend/app/core/config.py` — pydantic-settings 配置类
- `/backend/app/core/database.py` — SQLAlchemy引擎、会话、Base、init_db()自动建库建表
- `/frontend/` — 通过 `npm create vite@latest` 初始化 React+TS 模板
- `/frontend/tailwind.config.ts` — 梅花主题色板配置
- `/frontend/vite.config.ts` — /api代理到后端:8000
- `/frontend/.eslintrc.cjs`, `.prettierrc`, `tsconfig.json`, `postcss.config.js`

操作：
1. 创建 Conda 环境: `conda env create -f environment.yml`
2. 前端初始化: `pnpm create vite`, 安装 tailwindcss, zustand, react-router-dom, echarts 等（全程使用 pnpm）
3. 验证: backend `:8000/health` 返回 JSON, frontend `:5173` 渲染页面

### Phase 1 — 数据库层 (4张核心表)

**目标**: MySQL自动建库建表，ORM模型完备。

创建文件：
- `/backend/app/models/__init__.py` — 导出所有模型
- `/backend/app/models/user.py` — users表: id, username, email, hashed_password, created_at, updated_at, deleted_at
- `/backend/app/models/task.py` — tasks表: id, user_id(FK), title, description, status(pending/running/completed/failed), result, created_at, updated_at
- `/backend/app/models/tool.py` — tools表: id, name, description, code(TEXT), language, version, is_builtin, created_by(FK), created_at, updated_at
- `/backend/app/models/log.py` — logs表: id, task_id(FK), tool_id(FK), level, message, details(JSON), created_at
- `/backend/app/schemas/common.py` — ApiResponse[T] 统一响应格式
- `/backend/app/schemas/user.py`, `task.py`, `tool.py`, `log.py`, `chat.py`

关键设计：
- `init_db()` 先无库连接执行 `CREATE DATABASE IF NOT EXISTS xuanji`, 再建表
- BigInt主键、utf8mb4字符集、created_at/updated_at时间戳
- FastAPI lifespan 事件中调用 init_db()

### Phase 2 — 认证 & 用户系统

**目标**: 用户可注册登录，JWT鉴权。

创建文件：
- `/backend/app/core/security.py` — bcrypt哈希、JWT生成/验证
- `/backend/app/core/deps.py` — get_current_user 依赖
- `/backend/app/services/user_service.py` — 用户CRUD
- `/backend/app/api/__init__.py`, `/backend/app/api/v1/__init__.py`
- `/backend/app/api/v1/auth.py` — POST /register, POST /login, GET /me
- `/frontend/src/pages/LoginPage.tsx` — 登录/注册页面
- `/frontend/src/stores/authStore.ts` — 用户认证状态
- `/frontend/src/api/client.ts` — 基础请求封装
- `/frontend/src/api/auth.ts` — 认证API调用

### Phase 3 — AI客户端层

**目标**: Ollama和在线LLM均可调用并返回流式响应。

创建文件：
- `/backend/app/ai/__init__.py`
- `/backend/app/ai/base.py` — BaseLLMClient 抽象类 (chat, stream_chat)
- `/backend/app/ai/ollama.py` — OllamaClient (默认模型: `qingqi-qwen3.5:latest`)
- `/backend/app/ai/online.py` — OnlineLLMClient (OpenAI兼容)
- `/backend/app/ai/factory.py` — get_llm_client(), get_local_client(), get_online_client()
- `/backend/app/ai/prompts.py` — 所有系统提示词模板
- `/backend/app/api/v1/chat.py` — POST /chat (SSE流式响应)
- `/frontend/src/components/chat/ChatPanel.tsx` — 聊天面板
- `/frontend/src/components/chat/ChatInput.tsx` — 输入框
- `/frontend/src/components/chat/MessageBubble.tsx` — 消息气泡
- `/frontend/src/components/chat/StreamingIndicator.tsx` — 思考动画
- `/frontend/src/stores/chatStore.ts` — 消息状态管理
- `/frontend/src/hooks/useSSE.ts` — SSE流式处理Hook
- `/frontend/src/api/chat.ts` — 聊天API

### Phase 4 — 沙箱 & 工具执行引擎

**目标**: 可安全执行Python代码片段并返回结果。

创建文件：
- `/backend/app/sandbox/__init__.py`
- `/backend/app/sandbox/validator.py` — AST静态分析：禁止危险导入(os, subprocess, socket等)，验证函数签名
- `/backend/app/sandbox/executor.py` — subprocess执行器：30s超时、隔离环境变量、shell=False
- `/backend/app/services/tool_service.py` — 工具CRUD + 关键词搜索
- `/backend/app/api/v1/tools.py` — 工具管理端点
- `/backend/app/tools/.gitkeep` — 自动生成工具存放目录
- `/backend/sandbox/.gitkeep` — 沙箱工作目录

安全策略（多层防御）：
1. **静态分析**: ast.parse() 检查，禁止导入黑名单模块，验证函数签名
2. **运行时隔离**: subprocess.run(shell=False, timeout=30), 最小环境变量
3. **路径校验**: Path.resolve() + is_relative_to() 防止目录穿越
4. **资源限制**: 30秒超时硬限制

### Phase 5 — 智能体核心（系统大脑）

**目标**: 完整的 意图理解 → 工具检索 → 工具生成 → 执行 → 自进化 循环。

创建文件：
- `/backend/app/ai/agent.py` — 核心智能体编排器
- `/backend/app/ai/tool_generator.py` — 在线LLM生成Python工具代码
- `/backend/app/services/task_service.py` — 任务生命周期管理
- `/backend/app/services/log_service.py` — 结构化日志写入DB
- `/backend/app/api/v1/files.py` — GET /files/browse 目录浏览
- `/frontend/src/components/files/FolderSelector.tsx` — 文件夹选择器
- `/frontend/src/components/chat/ToolExecutionCard.tsx` — 工具执行卡片
- `/frontend/src/api/files.ts` — 文件浏览API

智能体执行循环（ReAct模式）：
```
用户消息 → [Ollama意图解析] → 任务/闲聊判断
  ↓(任务)
[工具检索(DB关键词+LLM辅助匹配)]
  ↓ 找到 → 直接执行
  ↓ 未找到 → [在线LLM生成工具代码]
  ↓
[代码校验(AST)] → [沙箱执行] → [结果解读(Ollama)]
  ↓
[自动保存工具到DB+磁盘] → 返回用户
```

SSE事件类型: thinking, tool_selected, tool_generating, tool_executing, tool_result, message, error, done

### Phase 6 — 统计面板、工具页面 & 主题美化

**目标**: 完整UI，梅花主题全面应用。

创建文件：
- `/backend/app/services/stats_service.py` — 聚合统计查询
- `/backend/app/api/v1/stats.py` — GET /stats/dashboard
- `/frontend/src/pages/ChatPage.tsx` — 聊天主页面
- `/frontend/src/pages/ToolsPage.tsx` — 工具管理页面
- `/frontend/src/pages/DashboardPage.tsx` — 统计面板页面
- `/frontend/src/components/layout/MainLayout.tsx` — 主布局壳
- `/frontend/src/components/layout/Sidebar.tsx` — 侧边栏导航
- `/frontend/src/components/layout/Header.tsx` — 顶栏
- `/frontend/src/components/tools/ToolListPanel.tsx` — 工具列表
- `/frontend/src/components/tools/ToolCard.tsx` — 工具卡片
- `/frontend/src/components/tools/ToolDetailModal.tsx` — 工具详情弹窗
- `/frontend/src/components/charts/EChart.tsx` — ECharts 通用 React 封装组件（遵循 echarts-charts skill 的 React Integration Pattern，含 ref 管理、resize 监听、dispose 清理）
- `/frontend/src/components/dashboard/StatsOverview.tsx` — 统计卡片（任务总数、成功率、工具数、活跃天数）
- `/frontend/src/components/dashboard/TaskTrendChart.tsx` — ECharts 折线图: 近7/30天任务趋势（smooth + areaStyle + markLine均值），遵循 chart-catalog Line Chart 模板
- `/frontend/src/components/dashboard/ToolUsageChart.tsx` — ECharts 水平柱状图: 工具使用次数排行（Top 10），遵循 chart-catalog Bar Chart 横向模板
- `/frontend/src/components/dashboard/TaskStatusPie.tsx` — ECharts 环形图: 任务状态分布（pending/running/completed/failed），遵循 chart-catalog Pie/Donut 模板（radius: ['35%', '65%']）
- `/frontend/src/components/dashboard/DailyActivityHeatmap.tsx` — ECharts 热力图: 按天/小时活动分布，遵循 chart-catalog Heatmap 模板（含 visualMap）

ECharts 实现规范（来自 echarts-charts skill）：
- 所有图表必须包含 tooltip 和 title
- 使用 `EChart` 通用组件渲染，通过 option prop 传入配置
- 容器尺寸通过 CSS（Tailwind className）控制，不在 init 中设定固定宽高
- 数值格式化使用中文习惯（万/亿缩写）
- 大数据集（500+）启用 `large: true` + `sampling: 'lttb'`
- 配色与梅花主题协调，注册自定义 ECharts 主题
- `/frontend/src/components/shared/Button.tsx`, `Modal.tsx`, `LoadingSpinner.tsx`, `EmptyState.tsx`

梅花主题色板：
| Token | 色值 | 用途 |
|-------|------|------|
| plum-50 | #FFF5F7 | 页面背景 |
| plum-100 | #FFE4EC | 卡片背景 |
| plum-200 | #FFC2D4 | 边框 |
| plum-300 | #FF8FAB | 标签 |
| plum-400 | #FF5C8A | 主要强调 |
| plum-500 | #E8366D | 主按钮 |
| plum-600 | #C41E56 | 悬停态 |
| ink | #2D1B25 | 正文 |

视觉特色：深梅色渐变侧边栏、粉白消息气泡、梅花花瓣加载动画、二次元风格空状态图

### 本地资源策略（无CDN依赖）

所有外部资源均下载到项目本地，确保离线可用：

**字体文件**（存放 `frontend/src/assets/fonts/`）：
- Inter（UI字体）— 从 Google Fonts 下载 woff2 文件到本地
- Noto Serif SC（中文标题字体）— 下载 woff2 到本地
- 在 `index.css` 中通过 `@font-face` 引用本地路径，不使用 Google Fonts CDN

**图标**（存放 `frontend/src/assets/icons/`）：
- 使用 `lucide-react` 图标库（npm安装，本地打包）
- 自定义梅花SVG图标直接放在 assets 中

**ECharts**：
- 通过 `npm install echarts` 安装到 node_modules，打包时 tree-shaking 按需引入
- 不使用 CDN 脚本标签

**所有npm包**均通过 `package.json` 管理，`pnpm install` 后完全本地可用
**所有pip包**均通过 `environment.yml` 管理，`conda env create` 后完全本地可用

## 关键配置值

```
# .env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=xuanji
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qingqi-qwen3.5:latest
LLM_PROVIDER=ollama
LLM_API_KEY=
LLM_API_BASE_URL=
LLM_MODEL_NAME=
SECRET_KEY=xuanji-secret-key-change-in-production
CORS_ORIGINS=http://localhost:5173
SANDBOX_DIR=./sandbox
SANDBOX_TIMEOUT=30
```

## API端点清单

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/v1/auth/register | 注册 |
| POST | /api/v1/auth/login | 登录 |
| GET | /api/v1/auth/me | 当前用户 |
| POST | /api/v1/chat/ | 与智能体对话(SSE) |
| GET | /api/v1/tasks/ | 任务列表 |
| GET | /api/v1/tasks/{id} | 任务详情 |
| GET | /api/v1/tools/ | 工具列表 |
| GET | /api/v1/tools/{id} | 工具详情 |
| GET | /api/v1/tools/search | 搜索工具 |
| DELETE | /api/v1/tools/{id} | 删除工具 |
| GET | /api/v1/files/browse | 浏览目录 |
| GET | /api/v1/stats/dashboard | 统计数据 |
| GET | /health | 健康检查 |

## 验证计划

1. **Phase 0**: `conda activate xuanji && uvicorn app.main:app` 启动后端，`npm run dev` 启动前端，浏览器访问 localhost:5173 能看到页面，/health 返回 JSON
2. **Phase 1**: 启动后端后 MySQL 中自动出现 xuanji 库和4张表
3. **Phase 2**: 可通过API注册用户、登录获取token、前端登录页面正常
4. **Phase 3**: 在聊天页面发送消息，Ollama返回流式响应显示在页面上
5. **Phase 4**: 工具CRUD API正常，沙箱可执行简单Python代码
6. **Phase 5**: 发送任务类消息 → 智能体完成意图解析、工具检索/生成、沙箱执行、结果返回的完整流程
7. **Phase 6**: 工具页面显示已注册工具，统计面板显示任务/工具/成功率数据
8. **最终**: `npm run lint` 和 `npm run typecheck` 通过，前后端协同正常
