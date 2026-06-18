"""ReAct (Reasoning + Acting) agent implementation."""
from __future__ import annotations
import json
from typing import Any, Optional
from agentforge.agents.base import BaseAgent, AgentConfig
from agentforge.tools.mcp_client import ToolRegistry
from agentforge.memory.store import MemoryStore
from agentforge.llm import get_llm


class ReActAgent(BaseAgent):
    """Agent that interleaves reasoning steps with tool actions."""

    TOOL_PROMPT = """You have access to these tools:
{tool_list}

To use a tool, output JSON:
{{"action": "TOOL", "tool": "<tool_name>", "args": {{...}}, "reasoning": "why you need this tool"}}

To give final answer, output JSON:
{{"action": "FINAL", "answer": "your final response"}}

Think step by step. Use tools when needed. Output ONLY valid JSON."""

    def __init__(self, config: AgentConfig, tool_registry: Optional[ToolRegistry] = None):
        super().__init__(config)
        self.tools = tool_registry or ToolRegistry()
        self.memory = MemoryStore()
        self.llm = get_llm()
        self.max_steps = 10

    async def run(self, inputs: dict) -> dict:
        query = inputs.get("message", inputs.get("_prompt", str(inputs)))
        context = inputs.get("context", "")
        steps = []
        tools_used = []

        tool_list = "\n".join(f"- {t['name']}: {t.get('description', '')[:100]}" for t in self.tools.list_all())
        system_prompt = self.config.system_prompt or self.TOOL_PROMPT.format(tool_list=tool_list)

        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({"role": "system", "content": f"Additional context:\n{context}"})
        messages.append({"role": "user", "content": query})

        for step in range(self.max_steps):
            response = self.llm.chat(messages, temperature=0.1, max_tokens=1024, json_mode=True)
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError:
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": "Output must be valid JSON. Try again."})
                continue

            steps.append(parsed)

            if parsed.get("action") == "FINAL":
                return {"answer": parsed.get("answer", ""), "steps": len(steps), "tools_used": tools_used, "reasoning_trace": steps}

            elif parsed.get("action") == "TOOL":
                tool_name = parsed.get("tool", "")
                tool_args = parsed.get("args", {})
                reasoning = parsed.get("reasoning", "")
                try:
                    import asyncio
                    result = await self.tools.execute(tool_name, tool_args)
                    tools_used.append(tool_name)
                    self.memory.log_tool_call(self.config.name, tool_name, tool_args, result)
                    messages.append({"role": "assistant", "content": f"[TOOL: {tool_name}] Reasoning: {reasoning}"})
                    messages.append({"role": "user", "content": f"Tool result:\n{json.dumps(result, default=str)[:2000]}"})
                except Exception as e:
                    messages.append({"role": "user", "content": f"Tool error: {e}. Try another approach."})

            else:
                messages.append({"role": "user", "content": "Unknown action. Use TOOL or FINAL."})

        return {"answer": "Max steps reached without final answer.", "steps": self.max_steps, "tools_used": tools_used, "reasoning_trace": steps}


class ChainOfThoughtAgent(BaseAgent):
    """Agent that explicitly thinks step by step before answering."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def run(self, inputs: dict) -> dict:
        query = inputs.get("message", str(inputs))

        think_prompt = f"""Think through this problem step by step. Output your reasoning as:
STEP 1: [first observation]
STEP 2: [second observation]
...
FINAL: [your conclusion]

Problem: {query}"""

        thought = self.llm.chat([{"role": "user", "content": think_prompt}], temperature=0.2, max_tokens=2048)

        answer_prompt = f"""Based on this reasoning, provide a clear, concise answer to the user.

Reasoning:
{thought}

Question: {query}

Answer:"""

        answer = self.llm.chat([{"role": "user", "content": answer_prompt}], temperature=0.3, max_tokens=1024)

        return {"thought_process": thought, "answer": answer}
