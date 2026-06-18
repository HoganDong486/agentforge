"""AgentForge CLI - command-line interface for the platform."""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
from agentforge.engine.node import Workflow
from agentforge.engine.executor import WorkflowExecutor
from agentforge.agents.registry import AgentRegistry
from agentforge.tools.mcp_client import ToolRegistry
from agentforge.tools.builtin_tools import BUILTIN_TOOLS
from agentforge.memory.store import MemoryStore
from agentforge.memory.compressor import ContextCompressor
from agentforge.evaluation.judge import Evaluator
from agentforge.config import Config, set_config


class CLI:
    def __init__(self):
        self.executor = WorkflowExecutor()
        self.registry = AgentRegistry()
        self.tools = ToolRegistry()
        self.memory = MemoryStore()
        self.compressor = ContextCompressor()
        self.evaluator = Evaluator()
        for name, func in BUILTIN_TOOLS.items():
            self.tools.register_function(name, func)

    def run(self, args: Optional[list] = None):
        parser = argparse.ArgumentParser(description="AgentForge CLI", prog="agentforge")
        subs = parser.add_subparsers(dest="command")

        run_p = subs.add_parser("run", help="Execute a workflow")
        run_p.add_argument("workflow_file", help="Path to workflow JSON file")
        run_p.add_argument("--inputs", help="JSON inputs for the workflow")

        agent_p = subs.add_parser("agent", help="Manage agents")
        agent_sub = agent_p.add_subparsers(dest="agent_action")
        agent_sub.add_parser("list", help="List registered agents")
        agent_info = agent_sub.add_parser("info", help="Show agent details")
        agent_info.add_argument("name", help="Agent name")

        tool_p = subs.add_parser("tool", help="Manage tools")
        tool_sub = tool_p.add_subparsers(dest="tool_action")
        tool_sub.add_parser("list", help="List available tools")
        tool_run = tool_sub.add_parser("run", help="Execute a tool")
        tool_run.add_argument("tool_name", help="Tool name")
        tool_run.add_argument("--args", default="{}", help="JSON tool arguments")

        mc_p = subs.add_parser("mcp", help="Manage MCP servers")
        mc_sub = mc_p.add_subparsers(dest="mcp_action")
        mc_sub.add_parser("list", help="List MCP servers")
        mc_add = mc_sub.add_parser("add", help="Add an MCP server")
        mc_add.add_argument("name", help="Server name")
        mc_add.add_argument("command", nargs="+", help="MCP server command")

        eval_p = subs.add_parser("evaluate", help="Evaluate agent output")
        eval_p.add_argument("--task", required=True, help="Original task")
        eval_p.add_argument("--output", required=True, help="Agent output to evaluate")
        eval_p.add_argument("--compare", nargs=2, metavar=("A", "B"), help="Compare two outputs")

        mem_p = subs.add_parser("memory", help="Memory operations")
        mem_sub = mem_p.add_subparsers(dest="mem_action")
        mem_sub.add_parser("stats", help="Memory store statistics")
        mem_search = mem_sub.add_parser("search", help="Search memory")
        mem_search.add_argument("query", help="Search query")

        bench_p = subs.add_parser("benchmark", help="Run benchmarks")
        bench_p.add_argument("benchmark_file", help="JSON benchmark file")

        subs.add_parser("serve", help="Start the API server")
        subs.add_parser("version", help="Show version")

        opts = parser.parse_args(args)
        if not opts.command:
            parser.print_help()
            return

        handlers = {
            "run": self._handle_run,
            "agent": self._handle_agent,
            "tool": self._handle_tool,
            "mcp": self._handle_mcp,
            "evaluate": self._handle_evaluate,
            "memory": self._handle_memory,
            "benchmark": self._handle_benchmark,
            "serve": self._handle_serve,
            "version": self._handle_version,
        }
        handler = handlers.get(opts.command)
        if handler:
            handler(opts)

    def _handle_run(self, opts):
        with open(opts.workflow_file) as f:
            data = json.load(f)
        workflow = Workflow.from_dict(data)
        inputs = json.loads(opts.inputs) if opts.inputs else {}
        result = self.executor.execute(workflow, inputs)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    def _handle_agent(self, opts):
        if opts.agent_action == "list":
            for a in self.registry.list_agents():
                print(f"  {a['name']:20s} {a['type']:15s} {a['description']}")
        elif opts.agent_action == "info":
            agent = self.registry.get(opts.name)
            if agent:
                print(json.dumps(agent.to_dict(), indent=2))
            else:
                print(f"Agent '{opts.name}' not found")

    def _handle_tool(self, opts):
        if opts.tool_action == "list":
            for t in self.tools.list_all():
                print(f"  {t['name']:30s} [{t.get('_server', 'builtin')}]")
        elif opts.tool_action == "run":
            result = asyncio.run(self.tools.execute(opts.tool_name, json.loads(opts.args)))
            print(f"Result: {result}")

    def _handle_mcp(self, opts):
        if opts.mcp_action == "list":
            clients = self.tools._mcp_clients
            if not clients:
                print("No MCP servers connected")
            for name, client in clients.items():
                print(f"  {name}: {len(client.list_tools())} tools")
        elif opts.mcp_action == "add":
            self.tools.register_mcp(opts.name, opts.command)

    def _handle_evaluate(self, opts):
        if opts.compare:
            result = self.evaluator.judge.diff(opts.task, opts.compare[0], opts.compare[1])
            print(result)
        else:
            report = self.evaluator.evaluate(opts.task, opts.output)
            print(f"Verdict: {report.verdict}")
            print(f"Overall Score: {report.overall_score}/60")
            print(f"Summary: {report.summary}")
            for r in report.results:
                print(f"\n  [{r.dimension}] {r.score}/10")
                print(f"  {r.reasoning}")

    def _handle_memory(self, opts):
        if opts.mem_action == "stats":
            print(json.dumps(self.memory.get_stats(), indent=2))
        elif opts.mem_action == "search":
            results = self.memory.recall(opts.query)
            for r in results:
                print(f"  [{r['score']:.2f}] {r['content'][:200]}")

    def _handle_benchmark(self, opts):
        with open(opts.benchmark_file) as f:
            cases = json.load(f)
        result = self.evaluator.benchmark(cases, lambda t: self.executor.execute(
            Workflow.from_dict({"id": "bench", "name": "bench", "nodes": [], "edges": []}), {"task": t}
        ))
        print(json.dumps(result, indent=2))

    def _handle_serve(self, _opts):
        from agentforge.api.server import start_server
        start_server()

    def _handle_version(self, _opts):
        from agentforge import __version__
        print(f"AgentForge v{__version__}")


def main():
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
