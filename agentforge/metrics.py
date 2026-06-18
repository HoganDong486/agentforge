"""Metrics collector and dashboard data provider for AgentForge."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricPoint:
    name: str
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    def __init__(self):
        self._metrics: list[MetricPoint] = []
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._timers: dict[str, list[float]] = {}

    def increment(self, name: str, value: int = 1, tags: dict = None):
        self._counters[name] = self._counters.get(name, 0) + value
        self._metrics.append(MetricPoint(name=name, value=float(value), tags=tags or {}))

    def gauge(self, name: str, value: float):
        self._gauges[name] = value

    def timing(self, name: str, duration_ms: float):
        if name not in self._timers:
            self._timers[name] = []
        self._timers[name].append(duration_ms)

    def get_snapshot(self) -> dict:
        avg_timers = {}
        for name, values in self._timers.items():
            if values:
                avg_timers[name] = round(sum(values) / len(values), 2)
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "avg_timers_ms": avg_timers,
            "total_events": len(self._metrics),
            "uptime_seconds": round(time.time() - (self._metrics[0].timestamp if self._metrics else time.time()), 1),
        }

    def reset_timers(self):
        self._timers = {}

    def clear(self):
        self._metrics = []
        self._counters = {}
        self._gauges = {}
        self._timers = {}
