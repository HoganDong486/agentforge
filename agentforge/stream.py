"""WebSocket streaming for real-time workflow monitoring."""
from __future__ import annotations
import asyncio
import json
from typing import Any, Optional


class WorkflowStream:
    def __init__(self):
        self._listeners: list[callable] = []
        self._event_log: list[dict] = []

    def add_listener(self, callback):
        self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def emit(self, event_type: str, data: dict):
        event = {"type": event_type, "timestamp": __import__("time").time(), "data": data}
        self._event_log.append(event)
        for callback in self._listeners:
            try:
                callback(event)
            except Exception:
                pass

    def node_started(self, node_id: str, node_name: str):
        self.emit("node_started", {"node_id": node_id, "node_name": node_name})

    def node_completed(self, node_id: str, node_name: str, output: Any, duration_ms: float):
        self.emit("node_completed", {"node_id": node_id, "node_name": node_name, "output_summary": str(output)[:200], "duration_ms": duration_ms})

    def node_failed(self, node_id: str, node_name: str, error: str):
        self.emit("node_failed", {"node_id": node_id, "node_name": node_name, "error": error})

    def workflow_started(self, workflow_id: str, workflow_name: str):
        self.emit("workflow_started", {"workflow_id": workflow_id, "workflow_name": workflow_name})

    def workflow_completed(self, workflow_id: str, result: dict):
        self.emit("workflow_completed", {"workflow_id": workflow_id, "result_summary": str(result)[:500]})

    def get_log(self, limit: int = 50) -> list[dict]:
        return self._event_log[-limit:]

    def to_json(self) -> str:
        return json.dumps(self._event_log, indent=2)
