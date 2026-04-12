import ast
from typing import NamedTuple

BLOCKED_MODULES = frozenset({
    "os", "subprocess", "sys", "shutil", "socket", "http", "urllib",
    "requests", "ctypes", "importlib", "multiprocessing", "signal",
    "webbrowser", "ftplib", "smtplib", "telnetlib", "xmlrpc",
})

# Sub-modules that are safe despite their root module being blocked
ALLOWED_SUBMODULES = frozenset({
    "urllib.parse",  # URL encoding/parsing only, no network access
})

ALLOWED_MODULES = frozenset({
    "json", "re", "math", "datetime", "collections", "itertools",
    "functools", "string", "pathlib", "csv", "io", "glob",
    "hashlib", "base64", "textwrap", "statistics", "typing",
    "httpx",  # HTTP requests for tool execution
})

BLOCKED_BUILTINS = frozenset({
    "eval", "exec", "compile", "__import__", "globals", "locals",
    "getattr", "setattr", "delattr", "breakpoint", "exit", "quit",
})


class ValidationResult(NamedTuple):
    valid: bool
    error: str | None


def validate_tool_code(code: str) -> ValidationResult:
    """Validate generated tool code for safety using AST analysis."""
    # Step 1: Parse
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ValidationResult(False, f"Syntax error: {e}")

    # Step 2: Check imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                full_module = alias.name
                module_root = full_module.split(".")[0]
                if full_module in ALLOWED_SUBMODULES:
                    continue
                if module_root in BLOCKED_MODULES:
                    return ValidationResult(False, f"Blocked import: {full_module}")
                if module_root not in ALLOWED_MODULES:
                    return ValidationResult(False, f"Unapproved import: {full_module}")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                full_module = node.module
                module_root = full_module.split(".")[0]
                if full_module in ALLOWED_SUBMODULES:
                    continue
                if module_root in BLOCKED_MODULES:
                    return ValidationResult(False, f"Blocked import: {full_module}")
                if module_root not in ALLOWED_MODULES:
                    return ValidationResult(False, f"Unapproved import: {full_module}")

    # Step 3: Check blocked builtins
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in BLOCKED_BUILTINS:
                return ValidationResult(False, f"Blocked builtin call: {func.id}")

    # Step 4: Check for dunder access
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                return ValidationResult(False, f"Blocked dunder access: {node.attr}")

    # Step 5: Check function signature
    functions = [n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.FunctionDef)]
    if not functions:
        return ValidationResult(False, "No function definition found")

    main_func = functions[0]
    args = main_func.args
    if len(args.args) != 1:
        return ValidationResult(False, "Function must accept exactly one argument (params: dict)")

    # Step 6: Check for path traversal in string literals
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if ".." in node.value and ("/" in node.value or "\\" in node.value):
                return ValidationResult(False, f"Potential path traversal: {node.value}")

    return ValidationResult(True, None)
