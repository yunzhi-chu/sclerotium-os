"""L3: Mycorrhizal Debate Network — 菌根辩论网络 (Phase 2 v4.0).

Biological Metaphor:
  Forest underground mycorrhizal network — Mother Tree Hub → fungal channels
  → sapling carbon transfer. Claims propagate like disease warnings through
  the fungal network: each connected node (tree) is both a consumer and
  forwarder of information.

Key Innovation (v4.0):
  Distributed claim propagation replacing centralized Market-of-Claims auction.
  MNIS (Mycelial Network Intelligence Score) — 8 orthogonal parameters → 0-1
  health score with 91.8% predictive accuracy, 42-day early warning (Baladi 2026).
  Neutrosophic (T,I,F) three-dimensional causal validation replacing Boolean logic.
  Cross-domain claim normalization from 6,067 skills.

Sub-modules:
  - MycorrhizalDebateNetwork: Distributed debate propagation + MNIS scoring
  - NeutrosophicCausalValidator: (T,I,F) three-dimensional truth verification
  - CrossDomainClaimNormalizer: Unified claim format across 6+ domains

References (2025-2026):
  - Baladi et al. (Nature Micro 2026): MNIS framework, 91.8% accuracy
  - Barbosa & Smarandache (June 2025): Neutrosophic causal AI
  - Mycel Network (Zenodo 2026): 70-day Stigmergy governance experiment
"""

from __future__ import annotations

from src.l3.mycorrhizal_debate_network import (
    MycorrhizalDebateNetwork,
    DebateNode,
    ClaimPropagation,
    NetworkTopology,
    ConsensusState,
    DebateNetworkConfig,
)
from src.l3.neutrosophic_causal_validator import (
    NeutrosophicCausalValidator,
    NeutrosophicVerdict,
    CausalIntervention,
    ValidatorConfig,
)
from src.l3.cross_domain_claim_normalizer import (
    CrossDomainClaimNormalizer,
    StandardClaim,
    Domain,
    EvidenceItem,
    NormalizerConfig,
)

__all__ = [
    # Mycorrhizal Debate Network
    "MycorrhizalDebateNetwork",
    "DebateNode",
    "ClaimPropagation",
    "NetworkTopology",
    "ConsensusState",
    "DebateNetworkConfig",
    # Neutrosophic Causal Validator
    "NeutrosophicCausalValidator",
    "NeutrosophicVerdict",
    "CausalIntervention",
    "ValidatorConfig",
    # Cross-Domain Claim Normalizer
    "CrossDomainClaimNormalizer",
    "StandardClaim",
    "Domain",
    "EvidenceItem",
    "NormalizerConfig",
]
