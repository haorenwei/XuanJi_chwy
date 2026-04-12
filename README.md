# 璇玑 (XuanJi) — 多智能体 AI 对话系统

璇玑是一个基于"五象协作"理念的多智能体 AI 对话系统。通过 **晴（意图识别）**、**焕（情感分析）**、**遥（风格设计）**、**玄（对话生成）**、**机（系统迭代）** 五大 AI 角色的分工与协同，构建出既具备强逻辑推理能力，又能提供温暖陪伴体验的对话体系。

> **注意：** 工具执行功能已停用，机的职责已从"工具执行者"转变为"AI系统迭代者"，在后台独立运行系统优化任务。

## 特性

- **多智能体协作** — 五象角色各司其职，形成意图→情绪→风格→对话的闭环
- **流式 SSE 交互** — 实时流式输出，前端边收边播，极低首字节延迟
- **多模型接入** — 支持本地 Ollama 与 OpenAI 兼容的在线模型，工厂模式灵活切换
- **五角色独立配置** — 每个 AI 角色在记忆体页面单独配置 LLM 提供商与模型，无默认值，无 Fallback
- **Skill 文件体系** — 各角色 Prompt、人设、演化规则以 Skill 文件形式组织（替代硬编码），修改无需改动代码
- **情感感知与记忆** — 长期情绪追踪、用户画像构建、记忆压缩与摘要
- **AI 身份演化** — 可个性化的 AI 角色设定，支持人设、说话风格与价值观演进
- **后台系统迭代** — 机在后台定时执行规则引擎优化、对话质量自评、画像监控、身份迭代、流程效率分析
- **安全沙箱执行** — 工具代码在隔离子进程中执行，保障系统安全（工具功能已停用）

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
│  │  │意图 │ │情感 │ │风格 │ │对话 │ │迭代 │  │  │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘  │  │
│  └─────────────────────────────────────────────┘  │
│  LLM 工厂 · 服务层 · 沙箱执行器                     │
└──────────────┬───────────────────────────────────┘
               │ SQLAlchemy ORM
┌──────────────▼───────────────────────────────────┐
│                  MySQL 数据库                       │
└──────────────────────────────────────────────────┘
```

### 五象智能体

| 角色 | 代号 | 职责 | 降级策略 |
|------|------|------|----------|
| **晴** | Qing | 意图调度中枢，分析用户消息的意图类型（chat/task），决定是否启动情绪分析 | LLM 不可用时规则引擎兜底，默认 chat |
| **焕** | Huan | 多维情感分析与心理建模，输出情绪状态、风险信号与交互建议 | 分析失败时跳过，返回 None，不阻塞对话 |
| **遥** | Yao | 风格设计师，根据焕的情绪分析动态生成回复格式指引（通过 LLM 调用） | LLM 未配置或失败时降级到静态情绪-风格映射模板 |
| **玄** | Xuan | 对话核心，融合多源上下文（人设、情绪、记忆、画像、格式）生成最终回复 | 配置缺失时直接报错，为核心对话能力 |
| **机** | Ji | AI 系统迭代者（后台独立运行），负责规则引擎优化、对话质量自评、画像监控、身份迭代、流程效率分析 | 后台定时任务，不参与用户对话流程 |

### 协作流程

```
用户消息 → 晴(意图识别) → 焕(情绪分析，按需并行)
                        → 遥(风格设计)
                        → 玄(对话生成)

机 在后台独立运行，每小时定时执行5项系统优化任务
```

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

# 安全
SECRET_KEY=change-me-to-random-string
```

> **重要：** 所有 AI 角色（玄/晴/焕/遥/机）的 LLM 配置（API Key、模型名称等）**只能在前端「记忆体」页面进行配置**，不在 `.env` 中设置。首次使用时，系统会提醒用户前往记忆体页面完成配置。每个角色独立配置，无默认值，无 Fallback，配置缺失时直接报错提醒。

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
│   │   │   ├── agent.py         # Agent 编排器（多角色协作）
│   │   │   ├── base.py          # LLM 客户端基类 + Skill 文件加载器
│   │   │   ├── factory.py       # LLM 工厂（5个独立工厂函数，无Fallback）
│   │   │   ├── online.py        # 在线模型客户端
│   │   │   ├── ollama.py        # Ollama 客户端
│   │   │   ├── skills/          # AI 角色 Skill 文件（替代 prompts.py）
│   │   │   │   ├── xuanji-xuan/ # 玄（SKILL.md, persona.md, ...）
│   │   │   │   ├── xuanji-huan/ # 焕
│   │   │   │   ├── xuanji-yao/  # 遥
│   │   │   │   ├── xuanji-qing/ # 晴
│   │   │   │   └── xuanji-ji/   # 机
│   │   │   ├── tool_generator.py # 工具代码生成器（已停用）
│   │   │   └── intent_rules.json # 意图规则引擎（机定时优化）
│   │   ├── api/v1/              # REST API 路由
│   │   ├── core/                # 核心基础设施（config, database, exceptions, security）
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
| `user_settings` | 用户 AI 模型配置（五角色独立配置） |
| `token_usages` | Token 用量记录（按角色分类） |
| `emotion_records` | 情感分析记录 |
| `user_profiles` | 用户心理画像 |
| `ai_identities` | AI 身份与人设 |
| `memory_summaries` | 记忆压缩摘要 |
| `tasks` | 后台任务 |
| `tools` | 工具注册表 |
| `tool_versions` | 工具版本快照 |
| `tool_compositions` | 工具组合关系（数据库保留，业务代码已清理） |
| `logs` | 系统日志 |

## API 概览

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /api/v1/auth/register` | 用户注册 |
| 认证 | `POST /api/v1/auth/login` | 用户登录，返回 JWT |
| 认证 | `GET /api/v1/auth/me` | 获取当前用户信息 |
| 聊天 | `POST /api/v1/chat/` | 流式 SSE 对话（支持非流式） |
| 会话 | `GET /api/v1/conversations/` | 获取会话列表 |
| 会话 | `POST /api/v1/conversations/` | 创建新会话 |
| 会话 | `GET /api/v1/conversations/recent-messages` | 获取近期消息 |
| 会话 | `GET /api/v1/conversations/{id}/messages` | 获取会话消息 |
| 情绪 | `GET /api/v1/conversations/emotions/latest` | 最新情绪记录 |
| 情绪 | `GET /api/v1/conversations/emotions/history` | 情绪历史 |
| 画像 | `GET /api/v1/conversations/profile` | 用户心理画像 |
| 身份 | `GET /api/v1/conversations/identities` | AI 角色身份列表 |
| 身份 | `PUT /api/v1/conversations/identities/{name}` | 更新 AI 角色身份 |
| 记忆 | `GET /api/v1/conversations/memories` | 记忆摘要查询 |
| 设置 | `GET/PUT /api/v1/settings/` | 用户设置管理 |
| 设置 | `GET /api/v1/settings/token-usage` | Token 用量查询 |
| 统计 | `GET /api/v1/stats/dashboard` | 仪表板统计 |
| 统计 | `GET /api/v1/stats/token-by-role` | 按角色统计 Token |
| 统计 | `GET /api/v1/stats/token-daily` | 每日 Token 趋势 |
| 统计 | `GET /api/v1/stats/token-by-model` | 按模型统计 Token |
| 工具 | `GET/POST /api/v1/tools/` | 工具列表/创建 |
| 工具 | `GET /api/v1/tools/search` | 工具搜索 |
| 工具 | `GET /api/v1/tools/export` | 导出工具 |
| 工具 | `POST /api/v1/tools/import` | 导入工具 |
| 工具 | `GET/PUT/DELETE /api/v1/tools/{id}` | 工具 CRUD |
| 工具 | `GET /api/v1/tools/{id}/versions` | 工具版本历史 |
| 工具 | `POST /api/v1/tools/{id}/rollback/{ver}` | 工具版本回滚 |
| 文件 | `GET /api/v1/files/browse` | 沙箱目录浏览 |
| 任务 | `GET /api/v1/tasks/` | 任务列表 |
| 日志 | `GET /api/v1/logs/` | 系统日志查询 |

## 常见问题

**后端无法连接数据库**
- 检查 `.env` 中数据库主机、端口、账号、密码是否正确
- 确认 MySQL 服务已启动，字符集为 `utf8mb4`

**前端无法访问后端接口**
- 确认后端运行在 `8000` 端口
- 检查 `vite.config.ts` 代理配置

**LLM 配置错误提示"AI配置缺失"**
- 所有 AI 角色的 LLM 配置**只能在前端「记忆体」页面设置**
- 至少需要配置玄（对话AI）才能正常对话
- 每个角色独立配置，无默认值，无 Fallback
- 使用 Ollama 时确认本地服务已启动

## 许可证

开源开源

## 作者的碎碎念
注意项目由AI coding(qoder)完成，存在很多bug和新增功能与旧的内容没有更新导致的冲突。
由于bug真太多了，工具模块，现在给我砍掉了，等以后由时间再说吧（大概率整个项目我都鸽了）
自己找ai一个一个，改的太累了，遂发布。(实习给我干的体力活，人干嘛了，晚上还要来跑这个项目)

说实话，现在的功能跟我预期差了很多，本来是想做在软件上的，
但是那个我跑了个demo版本，刚开始就一堆bug，就放弃了，转web了。

最初设想：做个跟智能体差不多的功能，类似个人助手。
可以对AI说自然语言，然后AI会理解你的意图
（比如AI自己写工具获取一些实时信息，获取用户需求中缺失的信息补充，然后将结果，和AI分析的用户画像、设定的身份，进行统一来回答）（感觉跟skill也差不多）
(小tips：
我提问，我下午想出去有什么建议吗？   
AI：目前检测缺失信息，目前时间/地点..... -> 创建/调用工具/询问 -> 
得到完整信息，结合用户习惯和记忆信息去上网搜索天气/景点...... -> 
信息补完+用户画像+ai设定，综合统一 -> 回复用户 
后台ai模型，对整体环节进行评估、迭代。
)
（再比如，可以完成用户的一些小要求之类的，对本地文件的操作、帮忙存储文档生成知识记忆库之类的、帮忙分析excel表，自然语言查数据库......）（做了前半段给我砍了）

通过这种多轮的对话，来让AI自我迭代（完善她们自己的skill），   （有迭代机制，但我不知道是否达到了预期，我估计大概没有）
逐渐分析用户，然后将这些分析数据，统合进行蒸馏，蒸馏出用户的skill(没做)


（最初设想就是做个简单的毕设,难蹦）
