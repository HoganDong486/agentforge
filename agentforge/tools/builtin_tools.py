"""Built-in tools for AgentForge agents. Sandboxed for security."""
import json
import os
import shlex
import subprocess
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
import ipaddress
import socket

DEFAULT_ROOT = os.environ.get("AGENTFORGE_SANDBOX", str(Path.home() / ".agentforge_sandbox"))
ALLOWED_COMMANDS = {"ls", "cat", "grep", "find", "wc", "head", "tail", "echo", "date", "pwd", "env", "python", "pip", "git", "node", "npm", "cargo", "go", "ruff", "pytest"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "metadata.google.internal", "[::1]"}


def _sandbox_path(raw_path: str) -> str:
    root = Path(DEFAULT_ROOT).resolve()
    root.mkdir(parents=True, exist_ok=True)
    resolved = (root / raw_path).resolve()
    if not str(resolved).startswith(str(root)):
        raise PermissionError(f"Path traversal blocked: {raw_path}")
    return str(resolved)


def read_file(args: dict) -> str:
    path = _sandbox_path(args["path"])
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(args: dict) -> str:
    path = _sandbox_path(args["path"])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(args["content"])
    return f"Written {len(args['content'])} bytes"


def list_files(args: dict) -> list:
    path = _sandbox_path(args.get("path", "."))
    entries = []
    for entry in sorted(Path(path).iterdir(), key=lambda e: (not e.is_dir(), e.name)):
        entries.append({"name": entry.name, "type": "dir" if entry.is_dir() else "file"})
    return entries


def run_command(args: dict) -> str:
    command_str = args["command"]
    tokens = shlex.split(command_str)
    if not tokens:
        return "(empty command)"
    if tokens[0] not in ALLOWED_COMMANDS:
        raise PermissionError(f"Command not allowed: {tokens[0]}. Allowed: {ALLOWED_COMMANDS}")
    try:
        result = subprocess.run(
            tokens, shell=False, capture_output=True, text=True,
            timeout=30, cwd=DEFAULT_ROOT,
        )
        return result.stdout or result.stderr or "(no output)"
    except subprocess.TimeoutExpired:
        return "(timeout after 30s)"


def web_fetch(args: dict) -> str:
    url = args["url"]
    parsed = urlparse(url)
    if parsed.scheme not in ("https",):
        raise PermissionError(f"Only HTTPS allowed, got: {parsed.scheme}")
    hostname = parsed.hostname
    if not hostname or hostname.lower() in BLOCKED_HOSTS:
        raise PermissionError(f"Host blocked: {hostname}")
    try:
        addr = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            raise PermissionError(f"Internal IP blocked: {ip}")
    except (socket.gaierror, ValueError):
        pass
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
