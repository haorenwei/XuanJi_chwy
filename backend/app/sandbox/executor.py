import ast
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from app.core.config import settings


def execute_tool(code: str, params: dict, working_dir: str | None = None) -> dict:
    """Execute tool code in an isolated subprocess."""
    sandbox_dir = Path(working_dir or settings.sandbox_dir).resolve()
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    # Extract function name from code
    tree = ast.parse(code)
    func_name = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            break

    if not func_name:
        return {"success": False, "result": "No function found in tool code"}

    # Build runner script
    runner = f"""\
import json, sys
sys.path.insert(0, '.')

{code}

params = json.loads('''{json.dumps(params)}''')
try:
    result = {func_name}(params)
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({{"success": False, "result": str(e)}}))
"""

    # Write to system temp dir to avoid triggering uvicorn reload
    # (sandbox dir is inside the project and watched by watchfiles)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(runner)
        temp_path = f.name

    try:
        # Execute in isolated subprocess
        # On Windows, use CREATE_NEW_PROCESS_GROUP to prevent parent
        # console signals (e.g. from uvicorn reload) from killing the child
        creation_flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            if platform.system() == "Windows"
            else 0
        )
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=settings.sandbox_timeout,
            cwd=str(sandbox_dir),
            creationflags=creation_flags,
            env={
                **os.environ,
                "PYTHONPATH": "",
                "HOME": str(sandbox_dir),
                "TEMP": str(sandbox_dir),
                "TMP": str(sandbox_dir),
                "USERPROFILE": str(sandbox_dir),
            },
        )

        if result.returncode != 0:
            return {
                "success": False,
                "result": f"Execution error: {result.stderr.strip()}"
            }

        stdout = result.stdout.strip()
        if not stdout:
            return {"success": False, "result": "No output from tool"}

        # Try to parse last line as JSON
        last_line = stdout.split("\n")[-1]
        return json.loads(last_line)

    except subprocess.TimeoutExpired:
        return {"success": False, "result": f"Execution timed out ({settings.sandbox_timeout}s)"}
    except json.JSONDecodeError:
        return {"success": False, "result": f"Invalid output: {stdout[:500]}"}
    finally:
        Path(temp_path).unlink(missing_ok=True)
