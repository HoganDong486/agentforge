"""Parallel execution scheduler for DAG workflows."""
from __future__ import annotations
import asyncio
from typing import Callable, Awaitable
from dataclasses import dataclass
from agentforge.engine.node import Node, NodeStatus, Workflow


@dataclass
class SchedulerConfig:
    max_parallel: int = 5
    retry_count: int = 3
    retry_delay: float = 1.0
    timeout_seconds: int = 120


class Scheduler:
    def __init__(self, config: SchedulerConfig | None = None):
        self.config = config or SchedulerConfig()
        self._running: dict[str, asyncio.Task] = {}
        self._callbacks: dict[str, list[Callable]] = {}

    def on_node_complete(self, node_id: str, callback: Callable[[Node], None]):
        if node_id not in self._callbacks:
            self._callbacks[node_id] = []
        self._callbacks[node_id].append(callback)

    async def run(
        self,
        workflow: Workflow,
        node_handler: Callable[[Node, Workflow], Awaitable[None]],
    ) -> Workflow:
        workflow.reset()
        semaphore = asyncio.Semaphore(self.config.max_parallel)

        async def _run_node(node: Node):
            async with semaphore:
                node.status = NodeStatus.RUNNING
                for attempt in range(self.config.retry_count + 1):
                    node.attempts = attempt + 1
                    try:
                        import time
                        start = time.time()
                        await asyncio.wait_for(
                            node_handler(node, workflow),
                            timeout=self.config.timeout_seconds,
                        )
                        node.duration_ms = (time.time() - start) * 1000
                        node.status = NodeStatus.SUCCESS
                        break
                    except asyncio.TimeoutError:
                        node.error = f"Timeout after {self.config.timeout_seconds}s"
                        if attempt == self.config.retry_count:
                            node.status = NodeStatus.FAILED
                        else:
                            await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    except Exception as e:
                        node.error = str(e)
                        if attempt == self.config.retry_count:
                            node.status = NodeStatus.FAILED
                        else:
                            await asyncio.sleep(self.config.retry_delay * (attempt + 1))

                for cb in self._callbacks.get(node.id, []):
                    try:
                        cb(node)
                    except Exception:
                        pass

        pending = set()
        while not workflow.is_complete():
            ready = workflow.get_ready_nodes()
            for node in ready:
                if node.id not in pending:
                    pending.add(node.id)
                    self._running[node.id] = asyncio.create_task(_run_node(node))

            if not pending and not workflow.is_complete() and not workflow.has_failed():
                await asyncio.sleep(0.1)
                continue

            if pending:
                done, _ = await asyncio.wait(
                    list(self._running.values()),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in done:
                    for nid, t in list(self._running.items()):
                        if t is task:
                            pending.discard(nid)
                            del self._running[nid]
                            break

            if workflow.has_failed():
                for t in self._running.values():
                    t.cancel()
                break

        return workflow
