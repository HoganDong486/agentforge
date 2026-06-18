"""MCP protocol client for AgentForge tool integration."""
from __future__ import annotations
import json
import subprocess
import asyncio
from typing import Any, Optional


class MCPClient:
    def __init__(self, command: list[str], env: Optional[dict] = None):
        self.command = command
        self.env = env
        self._process: Optional[subprocess.Popen] = None
        self._tools: dict[str, dict] = {}
        self._initialized = False

    def connect(self):
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.env,
        )
        init_req = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}
        resp = self._send(init_req)
        if resp and "error" not in resp:
            self._initialized = True
        tools_resp = self._send({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        if tools_resp:
            for tool in tools_resp.get("result", {}).get("tools", []):
                self._tools[tool["name"]] = tool

    def _send(self, req: dict) -> Optional[dict]:
        if not self._process or not self._process.stdin:
            return None
        try:
            self._process.stdin.write(json.dumps(req) + "\n")
            self._process.stdin.flush()
            line = self._process.stdout.readline()
            if line:
                return json.loads(line)
        except Exception:
            pass
        return None

    def call_tool(self, name: str, arguments: dict) -> dict:
        req = {
            "jsonrpc": "2.0", "id": 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        resp = self._send(req)
        if resp and "result" in resp:
            content = resp["result"].get("content", [])
            if content and isinstance(content, list):
                return {"data": [c.get("text", str(c)) for c in content]}
        return {"error": str(resp)}

    def list_tools(self) -> list[dict]:
        return list(self._tools.values())

    def disconnect(self):
        if self._process:
            self._process.stdin.close()
            self._process.terminate()
            self._process = None


class ToolRegistry:
    def __init__(self):
        self._mcp_clients: dict[str, MCPClient] = {}
        self._functions: dict[str, callable] = {}

    def register_function(self, name: str, func: callable):
        self._functions[name] = func

    def register_mcp(self, name: str, command: list[str], env: Optional[dict] = None):
        client = MCPClient(command, env)
        client.connect()
        self._mcp_clients[name] = client

    def list_all(self) -> list[dict]:
        tools = [{"name": n, "type": "function"} for n in self._functions]
        for name, client in self._mcp_clients.items():
            for tool in client.list_tools():
                tool["_server"] = name
                tools.append(tool)
        return tools

    async def execute(self, tool_name: str, args: dict) -> Any:
        if tool_name in self._functions:
            func = self._functions[tool_name]
            if asyncio.iscoroutinefunction(func):
                return await func(args)
            return func(args)
        for name, client in self._mcp_clients.items():
            tools = client.list_tools()
            if any(t["name"] == tool_name for t in tools):
                return client.call_tool(tool_name, args)
        return {"error": f"Tool not found: {tool_name}"}

    def cleanup(self):
        for client in self._mcp_clients.values():
            client.disconnect()
