# XuanJi: Emotion + Memory + New AI System Implementation Plan

## Context

XuanJi currently has 3 AI agents (玄/机/晴), no conversation persistence (messages lost on refresh), no emotion analysis, and no AI persona system. This plan adds:

1. **焕 (Huan)** - Emotion management AI (model: qwen3.6-plus)
2. **遥 (Yao)** - I/O format management AI (model: qwen3-vl-32b-thinking)
3. **Long-term memory** with human-like decay (day/week/month/year four-level compression cycles)
4. **Identity system** with fixed persona for 玄, self-iterating backgrounds for all AIs
5. **Emotion awareness** for all AIs, driven by 焕's per-message analysis

---

## Phase 1: Database Models (6 new tables + extend 1)

### New model files to create:

**`backend/app/models/conversation.py`** - Conversation + Message models

```
conversations: id, user_id(FK), title, is_active, message_count, created_at, updated_at
messages: id, conversation_id(FK), user_id(FK), role, content(Text), metadata(JSON), emotion_snapshot(JSON), is_summarized(Bool), created_at
```

**`backend/app/models/emotion.py`** - EmotionRecord model

```
emotion_records: id, user_id(FK), message_id(FK), conversation_id(FK), primary_emotion, emotion_intensity, deep_need, risk_level, interaction_recommendation(JSON), full_analysis(Text), created_at
```

**`backend/app/models/user_profile.py`** - UserProfile model

```
user_profiles: id, user_id(FK, unique), personality_traits(JSON), attachment_style, core_needs(JSON), emotional_baseline(JSON), trigger_topics(JSON), safe_topics(JSON), interests(JSON), summary_text(Text), version, created_at, updated_at
```

**`backend/app/models/ai_identity.py`** - AIIdentity model

```
ai_identities: id, user_id(FK), ai_name('xuan'|'ji'|'qing'|'huan'|'yao'),
  # Core persona
  persona_text(Text),           # Overall background story / description
  gender(String 20, nullable),  # Self-determined gender
  appearance(Text, nullable),   # Self-determined appearance description
  personality(JSON, nullable),  # Personality traits (e.g. ["温柔", "坚韧", "细腻"])
  speaking_style(JSON, nullable), # Speaking habits/patterns (e.g. {"tone": "温和", "habits": ["喜欢用比喻"], "catchphrases": []})
  values(JSON, nullable),       # 三观: worldview, life outlook, values (e.g. {"世界观": "...", "人生观": "...", "价值观": "..."})
  # State & evolution
  emotional_state(JSON, nullable),  # Current emotional state
  evolution_log(JSON, nullable),    # Array of timestamped changes [{timestamp, field, reason, old_value, new_value}]
  is_base_locked(Bool),         # If True, persona_text cannot auto-change (for 玄's initial persona)
  version(Int),
  created_at, updated_at
Unique constraint: (user_id, ai_name)
```

**Self-generation flow**: On first interaction, if an AI has no identity record, `IdentityService.seed_defaults(user_id)` creates entries. For 玄, `persona_text` + `gender` + `appearance` + `personality` + `speaking_style` + `values` are pre-set from XUAN_DEFAULT_PERSONA (is_base_locked=True for persona_text only). For other AIs (机/晴/焕/遥), these fields start as null — on their first invocation, the AI is prompted to self-generate its own gender, appearance, personality, speaking style, and values, which are then persisted. All fields can be iteratively updated through interaction except 玄's locked persona_text.

**`backend/app/models/memory_summary.py`** - MemorySummary model

```
memory_summaries: id, user_id(FK), period_type('daily'|'weekly'|'monthly'|'yearly'), period_start, period_end, summary_text(Text), key_emotions(JSON), key_topics(JSON), important_events(JSON), source_message_count, source_summary_ids(JSON), created_at
```

### Modify existing:

**`backend/app/models/setting.py`** - Add 6 columns:
- `emotion_llm_provider`, `emotion_llm_api_key`, `emotion_llm_model_name`
- `format_llm_provider`, `format_llm_api_key`, `format_llm_model_name`

**`backend/app/models/__init__.py`** - Import all new models

**`backend/app/core/database.py`** - Add new model imports to `init_db()`

---

## Phase 2: Config + Factory + Schema

### `backend/app/core/config.py` - Add Settings fields:
```python
emotion_llm_provider: str = ""
emotion_llm_api_key: str = ""
emotion_llm_model_name: str = "qwen3.6-plus"
format_llm_provider: str = ""
format_llm_api_key: str = ""
format_llm_model_name: str = "qwen3-vl-32b-thinking"
```

### `.env` - Add:
```
EMOTION_LLM_PROVIDER=online
EMOTION_LLM_MODEL_NAME=qwen3.6-plus
FORMAT_LLM_PROVIDER=online
FORMAT_LLM_MODEL_NAME=qwen3-vl-32b-thinking
```

### `backend/app/ai/factory.py` - Add 2 factory functions:
- `get_emotion_llm_client(user_setting=None)` - 3-tier fallback: user emotion_llm_* -> .env EMOTION_LLM_* -> chat LLM with default emotion model
- `get_format_llm_client(user_setting=None)` - 3-tier fallback: user format_llm_* -> .env FORMAT_LLM_* -> chat LLM with default format model

Both follow the exact pattern of existing `get_intent_llm_client()`.

### `backend/app/schemas/setting.py` - Extend both SettingUpdate and SettingResponse:
- Add `emotion_llm_provider`, `emotion_llm_api_key`, `emotion_llm_model_name`
- Add `format_llm_provider`, `format_llm_api_key`, `format_llm_model_name`
- Add new api key fields to `mask_api_key` validator

### `backend/app/services/setting_service.py`:
- Add `"emotion_llm_api_key"`, `"format_llm_api_key"`, `"intent_llm_api_key"` to `_is_masked_key()` check

### New schema files:
- `backend/app/schemas/conversation.py` - ConversationResponse, MessageResponse, ConversationCreate
- `backend/app/schemas/emotion.py` - EmotionRecordResponse
- `backend/app/schemas/profile.py` - UserProfileResponse
- `backend/app/schemas/identity.py` - AIIdentityResponse (includes all identity fields), AIIdentityUpdate (partial update for any field)

---

## Phase 3: Backend Services (5 new + modify 1)

### `backend/app/services/conversation_service.py`
- `get_or_create_active(user_id)` -> Conversation
- `add_message(conversation_id, user_id, role, content, metadata?, emotion_snapshot?)` -> Message
- `get_recent_messages_for_context(user_id, limit=20)` -> list[Message]
- `list_conversations(user_id, page, limit)` -> list[Conversation]
- `get_messages(conversation_id, limit?, before_id?)` -> list[Message]
- `mark_messages_summarized(message_ids)` -> None

### `backend/app/services/emotion_service.py`
- `analyze_message(user_id, message_id, user_message, conversation_context, user_setting)` -> EmotionRecord
  - Calls 焕 via `get_emotion_llm_client()` with SKILL.md content as system prompt
  - Parses structured JSON output -> stores in emotion_records
- `get_latest_emotion(user_id)` -> EmotionRecord | None
- `get_interaction_recommendation(user_id)` -> dict
- `generate_period_summary(user_id, period_type, start, end, user_setting)` -> updates user_profile

### `backend/app/services/profile_service.py`
- `get_or_create_profile(user_id)` -> UserProfile
- `update_from_emotion(user_id, emotion_record)` -> UserProfile
- `get_profile_context(user_id)` -> str (human-readable for prompt injection)

### `backend/app/services/identity_service.py`
- `get_or_create_identity(user_id, ai_name)` -> AIIdentity
- `get_persona_prompt(user_id, ai_name)` -> str (assembles full prompt from all identity fields: persona + gender + appearance + personality + speaking_style + values)
- `update_emotional_state(user_id, ai_name, state)` -> AIIdentity
- `evolve_field(user_id, ai_name, field, reason, new_value)` -> AIIdentity (rejects persona_text if is_base_locked; logs change to evolution_log)
- `self_generate_identity(user_id, ai_name, user_setting)` -> AIIdentity
  - Called when fields are null on first invocation
  - Prompts the AI to generate its own: gender, appearance, personality, speaking_style, values
  - Parses structured JSON response and persists to all fields
- `seed_defaults(user_id)` -> creates 5 AI identity records
  - 玄: pre-filled with XUAN_DEFAULT_PERSONA content (is_base_locked=True)
  - 机/晴/焕/遥: created with only ai_name set, other fields null (self-generate on first use)

### `backend/app/services/memory_service.py`
- `get_relevant_memories(user_id, query_text, limit=5)` -> list[MemorySummary]
  - Scoring: recency + keyword overlap + emotional significance
- `compress_day(user_id, date, user_setting)` -> MemorySummary
  - Fetch day's messages -> LLM summarize -> store -> mark is_summarized
  - High-emotion events stored in important_events (resist decay)
- `compress_week(user_id, week_start, user_setting)` -> MemorySummary
  - Merge 7 daily summaries -> weekly summary, carry forward important_events
- `compress_month(user_id, year, month, user_setting)` -> MemorySummary
  - Merge weekly summaries -> monthly summary
- `compress_year(user_id, year, user_setting)` -> MemorySummary
  - Merge monthly summaries -> yearly summary
- `should_preserve(emotion_record)` -> bool (high intensity / high risk = preserve)

---

## Phase 4: Prompts + Identity

### `backend/app/ai/prompts.py` - Add:

**XUAN_DEFAULT_PERSONA** - 玄's fixed persona (user-provided detailed Chinese description about the luminescent girl character), including pre-set gender, appearance, personality, speaking_style, values

**AI_SELF_IDENTITY_PROMPT** - Prompt template for AIs (机/晴/焕/遥) to self-generate their identity on first use:
```
你是{ai_name}，玄机系统中的{ai_role}。请为自己生成一个完整的身份设定。
你可以自由决定自己的性别、外貌、性格、说话风格和三观。
请以JSON格式返回：
{
  "gender": "你的性别",
  "appearance": "你的外貌描述（详细、有画面感）",
  "personality": ["性格特征1", "性格特征2", ...],
  "speaking_style": {"tone": "说话语气", "habits": ["语言习惯1", ...], "catchphrases": ["口头禅（可选）"]},
  "values": {"世界观": "...", "人生观": "...", "价值观": "..."}
}
```

**AI_IDENTITY_EVOLVE_PROMPT** - Prompt for iterative identity evolution during interaction:
```
基于你最近与用户的互动经历，审视自己当前的身份设定，如果你觉得某些方面需要成长或调整，请输出变更。
当前设定: {current_identity_json}
最近互动摘要: {recent_interaction_summary}
如无需变更返回 {"changes": []}，否则返回:
{"changes": [{"field": "字段名", "new_value": "新值", "reason": "变更原因"}]}
```

**EMOTION_SYSTEM_PROMPT** - 焕's system prompt, loads content from `.qoder/skills/psychological-emotion-analyst/SKILL.md` + requires JSON structured output matching emotion_records schema

**EMOTION_CONTEXT_INJECTION** - Template injected into all AIs' context:
```
当前用户情绪状态: {primary_emotion} (强度: {intensity})
深层需求: {deep_need}
建议沟通方式: {communication_approach}
建议语气: {tone}
建议节奏: {pacing}
```

**FORMAT_SYSTEM_PROMPT** - 遥's system prompt: format guidelines, quality standards, consistency rules for all AI outputs

---

## Phase 5: Agent Integration (Core Change)

### `backend/app/ai/agent.py` - Major modification

**New `__init__` additions:**
```python
self.conversation_service = ConversationService(db)
self.emotion_service = EmotionService(db)
self.profile_service = ProfileService(db)
self.identity_service = IdentityService(db)
self.memory_service = MemoryService(db)
```

**Modified `process_message()` flow:**

```
1. Persist user message -> ConversationService.add_message()
2. Fire 焕 analysis as asyncio.create_task() (non-blocking)
3. Build enriched context:
   a. 玄's persona (IdentityService.get_persona_prompt())
   b. Relevant memories (MemoryService.get_relevant_memories())
   c. Latest emotion recommendation (EmotionService.get_interaction_recommendation())
   d. User profile summary (ProfileService.get_profile_context())
   e. 遥's format guidelines (injected as system instruction)
   f. Recent conversation history (ConversationService.get_recent_messages_for_context())
4. Existing flow: _parse_intent -> [chat | tool flow]
   - chat path: enriched system prompt with persona + emotion context
   - tool path: existing logic unchanged
5. Persist assistant response -> ConversationService.add_message()
6. Await 焕's result if not yet done, update emotion_snapshot
7. New SSE event: emit 'emotion_update' with primary emotion + recommendation
8. Existing: yield 'done'
```

**Key design decisions:**
- 焕 runs async-parallel with intent parsing to minimize latency
- 遥 operates as pre-flight format guidelines injection (NOT post-processing), preserving streaming UX
- If 焕 is slow, current message proceeds without it; result stored for next message's context

### `backend/app/schemas/chat.py` - Add `conversation_id: int | None = None` to ChatRequest

### `backend/app/api/v1/chat.py` - Pass conversation_id to Agent, integrate ConversationService

---

## Phase 6: Memory Decay Scheduler

### `backend/app/services/scheduler.py` - New file

Use asyncio background tasks in FastAPI lifespan (no external dependency needed):

- **Daily (2 AM)**: For each active user -> `memory_service.compress_day(yesterday)`
- **Weekly (Monday 3 AM)**: For each active user -> `memory_service.compress_week(last_week_start)`
- **Monthly (1st of month 4 AM)**: -> `memory_service.compress_month(last_month)`
- **Yearly (Jan 1 5 AM)**: -> `memory_service.compress_year(last_year)`
- **Profile update**: After each daily compression, regenerate user profile from accumulated emotion data

Compression logic (four-level decay):
- Daily: raw messages -> LLM summary, high-emotion events in important_events
- Weekly: daily summaries -> LLM merge into weekly narrative, carry forward important_events
- Monthly: weekly summaries -> LLM merge, routine info compressed to patterns
- Yearly: monthly summaries -> LLM merge, only important_events + rough descriptions survive
- Messages with is_summarized=True older than 90 days can be archived (content set to null, metadata preserved)

### `backend/app/main.py` - Start scheduler in lifespan

---

## Phase 7: API Endpoints

### `backend/app/api/v1/conversations.py` - New router

- `GET /v1/conversations/` - List user's conversations
- `GET /v1/conversations/active` - Get/create active conversation
- `GET /v1/conversations/{id}/messages` - Get messages (paginated)
- `POST /v1/conversations/` - Create new conversation
- `PUT /v1/conversations/{id}` - Update title, close conversation

### `backend/app/api/v1/__init__.py` - Register conversations router

---

## Phase 8: Frontend Changes

### `frontend/src/types/setting.ts` - Add fields:
- `emotion_llm_provider`, `emotion_llm_api_key`, `emotion_llm_model_name`
- `format_llm_provider`, `format_llm_api_key`, `format_llm_model_name`

### `frontend/src/pages/MemoryPage.tsx` - Expand AI_CARDS from 3 to 5:

**焕 card**: name='焕', role='情绪管理 AI', icon=Heart, color=rose, keys=emotion_llm_*
**遥 card**: name='遥', role='格式管理 AI', icon=FileText, color=amber, keys=format_llm_*

Grid: `md:grid-cols-2 lg:grid-cols-3` (3+2 layout on large screens)

### `frontend/src/types/chat.ts` - Add:
- `'emotion_update'` to AgentEvent type union
- `emotionState?: { primary_emotion: string; intensity: string }` to ChatMessage

### `frontend/src/stores/chatStore.ts` - Changes:
- Add `conversationId` to state
- On init: fetch active conversation messages from server
- Handle `emotion_update` SSE event
- Call `POST /v1/conversations/active` on first load

### New files:
- `frontend/src/api/conversations.ts` - API client for conversation endpoints
- `frontend/src/types/conversation.ts` - Conversation, Message types

---

## File Summary

### New files (19):

| File | Purpose |
|---|---|
| `backend/app/models/conversation.py` | Conversation + Message models |
| `backend/app/models/emotion.py` | EmotionRecord model |
| `backend/app/models/user_profile.py` | UserProfile model |
| `backend/app/models/ai_identity.py` | AIIdentity model |
| `backend/app/models/memory_summary.py` | MemorySummary model |
| `backend/app/schemas/conversation.py` | Conversation/Message schemas |
| `backend/app/schemas/emotion.py` | Emotion schemas |
| `backend/app/schemas/profile.py` | Profile schemas |
| `backend/app/schemas/identity.py` | Identity schemas |
| `backend/app/services/conversation_service.py` | Message persistence |
| `backend/app/services/emotion_service.py` | 焕's analysis engine |
| `backend/app/services/profile_service.py` | User profile management |
| `backend/app/services/identity_service.py` | AI persona management |
| `backend/app/services/memory_service.py` | Memory compression/retrieval |
| `backend/app/services/scheduler.py` | Background decay tasks |
| `backend/app/api/v1/conversations.py` | Conversation API |
| `frontend/src/api/conversations.ts` | Frontend conversation API |
| `frontend/src/types/conversation.ts` | Conversation types |
| `frontend/src/stores/conversationStore.ts` | Conversation state (optional, can merge into chatStore) |

### Modified files (15):

| File | Changes |
|---|---|
| `.env` | Add EMOTION_LLM_* and FORMAT_LLM_* vars |
| `backend/app/core/config.py` | Add 6 emotion/format settings |
| `backend/app/core/database.py` | Import new models in init_db() |
| `backend/app/models/__init__.py` | Export new models |
| `backend/app/models/setting.py` | Add 6 columns |
| `backend/app/schemas/setting.py` | Add fields + update mask_api_key |
| `backend/app/schemas/chat.py` | Add conversation_id to ChatRequest |
| `backend/app/services/setting_service.py` | Update _is_masked_key() |
| `backend/app/ai/factory.py` | Add get_emotion_llm_client(), get_format_llm_client() |
| `backend/app/ai/prompts.py` | Add XUAN_DEFAULT_PERSONA, EMOTION_*, FORMAT_* prompts |
| `backend/app/ai/agent.py` | Major: emotion hook + context enrichment + persistence |
| `backend/app/api/v1/__init__.py` | Register conversations router |
| `backend/app/api/v1/chat.py` | Pass conversation context to Agent |
| `backend/app/main.py` | Start scheduler in lifespan |
| `frontend/src/types/setting.ts` | Add emotion/format fields |
| `frontend/src/types/chat.ts` | Add emotion event types |
| `frontend/src/pages/MemoryPage.tsx` | Expand to 5 AI cards |
| `frontend/src/stores/chatStore.ts` | Add conversation persistence + emotion events |

---

## Implementation Order

1. **Database + Config** (Phase 1-2): Models, settings, factory, schemas - foundation with no behavior change
2. **Conversation Persistence** (Phase 3 partial + 7): ConversationService + API + frontend integration
3. **Identity System** (Phase 3 partial + 4): IdentityService + 玄's persona prompt + seed logic
4. **Emotion System** (Phase 3 partial + 5): EmotionService + 焕 integration into Agent + SSE event
5. **Format System** (Phase 5): 遥's format guidelines injection
6. **Memory Decay** (Phase 6): MemoryService + scheduler + compression logic
7. **Frontend Polish** (Phase 8): 5 AI cards + emotion display + conversation loading

---

## Verification

1. **Database**: Start backend, verify 6 new tables auto-created via init_db()
2. **Config**: Check MemoryPage shows 5 AI cards, save 焕/遥 config successfully
3. **Persistence**: Send message, refresh page, verify messages reload from server
4. **Emotion**: Send emotional message, check emotion_records table has entry, check SSE stream has emotion_update event
5. **Persona**: Chat with 玄, verify response reflects the persona character traits
6. **Memory**: After daily compression runs, verify memory_summaries has daily entry, verify old messages marked is_summarized
7. **Format**: Verify 遥's format guidelines improve response consistency
