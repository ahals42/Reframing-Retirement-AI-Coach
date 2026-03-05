"""
PreToolUse hook: blocks two things before Claude edits a file:
  1. Direct edits to .env files
  2. Hardcoded secrets/API keys in the new content
"""
import sys
import json
import os
import re

data = json.load(sys.stdin)
fp = data.get("tool_input", {}).get("file_path", "")
content = (
    data.get("tool_input", {}).get("new_string", "")
    or data.get("tool_input", {}).get("content", "")
    or ""
)

# --- Block .env edits ---
if os.path.basename(fp) == ".env":
    print(
        "Blocked: direct .env edits not allowed. "
        "Update secrets via your shell or secrets manager.",
        file=sys.stderr,
    )
    sys.exit(2)

# --- Flag hardcoded secrets in new content ---
secret_patterns = [
    r"sk-[a-zA-Z0-9]{20,}",                                          # OpenAI / Anthropic keys
    r"(?i)(password|passwd|secret|api_key)\s*=\s*[\"'][^\"']{8,}[\"']",  # assignments
    r"ghp_[a-zA-Z0-9]{36}",                                           # GitHub PAT
]

for pattern in secret_patterns:
    if re.search(pattern, content):
        print(
            "Blocked: possible hardcoded secret detected. "
            "Use environment variables instead.",
            file=sys.stderr,
        )
        sys.exit(2)
