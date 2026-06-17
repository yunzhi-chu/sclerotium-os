"""P2P Bridge — DHT 对等知识同步 (L9 P2PMesh)。

多设备间的记忆同步 — 未来功能, 当前为基础骨架。

功能 (当前):
  - 节点注册 (identity/address)
  - 知识签名 (防篡改)
  - 同步请求/响应协议

使用方式:
    p2p = P2PBridge(node_id="desktop-001")
    p2p.register_knowledge("memory_hash_abc", "战略洞察: 用户迁移到TS")
    peers = p2p.list_peers()
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.p2p")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class NodeInfo:
    """节点信息。"""
    node_id: str
    address: str = "localhost"
    port: int = 0
    last_seen: float = field(default_factory=time.time)
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class KnowledgeSignature:
    """知识签名 (防篡改)。"""
    knowledge_id: str
    content_hash: str
    node_id: str = ""
    timestamp: float = field(default_factory=time.time)
    signature: str = ""


@dataclass(frozen=True)
class SyncRequest:
    """同步请求。"""
    request_id: str
    from_node: str
    knowledge_ids: tuple[str, ...] = ()
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# P2PBridge
# ═══════════════════════════════════════════════════════════════

class P2PBridge:
    """P2P 对等知识同步 (未来功能骨架)。

    使用方式:
        p2p = P2PBridge(node_id="my_device")
        sig = p2p.sign_knowledge("战略洞察: 用户偏好函数式")
        p2p.add_peer("laptop-001", "192.168.1.100:9999")
    """

    def __init__(self, node_id: str = "", address: str = "") -> None:
        self._node_id = node_id or f"node_{hash(time.time()) & 0xFFFF:04x}"
        self._address = address or "localhost"
        self._peers: dict[str, NodeInfo] = {}
        self._knowledge: dict[str, KnowledgeSignature] = {}
        self._sync_requests: list[SyncRequest] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def sign_knowledge(
        self, content: str, knowledge_id: str = "",
    ) -> KnowledgeSignature:
        """对知识签名 (防篡改哈希)。"""
        kid = knowledge_id or f"k_{hash(content) & 0xFFFF:04x}"
        content_hash = hashlib.sha256(
            (content + str(time.time())).encode()
        ).hexdigest()[:32]
        sig = KnowledgeSignature(
            knowledge_id=kid,
            content_hash=content_hash,
            node_id=self._node_id,
            signature=hashlib.sha256(
                (content_hash + self._node_id).encode()
            ).hexdigest()[:16],
        )
        self._knowledge[kid] = sig
        return sig

    def verify_knowledge(self, sig: KnowledgeSignature) -> bool:
        """验证知识签名完整性。"""
        expected = hashlib.sha256(
            (sig.content_hash + sig.node_id).encode()
        ).hexdigest()[:16]
        return expected == sig.signature

    def add_peer(self, node_id: str, address: str = "",
                 capabilities: tuple[str, ...] = ()) -> None:
        """添加对等节点。"""
        self._peers[node_id] = NodeInfo(
            node_id=node_id, address=address or node_id,
            capabilities=capabilities,
        )

    def remove_peer(self, node_id: str) -> bool:
        return self._peers.pop(node_id, None) is not None

    def list_peers(self) -> list[NodeInfo]:
        return list(self._peers.values())

    def create_sync_request(
        self, knowledge_ids: list[str],
    ) -> SyncRequest:
        """创建同步请求。"""
        req = SyncRequest(
            request_id=f"sync_{int(time.time()*1000)}",
            from_node=self._node_id,
            knowledge_ids=tuple(knowledge_ids),
        )
        self._sync_requests.append(req)
        return req

    def get_stats(self) -> dict[str, Any]:
        return {
            "node_id": self._node_id,
            "peers": len(self._peers),
            "knowledge_entries": len(self._knowledge),
            "sync_requests": len(self._sync_requests),
        }

    @property
    def node_id(self) -> str:
        return self._node_id
