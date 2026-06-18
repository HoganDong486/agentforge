"""FastAPI server for AgentForge."""
from __future__ import annotations
import json
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agentforge.engine.node import Workflow
from agentforge.engine.executor import WorkflowExecutor
from agentforge.agents.registry import AgentRegistry
from agentforge.tools.mcp_client import ToolRegistry
from agentforge.tools.builtin_tools import BUILTIN_TOOLS
from agentforge.memory.store import MemoryStore
from agentforge.memory.compressor import ContextCompressor
from agentforge.evaluation.judge import Evaluator

app = FastAPI(title="AgentForge API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

_executor = WorkflowExecutor()
_registry = AgentRegistry()
_tools = ToolRegistry()
_memory = MemoryStore()
_compressor = ContextCompressor()
_evaluator = Evaluator()

for name, func in BUILTIN_TOOLS.items():
    _tools.register_function(name, func)


class WorkflowRunRequest(BaseModel):
    workflow: dict
    inputs: Optional[dict] = {}


class AgentRunRequest(BaseModel):
    agent_name: str = "default"
    message: str
    context: Optional[str] = ""


class EvaluateRequest(BaseModel):
    task: str
    output: str


class MemorySearchRequest(BaseModel):
    query: str
    n_results: int = 5


class MCPAddRequest(BaseModel):
    name: str
    command: list[str]


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/agents")
def list_agents():
    return {"agents": _registry.list_agents()}


@app.post("/agents/run")
def run_agent(req: AgentRunRequest):
    agent = _registry.get(req.agent_name or "default")
    if not agent:
        raise HTTPException(404, f"Agent '{req.agent_name}' not found")
    import asyncio
    output = asyncio.run(agent.run({"message": req.message, "context": req.context}))
    return {"agent": req.agent_name, "output": output}


@app.get("/tools")
def list_tools():
    return {"tools": _tools.list_all()}


@app.post("/tools/{tool_name}")
def execute_tool(tool_name: str, args: dict = {}):
    import asyncio
    result = asyncio.run(_tools.execute(tool_name, args))
    return {"tool": tool_name, "result": result}


@app.post("/mcp/add")
def add_mcp(req: MCPAddRequest):
    _tools.register_mcp(req.name, req.command)
    return {"status": "connected", "name": req.name}


@app.get("/mcp")
def list_mcp():
    clients = {name: len(c.list_tools()) for name, c in _tools._mcp_clients.items()}
    return {"mcp_servers": clients}


@app.post("/workflows/run")
def run_workflow(req: WorkflowRunRequest):
    workflow = Workflow.from_dict(req.workflow)
    result = _executor.execute(workflow, req.inputs)
    return {"workflow_id": workflow.id, "result": result}


@app.post("/workflows/validate")
def validate_workflow(req: WorkflowRunRequest):
    try:
        workflow = Workflow.from_dict(req.workflow)
        return {"valid": True, "name": workflow.name, "nodes": len(workflow.nodes), "edges": len(workflow.edges)}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.post("/evaluate")
def evaluate(req: EvaluateRequest):
    report = _evaluator.evaluate(req.task, req.output)
    return {"verdict": report.verdict, "overall_score": report.overall_score, "results": [{"dimension": r.dimension, "score": r.score, "reasoning": r.reasoning} for r in report.results], "summary": report.summary}


@app.post("/evaluate/compare")
def evaluate_compare(task: str, output_a: str, output_b: str):
    result = _evaluator.judge.diff(task, output_a, output_b)
    return {"comparison": result}


@app.post("/memory/search")
def search_memory(req: MemorySearchRequest):
    results = _memory.recall(req.query, req.n_results)
    return {"query": req.query, "results": results}


@app.get("/memory/stats")
def memory_stats():
    return _memory.get_stats()


@app.post("/memory/knowledge")
def add_knowledge(topic: str, content: str):
    _memory.add_knowledge(topic, content)
    return {"status": "added", "topic": topic}


@app.post("/compress")
def compress_context(messages: list[dict], query: str = ""):
    compressed = _compressor.compress(messages, query)
    return {"original_count": len(messages), "compressed_count": len(compressed), "messages": compressed}


def start_server(host: str = "0.0.0.0", port: int = 8765):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
