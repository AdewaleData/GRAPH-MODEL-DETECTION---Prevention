"""Per-victim flow buffer — hash map + deque queue for streaming windows."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock

from ..core.config import FLOW_BUFFER_MAX_PER_VICTIM, GRAPH_MIN_FLOWS
from ..schemas.predict import FlowRecord

logger = logging.getLogger(__name__)


@dataclass
class BufferedFlow:
    record: FlowRecord
    feature_vector: list[float]


@dataclass
class VictimBuffer:
    """Queue of flows for one victim IP."""

    flows: deque[BufferedFlow] = field(default_factory=deque)

    def append(self, flow: BufferedFlow, max_size: int) -> None:
        self.flows.append(flow)
        while len(self.flows) > max_size:
            self.flows.popleft()


class FlowBufferService:
    """
    DSA: dict[victim_ip] -> VictimBuffer (deque).
    O(1) append; O(k) window extraction.
    """

    def __init__(self, max_per_victim: int = FLOW_BUFFER_MAX_PER_VICTIM) -> None:
        self.max_per_victim = max_per_victim
        self._buffers: dict[str, VictimBuffer] = defaultdict(VictimBuffer)
        self._lock = Lock()

    def ingest(self, flow: FlowRecord, features: list[float]) -> str:
        victim = flow.destination_ip
        with self._lock:
            buf = self._buffers[victim]
            buf.append(BufferedFlow(flow, features), self.max_per_victim)
            logger.debug("Buffered flow victim=%s size=%d", victim, len(buf.flows))
        return victim

    def get_window(self, victim_ip: str, min_flows: int = GRAPH_MIN_FLOWS) -> list[BufferedFlow] | None:
        with self._lock:
            buf = self._buffers.get(victim_ip)
            if not buf or len(buf.flows) < min_flows:
                return None
            return list(buf.flows)

    def victim_ips(self) -> list[str]:
        with self._lock:
            return list(self._buffers.keys())
