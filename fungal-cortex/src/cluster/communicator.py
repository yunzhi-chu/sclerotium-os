"""L5 4.2: ClusterCommunicator — "蜜蜂摇摆舞 + 细菌QS + 蚁群信息素" 三合一通信.

Biological Metaphor:
  三合一通信协议——蜜蜂(舞蹈语言)+ 细菌(化学扩散)+ 蚂蚁(地面信息素):

  蜜蜂层——摇摆舞通信(Waggle Dance, 长距离定向):
    侦察蜂发现食物源→回巢表演摇摆舞→编码距离(摇摆持续时长)
    和方向(相对于太阳的角度)→其他工蜂解码→飞向食物源

  细菌层——群体感应(Quorum Sensing, 化学扩散):
    Pseudomonas aeruginosa的QS系统:
    LasI合成3-oxo-C12-HSL→LasR接收→当浓度>阈值→全群体同步激活
    → 生物膜形成/毒力因子表达

  蚂蚁层——信息素地面通信(Stigmergy, 间接通信):
    蚂蚁不直接交流——在走过的路上留下信息素→后续蚂蚁概率跟随
    task_pheromone: "这里有任务"→30分钟蒸发
    knowledge_pheromone: "这里有发现"→持续沉积(多重确认)
    avoidance_pheromone: "这里有故障"→5分钟快速蒸发

  O(n)通信复杂度 vs O(n²)显式通信

Reference:
  S-MADRL (AROB 2026); Armenteros Rey (2025), "Critical consensus";
  Zhu et al. (2025), "QS-mediated policing"; Freire-Obregón (2026), ICAART
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


# ── Constants ────────────────────────────────────────────────────────

class MessageType(str, Enum):
    """11 message types — bee dance encoding variants."""
    TASK_ASSIGN = "task_assign"         # food source location (distance+dir)
    TASK_RESULT = "task_result"         # report nectar quality
    TASK_PROGRESS = "task_progress"     # work-in-progress update
    HEARTBEAT = "heartbeat"             # hive temperature regulation
    KNOWLEDGE_SYNC = "knowledge_sync"   # waggle dance learning
    AGENT_JOIN = "agent_join"           # new bee enters hive
    AGENT_LEAVE = "agent_leave"         # bee dies/leaves
    ALERT = "alert"                     # danger signal
    CONSENSUS_VOTE = "consensus_vote"   # scout bee voting
    CLUSTER_STATE = "cluster_state"     # hive status broadcast
    CUSTOM = "custom"                   # user-defined


PheromoneType = str
PHEROMONE_EVAPORATION: dict[str, float] = {
    "task": 1800.0,       # 30 min half-life
    "knowledge": 3600.0,  # 60 min half-life
    "avoidance": 300.0,   # 5 min half-life
}
DEFAULT_QS_THRESHOLD = 0.6  # quorum sensing threshold
MAX_PHEROMONES = 5000


# ── Data Structures ──────────────────────────────────────────────────


@dataclass
class ClusterMessage:
    """A message between cluster agents — like a bee dance or chemical signal."""

    msg_id: str
    msg_type: MessageType
    sender_id: str
    receiver_id: str  # "" = broadcast
    payload: dict[str, Any]
    priority: int = 5  # 1-10, like dance intensity
    created_at: float = field(default_factory=time.time)
    ttl: float = 60.0  # seconds


@dataclass
class Pheromone:
    """A pheromone deposit on the virtual ground — stigmergic signal."""

    pheromone_id: str
    ptype: str  # "task", "knowledge", "avoidance"
    location: str  # topic/queue identifier
    intensity: float = 1.0  # initial strength
    agent_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def current_intensity(self, current_time: float | None = None) -> float:
        """Current intensity after evaporation decay."""
        t = current_time or time.time()
        half_life = PHEROMONE_EVAPORATION.get(self.ptype, 1800.0)
        elapsed = t - self.created_at
        return self.intensity * math.exp(-elapsed * math.log(2) / half_life)


# ── Main Class ───────────────────────────────────────────────────────


class ClusterCommunicator:
    """Tri-modal cluster communication: Bee dance + Bacterial QS + Ant pheromones.

    Config:
      - quorum_threshold: QS activation threshold
      - max_pheromones: max stored pheromone deposits
      - evaporation_enabled: enable auto-evaporation
    """

    def __init__(
        self,
        quorum_threshold: float = DEFAULT_QS_THRESHOLD,
        max_pheromones: int = MAX_PHEROMONES,
        evaporation_enabled: bool = True,
    ) -> None:
        self._quorum_threshold = quorum_threshold
        self._max_pheromones = max_pheromones
        self._evaporation_enabled = evaporation_enabled

        self._messages: deque[ClusterMessage] = deque(maxlen=1000)
        self._pheromones: dict[str, Pheromone] = {}  # {pheromone_id: pheromone}
        self._subscriptions: dict[str, list[str]] = defaultdict(list)  # {topic: [agent_ids]}
        self._qs_signals: dict[str, list[float]] = defaultdict(list)  # {signal_type: [concentrations]}

        self._logger = CortexLogger("cluster_communicator")

    # ── Bee Layer: Direct Messaging ────────────────────────────────

    def send(
        self, msg_type: MessageType, sender_id: str,
        payload: dict[str, Any], receiver_id: str = "",
        priority: int = 5, ttl: float = 60.0,
    ) -> ClusterMessage:
        """Send a direct message (bee dance)."""
        msg = ClusterMessage(
            msg_id=self._gen_msg_id(sender_id, msg_type.value),
            msg_type=msg_type,
            sender_id=sender_id,
            receiver_id=receiver_id,
            payload=payload,
            priority=priority,
            ttl=ttl,
        )
        self._messages.append(msg)
        return msg

    def broadcast(self, msg_type: MessageType, sender_id: str,
                  payload: dict[str, Any], priority: int = 5) -> ClusterMessage:
        """Broadcast to all agents (scout bee returning to hive)."""
        return self.send(msg_type, sender_id, payload, receiver_id="*", priority=priority)

    def receive(self, receiver_id: str, consume: bool = True) -> list[ClusterMessage]:
        """Get messages for a specific agent."""
        received: list[ClusterMessage] = []
        now = time.time()

        for msg in list(self._messages):
            if now - msg.created_at > msg.ttl:
                if consume:
                    self._messages.remove(msg)
                continue
            if msg.receiver_id in (receiver_id, "*", ""):
                received.append(msg)
                if consume:
                    self._messages.remove(msg)

        return received

    def subscribe(self, agent_id: str, topic: str) -> None:
        """Subscribe to a message topic."""
        if agent_id not in self._subscriptions[topic]:
            self._subscriptions[topic].append(agent_id)

    def unsubscribe(self, agent_id: str, topic: str) -> None:
        self._subscriptions[topic] = [a for a in self._subscriptions.get(topic, []) if a != agent_id]

    # ── Ant Layer: Stigmergic Pheromones ───────────────────────────

    def deposit_pheromone(
        self, ptype: str, location: str, intensity: float = 1.0,
        agent_id: str = "", payload: dict[str, Any] | None = None,
    ) -> Pheromone:
        """Deposit a pheromone on the virtual ground."""
        phero_id = self._gen_pheromone_id(ptype, location)
        phero = Pheromone(
            pheromone_id=phero_id,
            ptype=ptype,
            location=location,
            intensity=intensity,
            agent_id=agent_id,
            payload=payload or {},
        )
        self._pheromones[phero_id] = phero

        # Enforce limit
        if len(self._pheromones) > self._max_pheromones:
            self._evaporate()

        return phero

    def sniff(self, location: str, ptype: str | None = None,
              min_intensity: float = 0.01) -> list[Pheromone]:
        """Sniff pheromones at a location (agent decision-making)."""
        now = time.time()
        results: list[Pheromone] = []

        for phero in self._pheromones.values():
            if ptype and phero.ptype != ptype:
                continue
            if phero.location != location:
                continue
            intensity = phero.current_intensity(now)
            if intensity >= min_intensity:
                results.append(phero)

        results.sort(key=lambda p: p.current_intensity(now), reverse=True)
        return results

    def _evaporate(self) -> int:
        """Evaporate weakened pheromones. Returns count removed."""
        now = time.time()
        to_remove: list[str] = []

        for pid, phero in self._pheromones.items():
            if phero.current_intensity(now) < 0.001:
                to_remove.append(pid)

        for pid in to_remove:
            del self._pheromones[pid]

        return len(to_remove)

    # ── Bacteria Layer: Quorum Sensing ─────────────────────────────

    def emit_qs_signal(self, signal_type: str, concentration: float) -> float:
        """Emit a quorum sensing signal. Returns current aggregate concentration."""
        self._qs_signals[signal_type].append(concentration)
        if len(self._qs_signals[signal_type]) > 100:
            self._qs_signals[signal_type] = self._qs_signals[signal_type][-100:]

        # Decay old signals (half-life of ~10 minutes)
        now = time.time()
        for sig_type in list(self._qs_signals.keys()):
            self._qs_signals[sig_type] = [
                c * math.exp(-0.001) for c in self._qs_signals[sig_type]
                if c > 0.001
            ]

        return sum(self._qs_signals[signal_type])

    def check_quorum(self, signal_type: str) -> bool:
        """Check if quorum is reached for a signal type."""
        total = sum(self._qs_signals.get(signal_type, []))
        return total >= self._quorum_threshold

    def qs_activate(self, signal_type: str) -> dict[str, Any]:
        """Attempt to activate coordinated behavior via QS."""
        quorum_reached = self.check_quorum(signal_type)
        total_concentration = sum(self._qs_signals.get(signal_type, []))

        if quorum_reached:
            self._logger.info("quorum_reached", signal=signal_type, concentration=round(total_concentration, 3))
            # Reset after activation
            self._qs_signals[signal_type] = []

        return {
            "signal_type": signal_type,
            "quorum_reached": quorum_reached,
            "concentration": total_concentration,
            "threshold": self._quorum_threshold,
        }

    # ── Combined Operations ────────────────────────────────────────

    def task_announce(self, task_id: str, requirements: dict[str, Any],
                      sender_id: str) -> tuple[ClusterMessage, Pheromone]:
        """Announce a task via both dance (direct) and pheromone (indirect)."""
        msg = self.broadcast(MessageType.TASK_ASSIGN, sender_id, {
            "task_id": task_id, "requirements": requirements,
        })
        phero = self.deposit_pheromone("task", f"queue:{task_id}", 1.0, sender_id)
        return msg, phero

    def knowledge_share(self, topic: str, data: dict[str, Any],
                        sender_id: str, confidence: float = 0.5) -> None:
        """Share knowledge with reinforcement (pheromone accumulates)."""
        self.broadcast(MessageType.KNOWLEDGE_SYNC, sender_id, {
            "topic": topic, "data": data, "confidence": confidence,
        })
        # Knowledge pheromones accumulate (multiple confirmations increase intensity)
        existing = self.sniff(topic, ptype="knowledge")
        boost = 0.2 if existing else 0.5  # new knowledge starts stronger
        self.deposit_pheromone("knowledge", topic, boost, sender_id, data)

    def avoidance_mark(self, location: str, reason: str, agent_id: str) -> Pheromone:
        """Mark a location as problematic (fast-evaporating avoidance pheromone)."""
        return self.deposit_pheromone("avoidance", location, 1.0, agent_id, {"reason": reason})

    # ── Maintenance ────────────────────────────────────────────────

    # ── Phase 7.1b: ZeroMQ Transport (Myelinated Saltatory Conduction) ──

    def enable_zmq_transport(self, bind_address: str = "tcp://127.0.0.1:5555",
                             mode: str = "pubsub") -> bool:
        """Enable ZeroMQ high-performance transport — 10x like myelinated axons.

        Biological Metaphor:
          Myelinated saltatory conduction (150 m/s):
            Schwann cells wrap around axons → action potentials "jump"
            between Nodes of Ranvier → 150 m/s vs 1 m/s (unmyelinated)

          ZeroMQ = myelin sheath:
            PUB/SUB for broadcasting (like inter-node signal propagation)
            PUSH/PULL for task distribution (like neuromuscular junction)
            DEALER/ROUTER for peer-to-peer (like gap junctions)

        Args:
            bind_address: ZMQ socket bind address
            mode: "pubsub", "pushpull", or "dealer"
        Returns:
            True if ZMQ transport initialized successfully
        """
        try:
            import zmq  # noqa: F401
        except ImportError:
            self._logger.warn("zmq_unavailable", reason="pyzmq not installed")
            return False

        try:
            import zmq

            self._zmq_context = zmq.Context()
            self._zmq_mode = mode
            self._zmq_address = bind_address

            if mode == "pubsub":
                self._zmq_pub = self._zmq_context.socket(zmq.PUB)
                self._zmq_pub.bind(bind_address)
                self._zmq_sub = self._zmq_context.socket(zmq.SUB)
                self._zmq_sub.bind(bind_address.replace("5555", "5556"))
            elif mode == "pushpull":
                self._zmq_push = self._zmq_context.socket(zmq.PUSH)
                self._zmq_push.bind(bind_address)
                self._zmq_pull = self._zmq_context.socket(zmq.PULL)
                self._zmq_pull.bind(bind_address.replace("5555", "5556"))
            else:
                self._zmq_dealer = self._zmq_context.socket(zmq.DEALER)
                self._zmq_dealer.bind(bind_address)

            self._logger.info("zmq_transport_enabled", mode=mode, address=bind_address)
            return True
        except Exception as exc:
            self._logger.error("zmq_init_failed", error=str(exc))
            return False

    def disable_zmq_transport(self) -> None:
        """Disable ZeroMQ transport — demyelination."""
        for attr in ("_zmq_pub", "_zmq_sub", "_zmq_push", "_zmq_pull",
                      "_zmq_dealer", "_zmq_context"):
            sock = getattr(self, attr, None)
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
                setattr(self, attr, None)
        self._logger.info("zmq_transport_disabled")

    def send_zmq(self, msg: ClusterMessage) -> bool:
        """Send message via ZeroMQ — saltatory signal propagation."""
        if not hasattr(self, "_zmq_context") or self._zmq_context is None:
            return False

        try:
            import json
            import zmq

            raw = json.dumps({
                "msg_id": msg.msg_id, "msg_type": msg.msg_type.value,
                "sender_id": msg.sender_id, "receiver_id": msg.receiver_id,
                "payload": msg.payload, "priority": msg.priority,
                "created_at": msg.created_at, "ttl": msg.ttl,
            }).encode("utf-8")

            if self._zmq_mode == "pubsub":
                self._zmq_pub.send_multipart([msg.msg_type.value.encode(), raw])
            elif self._zmq_mode == "pushpull":
                self._zmq_push.send(raw)
            else:
                self._zmq_dealer.send(raw)
            return True
        except Exception as exc:
            self._logger.error("zmq_send_failed", error=str(exc))
            return False

    def cleanup(self) -> dict[str, int]:
        """Run maintenance: evaporate pheromones, remove expired messages."""
        evaporated = self._evaporate()
        now = time.time()
        removed_msgs = 0
        for msg in list(self._messages):
            if now - msg.created_at > msg.ttl:
                self._messages.remove(msg)
                removed_msgs += 1

        return {"evaporated": evaporated, "expired_messages": removed_msgs}

    @staticmethod
    def _gen_msg_id(sender_id: str, msg_type: str) -> str:
        raw = f"{sender_id}|{msg_type}|{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _gen_pheromone_id(ptype: str, location: str) -> str:
        raw = f"{ptype}|{location}|{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "queued_messages": len(self._messages),
            "pheromones": len(self._pheromones),
            "pheromone_types": {
                pt: sum(1 for p in self._pheromones.values() if p.ptype == pt)
                for pt in PHEROMONE_EVAPORATION
            },
            "subscriptions": {k: len(v) for k, v in self._subscriptions.items()},
            "qs_signals": {k: round(sum(v), 3) for k, v in self._qs_signals.items()},
        }
