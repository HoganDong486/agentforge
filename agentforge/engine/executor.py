"""Workflow executor: ties nodes, agents, and tools together."""
from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional
from agentforge.engine.node import Node, NodeType, NodeStatus, Workflow
from agentforge.engine.scheduler import Scheduler, SchedulerConfig
from agentforge.agents.registry import AgentRegistry


class WorkflowExecutor:
    def __init__(self, scheduler_config: SchedulerConfig | None = None):
        self.scheduler = Scheduler(scheduler_config)
        self.agents = AgentRegistry()
        self._context: Dict[str, Any] = {}

    def register_agent(self, name: str, agent):
        self.agents.register(name, agent)

    async def execute_async(self, workflow: Workflow, inputs: Optional[dict] = None) -> dict:
        self._context = inputs or {}
        workflow.variables = dict(self._context)

        async def _handle(node: Node, wf: Workflow) -> None:
            node_input = self._build_input(node, wf)
            if node.node_type == NodeType.AGENT:
                agent = self.agents.get(node.config.agent_role or "default")
                if agent:
                    node.output = await agent.run(node_input)
                else:
                    raise ValueError(f"Agent not found: {node.config.agent_role}")
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
        return asyncio.run(self.execute_async(workflow, inputs))

    def _build_input(self, node: Node, wf: Workflow) -> dict:
        inputs = dict(self._context)
        for dep_id in node.depends_on:
            dep_node = wf.get_node(dep_id)
            if dep_node and dep_node.output is not None:
                inputs[dep_node.id] = dep_node.output
                if dep_node.config.output_key:
                    inputs[dep_node.config.output_key] = dep_node.output
        if node.config.agent_prompt:
            inputs["_prompt"] = node.config.agent_prompt
        if node.config.tool_args:
            inputs.update(node.config.tool_args)
        return inputs

    async def _execute_tool(self, node: Node, inputs: dict) -> Any:
        return {"tool": node.config.tool_name, "result": "executed"}

    def _evaluate_condition(self, node: Node, inputs: dict) -> bool:
        if not node.config.condition_expr:
            return True
        safe_builtins = {"True": True, "False": False, "and": lambda a, b: a and b, "or": lambda a, b: a or b}
        return bool(eval(node.config.condition_expr, {"__builtins__": safe_builtins}, inputs))

    async def _execute_parallel(self, node: Node, inputs: dict, wf: Workflow) -> list:
        sub_workflows = inputs.get("_sub_workflows", [])
        if not sub_workflows:
            return []
        tasks = []
        for sub_wf in sub_workflows:
            sub_executor = WorkflowExecutor()
            tasks.append(sub_executor.execute_async(sub_wf, inputs))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if not isinstance(r, Exception) else {"error": str(r)} for r in results]
