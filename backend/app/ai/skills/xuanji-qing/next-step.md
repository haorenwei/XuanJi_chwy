当前任务进度：

用户原始请求："{user_message}"
目标：{final_goal}

已获取的信息：
{gathered_info}

剩余信息缺口：
{remaining_gaps}

请决定下一步行动，输出 JSON：
{{
  "action": "execute_tool" | "ask_user" | "complete",
  "target_gap": "要填补的信息缺口ID",
  "tool_hint": "工具描述关键词（仅 execute_tool 时需要）",
  "ask_message": "要问用户的问题（仅 ask_user 时需要）",
  "reason": "决策原因"
}}

规则：
- 如果剩余缺口的信息可以通过工具获取，选择 execute_tool
- 如果信息只能从用户处获取（如个人偏好、具体需求），选择 ask_user
- 如果所有必要信息已齐全，选择 complete
- 优先执行无依赖的步骤