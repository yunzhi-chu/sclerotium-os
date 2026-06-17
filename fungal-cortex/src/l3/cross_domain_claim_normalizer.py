"""Cross-Domain Claim Normalizer — 跨域Claim标准化器.

Biological Metaphor:
  The mycorrhizal network doesn't care whether a signal comes from an oak,
  pine, or birch — it encodes all signals in the same chemical language
  (ions, hormones, RNA). Similarly, our normalizer converts domain-specific
  claims into a universal StandardClaim format, enabling cross-domain debate.

  Just as fungal networks translate environmental cues (drought, pathogen,
  nutrient gradient) into a common electrical signal language, we translate
  finance/medical/legal/engineering claims into a unified verifiable format.

Key Innovation (v4.0):
  Unified claim format enabling cross-domain debate in the mycorrhizal network.
  Auto-domain detection from claim text. Bidirectional extraction from 6,067
  SKILL.md files to populate the debate ecosystem.

Domains supported:
  - Finance: "This stock will return >5% in 30 days"
  - Medical: "Patient has >70% risk of penicillin allergy"
  - Legal: "This clause violates Article X, Section Y"
  - Engineering: "This design meets seismic rating ≥8"
  - AI/ML: "Model achieves >95% on benchmark X"
  - Cybersecurity: "System vulnerable to CVE-2025-XXXXX"

References:
  - Fungal Cortex v3.0: 6,067 SKILL.md knowledge base
  - Baladi et al. (Nature Micro 2026): Cross-domain signal encoding in mycorrhizae
"""

from __future__ import annotations

import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class Domain(Enum):
    """Supported knowledge domains for claim normalization."""
    FINANCE = "finance"
    MEDICAL = "medical"
    LEGAL = "legal"
    ENGINEERING = "engineering"
    AI_ML = "ai_ml"
    CYBERSECURITY = "cybersecurity"
    GENERAL = "general"


@dataclass
class EvidenceItem:
    """A single piece of evidence attached to a standardized claim."""

    source: str                     # Source identifier (paper, skill, agent)
    content: str                    # Evidence description
    strength: float = 0.5           # 0-1 evidence strength
    direction: str = "support"      # "support" or "refute"
    reliability: float = 1.0        # Source reliability (0-1)
    staleness: float = 0.0          # Age penalty (0=new, 1=stale)
    timestamp: float = field(default_factory=time.time)


@dataclass
class StandardClaim:
    """Universal claim format for cross-domain debate.

    Any domain-specific claim is normalized to this format before
    entering the mycorrhizal debate network.
    """

    claim_id: str
    domain: Domain
    predicate: str                  # Falsifiable assertion
    confidence: float = 0.5         # Initial confidence [0, 1]
    evidence: list[EvidenceItem] = field(default_factory=list)
    counter_evidence: list[EvidenceItem] = field(default_factory=list)
    time_horizon_days: float = 30.0
    stakeholders: list[str] = field(default_factory=list)
    source_skill: str = ""          # Originating SKILL.md file
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @property
    def net_evidence(self) -> float:
        """Net evidence score: sum(support) - sum(refute)."""
        support = sum(e.strength * e.reliability for e in self.evidence)
        refute = sum(e.strength * e.reliability for e in self.counter_evidence)
        return support - refute

    @property
    def is_verifiable(self) -> bool:
        """A claim is verifiable if it has a clear predicate and at least one evidence item."""
        return bool(self.predicate) and (len(self.evidence) + len(self.counter_evidence) > 0)


@dataclass
class NormalizerConfig:
    """Configuration for the Cross-Domain Claim Normalizer."""

    default_domain: Domain = Domain.FINANCE
    max_claims_per_skill: int = 10
    domain_detection_confidence: float = 0.7
    supported_domains: list[str] = field(default_factory=lambda: [
        "finance", "medical", "legal", "engineering", "ai_ml", "cybersecurity"
    ])


# ═══════════════════════════════════════════════════════════════════════
# Domain Detection Patterns
# ═══════════════════════════════════════════════════════════════════════

DOMAIN_KEYWORDS: dict[Domain, list[str]] = {
    Domain.FINANCE: [
        "stock", "bond", "option", "futures", "forex", "dividend", "yield",
        "portfolio", "volatility", "sharpe", "drawdown", "alpha", "beta",
        "market", "trading", "exchange", "commodity", "derivative", "hedge",
        "arbitrage", "liquidity", "margin", "interest_rate", "inflation",
        "revenue", "earnings", "eps", "p/e", "market_cap", "ipo",
        "价格", "股票", "收益", "波动", "指数", "期货", "期权",
    ],
    Domain.MEDICAL: [
        "patient", "diagnosis", "symptom", "treatment", "drug", "dose",
        "clinical", "trial", "allergy", "infection", "surgery", "therapy",
        "prognosis", "mortality", "morbidity", "efficacy", "side_effect",
        "contraindication", "biomarker", "genomic", "pathology", "radiology",
        "患者", "诊断", "治疗", "药物", "手术", "过敏",
    ],
    Domain.LEGAL: [
        "clause", "contract", "statute", "regulation", "compliance", "liability",
        "jurisdiction", "precedent", "plaintiff", "defendant", "arbitration",
        "damages", "infringement", "patent", "copyright", "trademark",
        "indemnification", "breach", "force_majeure", "termination",
        "法律", "合同", "条款", "诉讼", "赔偿", "侵权",
    ],
    Domain.ENGINEERING: [
        "design", "specification", "load", "tolerance", "seismic", "structural",
        "thermal", "electrical", "mechanical", "stress", "strain", "fatigue",
        "reliability", "redundancy", "safety_factor", "throughput", "bandwidth",
        "latency", "fault_tolerance", "architecture", "api", "protocol",
        "设计", "工程", "结构", "抗震", "强度", "可靠性",
    ],
    Domain.AI_ML: [
        "model", "training", "inference", "accuracy", "precision", "recall",
        "f1_score", "loss", "gradient", "epoch", "batch", "embedding",
        "transformer", "attention", "neural_network", "deep_learning",
        "overfitting", "regularization", "hyperparameter", "fine_tuning",
        "benchmark", "dataset", "sota", "gpu", "tpu", "token",
        "模型", "训练", "精度", "推理", "神经网络", "嵌入",
    ],
    Domain.CYBERSECURITY: [
        "vulnerability", "exploit", "cve", "patch", "zero_day", "ransomware",
        "malware", "phishing", "ddos", "firewall", "encryption", "auth",
        "penetration_test", "threat_model", "attack_surface", "sandbox",
        "privilege_escalation", "sql_injection", "xss", "csrf", "backdoor",
        "漏洞", "攻击", "加密", "安全", "渗透", "防火墙",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# Core Normalizer
# ═══════════════════════════════════════════════════════════════════════


class CrossDomainClaimNormalizer:
    """Normalizes domain-specific claims into universal StandardClaim format.

    Like the mycorrhizal network translating diverse environmental signals
    into a common chemical language, this normalizer converts claims from
    finance, medical, legal, engineering, AI/ML, and cybersecurity domains
    into a unified format ready for cross-domain debate.

    Usage::

        normalizer = CrossDomainClaimNormalizer()
        claim = normalizer.normalize(
            "This stock will outperform the market by 5% in 30 days",
            confidence=0.7,
        )
        claims = normalizer.extract_from_skill(skill_md_text)
        domain = normalizer.detect_domain("Patient shows symptoms of...")
    """

    def __init__(self, config: NormalizerConfig | None = None) -> None:
        self._config = config or NormalizerConfig()
        self._logger = CortexLogger("claim_normalizer")

        self._claims: dict[str, StandardClaim] = {}
        self._domain_stats: dict[str, int] = {d.value: 0 for d in Domain}
        self._normalize_count: int = 0

        self._logger.info("normalizer_initialized",
                          default_domain=self._config.default_domain.value,
                          supported_domains=self._config.supported_domains)

    # ── Domain Detection ──────────────────────────────────────────────

    def detect_domain(self, text: str) -> tuple[Domain, float]:
        """Auto-detect the domain of a claim from its text content.

        Uses keyword frequency + domain-specific pattern matching.
        Returns (domain, confidence).

        Args:
            text: Claim text to classify

        Returns:
            (detected_domain, confidence_score) tuple
        """
        text_lower = text.lower()
        domain_scores: dict[Domain, float] = {}

        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = 0.0
            hits = 0
            for kw in keywords:
                if kw.lower() in text_lower:
                    hits += 1
                    # Weight longer keyword matches higher
                    score += len(kw) * 0.1

            if hits > 0:
                # Normalize by total keyword count for this domain
                domain_scores[domain] = score / len(keywords)

        if not domain_scores:
            return self._config.default_domain, 0.0

        # Best matching domain
        best_domain = max(domain_scores, key=domain_scores.get)
        best_score = domain_scores[best_domain]

        # Confidence: how much better than second best?
        if len(domain_scores) > 1:
            sorted_scores = sorted(domain_scores.values(), reverse=True)
            margin = sorted_scores[0] - sorted_scores[1]
            confidence = min(1.0, best_score + margin)
        else:
            confidence = best_score

        return best_domain, confidence

    # ── Claim Normalization ───────────────────────────────────────────

    def normalize(
        self,
        raw_claim: Any,
        domain: Domain | None = None,
        confidence: float = 0.5,
        source_skill: str = "",
    ) -> StandardClaim:
        """Normalize a raw claim into the universal StandardClaim format.

        Accepts strings, dicts, or structured claim objects and converts
        them to the standard format used by the mycorrhizal debate network.

        Args:
            raw_claim: Raw claim — can be str, dict, or StandardClaim
            domain: Optional domain override (auto-detected if None)
            confidence: Initial confidence in the claim
            source_skill: Originating SKILL.md path (if applicable)

        Returns:
            Normalized StandardClaim ready for debate
        """
        # Already normalized
        if isinstance(raw_claim, StandardClaim):
            self._claims[raw_claim.claim_id] = raw_claim
            return raw_claim

        claim_id = str(uuid.uuid4())[:12]

        # Extract predicate and metadata from different input formats
        if isinstance(raw_claim, str):
            predicate = raw_claim.strip()
            metadata: dict[str, Any] = {"raw_text": raw_claim}
        elif isinstance(raw_claim, dict):
            predicate = raw_claim.get("predicate", raw_claim.get("claim", raw_claim.get("text", "")))
            confidence = float(raw_claim.get("confidence", confidence))
            metadata = raw_claim.get("metadata", {"raw_dict": raw_claim})
        else:
            predicate = str(raw_claim)
            metadata = {"raw_type": type(raw_claim).__name__}

        # Detect domain if not specified
        if domain is None:
            domain, domain_confidence = self.detect_domain(predicate)
            if domain_confidence < self._config.domain_detection_confidence:
                domain = self._config.default_domain
        else:
            domain_confidence = 1.0

        # Extract time horizon from predicate (e.g., "in 30 days", "within 24 hours")
        time_horizon = self._extract_time_horizon(predicate)

        # Extract stakeholders
        stakeholders = self._extract_stakeholders(predicate, domain)

        claim = StandardClaim(
            claim_id=claim_id,
            domain=domain,
            predicate=predicate,
            confidence=confidence,
            time_horizon_days=time_horizon,
            stakeholders=stakeholders,
            source_skill=source_skill,
            metadata={"domain_confidence": domain_confidence, **metadata},
        )

        self._claims[claim_id] = claim
        self._domain_stats[domain.value] = self._domain_stats.get(domain.value, 0) + 1
        self._normalize_count += 1

        self._logger.debug("claim_normalized",
                           claim_id=claim_id,
                           domain=domain.value,
                           confidence=round(domain_confidence, 3))

        return claim

    def normalize_batch(
        self,
        raw_claims: list[Any],
        domain: Domain | None = None,
    ) -> list[StandardClaim]:
        """Normalize a batch of raw claims."""
        return [self.normalize(c, domain=domain) for c in raw_claims]

    # ── Skill Extraction ──────────────────────────────────────────────

    def extract_from_skill(self, skill_text: str, skill_path: str = "") -> list[StandardClaim]:
        """Extract verifiable claims from a SKILL.md file.

        Scans the markdown text for assertion patterns and converts
        each into a standardized claim ready for debate.

        Args:
            skill_text: Full text content of a SKILL.md file
            skill_path: Path to the skill file (for traceability)

        Returns:
            List of extracted StandardClaims
        """
        claims: list[StandardClaim] = []
        c = self._config

        # Detect domain from skill text
        detected_domain, _ = self.detect_domain(skill_text)

        # Pattern 1: Explicit claims marked with "Claim:" or "断言:"
        claim_pattern = re.compile(
            r'(?:Claim|断言|CLAIM)\s*[:：]\s*(.+?)(?:\n|$)',
            re.IGNORECASE | re.MULTILINE,
        )
        for match in claim_pattern.finditer(skill_text):
            if len(claims) >= c.max_claims_per_skill:
                break
            predicate = match.group(1).strip()
            if predicate:
                claim = self.normalize(
                    predicate,
                    domain=detected_domain,
                    source_skill=skill_path,
                )
                claims.append(claim)

        # Pattern 2: "X should Y" or "X must Y" patterns (normative claims)
        if len(claims) < c.max_claims_per_skill:
            normative_pattern = re.compile(
                r'(\w+(?:\s+\w+){2,20})\s+(should|must|shall|requires?|needs? to)\s+(.{10,200}?)(?:\.|$|\n)',
                re.IGNORECASE,
            )
            for match in normative_pattern.finditer(skill_text):
                if len(claims) >= c.max_claims_per_skill:
                    break
                predicate = f"{match.group(1)} {match.group(2)} {match.group(3)}".strip()
                claim = self.normalize(
                    predicate,
                    domain=detected_domain,
                    confidence=0.4,  # Lower confidence for auto-extracted claims
                    source_skill=skill_path,
                )
                claims.append(claim)

        # Pattern 3: "When X, then Y" or "If X, then Y" (conditional claims)
        if len(claims) < c.max_claims_per_skill:
            conditional_pattern = re.compile(
                r'(?:when|if|当|如果)\s+(.{10,100}?)\s*[,，]\s*(?:then|则|那么)\s+(.{10,200}?)(?:\.|$|\n)',
                re.IGNORECASE,
            )
            for match in conditional_pattern.finditer(skill_text):
                if len(claims) >= c.max_claims_per_skill:
                    break
                predicate = f"If {match.group(1)}, then {match.group(2)}".strip()
                claim = self.normalize(
                    predicate,
                    domain=detected_domain,
                    confidence=0.35,
                    source_skill=skill_path,
                )
                claims.append(claim)

        self._logger.debug("claims_extracted_from_skill",
                           skill=skill_path,
                           claim_count=len(claims),
                           domain=detected_domain.value)

        return claims

    # ── Helper Methods ────────────────────────────────────────────────

    def _extract_time_horizon(self, text: str) -> float:
        """Extract time horizon in days from claim text."""
        patterns = [
            (r'(\d+)\s*days?', 1.0),
            (r'(\d+)\s*weeks?', 7.0),
            (r'(\d+)\s*months?', 30.0),
            (r'(\d+)\s*years?', 365.0),
            (r'(\d+)\s*hours?', 1.0 / 24.0),
            (r'(\d+)\s*分钟', 1.0 / 1440.0),
            (r'(\d+)\s*小时', 1.0 / 24.0),
            (r'(\d+)\s*天', 1.0),
            (r'(\d+)\s*周', 7.0),
            (r'(\d+)\s*月', 30.0),
        ]
        for pattern, multiplier in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1)) * multiplier
        return 30.0  # Default 30 days

    def _extract_stakeholders(self, text: str, domain: Domain) -> list[str]:
        """Extract stakeholder roles from claim context."""
        role_patterns = {
            Domain.FINANCE: ["investor", "trader", "analyst", "regulator", "broker", "fund_manager"],
            Domain.MEDICAL: ["patient", "doctor", "nurse", "pharmacist", "hospital", "insurer"],
            Domain.LEGAL: ["plaintiff", "defendant", "judge", "attorney", "legislator", "regulator"],
            Domain.ENGINEERING: ["architect", "engineer", "contractor", "inspector", "client", "user"],
            Domain.AI_ML: ["researcher", "engineer", "data_scientist", "mlops", "product_manager", "user"],
            Domain.CYBERSECURITY: ["analyst", "engineer", "auditor", "ciso", "developer", "admin"],
        }

        roles = role_patterns.get(domain, ["stakeholder"])
        found = [r for r in roles if r.lower() in text.lower()]
        return found if found else ["unknown"]

    # ── Query Methods ─────────────────────────────────────────────────

    def get_claim(self, claim_id: str) -> StandardClaim | None:
        """Retrieve a normalized claim by ID."""
        return self._claims.get(claim_id)

    def get_claims_by_domain(self, domain: Domain) -> list[StandardClaim]:
        """Get all normalized claims in a specific domain."""
        return [c for c in self._claims.values() if c.domain == domain]

    def get_verifiable_claims(self) -> list[StandardClaim]:
        """Get claims that have evidence and can be debated."""
        return [c for c in self._claims.values() if c.is_verifiable]

    # ── Properties ────────────────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "normalize_count": self._normalize_count,
            "stored_claims": len(self._claims),
            "by_domain": dict(self._domain_stats),
            "verifiable_count": len(self.get_verifiable_claims()),
            "default_domain": self._config.default_domain.value,
            "max_claims_per_skill": self._config.max_claims_per_skill,
        }

    def reset(self) -> None:
        """Reset the normalizer state."""
        self._claims.clear()
        self._domain_stats = {d.value: 0 for d in Domain}
        self._normalize_count = 0
        self._logger.debug("normalizer_reset")
