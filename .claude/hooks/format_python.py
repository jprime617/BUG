#!/usr/bin/env python3
"""Hook PostToolUse: roda `ruff` no `.py` recém-editado (format + fix seguro).

No-op se ruff não estiver instalado. Nunca bloqueia: sai 0 em qualquer erro.
"""

import json
import shutil
import subprocess
import sys


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    tool_input = data.get("tool_input", {}) or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path or not path.lower().endswith(".py"):
        return
    if shutil.which("ruff") is None:
        return

    subprocess.run(["ruff", "check", "--fix", path], capture_output=True)
    subprocess.run(["ruff", "format", path], capture_output=True)
    print(json.dumps({"systemMessage": f"ruff aplicado em {path}"}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
