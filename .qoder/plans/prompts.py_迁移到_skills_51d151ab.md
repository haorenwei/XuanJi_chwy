# prompts.py 迁移到 Skills 目录

## 背景

`prompts.py` 包含 21 个常量，主要被 `agent.py`（16个）和 `tool_generator.py`（1个）使用。焕已完全迁移到动态加载 skill 文件，其余 4 个角色的 prompt 仍残留在 prompts.py。项目已有完善的 skill 目录体系（`backend/app/ai/skills/xuanji-{role}/`），迁移条件成熟。

## 迁移映射表

| 常量 | 目标文件 | 是否用 .format() |
|------|---------|:---:|
| **晴 (qing)** | | |
| INTENT_SYSTEM_PROMPT | `xuanji-qing/system-prompt.md` | 否 |
| TASK_PLANNING_PROMPT | `xuanji-qing/task-planning.md` | 是 |
| NEXT_STEP_PROMPT | `xuanji-qing/next-step.md` | 是 |
| **遥 (yao)** | | |
| FORMAT_SYSTEM_PROMPT | `xuanji-yao/system-prompt.md` | 否 |
| EMOTION_AWARE_FORMAT_TEMPLATE | `xuanji-yao/emotion-format.md` | 是 |
| EMOTION_STYLE_MAP | `xuanji-yao/emotion-style-map.json` | - |
| FORMAT_FALLBACK_TEMPLATES | `xuanji-yao/fallback-templates.json` | - |
| DEFAULT_STYLE | `xuanji-yao/emotion-style-map.json`（default 字段） | - |
| **玄 (xuan)** | | |
| MULTI_STEP_INTERPRET_PROMPT | `xuanji-xuan/multi-step-interpret.md` | 是 |
| EMOTION_CONTEXT_INJECTION | `xuanji-xuan/context-injection.md`（段落 1） | 是 |
| MEMORY_CONTEXT_INJECTION | `xuanji-xuan/context-injection.md`（段落 2） | 是 |
| USER_PROFILE_INJECTION | `xuanji-xuan/context-injection.md`（段落 3） | 是 |
| FORMAT_CONTEXT_INJECTION | `xuanji-xuan/context-injection.md`（段落 4） | 是 |
| STYLE_PROHIBITION_DECLARATION | `xuanji-xuan/style-rules.md` | 否 |
| XUAN_DEFAULT_PERSONA | 删除（已迁移到 persona.md） | - |
| SIMPLE_CHAT_PERSONA | 删除（已迁移到 persona.md） | - |
| **机 (ji)** | | |
| TOOL_MATCH_PROMPT | `xuanji-ji/tool-match.md` | 是 |
| TOOL_GENERATE_PROMPT | `xuanji-ji/tool-generate.md` | 是 |
| RESULT_INTERPRET_PROMPT | `xuanji-ji/result-interpret.md` | 是 |
| TOOL_ITERATE_DECISION_PROMPT | `xuanji-ji/tool-iterate.md` | 是 |
| **全局** | | |
| XUANJI_TEAM_CONTEXT | 删除（内容已嵌入晴的 system-prompt.md 中） | - |

## 关键设计决策

**加载方式**：在 `backend/app/ai/base.py` 新增 `load_prompt()` 和 `load_json_config()` 两个函数，使用 `@lru_cache` 缓存，性能与直接 import 等价。

**模板变量**：使用 `.format()` 的 prompt 文件中，字面量花括号用 `{{` / `}}` 转义（与 Python 源码一致）。不使用 `.format()` 的文件直接存储原始文本。

**玄的 context-injection.md**：4 个注入模板用 `---SECTION: xxx---` 分隔符分段，加载后按段拆分，避免 4 个小文件。

---

## Task 1: 创建 prompt 加载器

在 `backend/app/ai/base.py` 中新增：

```python
from functools import lru_cache
import json

SKILLS_DIR = Path(__file__).parent / "skills"

@lru_cache(maxsize=None)
def load_prompt(role: str, filename: str) -> str:
    path = SKILLS_DIR / f"xuanji-{role}" / filename
    return path.read_text(encoding="utf-8").strip()

@lru_cache(maxsize=None)
def load_json_config(role: str, filename: str) -> dict:
    path = SKILLS_DIR / f"xuanji-{role}" / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_prompt_sections(role: str, filename: str) -> dict[str, str]:
    """加载含分段标记的 prompt 文件，返回 {section_name: content}"""
    raw = load_prompt(role, filename)
    sections = {}
    current_key = None
    lines = []
    for line in raw.split("\n"):
        if line.startswith("---SECTION:") and line.endswith("---"):
            if current_key:
                sections[current_key] = "\n".join(lines).strip()
            current_key = line[len("---SECTION:"):- len("---")].strip()
            lines = []
        else:
            lines.append(line)
    if current_key:
        sections[current_key] = "\n".join(lines).strip()
    return sections
```

## Task 2: 创建所有 prompt 文件（晴 + 遥）

**晴** — 在 `backend/app/ai/skills/xuanji-qing/` 下创建 3 个 .md 文件：
- `system-prompt.md`：INTENT_SYSTEM_PROMPT 内容原样复制
- `task-planning.md`：TASK_PLANNING_PROMPT 内容（保留 `{{` 转义）
- `next-step.md`：NEXT_STEP_PROMPT 内容（保留 `{{` 转义）

**遥** — 在 `backend/app/ai/skills/xuanji-yao/` 下创建 4 个文件：
- `system-prompt.md`：FORMAT_SYSTEM_PROMPT 内容（保留 `{{` 转义）
- `emotion-format.md`：EMOTION_AWARE_FORMAT_TEMPLATE 内容
- `emotion-style-map.json`：EMOTION_STYLE_MAP + DEFAULT_STYLE 合并为 JSON
- `fallback-templates.json`：FORMAT_FALLBACK_TEMPLATES 转为 JSON

## Task 3: 创建所有 prompt 文件（玄 + 机）

**玄** — 在 `backend/app/ai/skills/xuanji-xuan/` 下创建 3 个 .md 文件：
- `multi-step-interpret.md`：MULTI_STEP_INTERPRET_PROMPT 内容
- `context-injection.md`：4 个注入模板用 `---SECTION: xxx---` 分隔
- `style-rules.md`：STYLE_PROHIBITION_DECLARATION 内容

**机** — 在 `backend/app/ai/skills/xuanji-ji/` 下创建 4 个 .md 文件：
- `tool-match.md`：TOOL_MATCH_PROMPT 内容（保留 `{{` 转义）
- `tool-generate.md`：TOOL_GENERATE_PROMPT 内容（保留 `{{` 转义）
- `result-interpret.md`：RESULT_INTERPRET_PROMPT 内容
- `tool-iterate.md`：TOOL_ITERATE_DECISION_PROMPT 内容（保留 `{{` 转义）

## Task 4: 重写 agent.py 的 import 和使用

将 `agent.py` 顶部的 16 个 `from app.ai.prompts import ...` 替换为：

```python
from app.ai.base import load_prompt, load_json_config, load_prompt_sections

# 按需加载（lru_cache 保证只读一次）
def _get_intent_prompt(): return load_prompt("qing", "system-prompt.md")
def _get_format_prompt(): return load_prompt("yao", "system-prompt.md")
# ... 其他类似包装函数或直接在使用处调用 load_prompt()
```

将所有使用常量的地方改为调用加载函数。具体需要替换约 20 处引用。

## Task 5: 更新 tool_generator.py

将 `from app.ai.prompts import TOOL_GENERATE_PROMPT` 替换为：
```python
from app.ai.base import load_prompt
TOOL_GENERATE_PROMPT = load_prompt("ji", "tool-generate.md")
```

## Task 6: 删除 prompts.py + 验证

- 删除 `backend/app/ai/prompts.py`
- 全局搜索确认无残留 import
- 运行 `py_compile` 验证所有修改的 .py 文件
- 运行 `pnpm build` 验证前端（无影响但确认）

---

## 执行依赖

```
Task 1 (加载器)  ──┐
Task 2 (晴+遥文件) ──┼── Task 4 (agent.py) ──┐
Task 3 (玄+机文件) ──┘                        ├── Task 6 (删除+验证)
                      Task 5 (tool_gen) ──────┘
```

Task 1/2/3 可并行，Task 4/5 依赖 1+2+3 完成后执行，Task 6 最后。
