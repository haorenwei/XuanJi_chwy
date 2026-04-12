# 璇玑 (XuanJi) — 多智能体 AI 对话系统

璇玑是一个基于"四象协作"理念的多智能体 AI 对话系统。通过 **晴（意图识别）**、**焕（情感分析）**、**遥（风格设计）**、**玄（对话生成）** 四大 AI 角色的分工与协同，构建出既具备强逻辑推理能力，又能提供温暖陪伴体验的对话体系。

> **注意：** 目前工具功能已被停用，等待未来后续开发。

## 特性

- **多智能体协作** — 四象角色各司其职，形成意图→情绪→风格→对话的闭环
- **流式 SSE 交互** — 实时流式输出，前端边收边播，极低首字节延迟
- **多模型接入** — 支持本地 Ollama 与 OpenAI 兼容的在线模型，工厂模式灵活切换
- **情感感知与记忆** — 长期情绪追踪、用户画像构建、记忆压缩与摘要
- **AI 身份演化** — 可个性化的 AI 角色设定，支持人设、说话风格与价值观演进
- **安全沙箱执行** — 工具代码在隔离沙箱中执行，保障系统安全（暂停中）

## 系统架构

```
┌──────────────────────────────────────────────────┐
│                   前端 (React)                     │
│         TypeScript · Vite · TailwindCSS · Zustand  │
└──────────────┬───────────────────────────────────┘
               │ SSE / REST API
┌──────────────▼───────────────────────────────────┐
│                  后端 (FastAPI)                     │
│  ┌─────────────────────────────────────────────┐  │
│  │              Agent 编排器                      │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │  │
│  │  │ 晴  │ │ 焕  │ │ 遥  │ │ 玄  │ │ 机  │  │  │
│  │  │意图 │ │情感 │ │风格 │ │对话 │ │工具 │  │  │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘  │  │
│  └─────────────────────────────────────────────┘  │
│  LLM 工厂 · 服务层 · 沙箱执行器                     │
└──────────────┬───────────────────────────────────┘
               │ SQLAlchemy ORM
┌──────────────▼───────────────────────────────────┐
│                  MySQL 数据库                       │
└──────────────────────────────────────────────────┘
```

### 四象智能体

| 角色 | 代号 | 职责 |
|------|------|------|
| **晴** | Qing | 意图识别与行为推测，提取意图、用户状态与目标路径 |
| **焕** | Huan | 多维情感分析与心理建模，输出情绪状态、风险信号与交互建议 |
| **遥** | Yao | 风格设计，将情绪分析转化为回复风格指引（语气、结构、长度） |
| **玄** | Xuan | 对话生成，融合多源上下文生成自然、温暖、口语化的回复 |
| **机** | Ji | 工具管理（暂停中），负责工具匹配、生成、执行与迭代优化 |

## 技术栈

### 后端
- **Python 3.11** + **Conda** 环境管理
- **FastAPI** — 异步 Web 框架，SSE 流式接口
- **SQLAlchemy 2.0** — ORM 与数据库管理
- **PyMySQL** — MySQL 驱动
- **httpx** — 异步 HTTP 客户端（调用 LLM API）
- **Pydantic v2** — 数据验证与序列化
- **python-jose** + **passlib** — JWT 认证与密码哈希

### 前端
- **React 19** + **TypeScript**
- **Vite** — 构建工具与开发服务器
- **TailwindCSS 4** — 样式系统
- **Zustand** — 状态管理
- **ECharts** — 数据可视化
- **React Router 7** — 路由管理

### AI 模型
- **Ollama** — 本地模型推理
- **OpenAI 兼容 API** — 在线模型接入（通义千问等）

## 快速开始

### 前置要求

- Python 3.11+（推荐使用 Conda）
- Node.js 18+
- MySQL 8.0+
- pnpm（前端包管理）

### 1. 克隆项目

```bash
git clone https://github.com/haorenwei/XuanJi.git
cd XuanJi
```

### 2. 后端配置

```bash
# 创建 Conda 环境
conda env create -f backend/environment.yml
conda activate xuanji

# 复制并编辑环境配置
cp backend/.env.example .env
# 编辑 .env 文件，填入数据库密码、LLM API Key 等
```

`.env` 关键配置项：

```env
# 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=xuanji

# AI 模型（二选一）
# 方式一：本地 Ollama
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=your-model:latest

# 方式二：在线模型（OpenAI 兼容）
LLM_PROVIDER=online
LLM_API_KEY=your-api-key
LLM_API_BASE_URL=https://your-api-endpoint/v1
LLM_MODEL_NAME=your-model-name

# 安全
SECRET_KEY=change-me-to-random-string
```

### 3. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --reload-dir app --port 8000
```

后端启动时会自动创建数据库和表结构。访问 `http://localhost:8000/health` 验证服务是否正常。

### 4. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

前端开发服务器运行在 `http://localhost:5173`，已配置代理将 `/api` 请求转发到后端。

## 项目结构

```
XuanJi/
├── backend/
│   ├── app/
│   │   ├── ai/                  # AI 核心
│   │   │   ├── skills/          # 四象角色技能定义
│   │   │   │   ├── xuanji-qing/ # 晴 - 意图识别
│   │   │   │   ├── xuanji-huan/ # 焕 - 情感分析
│   │   │   │   ├── xuanji-yao/  # 遥 - 风格设计
│   │   │   │   ├── xuanji-xuan/ # 玄 - 对话生成
│   │   │   │   └── xuanji-ji/   # 机 - 工具管理
│   │   │   ├── agent.py         # Agent 编排器
│   │   │   ├── base.py          # LLM 客户端基类
│   │   │   ├── factory.py       # LLM 工厂模式
│   │   │   ├── online.py        # 在线模型客户端
│   │   │   ├── ollama.py        # Ollama 客户端
│   │   │   └── tool_generator.py # 工具代码生成器
│   │   ├── api/v1/              # REST API 路由
│   │   ├── core/                # 核心基础设施
│   │   ├── models/              # 数据库模型
│   │   ├── schemas/             # 请求/响应模式
│   │   ├── services/            # 业务服务层
│   │   ├── sandbox/             # 沙箱执行环境
│   │   └── main.py              # 应用入口
│   └── environment.yml          # Conda 环境定义
├── frontend/
│   ├── src/
│   │   ├── api/                 # API 客户端封装
│   │   ├── components/          # UI 组件
│   │   ├── pages/               # 页面组件
│   │   ├── stores/              # Zustand 状态管理
│   │   ├── types/               # TypeScript 类型定义
│   │   └── utils/               # 工具函数
│   └── package.json
├── .env                         # 环境变量（不提交）
└── .gitignore
```

## 数据库模型

系统包含以下核心数据表：

| 表名 | 说明 |
|------|------|
| `users` | 用户账号（支持软删除） |
| `conversations` | 对话会话 |
| `messages` | 对话消息（含情感快照） |
| `user_settings` | 用户 AI 模型配置 |
| `token_usages` | Token 用量记录 |
| `emotion_records` | 情感分析记录 |
| `user_profiles` | 用户心理画像 |
| `ai_identities` | AI 身份与人设 |
| `memory_summaries` | 记忆压缩摘要 |
| `tasks` | 后台任务 |
| `tools` | 工具注册表 |
| `logs` | 系统日志 |

## API 概览

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /api/v1/auth/login` | 用户登录，返回 JWT |
| 认证 | `POST /api/v1/auth/register` | 用户注册 |
| 聊天 | `POST /api/v1/chat/` | 流式 SSE 对话 |
| 会话 | `GET /api/v1/conversations/` | 获取会话列表 |
| 设置 | `GET/PUT /api/v1/settings/` | 用户设置管理 |
| 统计 | `GET /api/v1/stats/` | 使用统计与概览 |

## 常见问题

**后端无法连接数据库**
- 检查 `.env` 中数据库主机、端口、账号、密码是否正确
- 确认 MySQL 服务已启动，字符集为 `utf8mb4`

**前端无法访问后端接口**
- 确认后端运行在 `8000` 端口
- 检查 `vite.config.ts` 代理配置

**LLM 配置错误**
- 确认 `.env` 中 `LLM_PROVIDER` 与对应的 API Key / URL 已正确填写
- 使用 Ollama 时确认本地服务已启动

## 许可证

本项目仅供学习与个人使用。
