# XuanJi 项目审查与优化方案

## Context

项目审查文档 `PROJECT_AUDIT_DOC.md` 与实际代码存在多处不一致。用户确认了以下核心决策：
1. **所有AI角色配置无默认值** - 强制用户在「记忆体」页面手动配置
2. **每个AI角色完全独立配置** - 不允许复用其他角色配置，无任何 Fallback
3. **复合工具确认废弃** - 清理所有 composite/pipeline 相关业务代码，保留数据库表向后兼容
4. **缺失配置时直接报错** - 不做静默降级，明确提示用户前往配置

---

## 修改清单

### 第一部分：AI 配置严格化

#### 1. 新建 `backend/app/core/exceptions.py`

创建自定义异常类 `LLMConfigError(Exception)`：
- 属性：`role_name`（AI角色名如"玄/对话AI"）、`missing_fields`（缺失字段列表）
- `__str__` 返回中文友好提示，如："AI配置缺失：对话AI（玄）未配置 provider。请前往「记忆体」页面完成配置。"

#### 2. 修改 `backend/app/core/config.py`

清空以下硬编码默认值：
| 行 | 当前值 | 改为 |
|----|--------|------|
| 17 | `llm_provider: str = "ollama"` | `llm_provider: str = ""` |
| 26 | `intent_llm_model_name: str = "qwen3-vl-235b-a22b-thinking"` | `intent_llm_model_name: str = ""` |
| 32 | `emotion_llm_model_name: str = "qwen3.6-plus"` | `emotion_llm_model_name: str = ""` |
| 38 | `format_llm_model_name: str = "qwen3-vl-32b-thinking"` | `format_llm_model_name: str = ""` |

更新注释，移除 `(fallback to chat LLM if not set)` 描述。

#### 3. 重写 `backend/app/ai/factory.py`

**删除**以下不再使用的函数：
- `get_llm_client()` (行7-14) - 无外部调用者
- `get_local_client()` (行17-19) - 无外部调用者
- `get_online_client()` (行22-24) - 无外部调用者

**添加**私有辅助函数 `_create_client_from_setting(user_setting, prefix, role_name)`：
- 统一处理从 user_setting 提取配置并创建客户端的逻辑
- `prefix` 为字段前缀（如 `"llm"`, `"tool_llm"`, `"intent_llm"` 等）
- 验证 user_setting 非 None，provider 非空，根据 provider 类型校验必要字段
- 缺失则抛出 `LLMConfigError`

**重写 5 个工厂函数**，每个函数逻辑统一为：
1. 验证 `user_setting` 非 None → 否则抛 `LLMConfigError`
2. 读取该角色对应前缀的 provider 字段
3. provider 为空 → 抛 `LLMConfigError`
4. provider="online" → 校验 api_key、base_url、model_name 后创建 `OnlineLLMClient`
5. provider="ollama" → 校验 base_url、model_name 后创建 `OllamaClient`（对话AI玄还使用 `ollama_base_url`/`ollama_model`，其他角色使用 `{prefix}_model_name` + 默认 ollama base_url）

各函数的字段前缀映射：
- `get_chat_llm_client` → 前缀 `llm`（特殊：ollama 用 `ollama_base_url`/`ollama_model`）
- `get_tool_llm_client` → 前缀 `tool_llm`（特殊：ollama 用 `tool_ollama_base_url`/`tool_ollama_model` 历史字段）
- `get_intent_llm_client` → 前缀 `intent_llm`
- `get_emotion_llm_client` → 前缀 `emotion_llm`
- `get_format_llm_client` → 前缀 `format_llm`

**完全移除**：所有从 `settings` 全局配置读取的 Fallback 逻辑，不再 `from app.core.config import settings`。

#### 4. 适配 `backend/app/ai/agent.py` — 错误处理 + 遥 LLM 集成

**4a. 错误处理适配：**
- 行12-16 导入：新增 `from app.core.exceptions import LLMConfigError`，新增 `from app.ai.factory import get_format_llm_client`
- 行52-56 `__init__`：将 `self.llm = get_chat_llm_client(user_setting)` 包裹在 try/except 中，捕获 `LLMConfigError` 后记录到 `self._config_error`
- 行69+ `process_message()` 入口：新增配置错误守卫
  ```python
  if self._config_error:
      yield {"type": "error", "content": str(self._config_error)}
      yield {"type": "done", "content": ""}
      return
  ```
- 行718 `_parse_intent()`：捕获 `LLMConfigError`，记录 warning，默认返回 `{"action_type": "chat", ...}`（规则匹配仍工作）
- 行884 `_decide_tool_iteration()`：捕获 `LLMConfigError`，返回 None
- 工具生成调用处（约行339）：捕获 `LLMConfigError`，yield error 事件

**4b. 遥（格式AI）LLM 调用集成：**

当前问题：agent.py 行591-604 使用纯静态模板 `EMOTION_AWARE_FORMAT_TEMPLATE` + `EMOTION_STYLE_MAP` 生成格式指引，没有调用 `get_format_llm_client`。但 prompts.py 中已有完整的 `FORMAT_SYSTEM_PROMPT`（遥的 LLM system prompt）和 `FORMAT_CONTEXT_INJECTION`（LLM 输出注入模板）。

修改方案：

1. **新增方法 `_generate_format_guidelines(user_message, emotion_record)`**：
   - 调用 `get_format_llm_client(self.user_setting)` 获取遥的 LLM 客户端
   - 构建消息：system=`FORMAT_SYSTEM_PROMPT`，user=包含用户消息+焕的情绪分析结果的上下文
   - 调用 `format_llm.chat()` 获取 JSON 格式的格式指引
   - 解析 JSON，提取 `format_guidelines` 中的 structure/length/style/special_elements/avoid
   - 返回格式化后的 `FORMAT_CONTEXT_INJECTION` 字符串
   - 整个方法包裹在 try/except 中，`LLMConfigError` 或任何异常时降级到当前静态模板

2. **修改 `_build_enriched_system_prompt()` 行591-604**：
   - 将当前静态模板渲染替换为调用 `_generate_format_guidelines()`
   - 参考焕的模式，遥的 LLM 调用也可以异步化（在 process_message 中与焕并行启动），但考虑到遥的输出需要在构建 system prompt 时使用，建议在 `_build_enriched_system_prompt` 内同步 await

3. **保留静态模板作为降级方案**：
   - `EMOTION_AWARE_FORMAT_TEMPLATE` + `EMOTION_STYLE_MAP` 保留在 prompts.py 中
   - 当遥的 LLM 未配置或调用失败时，降级使用静态模板（当前逻辑）

#### 5. 适配其他调用者

| 文件 | 行 | 调用 | 处理方式 |
|------|----|------|----------|
| `services/emotion_service.py` | 95 | `get_emotion_llm_client` | 已有 try/except 包裹，`LLMConfigError` 会被捕获返回 None，加 logger.warning |
| `services/memory_service.py` | 260 | `get_emotion_llm_client` | 已有 try/except 包裹，同上 |
| `services/identity_service.py` | 222 | `get_chat_llm_client` | 已有 try/except 包裹，同上 |
| `ai/tool_generator.py` | 21 | `get_tool_llm_client` | 异常会传播到 agent.py，需在 agent 调用处捕获 |

---

### 第二部分：复合工具清理

#### 6. 后端 API 层 - `backend/app/api/v1/tools.py`

**删除端点：**
- `POST /composite` (行60-80)
- `GET /{tool_id}/pipeline` (行181-193)
- `PUT /{tool_id}/pipeline` (行196-237)
- `GET /{tool_id}/usage` (行274-286)

**修改端点：**
- `GET /` (行31-36)：移除 `tool_type` 查询参数过滤
- `GET /{tool_id}` (行143-145)：移除 `if tool.tool_type == "composite"` 分支
- `GET /export` (行110-111)：移除 composite 管道步骤导出
- `POST /{tool_id}/rollback/{version}` (行255-271)：移除 composite 管道恢复逻辑

**清理导入：** 移除 `CompositeToolCreate`, `PipelineStepSchema`, `ToolComposition` 导入

#### 7. 后端服务层 - `backend/app/services/tool_service.py`

**删除方法：**
- `create_composite_tool()` (行196-243)
- `get_pipeline_steps()` (行245-264)
- `get_sub_tool_usage()` (行349-364)
- `_build_pipeline_snapshot()` (行368-384)

**修改方法：**
- `delete_tool()` (行76-92)：移除复合工具引用检查
- `import_tools()` (行94-155)：移除 composite/pipeline 处理逻辑
- `save_version_snapshot()` (行275-302)：pipeline_snapshot 固定为 None
- `rollback_version()` (行304-347)：移除管道恢复逻辑

#### 8. 后端 Schema - `backend/app/schemas/tool.py`

**删除类：**
- `PipelineStepSchema` (行69-75)
- `CompositeToolCreate` (行78-82)

**修改类：**
- `ToolCreate`：移除 `tool_type` 字段
- `ToolBrief`：移除 `tool_type`, `sub_tool_count`
- `ToolResponse`：移除 `pipeline_steps`
- `ToolImportItem`：移除 `tool_type`, `pipeline_steps`
- `ToolExportItem`：移除 `tool_type`, `pipeline_steps`
- `ToolVersionResponse`：**保留** `pipeline_snapshot`（历史数据只读）

#### 9. 后端沙箱 - `backend/app/sandbox/executor.py`

- **删除** `execute_pipeline()` 函数 (行148-204)
- **删除** `resolve_mapping()` 函数 (行104-145) — 仅被 `execute_pipeline` 使用

#### 10. 后端模型 - `backend/app/models/tool.py`

- **保留所有模型不动** — `Tool.tool_type`, `ToolComposition`, `ToolVersion.pipeline_snapshot` 均保留（数据库向后兼容）

#### 11. 后端 Prompts - `backend/app/ai/prompts.py`

- 搜索并删除 `TOOL_COMPOSE_DECISION_PROMPT` 和 `COMPOSITE_TOOL_GENERATE_PROMPT`（如果存在）

#### 12. 前端类型 - `frontend/src/types/tool.ts`

- **删除**：`ToolType` 类型、`PipelineStep` 接口
- **修改**：`Tool` 移除 `tool_type`, `pipeline_steps`；`ToolBrief` 移除 `tool_type`, `sub_tool_count`
- **保留**：`ToolVersion.pipeline_snapshot`（历史数据只读）

#### 13. 前端类型 - `frontend/src/types/chat.ts`

- **删除**：`PipelineExecution`, `PipelineStepExecution` 接口
- **修改**：`ChatMessage` 移除 `pipelineExecution`
- **修改**：`InfoCard.type` 移除 `'composed'`，只保留 `'iterated'`
- **修改**：`AgentEvent.type` 移除 `'pipeline_start'`, `'pipeline_step'`, `'pipeline_step_result'`, `'tool_composed'`

#### 14. 前端 API - `frontend/src/api/tools.ts`

- **删除**：`getToolPipeline()`, `getToolUsage()`, `createCompositeTool()` 函数
- **修改**：`listTools()` 移除 `toolType` 参数
- **清理导入**：移除 `PipelineStep`, `ToolType`

#### 15. 前端 Store - `frontend/src/stores/chatStore.ts`

- **删除**事件处理块：`pipeline_start` (行100-123), `pipeline_step` (行124-142), `pipeline_step_result` (行143-172), `tool_composed` (行173-187)
- **清理导入**：移除 `PipelineExecution`

#### 16. 前端组件 - `frontend/src/components/chat/ToolExecutionCard.tsx`

- **删除**：`PipelineExecutionCard` 组件及其辅助函数 (`StepStatusIcon`, `statusLabel`, `StepResult`)
- **保留**：`ToolExecutionCard` 组件（用于普通工具执行结果）
- **清理导入**：移除 `PipelineExecution`, `PipelineStepExecution`, `Workflow`, `Loader`, `Circle` 等仅 Pipeline 使用的导入

#### 17. 前端组件 - `frontend/src/components/chat/MessageBubble.tsx`

- **删除**：`{message.pipelineExecution && <PipelineExecutionCard .../>}` 渲染行
- **修改**：`infoCard` 渲染逻辑移除 `'composed'` 分支，只保留 `'iterated'`
- **清理导入**：移除 `PipelineExecutionCard`, `Combine` icon

---

### 第三部分：文档更新

#### 18. 更新 `PROJECT_AUDIT_DOC.md`

根据代码实际修改结果，更新以下部分：
- config.py Settings 类参数列表：所有 AI 角色配置默认值改为空
- 参数获取规则：明确"无默认值，无 Fallback，缺失直接报错"
- 复合工具相关描述：标注为"已从代码中清理"（数据库表保留）
- SSE 事件类型：移除废弃事件
- 工具系统：简化描述，不再区分原子/复合
- 工厂函数：更新为 5 个独立函数，无 Fallback

---

## 降级策略矩阵

| AI角色 | 配置缺失时行为 | 是否阻断流程 | 备注 |
|--------|---------------|-------------|------|
| 玄（对话） | 抛出 LLMConfigError，SSE error 事件 | **是** | 核心对话能力 |
| 晴（意图） | 规则匹配仍工作，LLM 不可用时默认 chat | **否** | 规则引擎兜底 |
| 焕（情绪） | 情绪分析跳过，返回 None | **否** | 非阻塞异步任务 |
| 机（工具） | 工具生成/迭代失败，yield error 事件 | **部分**（task流程受阻） | |
| 遥（格式） | 调用 `get_format_llm_client` + `FORMAT_SYSTEM_PROMPT` 动态生成格式指引；LLM 未配置或调用失败时降级到静态模板（`EMOTION_AWARE_FORMAT_TEMPLATE` + `EMOTION_STYLE_MAP`） | **否** | 遥负责规则引擎输出规范及各AI角色间输入输出格式协调；本次新增 LLM 调用，保留静态模板作为降级 |

---

## 实施顺序

1. 创建 `exceptions.py`
2. 修改 `config.py`（清空默认值）
3. 重写 `factory.py`（严格模式）
4. 适配 `agent.py` + `emotion_service.py` + `memory_service.py` + `identity_service.py` + `tool_generator.py`
5. 清理后端复合工具代码（tools API → tool_service → schemas → executor → prompts）
6. 清理前端复合工具代码（types → api → stores → components）
7. 更新审查文档
8. 验证

---

## 验证方案

### 后端验证
1. 启动后端服务，确认无导入错误
2. 未配置用户发送消息 → 应收到 SSE error 事件提示配置
3. 确认 `/api/v1/tools/composite` 等废弃端点返回 404
4. 确认 `/api/v1/tools/` 列表不再接受 `tool_type` 参数

### 前端验证
1. `pnpm run build` 确认无 TypeScript 编译错误
2. `pnpm run lint` 确认无 ESLint 错误
3. 确认聊天界面不再渲染 Pipeline 相关 UI
4. 确认工具页面正常工作

### 关键文件清单
- `backend/app/core/exceptions.py` (新建)
- `backend/app/core/config.py`
- `backend/app/ai/factory.py`
- `backend/app/ai/agent.py`
- `backend/app/ai/tool_generator.py`
- `backend/app/api/v1/tools.py`
- `backend/app/services/tool_service.py`
- `backend/app/services/emotion_service.py`
- `backend/app/services/memory_service.py`
- `backend/app/services/identity_service.py`
- `backend/app/schemas/tool.py`
- `backend/app/sandbox/executor.py`
- `backend/app/ai/prompts.py`
- `frontend/src/types/tool.ts`
- `frontend/src/types/chat.ts`
- `frontend/src/api/tools.ts`
- `frontend/src/stores/chatStore.ts`
- `frontend/src/components/chat/ToolExecutionCard.tsx`
- `frontend/src/components/chat/MessageBubble.tsx`
- `PROJECT_AUDIT_DOC.md`
