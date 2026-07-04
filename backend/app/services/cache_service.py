"""Optional Redis cache for prediction deduplication."""

from __future__ import annotations

import hashlib
import json
import logging

from ..core.config import CACHE_PREDICTION_TTL_SECONDS, REDIS_URL

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self) -> None:
        self._redis = None
        if REDIS_URL:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(REDIS_URL, decode_responses=True)
                logger.info("Redis cache enabled")
            except Exception as exc:
                logger.warning("Redis unavailable: %s", exc)

    def _key(self, victim_ip: str, flow_hash: str) -> str:
        return f"pred:{victim_ip}:{flow_hash}"

    @staticmethod
    def hash_flows(flows_payload: str) -> str:
        return hashlib.sha256(flows_payload.encode()).hexdigest()[:16]

    async def get_prediction(self, victim_ip: str, flow_hash: str) -> dict | None:
        if not self._redis:
            return None
        raw = await self._redis.get(self._key(victim_ip, flow_hash))
        return json.loads(raw) if raw else None

    async def set_prediction(self, victim_ip: str, flow_hash: str, payload: dict) -> None:
        if not self._redis:
            return
        await self._redis.setex(
            self._key(victim_ip, flow_hash),
            CACHE_PREDICTION_TTL_SECONDS,
            json.dumps(payload),
        )


cache_service = CacheService()
