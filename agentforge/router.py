"""Model router: select optimal model based on task characteristics."""
from dataclasses import dataclass
from typing import Optional
from agentforge.llm import LLMClient
from agentforge.config import get_config


@dataclass
class ModelRoute:
    model_id: str
    description: str
    max_tokens: int
    cost_per_1k: float
    strengths: list[str]


MODELS = [
    ModelRoute("gpt-4o", "Most capable, expensive", 16384, 0.015, ["reasoning", "complex", "planning", "creative"]),
    ModelRoute("gpt-4o-mini", "Fast, affordable", 16384, 0.0006, ["coding", "quick", "drafting"]),
    ModelRoute("claude-3-5-sonnet-20241022", "Strong coding, long context", 200000, 0.015, ["coding", "analysis", "refactoring"]),
    ModelRoute("claude-3-haiku-20240307", "Fast, cost-effective", 200000, 0.00125, ["quick", "classification", "summarization"]),
    ModelRoute("deepseek-chat", "Cost-effective reasoning", 65536, 0.002, ["reasoning", "coding", "analysis"]),
    ModelRoute("qwen-max", "Chinese-optimized", 32768, 0.004, ["chinese", "translation", "analysis"]),
]


class ModelRouter:
    def __init__(self, routes: Optional[list[ModelRoute]] = None):
        self.routes = routes or MODELS
        self.default_model = get_config().llm_model

    def select(self, task_type: str, estimated_tokens: int = 2000, max_cost: float = 0.01) -> str:
        candidates = []
        for route in self.routes:
            if any(s in task_type.lower() for s in route.strengths) and route.max_tokens >= estimated_tokens:
                est_cost = (estimated_tokens / 1000) * route.cost_per_1k
                if est_cost <= max_cost:
                    candidates.append((est_cost, route))
        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1].model_id
        return self.default_model

    def list_models(self) -> list[dict]:
        return [
            {"id": m.model_id, "description": m.description, "max_tokens": m.max_tokens, "cost_per_1k": m.cost_per_1k, "strengths": m.strengths}
            for m in self.routes
        ]

    def get_cheapest_for(self, task_type: str, estimated_tokens: int) -> Optional[str]:
        return self.select(task_type, estimated_tokens, float("inf"))
