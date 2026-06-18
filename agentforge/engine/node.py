"""DAG workflow node types and execution primitives."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
import json


class NodeType(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    HUMAN = "human"
    PARALLEL = "parallel"
    SUBGRAPH = "subgraph"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeConfig:
    agent_role: Optional[str] = None
    agent_prompt: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: dict[str, Any] = field(default_factory=dict)
    condition_expr: Optional[str] = None
    human_prompt: Optional[str] = None
    human_timeout: int = 300
    max_parallel: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0
    timeout_seconds: int = 120
    input_mapping: dict[str, str] = field(default_factory=dict)
    output_key: str = "output"


@dataclass
class Node:
    id: str
    name: str
    node_type: NodeType
    config: NodeConfig = field(default_factory=NodeConfig)
    depends_on: list[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    attempts: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type.value,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "config": {
                "agent_role": self.config.agent_role,
                "agent_prompt": self.config.agent_prompt,
                "tool_name": self.config.tool_name,
                "tool_args": self.config.tool_args,
                "condition_expr": self.config.condition_expr,
                "human_prompt": self.config.human_prompt,
                "max_parallel": self.config.max_parallel,
                "output_key": self.config.output_key,
            },
            "output": str(self.output)[:200] if self.output else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
        }

    def reset(self):
        self.status = NodeStatus.PENDING
        self.output = None
        self.error = None
        self.duration_ms = 0.0


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Node):
        self.nodes.append(node)

    def add_edge(self, from_id: str, to_id: str):
        self.edges.append((from_id, to_id))
        target = self.get_node(to_id)
        if target and from_id not in target.depends_on:
            target.depends_on.append(from_id)

    def get_node(self, node_id: str) -> Optional[Node]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_dependencies(self, node_id: str) -> list[str]:
        return [e[0] for e in self.edges if e[1] == node_id]

    def get_dependents(self, node_id: str) -> list[str]:
        return [e[1] for e in self.edges if e[0] == node_id]

    def get_root_nodes(self) -> list[Node]:
        all_deps = set()
        for _, to_id in self.edges:
            all_deps.add(to_id)
        return [n for n in self.nodes if n.id not in all_deps]

    def get_ready_nodes(self) -> list[Node]:
        ready = []
        for node in self.nodes:
            if node.status != NodeStatus.PENDING:
                continue
            deps_ready = all(
                self.get_node(dep).status == NodeStatus.SUCCESS
                for dep in node.depends_on
            )
            if deps_ready:
                ready.append(node)
        return ready

    def is_complete(self) -> bool:
        return all(n.status in (NodeStatus.SUCCESS, NodeStatus.SKIPPED) for n in self.nodes)

    def has_failed(self) -> bool:
        return any(n.status == NodeStatus.FAILED for n in self.nodes)

    def reset(self):
        for node in self.nodes:
            node.reset()
        self.variables = {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [{"from": e[0], "to": e[1]} for e in self.edges],
            "variables": self.variables,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Workflow:
        wf = cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            variables=data.get("variables", {}),
        )
        node_map = {}
        for nd in data["nodes"]:
            cfg = NodeConfig(
                agent_role=nd.get("config", {}).get("agent_role"),
                agent_prompt=nd.get("config", {}).get("agent_prompt"),
                tool_name=nd.get("config", {}).get("tool_name"),
                condition_expr=nd.get("config", {}).get("condition_expr"),
                output_key=nd.get("config", {}).get("output_key", "output"),
            )
            node = Node(
                id=nd["id"],
                name=nd["name"],
                node_type=NodeType(nd["type"]),
                config=cfg,
            )
            wf.nodes.append(node)
            node_map[node.id] = node
        for edge in data.get("edges", []):
            node_map[edge["to"]].depends_on.append(edge["from"])
            wf.edges.append((edge["from"], edge["to"]))
        return wf

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


def build_linear_workflow(name: str, steps: list[dict]) -> Workflow:
    """Build a linear pipeline: step1 → step2 → step3."""
    import uuid
    wf_id = uuid.uuid4().hex[:8]
    wf = Workflow(id=wf_id, name=name, description=f"Linear pipeline: {name}")

    prev_id = None
    for i, step in enumerate(steps):
        node_id = f"node_{i}"
        node = Node(
            id=node_id,
            name=step.get("name", f"Step {i+1}"),
            node_type=NodeType(step.get("type", "agent")),
            config=NodeConfig(
                agent_role=step.get("role"),
                agent_prompt=step.get("prompt"),
                tool_name=step.get("tool"),
            ),
        )
        wf.add_node(node)
        if prev_id:
            wf.add_edge(prev_id, node_id)
        prev_id = node_id
    return wf


def build_fan_out_workflow(name: str, dispatcher: dict, workers: list[dict], aggregator: dict) -> Workflow:
    """Build fan-out: dispatcher → [worker1, worker2, ...] → aggregator."""
    import uuid
    wf_id = uuid.uuid4().hex[:8]
    wf = Workflow(id=wf_id, name=name, description=f"Fan-out pipeline: {name}")

    disp = Node(
        id="dispatcher",
        name=dispatcher.get("name", "Dispatcher"),
        node_type=NodeType(dispatcher.get("type", "agent")),
        config=NodeConfig(agent_role=dispatcher.get("role"), agent_prompt=dispatcher.get("prompt")),
    )
    wf.add_node(disp)

    agg = Node(
        id="aggregator",
        name=aggregator.get("name", "Aggregator"),
        node_type=NodeType(aggregator.get("type", "agent")),
        config=NodeConfig(agent_role=aggregator.get("role"), agent_prompt=aggregator.get("prompt")),
    )
    wf.add_node(agg)

    for i, worker in enumerate(workers):
        w = Node(
            id=f"worker_{i}",
            name=worker.get("name", f"Worker {i+1}"),
            node_type=NodeType(worker.get("type", "agent")),
            config=NodeConfig(agent_role=worker.get("role"), agent_prompt=worker.get("prompt")),
        )
        wf.add_node(w)
        wf.add_edge("dispatcher", w.id)
        wf.add_edge(w.id, "aggregator")

    return wf
