"""Rate limiter and request queue for agent LLM calls."""
import time
import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Awaitable


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 30
    tokens_per_minute: int = 100000
    max_queue_size: int = 100
    cooldown_seconds: float = 1.0


class RateLimiter:
    def __init__(self, config: Optional["RateLimitConfig"] = None):
        self.config = config or RateLimitConfig()
        self._request_times: deque[float] = deque()
        self._token_usage: deque[tuple[float, int]] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 100) -> bool:
        async with self._lock:
            now = time.time()
            window = now - 60

            while self._request_times and self._request_times[0] < window:
                self._request_times.popleft()
            while self._token_usage and self._token_usage[0][0] < window:
                self._token_usage.popleft()

            if len(self._request_times) >= self.config.requests_per_minute:
                wait_time = self._request_times[0] + 60 - now + 0.1
                await asyncio.sleep(wait_time)
                return await self.acquire(estimated_tokens)

            tokens_used = sum(t[1] for t in self._token_usage)
            if tokens_used + estimated_tokens > self.config.tokens_per_minute:
                wait_time = self._token_usage[0][0] + 60 - now + 0.1
                await asyncio.sleep(wait_time)
                return await self.acquire(estimated_tokens)

            self._request_times.append(now)
            self._token_usage.append((now, estimated_tokens))
            return True

    def record_usage(self, tokens_used: int):
        self._token_usage.append((time.time(), tokens_used))

    def get_current_rate(self) -> dict:
        now = time.time()
        window = now - 60
        recent_requests = sum(1 for t in self._request_times if t >= window)
        recent_tokens = sum(t[1] for t in self._token_usage if t[0] >= window)
        return {
            "requests_last_60s": recent_requests,
            "tokens_last_60s": recent_tokens,
            "requests_limit": self.config.requests_per_minute,
            "tokens_limit": self.config.tokens_per_minute,
            "usage_percent": round(recent_requests / max(self.config.requests_per_minute, 1) * 100, 1),
        }


class RequestQueue:
    def __init__(self, limiter: Optional[RateLimiter] = None, max_concurrent: int = 3):
        self.limiter = limiter or RateLimiter()
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(self, fn: Callable[..., Awaitable], estimated_tokens: int = 100, *args, **kwargs) -> Any:
        await self.limiter.acquire(estimated_tokens)
        async with self._semaphore:
            result = await fn(*args, **kwargs)
            return result

    def stats(self) -> dict:
        return {"rate_limiter": self.limiter.get_current_rate(), "max_concurrent": self.max_concurrent}
