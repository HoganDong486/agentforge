"""Persistent memory store with ChromaDB for AgentForge."""
from __future__ import annotations
import hashlib
import json
import time
from typing import Any, Optional, Dict, List
import chromadb
from chromadb.config import Settings as ChromaSettings
from agentforge.llm import get_llm
from agentforge.config import get_config


class MemoryStore:
    def __init__(self, persist_dir: Optional[str] = None):
        cfg = get_config()
        persist_dir = persist_dir or cfg.memory_db_path
        self.client = chromadb.PersistentClient(path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False))
        self.llm = get_llm()
        self._ensure_collections()

    def _ensure_collections(self):
        self.sessions = self.client.get_or_create_collection("agentforge_sessions")
        self.knowledge = self.client.get_or_create_collection("agentforge_knowledge")
        self.tool_logs = self.client.get_or_create_collection("agentforge_tool_logs")

    def save_session(self, session_id: str, data: dict):
        doc_id = f"session_{session_id}_{int(time.time())}"
        text = json.dumps(data, ensure_ascii=False)
        embedding = self.llm.embed([text[:8000]])[0]
        self.sessions.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{"session_id": session_id, "timestamp": time.time()}],
        )

    def recall(self, query: str, n_results: int = 5) -> list[dict]:
        embedding = self.llm.embed([query])[0]
        results = self.sessions.query(query_embeddings=[embedding], n_results=n_results)
        docs = []
        if results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                docs.append({"content": doc, "score": 1.0 - float(results.get("distances", [[0]])[0][i])})
        return docs

    def add_knowledge(self, topic: str, content: str):
        doc_id = hashlib.md5(content.encode()).hexdigest()[:12]
        embedding = self.llm.embed([content[:8000]])[0]
        self.knowledge.add(ids=[doc_id], embeddings=[embedding], documents=[content], metadatas=[{"topic": topic}])

    def search_knowledge(self, query: str, n_results: int = 5) -> list[str]:
        embedding = self.llm.embed([query])[0]
        results = self.knowledge.query(query_embeddings=[embedding], n_results=n_results)
        return results.get("documents", [[]])[0] or []

    def log_tool_call(self, agent_id: str, tool_name: str, args: dict, result: Any):
        doc_id = f"tool_{agent_id}_{int(time.time() * 1000)}"
        data = json.dumps({"tool": tool_name, "args": args, "result": str(result)[:2000]})
        embedding = self.llm.embed([data[:8000]])[0]
        self.tool_logs.add(ids=[doc_id], embeddings=[embedding], documents=[data], metadatas=[{"agent_id": agent_id, "tool": tool_name, "timestamp": time.time()}])

    def get_stats(self) -> dict:
        return {
            "sessions": self.sessions.count(),
            "knowledge_items": self.knowledge.count(),
            "tool_calls_logged": self.tool_logs.count(),
        }
