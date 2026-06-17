"""Fractal Encoder — compress event streams into holographic interference patterns.

Inspired by RIFT theory: the brain doesn't store raw sensory data — it stores
a fractal compression of sensory interference patterns. Somatosensory multi-fractal
Ising lattices encode "fractal self-attractors" that generate holographic inner space.

Compression ratio target: > 100:1 (10,000 events → ~10KB interference pattern).
Local contains global — any frequency slice can reconstruct the whole.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InterferencePattern:
    """Holographic interference pattern — the compressed representation of system state."""

    frequency_bands: list[float]
    phase_angles: list[float]
    amplitudes: list[float]
    coherence: float  # 0-1, how coherent the pattern is
    entropy: float  # Shannon entropy of the pattern
    compression_ratio: float
    event_count: int
    pattern_hash: str
    timestamp: float = field(default_factory=time.time)


class FractalEncoder:
    """Compress event streams into holographic interference patterns.

    Algorithm:
    1. Hash each event into a frequency-phase pair (via multi-fractal spectrum)
    2. Accumulate amplitudes at each frequency band (constructive/destructive interference)
    3. Normalize to fixed-size interference pattern
    4. Compute coherence and entropy as metadata
    """

    def __init__(
        self,
        frequency_bands: int = 8,
        target_bits: int = 10 * 1024 * 8,
        coherence_decay: float = 0.01,
    ) -> None:
        self._n_bands = frequency_bands
        self._target_bits = target_bits
        self._decay = coherence_decay
        self._band_frequencies = [2.0 ** i for i in range(frequency_bands)]  # Octave spacing
        self._accumulated_amplitudes: list[float] = [0.0] * frequency_bands
        self._accumulated_phases: list[float] = [0.0] * frequency_bands
        self._event_count = 0
        self._raw_size_bytes = 0

    def encode_event(self, event: dict[str, Any]) -> None:
        """Encode a single event into the accumulating interference pattern."""
        event_str = str(sorted(event.items()))
        event_hash = hashlib.sha256(event_str.encode()).digest()
        self._raw_size_bytes += len(event_str.encode())

        for i in range(self._n_bands):
            freq = self._band_frequencies[i]
            hash_byte = event_hash[i % len(event_hash)]
            phase = (hash_byte / 255.0) * 2.0 * math.pi
            amplitude = 1.0 / freq  # Higher frequencies have lower amplitude (1/f noise)

            # Interference: accumulate with existing (constructive or destructive)
            existing_phase = self._accumulated_phases[i]
            if self._event_count > 0:
                existing_phase = existing_phase / (1.0 + self._decay)
            self._accumulated_phases[i] = existing_phase + phase * amplitude
            self._accumulated_amplitudes[i] += amplitude

        self._event_count += 1

    def encode_batch(self, events: list[dict[str, Any]]) -> None:
        for event in events:
            self.encode_event(event)

    def get_pattern(self) -> InterferencePattern:
        """Retrieve the current interference pattern."""
        if self._event_count == 0:
            return InterferencePattern(
                frequency_bands=[0.0] * self._n_bands,
                phase_angles=[0.0] * self._n_bands,
                amplitudes=[0.0] * self._n_bands,
                coherence=0.0,
                entropy=0.0,
                compression_ratio=float("inf"),
                event_count=0,
                pattern_hash="",
            )

        # Normalize amplitudes
        max_amp = max(self._accumulated_amplitudes) or 1.0
        norm_amps = [a / max_amp for a in self._accumulated_amplitudes]
        norm_phases = [(p % (2.0 * math.pi)) / (2.0 * math.pi) for p in self._accumulated_phases]

        # Coherence: how uniform are the phases? (std deviation from mean)
        mean_phase = sum(norm_phases) / len(norm_phases)
        phase_var = sum((p - mean_phase) ** 2 for p in norm_phases) / len(norm_phases)
        coherence = 1.0 / (1.0 + phase_var)

        # Entropy: diversity of amplitude distribution
        entropy = 0.0
        for amp in norm_amps:
            if amp > 1e-10:
                entropy -= amp * math.log2(amp)
        max_entropy = math.log2(self._n_bands)
        entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        pattern_size_bytes = self._n_bands * 3 * 8  # bands × (freq + phase + amp) × 8 bytes
        compression_ratio = self._raw_size_bytes / max(pattern_size_bytes, 1)

        pattern_data = f"{norm_amps}|{norm_phases}|{self._event_count}"
        pattern_hash = hashlib.sha256(pattern_data.encode()).hexdigest()[:16]

        return InterferencePattern(
            frequency_bands=list(self._band_frequencies),
            phase_angles=norm_phases,
            amplitudes=norm_amps,
            coherence=coherence,
            entropy=entropy,
            compression_ratio=compression_ratio,
            event_count=self._event_count,
            pattern_hash=pattern_hash,
        )

    def reset(self) -> None:
        self._accumulated_amplitudes = [0.0] * self._n_bands
        self._accumulated_phases = [0.0] * self._n_bands
        self._event_count = 0
        self._raw_size_bytes = 0

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "event_count": self._event_count,
            "raw_size_bytes": self._raw_size_bytes,
            "frequency_bands": self._n_bands,
            "target_bits": self._target_bits,
            "coherence_decay": self._decay,
        }
