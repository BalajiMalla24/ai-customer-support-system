import json
import os
from datetime import datetime, timezone

from redis.asyncio import Redis


class RedisSessionManager:
    """Ephemeral Redis session storage with safe fallbacks when Redis is unavailable."""

    def __init__(self):
        self.client: Redis | None = None
        self.enabled = False
        self.history_ttl_seconds = int(os.getenv("REDIS_SESSION_TTL_SECONDS", "86400"))
        self._profile_fallback: dict[str, dict] = {}

    async def connect(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            self.client = Redis.from_url(redis_url, decode_responses=True)
            await self.client.ping()
            self.enabled = True
            print(f"Connected to Redis at {redis_url}")
        except Exception as e:
            self.client = None
            self.enabled = False
            print(f"Redis unavailable, continuing without it: {e}")

    async def close(self):
        if self.client is not None:
            await self.client.close()

    def _history_key(self, session_id: str) -> str:
        return f"session:{session_id}:history"

    def _meta_key(self, session_id: str) -> str:
        return f"session:{session_id}:meta"

    def _profile_key(self, session_id: str) -> str:
        return f"session:{session_id}:profile"

    async def append_message(self, session_id: str, role: str, content: str):
        if not self.enabled or self.client is None:
            return
        payload = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        key = self._history_key(session_id)
        await self.client.rpush(key, json.dumps(payload, ensure_ascii=True))
        await self.client.expire(key, self.history_ttl_seconds)

    async def get_history(self, session_id: str) -> list[dict]:
        if not self.enabled or self.client is None:
            return []
        key = self._history_key(session_id)
        rows = await self.client.lrange(key, 0, -1)
        history = []
        for row in rows:
            try:
                history.append(json.loads(row))
            except Exception:
                continue
        return history

    async def set_meta(
        self,
        session_id: str,
        intent: str | None = None,
        priority: str | None = None,
        order_id: str | None = None,
    ):
        if not self.enabled or self.client is None:
            return

        updates = {}
        if intent:
            updates["intent"] = intent
        if priority:
            updates["priority"] = priority
        if order_id:
            updates["order_id"] = str(order_id).strip().upper()
        if not updates:
            return

        key = self._meta_key(session_id)
        await self.client.hset(key, mapping=updates)
        await self.client.expire(key, self.history_ttl_seconds)

    async def enqueue_email_ticket(self, ticket: dict):
        if not self.enabled or self.client is None:
            return
        await self.client.lpush("support:email:queue", json.dumps(ticket, ensure_ascii=True))

    async def set_profile(self, session_id: str, profile: dict):
        if not profile:
            return
        if not self.enabled or self.client is None:
            existing = self._profile_fallback.get(session_id, {})
            merged = dict(existing)
            merged.update({k: str(v) for k, v in profile.items() if v is not None and str(v).strip()})
            self._profile_fallback[session_id] = merged
            return
        key = self._profile_key(session_id)
        mapping = {k: str(v) for k, v in profile.items() if v is not None and str(v).strip()}
        if not mapping:
            return
        await self.client.hset(key, mapping=mapping)
        await self.client.expire(key, self.history_ttl_seconds)

    async def get_profile(self, session_id: str) -> dict:
        if not self.enabled or self.client is None:
            return self._profile_fallback.get(session_id, {})
        key = self._profile_key(session_id)
        return await self.client.hgetall(key)


redis_manager = RedisSessionManager()
