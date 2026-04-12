import asyncio
import json
import logging
import re
import time as _time
from pathlib import Path
from typing import AsyncIterator

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from app.ai.factory import (
    get_chat_llm_client,
    get_format_llm_client,
    get_intent_llm_client,
    get_tool_llm_client,
)
from app.ai.base import load_prompt, load_json_config, load_prompt_sections
from app.core.exceptions import LLMConfigError
from app.ai.tool_generator import generate_tool_code
from app.sandbox.executor import execute_tool
from app.schemas.task import TaskCreate, TaskStatus
from typing import Callable
from app.services.conversation_service import ConversationService
from app.services.emotion_service import EmotionService
from app.services.identity_service import IdentityService
from app.services.log_service import LogService
from app.services.memory_service import MemoryService
from app.services.profile_service import ProfileService
from app.services.task_service import TaskService
from app.services.tool_service import ToolService


class Agent:
    """Core AI agent that orchestrates intent understanding, tool matching,
    tool generation, sandbox execution, and result interpretation.
    Integrates emotion analysis, memory retrieval, user profiling and
    AI identity for context-enriched conversations."""

    _RULES_PATH = Path(__file__).parent / "intent_rules.json"
    _format_cache: dict[str, tuple[str, float]] = {}  # class-level cache

    def __init__(self, db: Session, user_id: int, user_setting=None):
        self.db = db
        self.user_id = user_id
        self.user_setting = user_setting
        self._config_error: LLMConfigError | None = None
        try:
            self.llm = get_chat_llm_client(user_setting)
        except LLMConfigError as e:
            self._config_error = e
            self.llm = None
        self.tool_service = ToolService(db)
        self.task_service = TaskService(db)
        self.log_service = LogService(db)
        # New services
        self.conversation_service = ConversationService(db)
        self.emotion_service = EmotionService(db)
        self.identity_service = IdentityService(db)
        self.profile_service = ProfileService(db)
        self.memory_service = MemoryService(db)
        # Load intent classification rules
        self._intent_rules = self._load_intent_rules()
        # Usage collection across all AI roles
        self._all_usages: list[dict] = []
        # 遥的最近一次风格设计结果（用于协作日志）
        self._last_format_result: dict | None = None

    def _make_usage_callback(self, role_name: str) -> Callable[[dict], None]:
        """Create a usage callback that tags usage with a role name and appends to _all_usages."""
        def callback(usage: dict):
            if "role_name" not in usage:
                usage["role_name"] = role_name
            self._all_usages.append(usage)
        return callback

    async def process_message(
        self,
        user_message: str,
        working_dir: str | None = None,
        conversation_id: int | None = None,
    ) -> AsyncIterator[dict]:
        """Process a user message through the full agent loop.
        Yields SSE-compatible event dicts."""

        self._all_usages = []
        _generator_closing = False
        _collaboration_log = []
        emotion_task = None
        user_msg_record = None

        try:
            # ── Config error guard ──
            if self._config_error is not None:
                yield {"type": "error", "content": str(self._config_error)}
                return

            # ── Conversation persistence: get or create ──
            if conversation_id:
                conv = self.conversation_service.get_conversation(conversation_id, self.user_id)
                if not conv:
                    conv = self.conversation_service.get_or_create_active(self.user_id)
            else:
                conv = self.conversation_service.get_or_create_active(self.user_id)

            # 发送 metadata 事件，让前端知道当前对话 ID
            yield {"type": "metadata", "conversation_id": conv.id}

            # Save user message
            user_msg_record = self.conversation_service.add_message(
                conversation_id=conv.id,
                user_id=self.user_id,
                role="user",
                content=user_message,
            )

            # ── Step 1: 获取最近情绪 + 快速规则匹配 + LLM Fallback 调度决策 ──
            yield {"type": "thinking", "content": "正在处理..."}

            # 获取 latest_emotion 供晴参考
            latest_emotion_for_qing = self.emotion_service.get_latest_emotion(self.user_id)

            intent = await self._parse_intent(user_message, latest_emotion=latest_emotion_for_qing)
            # [实验性功能] 工具路径暂时禁用，所有消息走对话路径
            intent_desc = intent.get('description', user_message)
            need_emotion = intent.get("need_emotion", True)  # 默认倾向 true
            user_state = intent.get("user_state", "")

            # 晴的协作日志：捕获真实决策
            _qing_next = ["焕", "玄"]
            _collaboration_log.append({
                "role": "晴",
                "action": "行为推测",
                "result": f"推测用户状态：{user_state[:30]}，{'需要' if need_emotion else '不需要'}启动焕的情绪分析。意图描述：{intent_desc[:50]}",
                "next": _qing_next,
            })

            # ── Step 2: 焕始终启动（情绪分析） ──
            emotion_task = asyncio.create_task(
                self.emotion_service.analyze_message(
                    user_id=self.user_id,
                    message_id=user_msg_record.id,
                    conversation_id=conv.id,
                    user_message=user_message,
                    user_setting=self.user_setting,
                    usage_callback=self._make_usage_callback("焕"),
                )
            )

            # 焕（情绪分析）日志
            _collaboration_log.append({
                "role": "焕",
                "action": "情绪分析",
                "result": "正在感知情绪状态...",
                "next": ["遥"],
            })

            # ── 所有消息走对话路径 ──
            is_simple = self._is_simple_chat(user_message, intent)

            if is_simple:
                # ── 轻量级闲聊路径 ──
                system_prompt = self.identity_service.get_persona_prompt(self.user_id, "xuan")
                # 注入 SKILL.md 行为规范
                xuan_skill = self.identity_service.get_skill_prompt("xuan")
                if xuan_skill:
                    system_prompt += f"\n\n{xuan_skill}"
                # 追加严格规范声明
                system_prompt += f"\n\n{load_prompt('xuan', 'style-rules.md')}"
                messages = [{"role": "system", "content": system_prompt}]

                recent_msgs = self.conversation_service.get_recent_messages_for_context(
                    self.user_id, limit=3
                )
                for msg in recent_msgs:
                    if msg.id == user_msg_record.id:
                        continue
                    messages.append({"role": msg.role, "content": msg.content})
                messages.append({"role": "user", "content": user_message})

                assistant_text = ""
                try:
                    async for chunk in self.llm.stream_chat(
                        messages,
                        max_tokens=200,
                        temperature=0.8,
                        usage_callback=self._make_usage_callback("玄"),
                    ):
                        assistant_text += chunk
                        yield {"type": "message", "content": chunk}
                except Exception as e:
                    logger.error(f"LLM 对话生成失败: {e}", exc_info=True)
                    yield {"type": "error", "content": f"对话生成失败：{str(e)}"}

                # 确保 assistant_text 不为空
                if not assistant_text:
                    assistant_text = "抱歉，我暂时无法生成回复，请稍后再试。"
                    yield {"type": "message", "content": assistant_text}

                _collaboration_log.append({
                    "role": "玄",
                    "action": "生成回复",
                    "result": f"综合所有信息，生成了{len(assistant_text)}字的回复",
                    "next": None,
                })
                self.conversation_service.add_message(
                    conversation_id=conv.id,
                    user_id=self.user_id,
                    role="assistant",
                    content=assistant_text,
                    metadata_json=json.dumps({"type": "simple_chat", "collaboration": _collaboration_log}, ensure_ascii=False),
                )

                return

            else:
                # ── 完整对话路径 ──
                latest_emotion = self.emotion_service.get_latest_emotion(self.user_id)

                system_prompt = await self._build_enriched_system_prompt(user_message, latest_emotion)
                memory_ctx = self.memory_service.get_memory_context(self.user_id, user_message)
                _yao_result = self._describe_format_result(memory_ctx)
                _collaboration_log.append({
                    "role": "遥",
                    "action": "风格设计",
                    "result": _yao_result,
                    "next": ["玄"],
                })
                messages = [{"role": "system", "content": system_prompt}]

                recent_msgs = self.conversation_service.get_recent_messages_for_context(
                    self.user_id, limit=10
                )
                for msg in recent_msgs:
                    if msg.id == user_msg_record.id:
                        continue
                    messages.append({"role": msg.role, "content": msg.content})
                messages.append({"role": "user", "content": user_message})

                assistant_text = ""
                try:
                    async for chunk in self.llm.stream_chat(
                        messages,
                        max_tokens=1000,
                        usage_callback=self._make_usage_callback("玄"),
                    ):
                        assistant_text += chunk
                        yield {"type": "message", "content": chunk}
                except Exception as e:
                    logger.error(f"LLM 对话生成失败: {e}", exc_info=True)
                    yield {"type": "error", "content": f"对话生成失败：{str(e)}"}

                # 确保 assistant_text 不为空
                if not assistant_text:
                    assistant_text = "抱歉，我暂时无法生成回复，请稍后再试。"
                    yield {"type": "message", "content": assistant_text}

                _collaboration_log.append({
                    "role": "玄",
                    "action": "生成回复",
                    "result": f"综合所有信息，生成了{len(assistant_text)}字的回复",
                    "next": None,
                })
                self.conversation_service.add_message(
                    conversation_id=conv.id,
                    user_id=self.user_id,
                    role="assistant",
                    content=assistant_text,
                    metadata_json=json.dumps({"type": "full_chat", "collaboration": _collaboration_log}, ensure_ascii=False),
                )

                return

            # ── Non-chat (tool) paths: conditionally wait for emotion ──
            emotion_record = None
            if emotion_task:
                try:
                    emotion_record = await asyncio.wait_for(emotion_task, timeout=15)
                    if emotion_record:
                        self.log_service.log(
                            "情绪AI（焕）分析成功", level="info",
                            user_id=self.user_id, source="agent.emotion", status_code=200,
                        )
                except asyncio.TimeoutError:
                    logger.warning(">>> TOOL_PATH: emotion_task timeout")
                    self.log_service.log(
                        "情绪AI（焕）分析超时", level="warn",
                        user_id=self.user_id, source="agent.emotion", status_code=408,
                    )
                    emotion_record = None
                except Exception as e:
                    logger.warning(">>> TOOL_PATH: emotion_task failed: %s", e)
                    self.log_service.log(
                        "情绪AI（焕）分析失败", level="error",
                        user_id=self.user_id, source="agent.emotion", status_code=500,
                        details={"error": str(e)},
                    )
                    emotion_record = None

            # Emit emotion update event if available
            if emotion_record:
                self._update_huan_log(_collaboration_log, emotion_record)

                yield {
                    "type": "emotion_update",
                    "content": json.dumps({
                        "primary_emotion": emotion_record.primary_emotion,
                        "emotion_intensity": emotion_record.emotion_intensity,
                        "deep_need": emotion_record.deep_need,
                        "risk_level": emotion_record.risk_level,
                    }, ensure_ascii=False),
                }

                self._persist_emotion_snapshot(emotion_record, user_msg_record)

                # 焕贡献规则引擎（与 chat 路径对齐）
                self._huan_contribute_to_rules(emotion_record, user_message)

            # Step 2: Create task
            description = intent.get("description", user_message)
            target_path = intent.get("target_path") or working_dir
            parameters = intent.get("parameters", {})
            if target_path:
                parameters["target_path"] = target_path

            task = self.task_service.create_task(
                TaskCreate(
                    title=self._summarize_message(user_message),
                    description=f"[{intent.get('user_state', 'request')}] {user_message}",
                ),
                user_id=self.user_id,
            )
            self.log_service.log(
                f"Task created: {description}",
                task_id=task.id,
                details=intent,
                user_id=self.user_id,
                source="agent.task",
                status_code=200,
            )

            # === 晴规划：仅在描述暗示复杂任务时才分析 ===
            # 对于简单的单工具查询，跳过多步规划以减少延迟和挂起风险
            _plan = None
            _desc_len = len(description)
            if _desc_len > 30 or '和' in user_message or '并且' in user_message or '同时' in user_message:
                _plan = await self._plan_task(user_message, description, emotion_task)

            if _plan and _plan.get("is_multi_step") and len(_plan.get("info_gaps", [])) > 1:
                # 多步编排路径
                async for event in self._execute_multi_step(
                    user_message, _plan, emotion_task, _collaboration_log, working_dir,
                    need_emotion, conv, user_msg_record
                ):
                    yield event
                _generator_closing = True  # 多步路径已发送 done，阻止 finally 重复发送
                return  # 多步路径完毕
            # === 否则走原有单步路径（完全不变）===

            # Step 3: Tool Retrieval
            yield {"type": "thinking", "content": "正在搜索匹配的工具..."}

            tool = await self._find_tool(description)

            tool_name = None
            tool_code = None
            description_zh = None
            success = False
            result_data = ""

            if tool:
                # ── Tool execution ──
                yield {"type": "tool_selected", "content": f"已找到工具：{tool.name}"}
                tool_code = tool.code
                tool_name = tool.name
                _collaboration_log.append({
                    "role": "机",
                    "action": "工具匹配",
                    "result": f"在数据库中匹配到工具「{tool.name}」({tool.description_zh or tool.description})",
                    "next": ["玄"],
                })
                self.log_service.log(
                    f"Tool matched: {tool.name}",
                    task_id=task.id,
                    tool_id=tool.id,
                    user_id=self.user_id,
                    source="agent.tool",
                    status_code=200,
                )

                yield {"type": "tool_executing", "content": f"正在执行 {tool_name}..."}
                exec_result = execute_tool(tool_code, parameters, working_dir=working_dir)
                success = exec_result.get("success", False)
                result_data = exec_result.get("result", "")

                yield {
                    "type": "tool_result",
                    "content": json.dumps({
                        "tool": tool_name,
                        "success": success,
                        "result": result_data,
                    }, ensure_ascii=False),
                }
                if success:
                    _exec_result_str = f"执行「{tool_name}」完成，获得结果：{str(result_data)[:100]}"
                else:
                    _err_msg = str(result_data)[:80]
                    _exec_result_str = f"执行「{tool_name}」失败：{_err_msg}"
                _collaboration_log.append({
                    "role": "机",
                    "action": "工具执行",
                    "result": _exec_result_str,
                    "next": ["玄"],
                })
                logger.info(">>> TOOL_PATH: tool_result yielded, tool=%s success=%s", tool_name, success)

                # ── Tool iteration on failure ──
                if not success:
                    iterate_decision = await self._decide_tool_iteration(
                        tool, exec_result, user_message
                    )
                    if iterate_decision and iterate_decision.get("should_iterate"):
                        new_code = iterate_decision.get("new_code")
                        if new_code:
                            try:
                                self.tool_service.save_version_snapshot(
                                    tool.id,
                                    change_summary=iterate_decision.get("change_summary", "Auto-iterated after failure"),
                                    created_by=self.user_id,
                                )
                                tool.code = new_code
                                tool.version += 1
                                self.db.commit()
                                self.db.refresh(tool)
                            except Exception as e:
                                self.db.rollback()
                                logger.warning(f"工具迭代版本保存失败: {e}")

                            yield {
                                "type": "tool_iterated",
                                "content": json.dumps({
                                    "tool_name": tool_name,
                                    "version": tool.version,
                                    "change_summary": iterate_decision.get("change_summary"),
                                    "reason": iterate_decision.get("reason"),
                                }, ensure_ascii=False),
                            }

                            # Re-execute with updated code
                            yield {"type": "tool_executing", "content": f"正在重新执行 {tool_name} (v{tool.version})..."}
                            try:
                                exec_result = execute_tool(new_code, parameters, working_dir=working_dir)
                                success = exec_result.get("success", False)
                                result_data = exec_result.get("result", "")

                                yield {
                                    "type": "tool_result",
                                    "content": json.dumps({
                                        "tool": tool_name,
                                        "success": success,
                                        "result": result_data,
                                        "iterated": True,
                                    }, ensure_ascii=False),
                                }
                            except Exception as e:
                                self.log_service.log(
                                    f"Tool iteration failed: {e}",
                                    task_id=task.id,
                                    tool_id=tool.id,
                                    user_id=self.user_id,
                                    source="agent.tool",
                                    status_code=500,
                                    details={"error": str(e)},
                                )

            else:
                # ── Tool Generation (original logic, enhanced with description_zh) ──
                yield {"type": "tool_generating", "content": "未找到匹配工具，正在生成新工具..."}

                try:
                    tool_name, tool_code, description_en, description_zh = await generate_tool_code(
                        description=description,
                        target_path=target_path,
                        parameters=parameters,
                        user_setting=self.user_setting,
                        usage_callback=self._make_usage_callback("机"),
                    )
                    _collaboration_log.append({
                        "role": "机",
                        "action": "工具生成",
                        "result": f"没有现成工具，为你生成了新工具「{tool_name}」",
                        "next": ["玄"],
                    })
                    yield {"type": "tool_generating", "content": f"已生成工具：{tool_name}"}
                except (ValueError, LLMConfigError) as e:
                    yield {"type": "error", "content": f"工具生成失败：{e}"}
                    self.task_service.update_status(task.id, TaskStatus.FAILED, str(e))
                    return

                # Execute generated tool
                yield {"type": "tool_executing", "content": f"正在执行 {tool_name}..."}
                exec_result = execute_tool(tool_code, parameters, working_dir=working_dir)
                success = exec_result.get("success", False)
                result_data = exec_result.get("result", "")

                yield {
                    "type": "tool_result",
                    "content": json.dumps({
                        "tool": tool_name,
                        "success": success,
                        "result": result_data,
                    }, ensure_ascii=False),
                }
                if success:
                    _gen_exec_result = f"执行「{tool_name}」完成，获得结果：{str(result_data)[:100]}"
                else:
                    _gen_err_msg = str(result_data)[:80]
                    _gen_exec_result = f"执行「{tool_name}」失败：{_gen_err_msg}"
                _collaboration_log.append({
                    "role": "机",
                    "action": "工具执行",
                    "result": _gen_exec_result,
                    "next": ["玄"],
                })

                # Auto-save generated tool if successful
                if success:
                    try:
                        saved_tool = self.tool_service.register_or_update(
                            name=tool_name,
                            description=description_en or tool_name.replace('_', ' ').title(),
                            code=tool_code,
                            user_id=self.user_id,
                            description_zh=description_zh,
                            tool_type="atomic",
                        )
                        self.log_service.log(
                            f"Tool auto-saved: {tool_name}",
                            task_id=task.id,
                            tool_id=saved_tool.id,
                            user_id=self.user_id,
                            source="agent.tool",
                            status_code=200,
                        )
                        yield {"type": "tool_generating", "content": f"工具 '{tool_name}' 已保存，可供后续复用。"}
                    except Exception as e:
                        self.db.rollback()
                        logger.warning(f"工具保存失败（不影响执行结果）: {e}")
                        yield {"type": "tool_generating", "content": f"工具执行成功，但保存失败：{e}"}

            # Step 7: 让遥参与 — 构建带记忆的系统提示（用于结果解读）
            logger.info(">>> TOOL_PATH: entering Step 7 (enriched prompt)")
            try:
                latest_emotion = emotion_record if emotion_record else None
                enriched_prompt = await self._build_enriched_system_prompt(user_message, latest_emotion)
                logger.info(">>> TOOL_PATH: enriched prompt built, len=%d", len(enriched_prompt))
                _mem_ctx = self.memory_service.get_memory_context(self.user_id, user_message)
                _yao_result = self._describe_format_result(_mem_ctx)
                _collaboration_log.append({
                    "role": "遥",
                    "action": "风格设计",
                    "result": _yao_result,
                    "next": ["玄"],
                })
            except Exception as e:
                logger.error(f"构建系统提示失败: {e}", exc_info=True)
                enriched_prompt = "You are a helpful assistant."

            # Step 8: Result Interpretation
            logger.info(">>> TOOL_PATH: entering Step 8 (result interpretation)")
            logger.info(f"Tool execution complete: tool_name={tool_name}, success={success}, result_len={len(str(result_data)) if result_data else 0}")
            yield {"type": "thinking", "content": "正在解读结果..."}

            try:
                _safe_result = str(result_data)[:2000].replace("{", "").replace("}", "") if result_data else "无结果"
                interpretation_prompt = load_prompt("ji", "result-interpret.md").format(
                    user_message=user_message,
                    tool_name=tool_name or "未知工具",
                    success=success,
                    result=_safe_result,
                )
            except Exception as fmt_err:
                logger.error(f"Prompt 格式化失败: {fmt_err}")
                interpretation_prompt = (
                    f"用户问：{user_message}\n"
                    f"工具 {tool_name or '未知工具'} {'执行成功' if success else '执行失败'}。"
                    f"结果：{str(result_data)[:500] if result_data else '无结果'}\n"
                    f"请用自然口语化的方式告诉用户结果。"
                )

            assistant_text = ""
            _stream_start = _time.time()
            _STREAM_TIMEOUT = 60  # 流式回复总超时60秒
            try:
                stream_iter = self.llm.stream_chat(
                    [
                        {"role": "system", "content": enriched_prompt},
                        {"role": "user", "content": interpretation_prompt},
                    ],
                    usage_callback=self._make_usage_callback("玄"),
                ).__aiter__()
                while True:
                    remaining = _STREAM_TIMEOUT - (_time.time() - _stream_start)
                    if remaining <= 0:
                        logger.error(">>> TOOL_PATH: stream_chat total timeout (%ds)", _STREAM_TIMEOUT)
                        break
                    try:
                        chunk = await asyncio.wait_for(stream_iter.__anext__(), timeout=min(remaining, 30))
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        logger.error(">>> TOOL_PATH: stream_chat chunk timeout (30s), total elapsed=%.1f", _time.time() - _stream_start)
                        break
                    assistant_text += chunk
                    yield {"type": "message", "content": chunk}
                logger.info(">>> TOOL_PATH: stream_chat completed, text_len=%d", len(assistant_text))
            except Exception as e:
                logger.error(f"LLM 结果解读失败: {e}", exc_info=True)
                # 降级回复 — 确保用户能看到结果
                if success:
                    fallback = f"工具 {tool_name} 执行成功。结果：{str(result_data)[:500]}"
                else:
                    fallback = f"工具 {tool_name} 执行失败。错误：{str(result_data)[:500]}"
                assistant_text = fallback
                yield {"type": "message", "content": fallback}
                _collaboration_log.append({
                    "role": "玄",
                    "action": "生成回复",
                    "result": f"综合所有信息，生成了{len(assistant_text)}字的回复（降级）",
                    "next": None,
                })

            # 确保 assistant_text 不为空（极端降级）
            if not assistant_text:
                if success:
                    assistant_text = f"工具 {tool_name} 执行成功。结果：{str(result_data)[:500]}"
                else:
                    assistant_text = f"工具 {tool_name} 执行失败。{str(result_data)[:500]}"
                yield {"type": "message", "content": assistant_text}

            # Save assistant message for task results
            if not any(log.get("role") == "玄" and log.get("action") == "生成回复" for log in _collaboration_log):
                _collaboration_log.append({
                    "role": "玄",
                    "action": "生成回复",
                    "result": f"综合所有信息，生成了{len(assistant_text)}字的回复",
                    "next": None,
                })
            self.conversation_service.add_message(
                conversation_id=conv.id,
                user_id=self.user_id,
                role="assistant",
                content=assistant_text,
                metadata_json=json.dumps({
                    "type": "task_result",
                    "tool_name": tool_name,
                    "success": success,
                    "collaboration": _collaboration_log,
                }, ensure_ascii=False),
            )

            # Update task status
            final_status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            self.task_service.update_status(task.id, final_status, str(result_data)[:5000])

            self.log_service.log(
                f"Task {final_status.value}: {tool_name}",
                task_id=task.id,
                details={"success": success, "result_preview": str(result_data)[:500]},
                user_id=self.user_id,
                source="agent.task",
                status_code=200 if success else 500,
            )

        except GeneratorExit:
            _generator_closing = True
            return
        except Exception as e:
            logger.error(f"process_message 异常: {e}", exc_info=True)
            yield {"type": "error", "content": f"处理消息时发生错误：{str(e)}"}
        finally:
            logger.info(">>> TOOL_PATH: entered finally block, _generator_closing=%s", _generator_closing)
            if not _generator_closing:
                # 先发 done 事件，立即解锁用户交互
                usages_count_at_done = len(self._all_usages)
                yield {
                    "type": "done",
                    "content": "",
                    "conversation_id": conv.id if conv else None,
                    "usages": self._all_usages if self._all_usages else None,
                }

                # 在 done 之后处理焕的情绪分析，不阻塞用户交互
                if emotion_task and not emotion_task.done():
                    try:
                        emotion_record = await emotion_task
                        if emotion_record:
                            self._update_huan_log(_collaboration_log, emotion_record)
                            self._persist_emotion_snapshot(emotion_record, user_msg_record)
                            self._huan_contribute_to_rules(emotion_record, user_message)
                            self.log_service.log(
                                "情绪AI（焕）分析成功", level="info",
                                user_id=self.user_id, source="agent.emotion", status_code=200,
                            )
                    except Exception as e:
                        logger.error(f"Emotion finalization failed (finally): {e}")
                elif emotion_task and emotion_task.done():
                    try:
                        emotion_record = emotion_task.result()
                        if emotion_record:
                            self._update_huan_log(_collaboration_log, emotion_record)
                            self._persist_emotion_snapshot(emotion_record, user_msg_record)
                            self._huan_contribute_to_rules(emotion_record, user_message)
                    except Exception as e:
                        logger.error(f"Emotion result retrieval failed: {e}")

                # 记录 done 之后新增的 token 用量（如焕的情绪分析）
                if len(self._all_usages) > usages_count_at_done:
                    late_usages = self._all_usages[usages_count_at_done:]
                    try:
                        from app.services.token_service import TokenService
                        token_svc = TokenService(self.db)
                        for u in late_usages:
                            if u:
                                token_svc.record_usage(
                                    user_id=self.user_id,
                                    prompt_tokens=u.get("prompt_tokens", 0),
                                    completion_tokens=u.get("completion_tokens", 0),
                                    total_tokens=u.get("total_tokens", 0),
                                    model=u.get("model"),
                                    role_name=u.get("role_name"),
                                )
                        logger.info(f"已补录 {len(late_usages)} 条后置 token 用量")
                    except Exception as e:
                        logger.error(f"后置 token 记录失败: {e}")

                # 再发协作日志（前端用 requestIdleCallback 异步处理，不阻塞）
                if _collaboration_log:
                    yield {
                        "type": "collaboration",
                        "content": "",
                        "conversation_id": conv.id if conv else None,
                        "collaboration": _collaboration_log,
                    }

                # 后台触发记忆压缩（fire-and-forget）
                try:
                    asyncio.create_task(self.memory_service.compress_recent(self.user_id, self.user_setting))
                except Exception:
                    pass

                # 后台触发用户画像提取（fire-and-forget）
                try:
                    asyncio.create_task(
                        self.profile_service.update_from_conversation(
                            self.user_id, user_message, self.user_setting
                        )
                    )
                except Exception:
                    pass

                # 低频触发画像摘要 + 身份迭代评估
                try:
                    _conv_obj = self.conversation_service.get_conversation(conv.id, self.user_id) if conv else None
                    _msg_count = getattr(_conv_obj, 'message_count', 0) if _conv_obj else 0

                    # 每10轮触发画像摘要
                    if _msg_count > 0 and _msg_count % 10 == 0:
                        try:
                            await self.profile_service.generate_summary(self.user_id, self.user_setting)
                        except Exception as e:
                            logger.warning(f"画像摘要生成异常: {e}")

                    # 每20轮触发身份迭代 - 并发执行但有超时和异常捕获
                    if _msg_count > 0 and _msg_count % 20 == 0:
                        _recent_msgs = self.conversation_service.get_recent_messages_for_context(self.user_id, limit=20)
                        _summary = "\n".join([f"[{m.role}] {m.content[:100]}" for m in _recent_msgs[-10:]])
                        tasks = []
                        ai_names = ["xuan", "huan", "yao", "qing"]
                        for _ai in ai_names:
                            tasks.append(
                                self.identity_service.auto_evolve(self.user_id, _ai, _summary, self.user_setting)
                            )
                        # gather 并发执行，return_exceptions=True 确保不会因单个失败中断全部
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                logger.warning(f"身份迭代异常 ({ai_names[i]}): {result}")
                except Exception:
                    pass

    # ── Simple Chat Classification ────────────────────────────────────

    def _describe_format_result(self, memory_ctx) -> str:
        """根据遥的实际风格设计结果生成协作日志描述。"""
        parts = []
        # 记忆检索部分
        if memory_ctx:
            if "[短期记忆]" in memory_ctx:
                parts.append("回忆了最近的对话片段")
            else:
                parts.append("找到相关记忆片段")
        else:
            parts.append("未找到相关记忆")
        # 风格设计部分
        fmt = self._last_format_result
        if fmt and not fmt.get("fallback"):
            guidelines = fmt.get("format_guidelines", {})
            style = guidelines.get("style", "")
            length = guidelines.get("length", "")
            structure = guidelines.get("structure", "")
            fmt_parts = []
            if style:
                fmt_parts.append(f"风格{style}")
            if length:
                fmt_parts.append(f"长度{length}")
            if structure:
                fmt_parts.append(f"结构{structure}")
            if fmt_parts:
                parts.append(f"设计回复风格：{'，'.join(fmt_parts)}")
            else:
                parts.append("完成风格设计")
        elif fmt and fmt.get("fallback"):
            parts.append(f"使用静态风格模板（情绪状态：{fmt.get('emotion_state', 'neutral')}）")
        else:
            parts.append("完成风格设计")
        return "，".join(parts)

    def _is_simple_chat(self, message: str, intent: dict) -> bool:
        """判断是否为简单闲聊，可以走轻量级路径。"""
        if intent.get("need_emotion", True):
            return False
        if len(message.strip()) > 80:
            return False
        return True

    # ── Emotion Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _update_huan_log(collaboration_log: list, emotion_record) -> None:
        """更新焕的协作日志条目为实际情绪分析结果。
        优先使用 full_analysis 中的完整分析内容，fallback 到模板拼接。"""
        if not emotion_record:
            return

        # 尝试从 full_analysis 提取丰富内容
        huan_result = None
        full_analysis = getattr(emotion_record, 'full_analysis', None)
        if full_analysis:
            # full_analysis 可能是 JSON 字符串或普通字符串
            if isinstance(full_analysis, str):
                try:
                    fa_data = json.loads(full_analysis)
                    # 从 JSON 中提取 analysis_summary
                    huan_result = fa_data.get('analysis_summary')
                except (json.JSONDecodeError, TypeError):
                    # 非JSON，直接当作分析文本使用
                    huan_result = full_analysis

        # fallback: 模板拼接
        if not huan_result:
            _emotion_label = getattr(emotion_record, 'primary_emotion', None)
            _emotion_intensity = getattr(emotion_record, 'emotion_intensity', None)
            _deep_need = getattr(emotion_record, 'deep_need', None)
            _rec = getattr(emotion_record, 'interaction_recommendation', None)
            _comm_approach = None
            if _rec:
                try:
                    _rec_data = json.loads(_rec)
                    _comm_approach = _rec_data.get('communication_approach')
                except (json.JSONDecodeError, TypeError):
                    pass
            if _emotion_label:
                _parts = [f"感知到{_emotion_label}情绪"]
                if _emotion_intensity:
                    _parts[0] += f"（强度{_emotion_intensity}）"
                if _deep_need:
                    _parts.append(f"深层需求：{_deep_need}")
                if _comm_approach:
                    _parts.append(f"建议{_comm_approach}的沟通方式")
                huan_result = "，".join(_parts)
            else:
                huan_result = "完成了情绪感知"

        # 写入协作日志
        for _log in collaboration_log:
            if _log.get("role") == "焕":
                _log["result"] = huan_result
                break

    def _persist_emotion_snapshot(self, emotion_record, user_msg_record):
        """Save emotion snapshot on the user message and update user profile."""
        try:
            snapshot = json.dumps({
                "primary_emotion": emotion_record.primary_emotion,
                "emotion_intensity": emotion_record.emotion_intensity,
                "risk_level": emotion_record.risk_level,
            }, ensure_ascii=False)
            user_msg_record.emotion_snapshot = snapshot
            self.db.commit()
        except Exception:
            self.db.rollback()

        try:
            self.profile_service.update_from_emotion(self.user_id, {
                "primary_emotion": emotion_record.primary_emotion,
                "emotion_intensity": emotion_record.emotion_intensity,
                "deep_need": emotion_record.deep_need,
                "risk_level": emotion_record.risk_level,
                "full_analysis": emotion_record.full_analysis,
            })
        except Exception:
            pass

        # 回写焕的 emotional_state
        try:
            from datetime import datetime
            self.identity_service.update_emotional_state(
                self.user_id, "huan",
                {
                    "last_analysis": {
                        "primary_emotion": emotion_record.primary_emotion,
                        "emotion_intensity": emotion_record.emotion_intensity,
                        "deep_need": emotion_record.deep_need,
                        "risk_level": emotion_record.risk_level,
                    },
                    "updated_at": datetime.now().isoformat(),
                }
            )
        except Exception:
            pass

    def _huan_contribute_to_rules(self, emotion_record, user_message: str):
        """焕完成情绪分析后，向规则引擎贡献学习数据。"""
        try:
            rules = self._load_intent_rules()
            changed = False

            # 1. 高强度情绪 → 提取触发词加入 emotion_keywords
            if emotion_record.emotion_intensity in ("moderate", "high"):
                words = re.findall(r'[\u4e00-\u9fff]{2,4}', user_message.lower())
                emotion_kws = set(rules.get("emotion_keywords", []))
                query_kws = set(rules.get("query_keywords", []))

                for w in words:
                    if w not in emotion_kws and w not in query_kws and len(w) >= 2:
                        rules.setdefault("emotion_keywords", []).append(w)
                        changed = True
                        logger.info(f"焕: 新增情绪关键词 '{w}' (来自 {emotion_record.primary_emotion}/{emotion_record.emotion_intensity})")

                # 限制 emotion_keywords 最大数量
                if len(rules.get("emotion_keywords", [])) > 200:
                    rules["emotion_keywords"] = rules["emotion_keywords"][-150:]
                    changed = True

            # 2. 高风险情绪 → 加入 trigger_topics
            if emotion_record.risk_level in ("moderate", "high"):
                user_habits = rules.setdefault("user_habits", {})
                trigger_topics = user_habits.setdefault("trigger_topics", [])

                words = re.findall(r'[\u4e00-\u9fff]{2,4}', user_message.lower())
                for w in words:
                    if w not in trigger_topics and len(w) >= 2:
                        trigger_topics.append(w)
                        changed = True
                        logger.info(f"焕: 新增触发话题 '{w}' (风险等级: {emotion_record.risk_level})")

                # 限制 trigger_topics 最大数量
                if len(trigger_topics) > 50:
                    user_habits["trigger_topics"] = trigger_topics[-40:]
                    changed = True

            # 3. 持久化
            if changed:
                with open(self._RULES_PATH, "w", encoding="utf-8") as f:
                    json.dump(rules, f, ensure_ascii=False, indent=2)
                logger.info("焕: 规则引擎已更新")

        except Exception as e:
            logger.error(f"焕规则贡献失败: {e}")

    # ── Enriched System Prompt Builder ───────────────────────────────────

    async def _build_enriched_system_prompt(
        self, user_message: str, emotion_record=None
    ) -> str:
        """Build a system prompt enriched with persona, emotion, memory and profile context."""
        parts = []

        # 1. AI persona from identity service
        persona = self.identity_service.get_persona_prompt(self.user_id, "xuan")
        if persona:
            parts.append(persona)

        # 1.5 SKILL.md 行为规范注入
        xuan_skill = self.identity_service.get_skill_prompt("xuan")
        if xuan_skill:
            parts.append(f"\n{xuan_skill}\n")

        # 触发所有 AI 的身份自动生成（fire-and-forget）
        for _ai_name in ["xuan", "huan", "yao", "ji", "qing"]:
            _identity = self.identity_service.get_or_create_identity(self.user_id, _ai_name)
            if not _identity.gender or not _identity.personality:
                asyncio.create_task(
                    self.identity_service.self_generate_identity(
                        self.user_id, _ai_name, self.user_setting
                    )
                )

        # 2. Emotion context injection
        if emotion_record:
            rec = emotion_record.interaction_recommendation
            recommendation = {}
            if rec:
                try:
                    recommendation = json.loads(rec)
                except (json.JSONDecodeError, TypeError):
                    pass
            emotion_ctx = load_prompt_sections("xuan", "context-injection.md")["EMOTION_CONTEXT_INJECTION"].format(
                primary_emotion=emotion_record.primary_emotion or "unknown",
                emotion_intensity=emotion_record.emotion_intensity or "light",
                deep_need=emotion_record.deep_need or "unknown",
                risk_level=emotion_record.risk_level or "none",
                communication_approach=recommendation.get("communication_approach", "neutral"),
                tone=recommendation.get("tone", "neutral"),
                pacing=recommendation.get("pacing", "normal"),
                key_guidance=recommendation.get("key_guidance", ""),
            )
            parts.append(emotion_ctx)

        # 3. Memory context injection
        memory_ctx = self.memory_service.get_memory_context(self.user_id, user_message)
        if memory_ctx:
            parts.append(load_prompt_sections("xuan", "context-injection.md")["MEMORY_CONTEXT_INJECTION"].format(memory_fragments=memory_ctx))

        # 4. User profile injection
        profile_text = self.profile_service.get_profile_context(self.user_id)
        if profile_text:
            parts.append(load_prompt_sections("xuan", "context-injection.md")["USER_PROFILE_INJECTION"].format(profile_text=profile_text))

        # 5. Format guidelines — 遥 × 焕 联动
        format_section = await self._generate_format_guidelines(user_message, emotion_record)
        parts.append(format_section)

        # 6. 严格规范声明（放在最后，确保最高优先级）
        parts.append(load_prompt("xuan", "style-rules.md"))

        return "\n\n".join(parts) if parts else "You are a helpful assistant."

    async def _build_basic_system_prompt(self, user_message: str) -> str:
        """构建不含遥风格设计的基础系统 prompt（仅人设 + 记忆 + 画像）。"""
        parts = []

        # 1. AI persona
        persona = self.identity_service.get_persona_prompt(self.user_id, "xuan")
        if persona:
            parts.append(persona)

        # 1.5 SKILL.md 行为规范注入
        xuan_skill = self.identity_service.get_skill_prompt("xuan")
        if xuan_skill:
            parts.append(f"\n{xuan_skill}\n")

        # 2. Memory context injection
        memory_ctx = self.memory_service.get_memory_context(self.user_id, user_message)
        if memory_ctx:
            parts.append(load_prompt_sections("xuan", "context-injection.md")["MEMORY_CONTEXT_INJECTION"].format(memory_fragments=memory_ctx))

        # 3. User profile injection
        profile_text = self.profile_service.get_profile_context(self.user_id)
        if profile_text:
            parts.append(load_prompt_sections("xuan", "context-injection.md")["USER_PROFILE_INJECTION"].format(profile_text=profile_text))

        # 4. 严格规范声明
        parts.append(load_prompt("xuan", "style-rules.md"))

        return "\n\n".join(parts) if parts else "You are a helpful assistant."

    def _get_emotion_category(self, emotion_record) -> str:
        """将具体情绪映射到大类用于缓存"""
        if not emotion_record:
            return "default"
        # emotion_record 可能是 dict 或 ORM 对象
        primary = None
        if isinstance(emotion_record, dict):
            primary = emotion_record.get("primary_emotion", "")
        else:
            primary = getattr(emotion_record, "primary_emotion", "") or ""
        primary = primary.lower()
        positive = {"开心", "快乐", "兴奋", "满足", "喜悦", "愉快", "幸福", "感动", "期待", "happy", "excited", "joyful"}
        negative = {"难过", "伤心", "悲伤", "沮丧", "失望", "焦虑", "担忧", "害怕", "孤独", "sad", "anxious", "worried"}
        intense = {"愤怒", "暴怒", "恐惧", "崩溃", "绝望", "angry", "furious", "desperate"}
        if primary in positive or any(k in primary for k in positive):
            return "positive"
        if primary in negative or any(k in primary for k in negative):
            return "negative"
        if primary in intense or any(k in primary for k in intense):
            return "intense"
        return "neutral"

    async def _generate_format_guidelines(self, user_message: str, emotion_record) -> str:
        """遥（格式AI）动态生成格式指引。LLM 未配置或失败时降级到静态模板。"""
        # 缓存检查
        category = self._get_emotion_category(emotion_record)
        cache_key = f"{self.user_id}:{category}"
        now = _time.time()
        if cache_key in self.__class__._format_cache:
            guidelines, ts = self.__class__._format_cache[cache_key]
            if now - ts < 1800:  # 30 min TTL
                logger.info(f">>> FORMAT_CACHE HIT: {cache_key}")
                return guidelines

        # 静态模板降级所需数据
        emotion_state = "neutral"
        intensity = "低"
        if emotion_record:
            emotion_state = getattr(emotion_record, "primary_emotion", "neutral") or "neutral"
            intensity = getattr(emotion_record, "emotion_intensity", "低") or "低"

        format_usage = None
        try:
            format_llm = get_format_llm_client(self.user_setting)

            # 构建遥的上下文
            emotion_ctx = ""
            if emotion_record:
                emotion_ctx = (
                    f"焕的情绪分析结果：\n"
                    f"- 情绪类型: {emotion_state}\n"
                    f"- 情绪强度: {intensity}\n"
                    f"- 深层需求: {getattr(emotion_record, 'deep_need', 'unknown') or 'unknown'}\n"
                    f"- 风险等级: {getattr(emotion_record, 'risk_level', 'none') or 'none'}"
                )

            user_ctx = f"用户消息：{user_message}"
            if emotion_ctx:
                user_ctx = f"{emotion_ctx}\n\n{user_ctx}"

            response, format_usage = await format_llm.chat(
                [
                    {"role": "system", "content": load_prompt("yao", "system-prompt.md")},
                    {"role": "user", "content": user_ctx},
                ],
                temperature=0.3,
            )

            # 解析 JSON 输出
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            result = json.loads(response)
            self._last_format_result = result
            guidelines = result.get("format_guidelines", {})

            special_elements = guidelines.get("special_elements", [])
            if isinstance(special_elements, list):
                special_elements = "、".join(special_elements)
            avoid = guidelines.get("avoid", [])
            if isinstance(avoid, list):
                avoid = "、".join(avoid)

            result = load_prompt_sections("xuan", "context-injection.md")["FORMAT_CONTEXT_INJECTION"].format(
                structure=guidelines.get("structure", "自然组织"),
                length=guidelines.get("length", "medium"),
                style=guidelines.get("style", "自然亲和"),
                special_elements=special_elements or "无",
                avoid=avoid or "无",
            )

            self.__class__._format_cache[cache_key] = (result, now)
            self.log_service.log(
                "格式AI（遥）调用成功", level="info",
                user_id=self.user_id, source="agent.format", status_code=200,
            )
            return result

        except LLMConfigError:
            logger.error("遥(格式AI) LLM 调用失败: user_setting 未配置或格式AI未启用")
            self.log_service.log(
                "格式AI（遥）未配置", level="warn",
                user_id=self.user_id, source="agent.format", status_code=501,
            )
        except Exception as e:
            logger.error(f"遥(格式AI) LLM 调用失败: {e}")
            self.log_service.log(
                "格式AI（遥）调用失败", level="error",
                user_id=self.user_id, source="agent.format", status_code=500,
                details={"error": str(e)},
            )
        finally:
            if format_usage:
                self._all_usages.append({**format_usage, "role_name": "遥"})

        # 降级：使用静态 fallback 模板
        self._last_format_result = {"fallback": True, "emotion_state": emotion_state, "intensity": intensity}
        _fallback_templates = load_json_config("yao", "fallback-templates.json")
        fallback = _fallback_templates.get(category, _fallback_templates["default"])
        self.__class__._format_cache[cache_key] = (fallback, now)  # 缓存 fallback 避免重复超时/失败
        return fallback

    # ── Intent Rules Loading & Learning ──────────────────────────────────

    def _load_intent_rules(self) -> dict:
        """Load intent classification rules from JSON file."""
        try:
            if self._RULES_PATH.exists():
                with open(self._RULES_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load intent rules: {e}")
        return {"query_keywords": [], "casual_keywords": [], "emotion_keywords": [], "learned_patterns": {}}

    def _learn_intent_pattern(self, message: str, intent_result: dict):
        """
        晴主导的规则迭代：
        1. 记录 LLM 分类结果作为学习素材
        2. 从焕的用户画像中提取习惯信息来优化规则
        """
        try:
            msg = message.strip().lower()
            rules = self._intent_rules
            learned = rules.setdefault("learned_patterns", {})

            # ── 1. 存储分类模式 ──
            pattern = msg[:30] if len(msg) > 30 else msg

            # 限制 learned_patterns 数量，保留最新 400 个
            if len(learned) > 500:
                keys = list(learned.keys())
                for k in keys[: len(keys) - 400]:
                    del learned[k]

            learned[pattern] = {
                "description": intent_result.get("description", message),
                "user_state": intent_result.get("user_state", ""),
                "target_path": intent_result.get("target_path"),
                "parameters": intent_result.get("parameters", {}),
                "need_emotion": intent_result.get("need_emotion", True),
            }

            # ── 2. 从消息中提取关键词 ──
            words = re.findall(r'[\u4e00-\u9fff]{2,4}', msg)
            # 关键词现在只用于情绪/查询匹配，不再区分 task/chat

            # ── 3. 向焕请求用户习惯，优化规则 ──
            self._sync_user_habits_to_rules(rules)

            # 持久化
            with open(self._RULES_PATH, "w", encoding="utf-8") as f:
                json.dump(rules, f, ensure_ascii=False, indent=2)

            logger.info(f"晴: learned pattern '{pattern}' -> user_state={intent_result.get('user_state', '')[:20]}")
        except Exception as e:
            logger.warning(f"晴: rule learning failed: {e}")

    def _sync_user_habits_to_rules(self, rules: dict):
        """
        晴向焕（通过 profile_service）请求用户习惯分析，
        将用户兴趣、常用话题等融入规则引擎。
        """
        try:
            profile = self.profile_service.get_or_create_profile(self.user_id)
            if not profile:
                return

            # 从用户画像中提取习惯性关键词
            user_section = rules.setdefault("user_habits", {})

            # 兴趣领域 → 可能的 task 关键词
            interests = ProfileService._load_json_list(getattr(profile, "interests", None))
            if interests:
                user_section["interests"] = interests

            # 触发话题 → 需要情绪关注的关键词
            trigger_topics = ProfileService._load_json_list(getattr(profile, "trigger_topics", None))
            if trigger_topics:
                user_section["trigger_topics"] = trigger_topics
                # 将触发话题加入 emotion_keywords
                emotion_kws = set(rules.get("emotion_keywords", []))
                for topic in trigger_topics:
                    if isinstance(topic, str) and topic not in emotion_kws:
                        rules.setdefault("emotion_keywords", []).append(topic)

            # 安全话题 → 不需要情绪分析的话题
            safe_topics = ProfileService._load_json_list(getattr(profile, "safe_topics", None))
            if safe_topics:
                user_section["safe_topics"] = safe_topics

        except Exception as e:
            logger.debug(f"晴: sync user habits failed (may not have profile yet): {e}")

    # ── Intent Parsing ──────────────────────────────────────────────────

    async def _parse_intent(self, message: str, latest_emotion=None) -> dict:
        """Use fast rule-based classification first, LLM fallback only when ambiguous."""

        # ── 快速规则匹配（<1ms）──
        fast_result = self._fast_classify(message)
        if fast_result is not None:
            logger.info(f"Intent fast-classified: desc={fast_result.get('description', '')[:30]}, need_emotion={fast_result.get('need_emotion')}")
            return fast_result

        # ── LLM Fallback（仅当规则无法判断时）──
        logger.info("Intent ambiguous, falling back to LLM")
        intent_usage = None
        try:
            intent_llm = get_intent_llm_client(self.user_setting)

            # 构造用户消息，注入 latest_emotion 上下文
            user_content = message
            if latest_emotion:
                emotion_info = f"{getattr(latest_emotion, 'primary_emotion', 'unknown')}（强度：{getattr(latest_emotion, 'emotion_intensity', 'unknown')}）"
                deep_need = getattr(latest_emotion, 'deep_need', None)
                if deep_need:
                    emotion_info += f"，深层需求：{deep_need}"
                user_content = f"[用户最近情绪状态: {emotion_info}]\n\n{message}"

            response, intent_usage = await intent_llm.chat(
                [
                    {"role": "system", "content": load_prompt("qing", "system-prompt.md")},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
            )
            # 使用健壮的 JSON 提取逻辑
            result = self._parse_json_response(response)
            if result is None:
                logger.warning(f"Intent JSON extraction failed, response: {response[:200] if response else '(empty)'}")
                self.log_service.log(
                    "意图AI（晴）JSON解析错误", level="warn",
                    user_id=self.user_id, source="agent.intent", status_code=422,
                    details={"error": "Failed to extract JSON from response", "response_preview": (response or "")[:200]},
                )
                return {"description": message, "user_state": "未知", "need_emotion": True}

            # 验证必需字段
            if "description" not in result:
                logger.warning(f"Intent parsing missing description, response: {response[:200]}")
                return {"description": message, "user_state": "未知", "need_emotion": True}

            # Learn from LLM result for future fast classification
            self._learn_intent_pattern(message, result)

            logger.info(f"Intent parsed (LLM fallback): desc={result.get('description', '')[:30]}, user_state={result.get('user_state', '')[:30]}, need_emotion={result.get('need_emotion')}")
            self.log_service.log(
                "意图AI（晴）调用成功", level="info",
                user_id=self.user_id, source="agent.intent", status_code=200,
            )
            return result

        except LLMConfigError as e:
            logger.warning(f"意图AI（晴）未配置，使用默认模式: {e}")
            self.log_service.log(
                "意图AI（晴）未配置", level="warn",
                user_id=self.user_id, source="agent.intent", status_code=501,
            )
            return {"description": message, "user_state": "未知", "need_emotion": True}
        except Exception as e:
            logger.error(f"Intent LLM fallback failed: {e}")
            self.log_service.log(
                "意图AI（晴）调用失败", level="error",
                user_id=self.user_id, source="agent.intent", status_code=500,
                details={"error": str(e)},
            )
            return {"description": message, "user_state": "未知", "need_emotion": True}
        finally:
            if intent_usage:
                self._all_usages.append({**intent_usage, "role_name": "晴"})

    def _summarize_message(self, message: str) -> str:
        """从用户消息中提取简洁的任务标题（5-20字）"""
        msg = message.strip()
        # 移除常见的口语化前缀
        prefixes = ["帮我", "请帮我", "麻烦", "我想", "我要", "能不能", "可以", "请"]
        for p in prefixes:
            if msg.startswith(p):
                msg = msg[len(p):]
                break
        if len(msg) <= 20:
            return msg  # 短消息可以直接用
        return msg[:20]

    def _fast_classify(self, message: str) -> dict | None:
        """
        Rule-based fast intent classification (<1ms).
        Returns intent dict if confident, None if ambiguous (needs LLM).
        """
        msg = message.strip().lower()
        rules = self._intent_rules

        # 0. 预加载用户习惯数据（用于后续叠加）
        user_habits = rules.get("user_habits", {})
        trigger_topics = user_habits.get("trigger_topics", [])
        safe_topics = user_habits.get("safe_topics", [])
        has_trigger = any(t in msg for t in trigger_topics if isinstance(t, str))
        is_safe_topic = any(t in msg for t in safe_topics if isinstance(t, str))

        # 1. Check learned patterns first (exact substring match from history)
        learned = rules.get("learned_patterns", {})
        for pattern, intent_data in learned.items():
            if pattern in msg:
                logger.info(f"Intent matched learned pattern: '{pattern}'")
                result = dict(intent_data)
                # 用户习惯叠加：触发话题强制 need_emotion
                if has_trigger and not is_safe_topic:
                    result["need_emotion"] = True
                return result

        # 2. Keyword matching
        query_kws = rules.get("query_keywords", [])
        casual_kws = rules.get("casual_keywords", [])
        emotion_kws = rules.get("emotion_keywords", [])

        has_query_kw = any(kw in msg for kw in query_kws)
        has_casual_kw = any(kw in msg for kw in casual_kws)
        has_emotion_kw = any(kw in msg for kw in emotion_kws)

        # 用户习惯叠加：触发话题也视为需要情绪分析
        need_emotion = has_emotion_kw or (has_trigger and not is_safe_topic)

        # 明确的查询/请求（有query关键词，没有casual关键词）
        if has_query_kw and not has_casual_kw:
            return {
                "description": self._summarize_message(message),
                "user_state": "用户在查询或请求信息",
                "target_path": None,
                "parameters": {},
                "need_emotion": need_emotion or True,  # 默认倾向 true
            }

        # 明确的闲聊（有casual关键词，没有query关键词）
        if has_casual_kw and not has_query_kw:
            return {
                "description": message,
                "user_state": "随意闲聊",
                "target_path": None,
                "parameters": {},
                "need_emotion": need_emotion or True,  # 默认倾向 true
            }

        # 纯短消息（<10字，没有query关键词）→ 检查是否含疑问/查询指示词
        query_indicators = ["什么", "几", "多少", "怎么", "如何", "哪", "吗", "呢", "查", "搜", "获取"]
        has_query = any(ind in msg for ind in query_indicators)

        if len(msg) < 10 and not has_query_kw:
            if has_query:
                # 含疑问词的短消息 → 不确定，让 LLM 判断
                return None
            return {
                "description": message,
                "user_state": "简短交流",
                "target_path": None,
                "parameters": {},
                "need_emotion": need_emotion or True,  # 默认倾向 true
            }

        # 歧义 → 返回 None，让 LLM 判断
        return None

    # ── Multi-Step Orchestration ──────────────────────────────────────

    async def _plan_task(self, user_message: str, description: str, emotion_task=None) -> dict | None:
        """晴分析任务，判断是否需要多步执行。参考焕的情绪分析辅助决策。"""
        try:
            # 如果焕的分析已完成，获取情绪上下文辅助晴的判断
            emotion_hint = ""
            if emotion_task and emotion_task.done():
                try:
                    _er = emotion_task.result()
                    if _er:
                        emotion_hint = f"\n用户情绪状态：{_er.primary_emotion}（强度：{_er.emotion_intensity}）\n深层需求：{_er.deep_need or '无'}"
                except Exception:
                    pass

            prompt = load_prompt("qing", "task-planning.md").format(
                user_message=user_message,
                description=description,
            )
            if emotion_hint:
                prompt += f"\n\n焕的情绪分析参考：{emotion_hint}"

            llm = get_intent_llm_client(self.user_setting)
            try:
                response, plan_usage = await asyncio.wait_for(
                    llm.chat([{"role": "user", "content": prompt}], temperature=0.3),
                    timeout=15,
                )
                if plan_usage:
                    self._all_usages.append({**plan_usage, "role_name": "晴"})
            except asyncio.TimeoutError:
                logger.warning("任务规划超时（15s），跳过多步分析")
                return None
            return self._parse_json_response(response)
        except Exception as e:
            logger.warning(f"任务规划失败: {e}")
            return None

    async def _execute_multi_step(
        self, user_message, plan, emotion_task, _collaboration_log, working_dir,
        need_emotion,  # NOTE: 焕的调度已改由 participants 控制，此参数保留用于将来扩展
        conv, user_msg_record
    ):
        """多步工具编排执行循环"""
        info_gaps = plan["info_gaps"]
        final_goal = plan.get("final_goal", user_message)
        gathered_info = {}  # {gap_id: result_data}
        remaining_gaps = list(info_gaps)
        max_steps = len(info_gaps) * 2 + 2  # 防止无限循环
        step_count = 0
        ask_messages = []  # 收集需要问用户的问题

        # 晴动态分配的参与者
        participants = plan.get("participants") if plan.get("participants") is not None else ["huan", "yao"]
        # 计算信息收集完毕后的 next 角色列表
        _post_collect_next = []
        if "huan" in participants:
            _post_collect_next.append("焕")
        if "yao" in participants:
            _post_collect_next.append("遥")
        _post_collect_next.append("玄")

        # 晴的规划日志
        participants_desc = "、".join(participants) if participants else "无额外角色"
        _collaboration_log.append({
            "role": "晴",
            "action": "任务规划",
            "result": f"识别到{len(info_gaps)}个信息缺口，启动多步编排，调动角色：{participants_desc}",
            "next": ["机"],
        })
        yield {"type": "thinking", "content": f"正在规划，需要收集{len(info_gaps)}项信息..."}

        while remaining_gaps and step_count < max_steps:
            step_count += 1

            # 1. 决定下一步
            next_step = await self._decide_next_step(
                user_message, final_goal, gathered_info, remaining_gaps
            )

            if not next_step or next_step.get("action") == "complete":
                break

            target_gap_id = next_step.get("target_gap", "")

            if next_step.get("action") == "ask_user":
                # 收集要问用户的问题
                ask_msg = next_step.get("ask_message", "")
                if ask_msg:
                    ask_messages.append(ask_msg)
                gathered_info[target_gap_id] = "需要用户提供"
                remaining_gaps = [g for g in remaining_gaps if g["id"] != target_gap_id]
                _collaboration_log.append({
                    "role": "晴",
                    "action": "标记询问",
                    "result": f"「{target_gap_id}」需要询问用户：{ask_msg}",
                    "next": ["机"] if remaining_gaps else _post_collect_next,
                })
                continue

            # 2. action == "execute_tool"
            tool_hint = next_step.get("tool_hint", "")

            yield {"type": "thinking", "content": f"正在获取{target_gap_id}信息..."}

            # 3. 机匹配并执行工具
            tool = await self._find_tool(tool_hint)
            if tool:
                try:
                    # 构建参数（注入前序结果上下文）
                    tool_params = {}
                    if gathered_info:
                        tool_params["context"] = gathered_info

                    exec_result = execute_tool(tool.code, tool_params, working_dir=working_dir)
                    success = exec_result.get("success", False)
                    result_data = exec_result.get("result", "")

                    if success:
                        gathered_info[target_gap_id] = result_data
                        remaining_gaps = [g for g in remaining_gaps if g["id"] != target_gap_id]
                        _collaboration_log.append({
                            "role": "机",
                            "action": f"获取{target_gap_id}",
                            "result": f"执行「{tool.name}」成功",
                            "next": ["机"] if remaining_gaps else _post_collect_next,
                        })
                    else:
                        gathered_info[target_gap_id] = f"获取失败: {str(result_data)[:200]}"
                        remaining_gaps = [g for g in remaining_gaps if g["id"] != target_gap_id]
                        _collaboration_log.append({
                            "role": "机",
                            "action": f"获取{target_gap_id}",
                            "result": f"执行「{tool.name}」失败，标记为缺失",
                            "next": ["机"] if remaining_gaps else _post_collect_next,
                        })
                except Exception as e:
                    logger.warning(f"多步编排工具执行异常: {e}")
                    gathered_info[target_gap_id] = f"执行异常: {str(e)[:200]}"
                    remaining_gaps = [g for g in remaining_gaps if g["id"] != target_gap_id]
            else:
                # 无匹配工具 — 尝试生成工具
                try:
                    yield {"type": "thinking", "content": "未找到现有工具，正在生成..."}
                    func_name, gen_code, desc_en, desc_zh = await generate_tool_code(
                        description=tool_hint,
                        user_setting=self.user_setting,
                        usage_callback=self._make_usage_callback("机"),
                    )
                    if gen_code:
                        exec_result = execute_tool(gen_code, {}, working_dir=working_dir)
                        success = exec_result.get("success", False)
                        result_data = exec_result.get("result", "")

                        if success:
                            gathered_info[target_gap_id] = result_data
                            # 注册新工具
                            try:
                                self.tool_service.register_or_update(
                                    name=func_name,
                                    description=desc_en or func_name.replace("_", " ").title(),
                                    code=gen_code,
                                    user_id=self.user_id,
                                    description_zh=desc_zh,
                                    tool_type="atomic",
                                )
                            except Exception:
                                pass
                        else:
                            gathered_info[target_gap_id] = f"工具生成后执行失败: {str(result_data)[:200]}"
                    else:
                        gathered_info[target_gap_id] = "无法生成对应工具"
                except Exception as e:
                    logger.warning(f"多步编排工具生成异常: {e}")
                    gathered_info[target_gap_id] = f"工具生成失败: {str(e)[:200]}"

                remaining_gaps = [g for g in remaining_gaps if g["id"] != target_gap_id]
                _collaboration_log.append({
                    "role": "机",
                    "action": f"获取{target_gap_id}",
                    "result": "通过生成工具尝试获取",
                    "next": ["机"] if remaining_gaps else _post_collect_next,
                })

        # === 所有信息收集完毕（或达上限），综合生成回复 ===

        # 条件性调度焕（情绪分析）
        emotion_record = None
        if "huan" in participants and emotion_task:
            try:
                emotion_record = await emotion_task
                # 更新焕的日志
                self._update_huan_log(_collaboration_log, emotion_record)
            except Exception:
                pass
        elif emotion_task:
            # 焕未被选中参与，但任务已启动 — 仍等待完成避免泄漏，但不使用结果
            try:
                await emotion_task
            except Exception:
                pass

        # 情绪快照持久化（仅焕参与时）
        if emotion_record:
            try:
                self._persist_emotion_snapshot(emotion_record, user_msg_record)
            except Exception:
                pass

        # 条件性调度遥（风格设计）
        if "yao" in participants:
            try:
                enriched_prompt = await self._build_enriched_system_prompt(user_message, emotion_record)
                _collaboration_log.append({
                    "role": "遥",
                    "action": "风格设计",
                    "result": "为综合回复设计了表达风格",
                    "next": ["玄"],
                })
            except Exception as e:
                logger.error(f"多步编排系统提示构建失败: {e}")
                enriched_prompt = "You are a helpful assistant."
        else:
            # 遥未参与 — 使用基础 prompt（仅人设 + 记忆 + 画像，跳过风格设计 LLM 调用）
            try:
                enriched_prompt = await self._build_basic_system_prompt(user_message)
            except Exception as e:
                logger.error(f"多步编排基础提示构建失败: {e}")
                enriched_prompt = "You are a helpful assistant."

        # 综合解读
        all_results_text = "\n".join([
            f"- {k}: {v}" for k, v in gathered_info.items()
        ])

        # 如果有需要问用户的问题，追加到 prompt
        ask_section = ""
        if ask_messages:
            ask_section = "\n\n另外，以下信息需要用户补充，请在回复中自然地提出这些问题：\n" + "\n".join([f"- {q}" for q in ask_messages])

        interpretation = load_prompt("xuan", "multi-step-interpret.md").format(
            user_message=user_message,
            all_results=all_results_text,
        ) + ask_section

        messages = [
            {"role": "system", "content": enriched_prompt},
            {"role": "user", "content": interpretation},
        ]

        # 流式生成
        yield {"type": "thinking", "content": "正在综合分析..."}

        llm = get_chat_llm_client(self.user_setting)
        assistant_text = ""
        try:
            async for chunk in llm.stream_chat(messages, temperature=0.7, usage_callback=self._make_usage_callback("玄")):
                assistant_text += chunk
                yield {"type": "message", "content": chunk}
        except Exception as e:
            logger.error(f"多步编排生成回复失败: {e}")
            fallback = "抱歉，综合分析时遇到了问题。我收集到的信息：" + all_results_text
            assistant_text = fallback
            yield {"type": "message", "content": fallback}

        # 确保 assistant_text 不为空（极端降级）
        if not assistant_text:
            assistant_text = "抱歉，综合分析时未能生成回复。收集到的信息：" + all_results_text
            yield {"type": "message", "content": assistant_text}

        # 玄的日志
        _collaboration_log.append({
            "role": "玄",
            "action": "综合回复",
            "result": f"综合{len(gathered_info)}项信息，生成了{len(assistant_text)}字的回复",
            "next": None,
        })

        # 保存消息（复用现有模式）
        try:
            self.conversation_service.add_message(
                conversation_id=conv.id,
                user_id=self.user_id,
                role="assistant",
                content=assistant_text,
                metadata_json=json.dumps({
                    "type": "multi_step_result",
                    "multi_step": True,
                    "gathered_info": {k: str(v)[:500] for k, v in gathered_info.items()},
                    "collaboration": _collaboration_log,
                }, ensure_ascii=False),
            )
        except Exception as e:
            logger.error(f"多步编排消息保存失败: {e}")

        # 先发 done 事件，解锁交互
        yield {
            "type": "done",
            "content": "",
            "conversation_id": conv.id if conv else None,
            "usages": self._all_usages if self._all_usages else None,
        }

        # 再发协作日志
        if _collaboration_log:
            yield {
                "type": "collaboration",
                "content": "",
                "conversation_id": conv.id if conv else None,
                "collaboration": _collaboration_log,
            }

        # 后台触发记忆压缩 + 画像提取（fire-and-forget，与主路径 finally 一致）
        try:
            asyncio.create_task(self.memory_service.compress_recent(self.user_id, self.user_setting))
        except Exception:
            pass
        try:
            asyncio.create_task(
                self.profile_service.update_from_conversation(
                    self.user_id, user_message, self.user_setting
                )
            )
        except Exception:
            pass

    async def _decide_next_step(self, user_message, final_goal, gathered_info, remaining_gaps):
        """机/晴协作决定下一步操作"""
        try:
            prompt = load_prompt("qing", "next-step.md").format(
                user_message=user_message,
                final_goal=final_goal,
                gathered_info=json.dumps(gathered_info, ensure_ascii=False, indent=2) if gathered_info else "暂无",
                remaining_gaps=json.dumps(
                    [{"id": g["id"], "description": g["description"]} for g in remaining_gaps],
                    ensure_ascii=False
                ),
            )
            llm = get_intent_llm_client(self.user_setting)
            response, next_usage = await llm.chat(
                [{"role": "user", "content": prompt}], temperature=0.3
            )
            if next_usage:
                self._all_usages.append({**next_usage, "role_name": "晴"})
            return self._parse_json_response(response)
        except Exception:
            # 降级：直接按顺序执行下一个 gap
            if remaining_gaps:
                gap = remaining_gaps[0]
                return {
                    "action": "execute_tool",
                    "target_gap": gap["id"],
                    "tool_hint": gap.get("tool_hint", gap["description"]),
                }
            return {"action": "complete"}

    # ── Tool Finding (original) ─────────────────────────────────────────

    async def _find_tool(self, description: str):
        """Search for a matching tool in the database."""
        # 提取中文字符序列和英文单词
        cn_phrases = re.findall(r'[\u4e00-\u9fff]+', description)
        en_words = [w for w in re.findall(r'[a-zA-Z_]{3,}', description)]

        # 从中文片段中提取 2-4 字符的子串作为关键词
        cn_keywords = []
        for phrase in cn_phrases:
            for i in range(len(phrase)):
                for size in (2, 3, 4):
                    if i + size <= len(phrase):
                        cn_keywords.append(phrase[i:i+size])

        keywords = list(set(en_words + cn_keywords))[:15]

        # 搜索匹配的工具
        candidates = []
        for kw in keywords:
            found = self.tool_service.search_tools(kw)
            candidates.extend(found)

        # Deduplicate
        seen = set()
        unique = []
        for t in candidates:
            if t.id not in seen:
                seen.add(t.id)
                unique.append(t)

        if not unique:
            return None

        if len(unique) == 1:
            return unique[0]

        # LLM-assisted selection
        tool_list = "\n".join(f"- {t.name}: {t.description}" for t in unique)
        prompt = load_prompt("ji", "tool-match.md").format(description=description, tool_list=tool_list)

        try:
            selection, tool_usage = await self.llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            if tool_usage:
                self._all_usages.append({**tool_usage, "role_name": "玄"})
            selection = selection.strip().lower()
            if selection == "none":
                return None
            for t in unique:
                if t.name.lower() == selection:
                    return t
        except Exception:
            pass

        return unique[0] if unique else None

    # ── Tool Iteration Decision ─────────────────────────────────────────

    async def _decide_tool_iteration(self, tool, exec_result, user_request) -> dict | None:
        """Ask LLM whether to iterate on a failed tool."""
        try:
            iterate_prompt = load_prompt("ji", "tool-iterate.md").format(
                tool_name=tool.name,
                version=tool.version,
                description=tool.description,
                code=tool.code,
                result=str(exec_result.get("result", ""))[:2000],
                success=exec_result.get("success", False),
                user_request=user_request,
            )

            iterate_llm = get_tool_llm_client(self.user_setting)
            raw_response, iter_usage = await iterate_llm.chat(
                [{"role": "user", "content": iterate_prompt}],
                temperature=0.2,
            )
            if iter_usage:
                self._all_usages.append({**iter_usage, "role_name": "机"})

            return self._parse_json_response(raw_response)
        except Exception:
            return None

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(text: str) -> dict | None:
        """Extract JSON from LLM response, handling markdown fences, <think> tags, etc."""
        if not text or not text.strip():
            return None

        text = text.strip()

        # 移除 <think>...</think> 标签（thinking 模型可能返回）
        text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()

        if not text:
            return None

        # 移除 markdown 代码块包裹
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # 1. 直接尝试解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 尝试提取第一个 { 到最后一个 } 之间的内容
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # 3. 逐行查找：第一行以 { 开头 到 最后一行以 } 结尾
        lines = text.split("\n")
        start_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("{") and start_idx is None:
                start_idx = i
            if stripped.endswith("}"):
                end_idx = i
        if start_idx is not None and end_idx is not None and end_idx >= start_idx:
            candidate = "\n".join(lines[start_idx:end_idx + 1]).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        return None
