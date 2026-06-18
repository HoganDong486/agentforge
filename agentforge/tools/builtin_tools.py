"""Built-in tools for AgentForge agents."""
import json
import os
import subprocess
import urllib.request
from pathlib import Path


def read_file(args: dict) -> str:
    with open(args["path"], "r", encoding="utf-8") as f:
        return f.read()


def write_file(args: dict) -> str:
    path = args["path"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(args["content"])
    return f"Written {len(args['content'])} bytes to {path}"


def list_files(args: dict) -> list:
    path = args.get("path", ".")
    entries = []
    for entry in sorted(Path(path).iterdir(), key=lambda e: (not e.is_dir(), e.name)):
        entries.append({"name": entry.name, "type": "dir" if entry.is_dir() else "file"})
    return entries


def run_command(args: dict) -> str:
    result = subprocess.run(args["command"], shell=True, capture_output=True, text=True)
    return result.stdout or result.stderr or "(no output)"


def web_fetch(args: dict) -> str:
    url = args["url"]
    req = urllib.request.Request(url, headers={"User-Agent": "AgentForge/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode("utf-8", errors="ignore")
        return content[:5000]


BUILTIN_TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "run_command": run_command,
    "web_fetch": web_fetch,
}
