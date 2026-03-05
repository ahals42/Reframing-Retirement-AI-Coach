"""
PostToolUse hook: runs pytest after Claude edits a Python file.
Skips test files themselves (editing a test doesn't re-run all tests mid-edit).
"""
import sys
import json
import subprocess
import os

data = json.load(sys.stdin)
fp = data.get("tool_input", {}).get("file_path", "")

# Only trigger on non-test Python files
if not fp.endswith(".py"):
    sys.exit(0)
if "/tests/" in fp or fp.startswith("tests/"):
    sys.exit(0)

project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")

result = subprocess.run(
    ["python", "-m", "pytest", "tests/", "-q", "--tb=short"],
    capture_output=True,
    text=True,
    cwd=project_dir,
)

output = (result.stdout + result.stderr).strip()
if output:
    # Trim to avoid flooding Claude's context
    print(output[-3000:] if len(output) > 3000 else output)
