"""AgentForge core configuration."""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""), repr=False)
    openai_base_url: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_BASE_URL"))
    llm_model: str = field(default_factory=lambda: os.environ.get("AGENTFORGE_MODEL", "gpt-4o-mini"))
    embedding_model: str = field(default_factory=lambda: os.environ.get("AGENTFORGE_EMBEDDING", "text-embedding-3-small"))
    max_tokens: int = 4096
    temperature: float = 0.3
    max_parallel_agents: int = 5
    max_retries: int = 3
    request_timeout: int = 60
    memory_db_path: str = "./agentforge_memory"
    log_level: str = "INFO"
    workflow_dir: str = "./workflows"


_default_config: Optional[Config] = None


def get_config() -> Config:
    global _default_config
    if _default_config is None:
        _default_config = Config()
    return _default_config


def set_config(config: Config):
    global _default_config
    _default_config = config
