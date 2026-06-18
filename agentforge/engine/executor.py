"""Workflow executor: ties nodes, agents, and tools together."""
from __future__ import annotations
import ast
import asyncio
import operator
from typing import Any, Dict, Optional
from agentforge.engine.node import Node, NodeType, NodeStatus, Workflow
from agentforge.engine.scheduler import Scheduler, SchedulerConfig
from agentforge.agents.registry import AgentRegistry
from agentforge.tools.mcp_client import ToolRegistry
from agentforge.tools.builtin_tools import BUILTIN_TOOLS

SAFE_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.And: operator.and_, ast.Or: operator.or_,
    ast.Not: operator.not_, ast.In: lambda a, b: a in b,
}


class WorkflowExecutor:
    def __init__(self, scheduler_config: SchedulerConfig | None = None, tool_registry: Optional[ToolRegistry] = None):
        self.scheduler = Scheduler(scheduler_config)
        self.agents = AgentRegistry()
        self.tools = tool_registry or ToolRegistry()
        if tool_registry is None:
            for name, func in BUILTIN_TOOLS.items():
                self.tools.register_function(name, func)
        self._context: Dict[str, Any] = {}

    def register_agent(self, name: str, agent):
        self.agents.register(name, agent)

    async def execute_async(self, workflow: Workflow, inputs: Optional[dict] = None) -> dict:
        self._context = inputs or {}
        workflow.variables = dict(self._context)

        async def _handle(node: Node, wf: Workflow) -> None:
            node_input = self._build_input(node, wf)
            if node.node_type == NodeType.AGENT:
                role = node.config.agent_role if node.config.agent_role is not None else "default"
                agent = self.agents.get(role)
                if agent:
                    node.output = await agent.run(node_input)
                else:
                    raise ValueError(f"Agent not found: {role}")
            elif node.node_type == NodeType.TOOL:
                node.output = await self._execute_tool(node, node_input)
            elif node.node_type == NodeType.CONDITION:
                node.output = self._evaluate_condition(node, node_input)
            elif node.node_type == NodeType.PARALLEL:
                node.output = await self._execute_parallel(node, node_input, wf)
            else:
                node.output = node_input
            wf.variables[node.id] = node.output
            if node.config.output_key:
                wf.variables[node.config.output_key] = node.output

        await self.scheduler.run(workflow, _handle)
        return dict(workflow.variables)

    def execute(self, workflow: Workflow, inputs: Optional[dict] = None) -> dict:
        try:
            asyncio.get_running_loop()
            raise RuntimeError("execute() cannot be called from async context. Use: await executor.execute_async()")
        except RuntimeError as e:
            if "cannot be called from async context" in str(e):
                raise
            return asyncio.run(self.execute_async(workflow, inputs))

    def _build_input(self, node: Node, wf: Workflow) -> dict:
        inputs = dict(self._context)
        for dep_id in node.depends_on:
            dep_node = wf.get_node(dep_id)
            if dep_node and dep_node.output is not None:
                inputs[dep_node.id] = dep_node.output
                if dep_node.config.output_key:
                    inputs[dep_node.config.output_key] = dep_node.output
        if node.config.agent_prompt is not None:
            inputs["_prompt"] = node.config.agent_prompt
        if node.config.tool_args:
            inputs.update(node.config.tool_args)
        return inputs

    async def _execute_tool(self, node: Node, inputs: dict) -> Any:
        tool_name = node.config.tool_name
        if not tool_name:
            return {"error": "No tool specified"}
        if node.config.tool_args:
            inputs = {**inputs, **node.config.tool_args}
        return await self.tools.execute(tool_name, inputs)

    def _eval_node(self, node: ast.AST, ctx: dict) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return ctx.get(node.id, False)
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, ctx)
            for op, comp in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in SAFE_OPS:
                    raise ValueError(f"Unsafe operator: {op_type.__name__}")
                if not SAFE_OPS[op_type](left, self._eval_node(comp, ctx)):
                    return False
                left = self._eval_node(comp, ctx)
            return True
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v, ctx) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(self._eval_node(v, ctx) for v in node.values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self._eval_node(node.operand, ctx)
        raise ValueError(f"Unsafe expression: {ast.dump(node)}")

    def _evaluate_condition(self, node: Node, inputs: dict) -> bool:
        if not node.config.condition_expr:
            return True
        try:
            tree = ast.parse(node.config.condition_expr.strip(), mode="eval")
            return bool(self._eval_node(tree.body, inputs))
        except (SyntaxError, ValueError) as e:
            return False

    async def _execute_parallel(self, node: Node, inputs: dict, wf: Workflow) -> list:
        sub_workflows = inputs.get("_sub_workflows", [])
        if not sub_workflows:
            return []
        tasks = []
        for sub_wf in sub_workflows:
            sub_executor = WorkflowExecutor(tool_registry=self.tools)
            sub_executor.agents = self.agents
            tasks.append(sub_executor.execute_async(sub_wf, inputs))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if not isinstance(r, Exception) else {"error": str(r)} for r in results]
