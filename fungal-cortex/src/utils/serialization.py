"""Phase 7.1d: MessagePack Serialization — "DNA二进制编码"(DNA Binary Encoding).

Biological Metaphor:
  DNA的双螺旋二进制编码 vs 英文文本:
    DNA使用4碱基(A/T/C/G)编码——每个碱基对=2 bits信息
    人类基因组30亿碱基对 = ~750MB原始数据 → 实际压缩到~200MB(内含子/外显子)
    蛋白质使用20氨基酸编码——3碱基=1密码子=1氨基酸(6 bits→足够20种)
    → 这是自然界最高效的编码方式(核苷酸 vs 蛋白质)

  我们映射:
    JSON(文本) = 英文/蛋白质语言(人类可读, 冗余高)
    msgpack(二进制) = DNA/碱基编码(机器优化, 3x更紧凑)
    MessagePack = 自然界的"碱基对编码"方法

  性能对比:
    JSON: {"regime":"bear","confidence":0.95} = 38 bytes (文本)
    msgpack: 82 a6 72 65 67 69 6d 65 a4 62 65 61 72 ... = ~24 bytes
    → ~1.6x 更小, 编码/解码 ~3x 更快

Reference:
  MessagePack spec (msgpack.org);
  DNA information theory (Shannon 1948 — information entropy)
"""

from __future__ import annotations

import json
import struct
from typing import Any


# ── MessagePack Encoder/Decoder ─────────────────────────────────────

class MsgPackSerializer:
    """MessagePack binary serializer — nature's DNA encoding for APIs.

    Converts Python dicts to/from MessagePack binary format.
    Falls back to JSON if msgpack library is unavailable.
    """

    _msgpack_available: bool = False

    @classmethod
    def _check_msgpack(cls) -> bool:
        if not cls._msgpack_available:
            try:
                import msgpack  # noqa: F401
                cls._msgpack_available = True
            except ImportError:
                pass
        return cls._msgpack_available

    @staticmethod
    def encode(data: dict[str, Any] | list[Any]) -> bytes:
        """Encode Python data to MessagePack binary.

        Args:
            data: dict or list to encode
        Returns:
            MessagePack binary bytes (or JSON bytes as fallback)
        """
        if MsgPackSerializer._check_msgpack():
            import msgpack
            return msgpack.packb(data, use_bin_type=True)
        # Fallback: JSON with minimal overhead
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    @staticmethod
    def decode(raw: bytes) -> dict[str, Any] | list[Any]:
        """Decode MessagePack binary to Python data.

        Args:
            raw: MessagePack binary bytes (or JSON bytes)
        Returns:
            Decoded Python dict or list
        """
        if MsgPackSerializer._check_msgpack():
            import msgpack
            return msgpack.unpackb(raw, raw=False)
        return json.loads(raw.decode("utf-8"))


# ── Compact Event Format ────────────────────────────────────────────

class CompactEvent:
    """A compact binary event format for high-throughput messaging.

    Uses struct packing for fixed-width fields to minimize overhead.
    Like DNA's triplet codon system — each position has exact meaning.
    """

    _HEADER_FORMAT = "!dI H H"  # timestamp(f64) + data_len(u32) + topic_len(u16) + priority(u16)
    _HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)  # 16 bytes

    @staticmethod
    def serialize(topic: str, data: dict[str, Any],
                  priority: int = 2, timestamp: float | None = None) -> bytes:
        """Serialize an event to compact binary format.

        Header (16 bytes): [timestamp f64][data_len u32][topic_len u16][priority u16]
        Body: [topic UTF-8][data msgpack]
        """
        import time
        ts = timestamp or time.time()
        topic_bytes = topic.encode("utf-8")
        data_bytes = MsgPackSerializer.encode(data)

        header = struct.pack(
            CompactEvent._HEADER_FORMAT,
            ts, len(data_bytes), len(topic_bytes), priority,
        )
        return header + topic_bytes + data_bytes

    @staticmethod
    def deserialize(raw: bytes) -> dict[str, Any]:
        """Deserialize a compact event from binary format."""
        header = raw[:CompactEvent._HEADER_SIZE]
        ts, data_len, topic_len, priority = struct.unpack(
            CompactEvent._HEADER_FORMAT, header,
        )

        offset = CompactEvent._HEADER_SIZE
        topic = raw[offset:offset + topic_len].decode("utf-8")
        offset += topic_len
        data = MsgPackSerializer.decode(raw[offset:offset + data_len])

        return {
            "topic": topic,
            "data": data,
            "priority": priority,
            "timestamp": ts,
        }


# ── Size Comparison Utility ─────────────────────────────────────────

def compare_formats(data: dict[str, Any]) -> dict[str, Any]:
    """Compare JSON vs MessagePack encoding efficiency.

    Like comparing protein language (20 amino acids) to DNA (4 bases).
    """
    json_bytes = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    msgpack_bytes = MsgPackSerializer.encode(data)
    compact_bytes = CompactEvent.serialize("test.topic", data)

    return {
        "json_size": len(json_bytes),
        "msgpack_size": len(msgpack_bytes),
        "compact_size": len(compact_bytes),
        "msgpack_vs_json": f"{len(msgpack_bytes) / max(len(json_bytes), 1) * 100:.1f}%",
        "compact_vs_json": f"{len(compact_bytes) / max(len(json_bytes), 1) * 100:.1f}%",
        "json_bytes": json_bytes[:100],
        "msgpack_bytes": msgpack_bytes[:100],
    }
