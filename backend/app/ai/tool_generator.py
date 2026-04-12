import ast
import json
import re

from app.ai.factory import get_tool_llm_client
from app.ai.base import load_prompt
from app.sandbox.validator import validate_tool_code


async def generate_tool_code(
    description: str,
    target_path: str | None = None,
    parameters: dict | None = None,
    max_retries: int = 2,
    user_setting=None,
    usage_callback=None,
) -> tuple[str, str, str | None, str | None]:
    """Use LLM to generate Python tool code.

    Returns (function_name, code, description_en, description_zh) or raises ValueError on failure.
    """
    client = get_tool_llm_client(user_setting)

    prompt = load_prompt("ji", "tool-generate.md").format(
        description=description,
        target_path=target_path or "not specified",
        parameters=parameters or {},
    )

    last_error = ""
    for attempt in range(max_retries + 1):
        messages = [{"role": "user", "content": prompt}]
        if last_error:
            messages.append({
                "role": "user",
                "content": f"The previous code failed validation: {last_error}. Please fix it.",
            })

        code, gen_usage = await client.chat(messages, temperature=0.3)
        if usage_callback and gen_usage:
            usage_callback(gen_usage)

        # Clean markdown fences if present
        code = _clean_code(code)

        # Extract descriptions from META comment
        description_en = _extract_meta_description_en(code)
        description_zh = _extract_meta_description_zh(code)

        # Remove the META comment line from code before validation
        code = _strip_meta_comment(code)

        # Validate
        result = validate_tool_code(code)
        if result.valid:
            func_name = _extract_function_name(code)
            if func_name:
                # If META lacks English description, generate a default from function name
                if not description_en:
                    description_en = func_name.replace('_', ' ').capitalize()
                return func_name, code, description_en, description_zh

            last_error = "Could not extract function name"
        else:
            last_error = result.error or "Unknown validation error"

    raise ValueError(f"Failed to generate valid tool after {max_retries + 1} attempts: {last_error}")


def _clean_code(code: str) -> str:
    """Remove markdown code fences if present."""
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        # Remove first and last lines (``` markers)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    return code.strip()


def _extract_function_name(code: str) -> str | None:
    """Extract the first function name from code."""
    try:
        tree = ast.parse(code)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                return node.name
    except SyntaxError:
        pass
    return None


def _extract_meta_description_en(code: str) -> str | None:
    """Extract description (English) from the # META: {...} comment line."""
    for line in code.split("\n"):
        line = line.strip()
        if line.startswith("# META:"):
            try:
                meta_json = line[len("# META:"):].strip()
                meta = json.loads(meta_json)
                return meta.get("description")
            except (json.JSONDecodeError, Exception):
                pass
    return None


def _extract_meta_description_zh(code: str) -> str | None:
    """Extract description_zh from the # META: {...} comment line."""
    for line in code.split("\n"):
        line = line.strip()
        if line.startswith("# META:"):
            try:
                meta_json = line[len("# META:"):].strip()
                meta = json.loads(meta_json)
                return meta.get("description_zh")
            except (json.JSONDecodeError, Exception):
                pass
    return None


def _strip_meta_comment(code: str) -> str:
    """Remove # META: comment lines from code."""
    lines = code.split("\n")
    filtered = [ln for ln in lines if not ln.strip().startswith("# META:")]
    return "\n".join(filtered).strip()
