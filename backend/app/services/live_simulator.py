"""Background simulator — streams real CICDDoS flow windows through the live detection pipeline."""

from __future__ import annotations

import asyncio
import gc
import logging
import random

import pandas as pd

from ..core.config import (
    GRAPH_MIN_FLOWS,
    LIVE_SIMULATOR_ATTACKS_PER_10,
    LIVE_SIMULATOR_INTERVAL_SECONDS,
    LIVE_SIMULATOR_SAMPLE_ROWS,
    LIVE_SIMULATOR_TICKS_PER_INTERVAL,
    LOAD_GAT,
    resolve_simulator_csv_path,
)
from ..db.database import SessionLocal
from ..schemas.predict import FlowRecord, PredictRequest
from ..websockets.manager import ws_manager
from .detection_service import detection_service
from .metrics_service import MetricsService

logger = logging.getLogger(__name__)

_SKIP_COLS = {"Source IP", "Destination IP", "Flow ID", "Timestamp", "Label"}


def _row_to_flow(row: pd.Series) -> FlowRecord:
    extras: dict[str, float] = {}
    for col in row.index:
        key = str(col).strip()
        if key in _SKIP_COLS:
            continue
        try:
            val = row[col]
            if pd.isna(val):
                continue
            extras[key] = float(val)
        except (TypeError, ValueError):
            continue

    return FlowRecord(
        source_ip=str(row["Source IP"]).strip(),
        destination_ip=str(row["Destination IP"]).strip(),
        source_port=float(extras.get("Source Port", row.get("Source Port", 0)) or 0),
        destination_port=float(extras.get("Destination Port", row.get("Destination Port", 0)) or 0),
        protocol=float(extras.get("Protocol", row.get("Protocol", 6)) or 6),
        flow_duration=float(extras.get("Flow Duration", 0) or 0),
        total_fwd_packets=float(extras.get("Total Fwd Packets", 0) or 0),
        total_backward_packets=float(extras.get("Total Backward Packets", 0) or 0),
        flow_bytes_s=float(extras.get("Flow Bytes/s", 0) or 0),
        flow_packets_s=float(extras.get("Flow Packets/s", 1) or 1),
        syn_flag_count=float(extras.get("SYN Flag Count", 0) or 0),
        ack_flag_count=float(extras.get("ACK Flag Count", 1) or 1),
        extras=extras,
    )


class LiveSimulator:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False
        self._attack_windows: list[tuple[str, list[FlowRecord]]] = []
        self._benign_windows: list[tuple[str, list[FlowRecord]]] = []
        self._tick_counter = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def window_count(self) -> int:
        return len(self._attack_windows) + len(self._benign_windows)

    def _load_samples(self) -> None:
        path = resolve_simulator_csv_path()
        if not path.exists():
            logger.warning("Live simulator: dataset not found at %s", path)
            return

        logger.info("Live simulator: loading up to %d rows from %s", LIVE_SIMULATOR_SAMPLE_ROWS, path.name)
        df = pd.read_csv(path, nrows=LIVE_SIMULATOR_SAMPLE_ROWS)
        df.columns = [c.strip() for c in df.columns]

        attack_by_victim: dict[str, list[FlowRecord]] = {}
        benign_by_victim: dict[str, list[FlowRecord]] = {}

        for _, row in df.iterrows():
            try:
                flow = _row_to_flow(row)
            except (KeyError, ValueError, TypeError):
                continue
            label = str(row.get("Label", "BENIGN")).strip().upper()
            bucket = attack_by_victim if label != "BENIGN" else benign_by_victim
            bucket.setdefault(flow.destination_ip, []).append(flow)

        self._attack_windows = [
            (v, flows) for v, flows in attack_by_victim.items() if len(flows) >= GRAPH_MIN_FLOWS
        ]
        self._benign_windows = [
            (v, flows) for v, flows in benign_by_victim.items() if len(flows) >= GRAPH_MIN_FLOWS
        ]
        logger.info(
            "Live simulator: %d attack windows, %d benign windows",
            len(self._attack_windows),
            len(self._benign_windows),
        )

    def _pick_window(self) -> tuple[str, list[FlowRecord]] | None:
        """Exactly 4 of every 10 ticks use attack-labeled traffic."""
        self._tick_counter += 1
        slot = (self._tick_counter - 1) % 10
        use_attack = slot < LIVE_SIMULATOR_ATTACKS_PER_10

        if use_attack and self._attack_windows:
            return random.choice(self._attack_windows)
        if self._benign_windows:
            return random.choice(self._benign_windows)
        if self._attack_windows:
            return random.choice(self._attack_windows)
        return None

    async def _tick(self) -> None:
        picked = self._pick_window()
        if not picked:
            return

        victim, pool = picked
        batch_size = random.randint(GRAPH_MIN_FLOWS, min(28, len(pool)))
        flows = random.sample(pool, batch_size)
        model = random.choice(["gcn", "gat"] if LOAD_GAT else ["gcn"])

        request = PredictRequest(flows=flows, victim_ip=victim, model=model)
        metrics_svc = MetricsService()

        async with SessionLocal() as session:
            try:
                result = await detection_service.predict(session, request)
                await session.commit()
                logger.info(
                    "Live scan #%d victim=%s attack=%s prob=%.3f flows=%d",
                    self._tick_counter,
                    result.victim_ip,
                    result.is_attack,
                    result.probability,
                    result.num_flows,
                )
                summary = await metrics_svc.summary(session)
                await ws_manager.broadcast(
                    "metrics",
                    {"type": "summary", **summary.model_dump()},
                )
            except Exception:
                await session.rollback()
                logger.exception("Live simulator tick failed")
            finally:
                gc.collect()

    async def _run_loop(self) -> None:
        await asyncio.to_thread(self._load_samples)
        while self._running:
            for _ in range(LIVE_SIMULATOR_TICKS_PER_INTERVAL):
                if not self._running:
                    break
                await self._tick()
            await asyncio.sleep(LIVE_SIMULATOR_INTERVAL_SECONDS)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Live simulator started interval=%ss ticks=%s attacks_per_10=%s",
            LIVE_SIMULATOR_INTERVAL_SECONDS,
            LIVE_SIMULATOR_TICKS_PER_INTERVAL,
            LIVE_SIMULATOR_ATTACKS_PER_10,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Live simulator stopped")


live_simulator = LiveSimulator()
