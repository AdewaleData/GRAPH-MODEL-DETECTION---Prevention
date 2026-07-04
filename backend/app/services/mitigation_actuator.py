"""Mitigation actuators — simulated, iptables, and webhook enforcement."""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from abc import ABC, abstractmethod

import httpx

from ..core.config import MITIGATION_MODE, MITIGATION_WEBHOOK_URL, MITIGATION_WEBHOOK_TIMEOUT
from ..db.models import MitigationActionType

logger = logging.getLogger(__name__)


class MitigationActuator(ABC):
    @abstractmethod
    async def apply(self, source_ip: str, action: MitigationActionType, victim_ip: str, reason: str) -> dict:
        ...

    @abstractmethod
    async def revoke(self, source_ip: str, action: MitigationActionType) -> dict:
        ...


class SimulatedActuator(MitigationActuator):
    """Records actions in DB only — safe default for dev and thesis demos."""

    async def apply(self, source_ip: str, action: MitigationActionType, victim_ip: str, reason: str) -> dict:
        rule = _simulated_rule(action, source_ip, victim_ip)
        logger.info("Simulated mitigation %s source=%s victim=%s", action.value, source_ip, victim_ip)
        return {"mode": "simulated", "applied": True, "rule": rule}

    async def revoke(self, source_ip: str, action: MitigationActionType) -> dict:
        logger.info("Simulated revoke %s source=%s", action.value, source_ip)
        return {"mode": "simulated", "revoked": True}


class IptablesActuator(MitigationActuator):
    """Linux iptables enforcement — requires CAP_NET_ADMIN / root."""

    CHAIN = "HALAL_GRAPH_MITIGATION"

    async def apply(self, source_ip: str, action: MitigationActionType, victim_ip: str, reason: str) -> dict:
        if platform.system() != "Linux" or not shutil.which("iptables"):
            return {"mode": "iptables", "applied": False, "error": "iptables unavailable on this host"}

        try:
            self._ensure_chain()
            if action == MitigationActionType.block:
                cmd = ["iptables", "-A", self.CHAIN, "-s", source_ip, "-j", "DROP"]
            elif action == MitigationActionType.rate_limit:
                cmd = ["iptables", "-A", self.CHAIN, "-s", source_ip, "-m", "limit", "--limit", "10/sec", "-j", "ACCEPT"]
                subprocess.run(
                    ["iptables", "-A", self.CHAIN, "-s", source_ip, "-j", "DROP"],
                    check=True,
                    capture_output=True,
                    timeout=5,
                )
            else:
                cmd = ["iptables", "-A", self.CHAIN, "-s", source_ip, "-p", "tcp", "--syn", "-j", "DROP"]

            subprocess.run(cmd, check=True, capture_output=True, timeout=5)
            logger.info("iptables applied %s source=%s", action.value, source_ip)
            return {"mode": "iptables", "applied": True, "command": " ".join(cmd)}
        except subprocess.CalledProcessError as exc:
            logger.error("iptables apply failed: %s", exc.stderr)
            return {"mode": "iptables", "applied": False, "error": exc.stderr.decode() if exc.stderr else str(exc)}

    async def revoke(self, source_ip: str, action: MitigationActionType) -> dict:
        if platform.system() != "Linux" or not shutil.which("iptables"):
            return {"mode": "iptables", "revoked": False, "error": "iptables unavailable"}

        try:
            while True:
                result = subprocess.run(
                    ["iptables", "-D", self.CHAIN, "-s", source_ip, "-j", "DROP"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    break
            logger.info("iptables revoked source=%s", source_ip)
            return {"mode": "iptables", "revoked": True}
        except subprocess.SubprocessError as exc:
            return {"mode": "iptables", "revoked": False, "error": str(exc)}

    def _ensure_chain(self) -> None:
        subprocess.run(["iptables", "-N", self.CHAIN], capture_output=True, timeout=5)
        subprocess.run(
            ["iptables", "-C", "INPUT", "-j", self.CHAIN],
            capture_output=True,
            timeout=5,
        )
        if subprocess.run(["iptables", "-C", "INPUT", "-j", self.CHAIN], capture_output=True).returncode != 0:
            subprocess.run(["iptables", "-I", "INPUT", "1", "-j", self.CHAIN], check=True, capture_output=True, timeout=5)


class WebhookActuator(MitigationActuator):
    """SOAR / SIEM integration via HTTP webhook."""

    async def apply(self, source_ip: str, action: MitigationActionType, victim_ip: str, reason: str) -> dict:
        if not MITIGATION_WEBHOOK_URL:
            return {"mode": "webhook", "applied": False, "error": "MITIGATION_WEBHOOK_URL not configured"}

        payload = {
            "event": "mitigation_apply",
            "source_ip": source_ip,
            "victim_ip": victim_ip,
            "action": action.value,
            "reason": reason,
        }
        try:
            async with httpx.AsyncClient(timeout=MITIGATION_WEBHOOK_TIMEOUT) as client:
                resp = await client.post(MITIGATION_WEBHOOK_URL, json=payload)
                resp.raise_for_status()
            return {"mode": "webhook", "applied": True, "status_code": resp.status_code}
        except httpx.HTTPError as exc:
            logger.error("Webhook apply failed: %s", exc)
            return {"mode": "webhook", "applied": False, "error": str(exc)}

    async def revoke(self, source_ip: str, action: MitigationActionType) -> dict:
        if not MITIGATION_WEBHOOK_URL:
            return {"mode": "webhook", "revoked": False, "error": "MITIGATION_WEBHOOK_URL not configured"}

        payload = {"event": "mitigation_revoke", "source_ip": source_ip, "action": action.value}
        try:
            async with httpx.AsyncClient(timeout=MITIGATION_WEBHOOK_TIMEOUT) as client:
                resp = await client.post(MITIGATION_WEBHOOK_URL, json=payload)
                resp.raise_for_status()
            return {"mode": "webhook", "revoked": True, "status_code": resp.status_code}
        except httpx.HTTPError as exc:
            return {"mode": "webhook", "revoked": False, "error": str(exc)}


class CompositeActuator(MitigationActuator):
    """Runs simulated + optional secondary actuator."""

    def __init__(self) -> None:
        self._sim = SimulatedActuator()
        self._secondary: MitigationActuator | None = None
        if MITIGATION_MODE == "iptables":
            self._secondary = IptablesActuator()
        elif MITIGATION_MODE == "webhook":
            self._secondary = WebhookActuator()

    async def apply(self, source_ip: str, action: MitigationActionType, victim_ip: str, reason: str) -> dict:
        results = {"simulated": await self._sim.apply(source_ip, action, victim_ip, reason)}
        if self._secondary:
            results["enforcement"] = await self._secondary.apply(source_ip, action, victim_ip, reason)
        return results

    async def revoke(self, source_ip: str, action: MitigationActionType) -> dict:
        results = {"simulated": await self._sim.revoke(source_ip, action)}
        if self._secondary:
            results["enforcement"] = await self._secondary.revoke(source_ip, action)
        return results


def _simulated_rule(action: MitigationActionType, source_ip: str, victim_ip: str) -> str:
    if action == MitigationActionType.block:
        return f"iptables -A INPUT -s {source_ip} -d {victim_ip} -j DROP"
    if action == MitigationActionType.rate_limit:
        return f"iptables -A INPUT -s {source_ip} -m limit --limit 10/sec -j ACCEPT"
    return f"iptables -A INPUT -s {source_ip} -p tcp --syn -j DROP"


mitigation_actuator = CompositeActuator()
