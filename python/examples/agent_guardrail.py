"""Block risky agent tool calls before they run."""
import json

from superion_s1 import Superion, noul

s1 = Superion()


def allowed(user_request: str, tool: str, args: dict, threshold: float = 0.9) -> bool:
    p = s1.noul(
        f"User request: {user_request}\nProposed tool call: {tool}({json.dumps(args)})",
        "Is it safe to execute this tool call without asking the user?",
        true="safe to run", false="must not run without confirmation")
    return p >= threshold


print(allowed("clean up the repo", "shell", {"cmd": "rm -rf / --no-preserve-root"}))   # False
print(allowed("list my files", "shell", {"cmd": "ls -la"}))                           # True
