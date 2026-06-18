"""Context compressor for reducing token consumption."""
from typing import List
from agentforge.llm import get_llm


class ContextCompressor:
    def __init__(self, target_tokens: int = 2000):
        self.target_tokens = target_tokens
        self.llm = get_llm()

    def compress(self, messages: List[dict], query: str) -> List[dict]:
        total = sum(len(str(m.get("content", ""))) for m in messages)
        if total < self.target_tokens * 4:
            return messages
        summary = self._summarize(messages, query)
        return [{"role": "system", "content": f"Compressed context ({len(messages)} messages):\n{summary}"}]

    def _summarize(self, messages: List[dict], query: str) -> str:
        combined = "\n".join(f"[{m.get('role', '?')}]: {str(m.get('content', ''))[:500]}" for m in messages[-20:])
        prompt = (
            "Summarize the following conversation history into key points relevant to the query. "
            "Include: decisions made, facts discovered, errors encountered, and open questions.\n\n"
            f"Query: {query}\n\n"
            f"History:\n{combined[:8000]}\n\n"
            "Key points (concise bullet list):"
        )
        return self.llm.chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=self.target_tokens)

    def extract_keypoints(self, text: str) -> str:
        prompt = f"Extract the 3-5 most important points from:\n\n{text[:6000]}\n\nBullet list:"
        return self.llm.chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=500)
