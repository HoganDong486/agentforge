"""Base agent class and agent types for AgentForge."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
import json
from agentforge.llm import get_llm


@dataclass
class AgentConfig:
    name: str
    description: str
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    temperature: float = 0.3
    max_tokens: int = 2048
    json_output: bool = False


class BaseAgent(ABC):
    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = get_llm()

    @abstractmethod
    async def run(self, inputs: dict) -> Any:
        ...

    def to_dict(self) -> dict:
        return {
            "name": self.config.name,
            "description": self.config.description,
            "type": self.__class__.__name__,
            "tools": self.config.tools,
        }


class LLMAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def run(self, inputs: dict) -> str:
        prompt = inputs.get("_prompt", inputs.get("message", str(inputs)))
        context = inputs.get("context", "")
        messages = []
        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": prompt})
        return self.llm.chat(messages, temperature=self.config.temperature, max_tokens=self.config.max_tokens, json_mode=self.config.json_output)


class ToolAgent(BaseAgent):
    def __init__(self, config: AgentConfig, tool_registry=None):
        super().__init__(config)
        self.tool_registry = tool_registry

    async def run(self, inputs: dict) -> dict:
        tool_name = inputs.get("tool_name", self.config.tools[0] if self.config.tools else "")
        tool_args = inputs.get("tool_args", inputs)
        if tool_name and self.tool_registry:
            return await self.tool_registry.execute(tool_name, tool_args)
        return {"error": f"Tool not found: {tool_name}"}


class FunctionAgent(BaseAgent):
    def __init__(self, config: AgentConfig, func):
        super().__init__(config)
        self.func = func

    async def run(self, inputs: dict) -> Any:
        import asyncio
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(inputs)
        return self.func(inputs)
