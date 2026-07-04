"""In-memory blocklist for fast prevention at ingest time."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..db.models import MitigationActionType, MitigationStatus

logger = logging.getLogger(__name__)


class BlocklistService:
    """Thread-safe enough for async single-process uvicorn; Redis for multi-worker prod."""

    def __init__(self) -> None:
        self._blocked: dict[str, dict] = {}
        self._rate_limited: dict[str, dict] = {}
        self._quarantined: dict[str, dict] = {}

    def sync_from_records(self, records: list) -> None:
        self._blocked.clear()
        self._rate_limited.clear()
        self._quarantined.clear()
        for r in records:
            if r.status != MitigationStatus.active:
                continue
            entry = {
                "source_ip": r.source_ip,
                "victim_ip": r.victim_ip,
                "action": r.action.value,
                "record_id": r.id,
                "applied_at": r.applied_at.isoformat() if r.applied_at else None,
            }
            if r.action == MitigationActionType.block:
                self._blocked[r.source_ip] = entry
            elif r.action == MitigationActionType.rate_limit:
                self._rate_limited[r.source_ip] = entry
            else:
                self._quarantined[r.source_ip] = entry
        logger.info(
            "Blocklist synced: %d blocked, %d rate-limited, %d quarantined",
            len(self._blocked),
            len(self._rate_limited),
            len(self._quarantined),
        )

    def is_blocked(self, source_ip: str) -> bool:
        return source_ip in self._blocked

    def is_mitigated(self, source_ip: str) -> dict | None:
        if source_ip in self._blocked:
            return self._blocked[source_ip]
        if source_ip in self._quarantined:
            return self._quarantined[source_ip]
        if source_ip in self._rate_limited:
            return self._rate_limited[source_ip]
        return None

    def add(self, source_ip: str, action: MitigationActionType, victim_ip: str, record_id: int) -> None:
        entry = {
            "source_ip": source_ip,
            "victim_ip": victim_ip,
            "action": action.value,
            "record_id": record_id,
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }
        if action == MitigationActionType.block:
            self._blocked[source_ip] = entry
        elif action == MitigationActionType.rate_limit:
            self._rate_limited[source_ip] = entry
        else:
            self._quarantined[source_ip] = entry

    def remove(self, source_ip: str) -> None:
        self._blocked.pop(source_ip, None)
        self._rate_limited.pop(source_ip, None)
        self._quarantined.pop(source_ip, None)

    @property
    def stats(self) -> dict:
        return {
            "blocked": len(self._blocked),
            "rate_limited": len(self._rate_limited),
            "quarantined": len(self._quarantined),
            "total_active": len(self._blocked) + len(self._rate_limited) + len(self._quarantined),
        }

    def entries(self, action: MitigationActionType) -> list[dict]:
        store = {
            MitigationActionType.block: self._blocked,
            MitigationActionType.rate_limit: self._rate_limited,
            MitigationActionType.quarantine: self._quarantined,
        }[action]
        return list(store.values())


blocklist_service = BlocklistService()
