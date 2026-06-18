"""OpenAI-compatible LLM client for AgentForge."""
from typing import Optional
from openai import OpenAI
from agentforge.config import get_config


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        cfg = get_config()
        self.client = OpenAI(
            api_key=api_key or cfg.openai_api_key,
            base_url=base_url or cfg.openai_base_url,
        )
        self.model = model or cfg.llm_model

    def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        cfg = get_config()
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else cfg.temperature,
            "max_tokens": max_tokens or cfg.max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def embed(self, texts: list[str]) -> list[list[float]]:
        cfg = get_config()
        response = self.client.embeddings.create(model=cfg.embedding_model, input=texts)
        return [d.embedding for d in response.data]


_llm_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
