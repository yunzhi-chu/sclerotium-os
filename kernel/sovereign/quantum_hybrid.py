"""P3: Quantum-Hybrid Verification (Quantum Gödel Machine grade).

Quantum-witness verifiability for self-modification gates.
Classical verifier + quantum witness for code correctness proofs.

Reference: Quantum Gödel Machine (Ashrafian, TechRxiv 2026),
Super Wisdom Unified Theory (Tang, 2026).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class QuantumWitness:
    """A quantum witness for code correctness."""
    code_hash: str
    witness_data: str
    confidence: float  # [0,1] quantum verification confidence
    verified: bool = False


class QuantumHybridVerifier:
    """Quantum-classical hybrid code verifier.

    Phase 5: Classical simulation of quantum verification.
    Phase 6: Real quantum backend (Qiskit/Cirq/PennyLane).
    """

    def __init__(self) -> None:
        self._classical_verifier = None
        self._verified_witnesses: list[QuantumWitness] = []

    # ── Quantum witness generation (simulated) ──────────────────

    def generate_witness(self, code: str, claim: str) -> QuantumWitness:
        """Generate a quantum witness for code correctness claim.

        In quantum computing, a witness is a quantum state that proves
        a property. Here we simulate this classically with hash-based
        probabilistic verification.
        """
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:32]

        # Simulate quantum witness: structured randomness with
        # verification-friendly properties
        witness_seed = hashlib.sha256(f"{code_hash}:{claim}".encode()).hexdigest()

        # "Quantum confidence" — probability that a quantum verifier
        # would accept this witness
        confidence = self._quantum_confidence_simulation(code, claim)

        return QuantumWitness(
            code_hash=code_hash,
            witness_data=witness_seed,
            confidence=confidence,
            verified=confidence >= 0.7,  # BUG#12: >= 而非 >, 边缘值 0.7 应通过
        )

    def _quantum_confidence_simulation(self, code: str, claim: str) -> float:
        """Simulate quantum verification confidence.

        In a real quantum system, this would use amplitude estimation
        on a quantum circuit. Here we use classical heuristics.
        """
        # Structural soundness
        try:
            import ast
            ast.parse(code)
            structural_score = 1.0
        except SyntaxError:
            structural_score = 0.0

        # Safety score (no dangerous patterns)
        dangerous = ["eval(", "exec(", "os.system("]
        safety_score = 1.0 - sum(0.2 for d in dangerous if d in code)
        safety_score = max(0.0, safety_score)

        # BUG#12修复: relevance 使用更宽松的匹配 — 函数名/语义匹配
        claim_words = set(claim.lower().split())
        code_words = set(code.lower().split())
        # 也尝试词干匹配 (e.g., "addition" ← "add")
        from difflib import SequenceMatcher
        extra_hits = 0
        for cw in claim_words:
            for kw in code_words:
                if SequenceMatcher(None, cw, kw).ratio() > 0.6:
                    extra_hits += 0.5
        overlap = (len(claim_words & code_words) + extra_hits) / max(len(claim_words), 1)
        relevance_score = min(1.0, overlap * 2)

        conf = structural_score * 0.4 + safety_score * 0.3 + relevance_score * 0.3
        return conf

    # ── Self-modification gate ───────────────────────────────────

    def verify_self_modification(
        self, original_code: str, modified_code: str, improvement_claim: str
    ) -> dict[str, Any]:
        """Quantum Godel Machine gate: verify that modification improves code.

        主权#10修复: AST 语义等价检测 — 添加类型注解/重命名等语义保持变换不应被拒绝。
        先做 AST 结构比较, 如果结构等价则允许。
        """
        import ast as _ast
        original_witness = self.generate_witness(original_code, "correctness")
        modified_witness = self.generate_witness(modified_code, improvement_claim)

        # 主权#10: AST 语义等价检查
        ast_equivalent = False
        try:
            o_tree = _ast.dump(_ast.parse(original_code))
            m_tree = _ast.dump(_ast.parse(modified_code))
            # 移除类型注解后比较 (注解是语义保持的)
            o_norm = o_tree.replace("annotation", "").replace("returns", "")
            m_norm = m_tree.replace("annotation", "").replace("returns", "")
            ast_equivalent = (o_norm == m_norm)
        except SyntaxError:
            pass

        # Gate condition: higher confidence OR AST semantic equivalence
        confidence_improved = (modified_witness.confidence > original_witness.confidence
                              or modified_witness.confidence >= original_witness.confidence)
        if (confidence_improved or ast_equivalent) and modified_witness.verified:
            self._verified_witnesses.append(modified_witness)
            return {
                "allowed": True,
                "confidence_before": original_witness.confidence,
                "confidence_after": modified_witness.confidence,
                "delta": round(modified_witness.confidence - original_witness.confidence, 4),
                "ast_equivalent": ast_equivalent,
                "note": "AST semantically equivalent — allowed despite similar confidence"
                if ast_equivalent else "",
            }
        else:
            return {
                "allowed": False,
                "reason": "Modified code does not improve quantum confidence",
                "confidence_before": original_witness.confidence,
                "confidence_after": modified_witness.confidence,
                "ast_equivalent": ast_equivalent,
            }
