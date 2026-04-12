import asyncio
import json
import logging
import os
import re
import shutil
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.services.identity_service import IdentityService
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


def _extract_json_from_llm_response(text: str) -> dict | None:
    """从 LLM 返回中提取 JSON，处理 <think> 标签和 markdown 代码块。"""
    if not text:
        return None

    # 1. 移除 <think>...</think> 标签（含未闭合的情况）
    text = re.sub(r'<think>[\s\S]*?</think>', '', text)
    # 处理未闭合的 <think>：移除 <think> 及其后所有内容直到出现 { 之前
    text = re.sub(r'<think>[\s\S]*?(?=\{)', '', text)
    text = text.strip()

    # 2. 移除 markdown 代码块标记
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 3. 尝试直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 4. 提取从第一个 { 到最后一个 } 的内容
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except (json.JSONDecodeError, ValueError):
            pass

    # 5. 逐行搜索
    lines = text.split('\n')
    json_start = -1
    brace_count = 0
    json_lines: list[str] = []
    for line in lines:
        if json_start == -1 and '{' in line:
            json_start = line.index('{')
            line = line[json_start:]
        if json_start != -1:
            json_lines.append(line)
            brace_count += line.count('{') - line.count('}')
            if brace_count <= 0:
                try:
                    return json.loads('\n'.join(json_lines))
                except (json.JSONDecodeError, ValueError):
                    json_start = -1
                    brace_count = 0
                    json_lines = []

    return None

# Track running state
_scheduler_task: asyncio.Task | None = None
_ji_background_task: asyncio.Task | None = None


async def _run_daily_compression():
    """Compress yesterday's messages into daily summaries for all users."""
    from app.models.conversation import Message
    from sqlalchemy import distinct

    db = SessionLocal()
    try:
        yesterday = datetime.now() - timedelta(days=1)

        # Find all users who had messages yesterday
        day_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        user_ids = (
            db.query(distinct(Message.user_id))
            .filter(
                Message.is_summarized == False,
                Message.created_at >= day_start,
                Message.created_at < day_end,
            )
            .all()
        )

        memory_service = MemoryService(db)
        for (uid,) in user_ids:
            try:
                await memory_service.compress_day(uid, yesterday)
                logger.info(f"Daily compression completed for user {uid}")
            except Exception as e:
                logger.error(f"Daily compression failed for user {uid}: {e}")
    finally:
        db.close()


async def _run_weekly_compression():
    """Compress last week's daily summaries into weekly summaries."""
    from app.models.memory_summary import MemorySummary
    from sqlalchemy import distinct

    db = SessionLocal()
    try:
        # Last Monday
        today = datetime.now()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)

        user_ids = (
            db.query(distinct(MemorySummary.user_id))
            .filter(
                MemorySummary.period_type == "daily",
                MemorySummary.period_start >= last_monday,
                MemorySummary.period_start < last_monday + timedelta(days=7),
            )
            .all()
        )

        memory_service = MemoryService(db)
        for (uid,) in user_ids:
            try:
                await memory_service.compress_week(uid, last_monday)
                logger.info(f"Weekly compression completed for user {uid}")
            except Exception as e:
                logger.error(f"Weekly compression failed for user {uid}: {e}")
    finally:
        db.close()


async def _run_monthly_compression():
    """Compress last month's weekly summaries into monthly summaries."""
    from app.models.memory_summary import MemorySummary
    from sqlalchemy import distinct

    db = SessionLocal()
    try:
        today = datetime.now()
        if today.month == 1:
            last_month, last_year = 12, today.year - 1
        else:
            last_month, last_year = today.month - 1, today.year

        user_ids = (
            db.query(distinct(MemorySummary.user_id))
            .filter(MemorySummary.period_type == "weekly")
            .all()
        )

        memory_service = MemoryService(db)
        for (uid,) in user_ids:
            try:
                await memory_service.compress_month(uid, last_year, last_month)
                logger.info(f"Monthly compression completed for user {uid}")
            except Exception as e:
                logger.error(f"Monthly compression failed for user {uid}: {e}")
    finally:
        db.close()


async def _run_yearly_compression():
    """Compress last year's monthly summaries into yearly summaries."""
    from app.models.memory_summary import MemorySummary
    from sqlalchemy import distinct

    db = SessionLocal()
    try:
        last_year = datetime.now().year - 1

        user_ids = (
            db.query(distinct(MemorySummary.user_id))
            .filter(MemorySummary.period_type == "monthly")
            .all()
        )

        memory_service = MemoryService(db)
        for (uid,) in user_ids:
            try:
                await memory_service.compress_year(uid, last_year)
                logger.info(f"Yearly compression completed for user {uid}")
            except Exception as e:
                logger.error(f"Yearly compression failed for user {uid}: {e}")
    finally:
        db.close()


async def _run_identity_evolution():
    """每日评估所有用户的 AI 身份迭代。"""
    logger.info("开始执行每日身份迭代评估...")
    db = SessionLocal()
    try:
        from app.models.ai_identity import AIIdentity
        from app.models.conversation import Message
        from app.models.setting import UserSetting
        from sqlalchemy import distinct

        user_ids = db.query(distinct(AIIdentity.user_id)).all()
        user_ids = [uid[0] for uid in user_ids]

        identity_service = IdentityService(db)

        for user_id in user_ids:
            try:
                three_days_ago = datetime.now() - timedelta(days=3)
                recent_msgs = (
                    db.query(Message)
                    .filter(
                        Message.user_id == user_id,
                        Message.created_at >= three_days_ago,
                    )
                    .order_by(Message.created_at.desc())
                    .limit(30)
                    .all()
                )

                if not recent_msgs:
                    continue

                summary = "\n".join(
                    [
                        f"[{m.role}] {m.content[:100]}"
                        for m in reversed(recent_msgs[-15:])
                    ]
                )

                user_setting = (
                    db.query(UserSetting)
                    .filter(UserSetting.user_id == user_id)
                    .first()
                )

                for ai_name in ["xuan", "huan", "yao", "ji", "qing"]:
                    try:
                        await identity_service.auto_evolve(
                            user_id, ai_name, summary, user_setting
                        )
                    except Exception as e:
                        logger.warning(
                            f"身份迭代失败 user={user_id} ai={ai_name}: {e}"
                        )

            except Exception as e:
                logger.warning(f"用户 {user_id} 身份迭代异常: {e}")

        logger.info(f"每日身份迭代评估完成，处理了 {len(user_ids)} 个用户")
    except Exception as e:
        logger.error(f"每日身份迭代评估失败: {e}")
    finally:
        db.close()


async def _ji_task1_rule_engine(user_id, user_setting, log_service, token_service, db):
    """任务1：规则引擎迭代 — 审查并优化 intent_rules.json"""
    from app.ai.factory import get_tool_llm_client
    from app.models.log import Log

    result = {"name": "规则引擎迭代", "status": "success", "changes_made": [], "details": ""}

    # 读取当前规则文件
    rules_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "ai", "intent_rules.json"
    )
    with open(rules_path, "r", encoding="utf-8") as f:
        intent_rules = json.load(f)
    intent_rules_text = json.dumps(intent_rules, ensure_ascii=False, indent=2)

    # 获取最近的意图识别 / 分类日志摘要
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_logs = (
        db.query(Log)
        .filter(
            Log.user_id == user_id,
            Log.created_at >= one_hour_ago,
        )
        .order_by(Log.created_at.desc())
        .limit(30)
        .all()
    )
    logs_summary = "\n".join(
        [f"[{l.level}] {l.source or ''}: {l.message[:120]}" for l in recent_logs]
    ) if recent_logs else "（最近1小时无日志记录）"

    prompt = (
        '你是璇玑系统的迭代者"机"。请审查以下意图规则文件，结合最近的对话日志，'
        "评估规则质量并提出优化建议。\n\n"
        f"当前规则：\n{intent_rules_text}\n\n"
        f"最近对话日志摘要：\n{logs_summary}\n\n"
        "请输出 JSON：\n"
        '{\n'
        '  "analysis": "分析总结",\n'
        '  "changes": [\n'
        '    {"action": "remove", "category": "xxx", "keyword": "xxx", "reason": "xxx"},\n'
        '    {"action": "add", "category": "xxx", "keyword": "xxx", "reason": "xxx"},\n'
        '    {"action": "merge", "category": "xxx", "keywords": ["a","b"], "merged_to": "c", "reason": "xxx"}\n'
        '  ],\n'
        '  "no_change_reason": "如果不需要变更，说明原因"\n'
        '}'
    )

    llm = get_tool_llm_client(user_setting)
    response, usage = await llm.chat(
        [{"role": "user", "content": prompt}], temperature=0.3
    )
    if usage:
        try:
            token_service.record_usage(
                user_id=user_id,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                model=usage.get("model"),
                role_name="机",
            )
        except Exception as e:
            logger.warning(f"Token 记录失败 (rule_engine): {e}")

    data = _extract_json_from_llm_response(response)
    if not data:
        result["details"] = "LLM 返回无法解析为 JSON"
        result["status"] = "warning"
        return result

    result["details"] = data.get("analysis", "")
    changes = data.get("changes", [])

    if not changes:
        result["details"] += f" | 无变更原因: {data.get('no_change_reason', '未说明')}"
        return result

    # 备份原文件
    backup_path = rules_path + f".bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    shutil.copy2(rules_path, backup_path)

    # 安全应用变更（保守策略）
    modified = False
    for change in changes:
        action = change.get("action")
        category = change.get("category", "")
        if category not in intent_rules:
            continue

        if action == "add":
            kw = change.get("keyword", "")
            if kw and isinstance(intent_rules[category], list) and kw not in intent_rules[category]:
                intent_rules[category].append(kw)
                result["changes_made"].append(f"添加 {category}/{kw}")
                modified = True

        elif action == "remove":
            kw = change.get("keyword", "")
            if kw and isinstance(intent_rules[category], list) and kw in intent_rules[category]:
                intent_rules[category].remove(kw)
                result["changes_made"].append(f"移除 {category}/{kw}")
                modified = True

        elif action == "merge":
            keywords = change.get("keywords", [])
            merged_to = change.get("merged_to", "")
            if isinstance(intent_rules[category], list) and merged_to:
                removed = []
                for kw in keywords:
                    if kw in intent_rules[category]:
                        intent_rules[category].remove(kw)
                        removed.append(kw)
                if merged_to not in intent_rules[category]:
                    intent_rules[category].append(merged_to)
                if removed:
                    result["changes_made"].append(
                        f"合并 {category}/{removed} -> {merged_to}"
                    )
                    modified = True

    if modified:
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(intent_rules, f, ensure_ascii=False, indent=2)
        result["details"] += f" | 已备份至 {os.path.basename(backup_path)}"
    else:
        # 没有实际变更，删除备份
        try:
            os.remove(backup_path)
        except OSError:
            pass

    if not result["changes_made"]:
        result["changes_made"].append("无实际变更")

    return result


async def _ji_task2_conversation_quality(user_id, user_setting, summary, log_service, token_service):
    """任务2：对话质量自评"""
    from app.ai.factory import get_tool_llm_client

    result = {"name": "对话质量自评", "status": "success", "quality_score": None, "details": ""}

    if not summary:
        result["details"] = "无近期对话数据，跳过"
        return result

    prompt = (
        '你是璇玑系统的迭代者"机"。请分析以下最近的对话日志，评估对话质量。\n\n'
        f"最近对话摘要：\n{summary}\n\n"
        "请输出 JSON：\n"
        '{\n'
        '  "quality_score": 8,\n'
        '  "issues_found": ["xxx"],\n'
        '  "suggestions": ["xxx"],\n'
        '  "overall_assessment": "总结"\n'
        '}'
    )

    llm = get_tool_llm_client(user_setting)
    response, usage = await llm.chat(
        [{"role": "user", "content": prompt}], temperature=0.3
    )
    if usage:
        try:
            token_service.record_usage(
                user_id=user_id,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                model=usage.get("model"),
                role_name="机",
            )
        except Exception as e:
            logger.warning(f"Token 记录失败 (conversation_quality): {e}")

    data = _extract_json_from_llm_response(response)
    if data:
        result["quality_score"] = data.get("quality_score")
        issues = data.get("issues_found", [])
        suggestions = data.get("suggestions", [])
        assessment = data.get("overall_assessment", "")
        result["details"] = (
            f"评分: {result['quality_score']} | "
            f"问题: {issues} | 建议: {suggestions} | 总评: {assessment}"
        )
    else:
        result["details"] = "LLM 返回无法解析为 JSON"
        result["status"] = "warning"

    return result


async def _ji_task3_memory_profile_monitor(user_id, db):
    """任务3：记忆/画像质量监控 — 简单数据健康检查，不需要 LLM"""
    from app.models.memory_summary import MemorySummary
    from app.models.user_profile import UserProfile

    result = {"name": "记忆/画像质量监控", "status": "success", "details": ""}
    checks: list[str] = []

    # 检查画像字段完整性
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    if profile:
        profile_fields = [
            "personality_traits", "attachment_style", "core_needs",
            "emotional_baseline", "trigger_topics", "safe_topics",
            "interests", "summary_text",
        ]
        empty_fields = [f for f in profile_fields if not getattr(profile, f, None)]
        if empty_fields:
            checks.append(f"画像缺失字段: {empty_fields}")
        else:
            checks.append("画像字段完整")

        # 检查画像更新时效（超过30天未更新视为过期）
        if profile.updated_at:
            days_since_update = (datetime.now() - profile.updated_at).days
            if days_since_update > 30:
                checks.append(f"画像已 {days_since_update} 天未更新，可能过期")
            else:
                checks.append(f"画像最近更新于 {days_since_update} 天前")
    else:
        checks.append("用户画像不存在")

    # 检查记忆条目数量
    memory_count = (
        db.query(MemorySummary)
        .filter(MemorySummary.user_id == user_id)
        .count()
    )
    checks.append(f"记忆摘要总数: {memory_count}")
    if memory_count > 500:
        checks.append("记忆条目过多（>500），建议清理")
    elif memory_count > 200:
        checks.append("记忆条目较多（>200），需关注")

    # 检查是否有过期的 daily 记忆（超过90天的 daily 记忆应已被压缩）
    from app.models.memory_summary import MemorySummary as MS
    ninety_days_ago = datetime.now() - timedelta(days=90)
    stale_daily = (
        db.query(MS)
        .filter(
            MS.user_id == user_id,
            MS.period_type == "daily",
            MS.period_start < ninety_days_ago,
        )
        .count()
    )
    if stale_daily > 0:
        checks.append(f"发现 {stale_daily} 条超过90天的 daily 记忆，建议压缩或清理")

    result["details"] = " | ".join(checks)
    return result


async def _ji_task4_identity_evolve(user_id, user_setting, summary, identity_service):
    """任务4：身份迭代（已有逻辑，保留）"""
    result = {"name": "身份迭代", "status": "success", "changes_made": []}

    if not summary:
        result["changes_made"].append("无近期对话，跳过")
        return result

    evolved = await identity_service.auto_evolve(
        user_id, "ji", summary, user_setting
    )
    if evolved:
        result["changes_made"].append("身份迭代已触发变更")
    else:
        result["changes_made"].append("无变更")

    return result


async def _ji_task5_efficiency_analysis(user_id, db):
    """任务5：流程效率分析 — 简单统计，不需要 LLM"""
    from app.models.log import Log
    from app.models.token_usage import TokenUsage
    from sqlalchemy import func

    result = {"name": "流程效率分析", "status": "success", "details": ""}
    stats: list[str] = []

    one_hour_ago = datetime.now() - timedelta(hours=1)

    # 各角色的 token 消耗统计（最近1小时）
    role_usage = (
        db.query(
            TokenUsage.role_name,
            func.count(TokenUsage.id).label("call_count"),
            func.coalesce(func.sum(TokenUsage.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.avg(TokenUsage.total_tokens), 0).label("avg_tokens"),
        )
        .filter(
            TokenUsage.user_id == user_id,
            TokenUsage.created_at >= one_hour_ago,
        )
        .group_by(TokenUsage.role_name)
        .all()
    )

    if role_usage:
        for r in role_usage:
            stats.append(
                f"{r.role_name or '未知'}: {r.call_count}次调用, "
                f"共{int(r.total_tokens)}tokens, 平均{int(r.avg_tokens)}tokens/次"
            )
    else:
        stats.append("最近1小时无 token 使用记录")

    # 最近1小时日志中的错误数量
    error_count = (
        db.query(func.count(Log.id))
        .filter(
            Log.user_id == user_id,
            Log.level == "error",
            Log.created_at >= one_hour_ago,
        )
        .scalar()
    )
    stats.append(f"最近1小时错误日志: {error_count} 条")

    # 最近24小时 token 趋势（按角色）
    one_day_ago = datetime.now() - timedelta(hours=24)
    daily_usage = (
        db.query(
            TokenUsage.role_name,
            func.coalesce(func.sum(TokenUsage.total_tokens), 0).label("total_tokens"),
        )
        .filter(
            TokenUsage.user_id == user_id,
            TokenUsage.created_at >= one_day_ago,
        )
        .group_by(TokenUsage.role_name)
        .all()
    )
    if daily_usage:
        daily_parts = [f"{r.role_name or '未知'}:{int(r.total_tokens)}" for r in daily_usage]
        stats.append(f"24h token 趋势: {', '.join(daily_parts)}")

    result["details"] = " | ".join(stats)
    return result


async def _ji_background_loop():
    """机的后台定时工作循环：每1小时执行一次全部5项任务。"""
    from app.ai.factory import get_tool_llm_client
    from app.models.ai_identity import AIIdentity
    from app.models.conversation import Message
    from app.models.setting import UserSetting
    from app.services.log_service import LogService
    from app.services.token_service import TokenService
    from sqlalchemy import distinct

    logger.info("机后台定时任务已启动，间隔 1 小时，执行 5 项核心职责")

    while True:
        work_start = datetime.now()
        users_processed = 0

        db = SessionLocal()
        try:
            user_ids = db.query(distinct(AIIdentity.user_id)).all()
            user_ids = [uid[0] for uid in user_ids]

            identity_service = IdentityService(db)
            log_service = LogService(db)
            token_service = TokenService(db)

            for user_id in user_ids:
                user_start = datetime.now()
                tasks_results: list[dict] = []
                overall_status = "success"

                try:
                    # 获取最近对话摘要（供多个任务使用）
                    three_days_ago = datetime.now() - timedelta(days=3)
                    recent_msgs = (
                        db.query(Message)
                        .filter(
                            Message.user_id == user_id,
                            Message.created_at >= three_days_ago,
                        )
                        .order_by(Message.created_at.desc())
                        .limit(30)
                        .all()
                    )
                    summary = ""
                    if recent_msgs:
                        summary = "\n".join(
                            [f"[{m.role}] {m.content[:100]}" for m in reversed(recent_msgs[-15:])]
                        )

                    user_setting = (
                        db.query(UserSetting)
                        .filter(UserSetting.user_id == user_id)
                        .first()
                    )

                    # ── 任务 1：规则引擎迭代 ──
                    try:
                        t1 = await _ji_task1_rule_engine(
                            user_id, user_setting, log_service, token_service, db
                        )
                        tasks_results.append(t1)
                    except Exception as e:
                        logger.warning(f"任务1(规则引擎迭代) 失败 user={user_id}: {e}")
                        tasks_results.append({
                            "name": "规则引擎迭代", "status": "error",
                            "changes_made": [], "details": str(e),
                        })
                        overall_status = "partial_failure"

                    # ── 任务 2：对话质量自评 ──
                    try:
                        t2 = await _ji_task2_conversation_quality(
                            user_id, user_setting, summary, log_service, token_service
                        )
                        tasks_results.append(t2)
                    except Exception as e:
                        logger.warning(f"任务2(对话质量自评) 失败 user={user_id}: {e}")
                        tasks_results.append({
                            "name": "对话质量自评", "status": "error",
                            "quality_score": None, "details": str(e),
                        })
                        overall_status = "partial_failure"

                    # ── 任务 3：记忆/画像质量监控 ──
                    try:
                        t3 = await _ji_task3_memory_profile_monitor(user_id, db)
                        tasks_results.append(t3)
                    except Exception as e:
                        logger.warning(f"任务3(记忆/画像质量监控) 失败 user={user_id}: {e}")
                        tasks_results.append({
                            "name": "记忆/画像质量监控", "status": "error",
                            "details": str(e),
                        })
                        overall_status = "partial_failure"

                    # ── 任务 4：身份迭代（已有逻辑） ──
                    try:
                        t4 = await _ji_task4_identity_evolve(
                            user_id, user_setting, summary, identity_service
                        )
                        tasks_results.append(t4)
                    except Exception as e:
                        logger.warning(f"任务4(身份迭代) 失败 user={user_id}: {e}")
                        tasks_results.append({
                            "name": "身份迭代", "status": "error",
                            "changes_made": [str(e)],
                        })
                        overall_status = "partial_failure"

                    # ── 任务 5：流程效率分析 ──
                    try:
                        t5 = await _ji_task5_efficiency_analysis(user_id, db)
                        tasks_results.append(t5)
                    except Exception as e:
                        logger.warning(f"任务5(流程效率分析) 失败 user={user_id}: {e}")
                        tasks_results.append({
                            "name": "流程效率分析", "status": "error",
                            "details": str(e),
                        })
                        overall_status = "partial_failure"

                    users_processed += 1
                    user_end = datetime.now()

                    # 记录本轮综合日志
                    log_level = "info" if overall_status == "success" else "warn"
                    log_service.log(
                        f"机后台工作完成 (user={user_id})",
                        level=log_level,
                        user_id=user_id,
                        source="scheduler.ji",
                        status_code=200 if overall_status == "success" else 207,
                        details={
                            "status": overall_status,
                            "start_time": user_start.isoformat(),
                            "end_time": user_end.isoformat(),
                            "duration_seconds": round(
                                (user_end - user_start).total_seconds(), 2
                            ),
                            "tasks_executed": tasks_results,
                        },
                    )

                except Exception as e:
                    user_end = datetime.now()
                    logger.error(f"机后台工作异常 (user={user_id}): {e}")
                    try:
                        log_service.log(
                            f"机后台工作异常 (user={user_id})",
                            level="error",
                            user_id=user_id,
                            source="scheduler.ji",
                            status_code=500,
                            details={
                                "status": "error",
                                "start_time": user_start.isoformat(),
                                "end_time": user_end.isoformat(),
                                "duration_seconds": round(
                                    (user_end - user_start).total_seconds(), 2
                                ),
                                "tasks_executed": tasks_results,
                                "error": str(e),
                            },
                        )
                    except Exception:
                        pass

            work_end = datetime.now()
            total_duration = round((work_end - work_start).total_seconds(), 2)
            logger.info(
                f"机后台工作本轮完成: 处理 {users_processed}/{len(user_ids)} 个用户, "
                f"耗时 {total_duration}s, 5项任务全部执行"
            )

        except Exception as e:
            logger.error(f"机后台工作循环异常: {e}")
        finally:
            db.close()

        # 从工作完成时刻开始等待1小时
        await asyncio.sleep(3600)


async def _scheduler_loop():
    """Main scheduler loop. Runs compression tasks at scheduled intervals."""
    logger.info("Memory decay scheduler started")

    while True:
        now = datetime.now()

        # Daily compression: run at 03:00 every day
        if now.hour == 3 and now.minute == 0:
            logger.info("Running daily memory compression...")
            try:
                await _run_daily_compression()
            except Exception as e:
                logger.error(f"Daily compression error: {e}")

        # Weekly compression: run at 04:00 every Monday
        if now.weekday() == 0 and now.hour == 4 and now.minute == 0:
            logger.info("Running weekly memory compression...")
            try:
                await _run_weekly_compression()
            except Exception as e:
                logger.error(f"Weekly compression error: {e}")

        # Monthly compression: run at 05:00 on the 1st of each month
        if now.day == 1 and now.hour == 5 and now.minute == 0:
            logger.info("Running monthly memory compression...")
            try:
                await _run_monthly_compression()
            except Exception as e:
                logger.error(f"Monthly compression error: {e}")

        # Yearly compression: run at 06:00 on January 1st
        if now.month == 1 and now.day == 1 and now.hour == 6 and now.minute == 0:
            logger.info("Running yearly memory compression...")
            try:
                await _run_yearly_compression()
            except Exception as e:
                logger.error(f"Yearly compression error: {e}")

        # Identity evolution: run at 02:00 every day
        if now.hour == 2 and now.minute == 0:
            logger.info("Running daily identity evolution...")
            try:
                await _run_identity_evolution()
            except Exception as e:
                logger.error(f"Identity evolution error: {e}")

        # Sleep for 60 seconds between checks
        await asyncio.sleep(60)


def start_scheduler():
    """Start the background scheduler task."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())
        logger.info("Memory decay scheduler task created")


def stop_scheduler():
    """Stop the background scheduler task."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Memory decay scheduler task cancelled")


def start_ji_scheduler():
    """Start the background ji (机) scheduler task."""
    global _ji_background_task
    if _ji_background_task is None or _ji_background_task.done():
        _ji_background_task = asyncio.create_task(_ji_background_loop())
        logger.info("机后台定时任务已创建")


def stop_ji_scheduler():
    """Stop the background ji (机) scheduler task."""
    global _ji_background_task
    if _ji_background_task and not _ji_background_task.done():
        _ji_background_task.cancel()
        logger.info("机后台定时任务已取消")
