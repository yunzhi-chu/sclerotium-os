"""Phase 2 Mycorrhizal Bridge — L3 Debate → L5 Stigmergy Field integration.

This bridge is the "mycorrhizal hypha" connecting the v4.0 L3 debate network
to the v5.0 stigmergy field, enabling:
  - Claims normalized via L3 → deposited as traces in L5 field
  - Debate consensus → stigmergy trace quality scoring
  - Neutrosophic validation → behavioral trust signals
  - Swarm phase → debate topology adaptation

Architecture:
  Claim → L3 Normalizer → L3 Debate Network → L3 Validator
       → L5 Trace Grid → L5 Citation Graph → L5 Trust Scoring
       → L5 Swarm Phase ← debate topology feedback

The bridge runs alongside the existing v3.0 ClaimDebateBridge and
PDE-based StigmergyField without replacing them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.config import L3Config, L5Config, get_config
from src.l3.mycorrhizal_debate_network import (
    ClaimPropagation,
    ConsensusState,
    DebateNetworkConfig,
    DebateNode,
    MycorrhizalDebateNetwork,
    NetworkTopology,
)
from src.l3.neutrosophic_causal_validator import (
    NeutrosophicCausalValidator,
    NeutrosophicVerdict,
    ValidatorConfig,
)
from src.l3.cross_domain_claim_normalizer import (
    CrossDomainClaimNormalizer,
    Domain,
    EvidenceItem,
    NormalizerConfig,
    StandardClaim,
)
from src.l5.stigmergy_field_v2 import (
    CitationEdge,
    ResilienceReport,
    StigmergyFieldV2,
    StigmergyV2Config,
    TraceEntry,
    TrustScore,
)
from src.l5.swarm_self_organizer import (
    NucleationSite,
    PhotormoneField,
    SwarmOrganizerConfig,
    SwarmPhase,
    SwarmSelfOrganizer,
)
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class DebatePath(Enum):
    """Which debate path was used."""
    V3_MARKET = "v3_market"          # Old BULL/BEAR auction
    V4_MYCORRHIZAL = "v4_mycorrhizal"  # New distributed debate
    HYBRID = "hybrid"                  # Both paths fused


@dataclass
class Phase2Result:
    """Complete Phase 2 processing result from L3 debate + L5 stigmergy."""

    claim_id: str
    normalized_claim: StandardClaim
    propagation: ClaimPropagation | None = None
    consensus: ConsensusState = ConsensusState.PENDING
    verdict: NeutrosophicVerdict | None = None
    trace: TraceEntry | None = None
    citation: CitationEdge | None = None
    trust_score: TrustScore | None = None
    debate_path: DebatePath = DebatePath.V4_MYCORRHIZAL
    mnis: float = 0.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════
# Core Bridge
# ═══════════════════════════════════════════════════════════════════════


class Phase2MycorrhizalBridge:
    """Bridge connecting v4.0 L3 debate + L5 stigmergy to the pipeline.

    This is the primary integration point for Phase 2. It:
      - Normalizes raw claims through L3 CrossDomainClaimNormalizer
      - Propagates claims through L3 MycorrhizalDebateNetwork
      - Validates claims with L3 NeutrosophicCausalValidator
      - Deposits validated claims as traces in L5 StigmergyFieldV2
      - Builds citation edges between related traces
      - Scores behavioral trust for participating agents
      - Feeds swarm phase back to debate topology

    Usage::

        bridge = Phase2MycorrhizalBridge()
        await bridge.initialize()

        # Process a claim
        result = await bridge.process_claim(
            "This stock will return >5% in 30 days",
            agent_id="agent-1",
            evidence=[{"strength": 0.8, "direction": "support"}],
        )

        # Check consensus
        print(result.consensus)  # VERIFIED or REJECTED

        await bridge.shutdown()
    """

    def __init__(
        self,
        l3_config: L3Config | None = None,
        l5_config: L5Config | None = None,
        enable_validator: bool = True,
        enable_swarm: bool = True,
    ) -> None:
        self._logger = CortexLogger("phase2_bridge")

        # Load config
        app_config = get_config()
        l3_cfg = l3_config or app_config.l3
        l5_cfg = l5_config or app_config.l5

        self._enable_validator = enable_validator
        self._enable_swarm = enable_swarm

        # --- L3: Cross-Domain Claim Normalizer ---
        self._normalizer = CrossDomainClaimNormalizer(NormalizerConfig(
            default_domain=Domain(l3_cfg.cdn_default_domain),
            max_claims_per_skill=l3_cfg.cdn_max_claims_per_skill,
            domain_detection_confidence=l3_cfg.cdn_domain_detection_confidence,
            supported_domains=list(l3_cfg.cdn_supported_domains),
        ))

        # --- L3: Mycorrhizal Debate Network ---
        topology_map = {
            "hub_spoke": NetworkTopology.HUB_SPOKE,
            "mesh": NetworkTopology.MESH,
            "small_world": NetworkTopology.SMALL_WORLD,
        }
        self._debate_network = MycorrhizalDebateNetwork(DebateNetworkConfig(
            topology=topology_map.get(l3_cfg.mdn_topology, NetworkTopology.SMALL_WORLD),
            hub_count=l3_cfg.mdn_hub_count,
            mesh_degree=l3_cfg.mdn_mesh_degree,
            small_world_rewiring=l3_cfg.mdn_small_world_rewiring,
            consensus_threshold=l3_cfg.mdn_consensus_threshold,
            mnis_weights=list(l3_cfg.mdn_mnis_weights),
            propagation_max_hops=l3_cfg.mdn_propagation_steps,
            nutrient_decay=l3_cfg.mdn_nutrient_decay,
        ))

        # --- L3: Neutrosophic Causal Validator ---
        self._validator = NeutrosophicCausalValidator(ValidatorConfig(
            accept_truth=l3_cfg.ncv_accept_t,
            accept_falsity=l3_cfg.ncv_accept_f,
            accept_indeterminacy=l3_cfg.ncv_accept_i,
            do_samples=l3_cfg.ncv_do_intervention_samples,
            merge_method=l3_cfg.ncv_merge_method,
        )) if enable_validator else None

        # --- L5: Stigmergy Field V2 ---
        self._stigmergy = StigmergyFieldV2(StigmergyV2Config(
            trace_grid_size=l5_cfg.stg_trace_grid_size,
            citation_halflife_hours=l5_cfg.stg_citation_halflife_hours,
            niche_overlap_threshold=l5_cfg.stg_niche_overlap_threshold,
            trust_history_window=l5_cfg.stg_trust_history_window,
            trust_citation_weight=l5_cfg.stg_trust_citation_weight,
            trust_consistency_weight=l5_cfg.stg_trust_consistency_weight,
            trust_contribution_weight=l5_cfg.stg_trust_contribution_weight,
            resilience_bad_actor_ratio=l5_cfg.stg_resilience_bad_actor_ratio,
            norm_propagation_threshold=l5_cfg.stg_norm_propagation_threshold,
            max_trace_age_days=l5_cfg.stg_max_trace_age_days,
        ))

        # --- L5: Swarm Self-Organizer ---
        self._swarm = SwarmSelfOrganizer(SwarmOrganizerConfig(
            cooperation_default=l5_cfg.sso_cooperation_default,
            deposition_default=l5_cfg.sso_deposition_default,
            nucleation_threshold=l5_cfg.sso_nucleation_threshold,
            phase_hysteresis=l5_cfg.sso_phase_hysteresis,
            photormone_decay_rate=l5_cfg.sso_photormone_decay_rate,
        )) if enable_swarm else None

        # --- State ---
        self._initialized: bool = False
        self._process_count: int = 0
        self._results: list[Phase2Result] = []

        # Default debate nodes (one per domain)
        self._default_node_domains = ["finance", "medical", "legal", "engineering", "ai_ml", "cybersecurity"]

        self._logger.info("phase2_bridge_created",
                          enable_validator=enable_validator,
                          enable_swarm=enable_swarm,
                          topology=l3_cfg.mdn_topology,
                          consensus_threshold=l3_cfg.mdn_consensus_threshold)

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the Phase 2 bridge. Creates default debate nodes."""
        self._initialized = True

        # Create default debate nodes (one per domain)
        for i, domain in enumerate(self._default_node_domains):
            node = DebateNode(
                node_id=f"node-{domain}",
                domain=domain,
                nutrient_score=0.6 + i * 0.05,
                specialization=domain,
            )
            self._debate_network.add_node(node)

        # Build topology
        self._debate_network.build_topology()

        self._logger.info("phase2_bridge_initialized",
                          nodes=len(self._debate_network.nodes),
                          domains=self._default_node_domains)

    async def shutdown(self) -> None:
        """Gracefully shutdown the Phase 2 bridge."""
        self._initialized = False
        self._logger.info("phase2_bridge_shutdown",
                          total_processed=self._process_count)

    # ── Main Processing Pipeline ──────────────────────────────────────

    async def process_claim(
        self,
        raw_claim: Any,
        agent_id: str = "unknown",
        evidence: list[dict[str, Any]] | None = None,
        domain: Domain | None = None,
        parent_trace_id: str | None = None,
    ) -> Phase2Result:
        """Process a claim through the full L3→L5 pipeline.

        This is the MAIN entry point for Phase 2 integration.

        Flow:
          1. Normalize claim (L3 CrossDomainClaimNormalizer)
          2. Propagate through debate network (L3 MycorrhizalDebateNetwork)
          3. Validate with neutrosophic logic (L3 Validator)
          4. Deposit as stigmergy trace (L5 StigmergyFieldV2)
          5. Create citation edge if building on prior trace (L5)
          6. Score behavioral trust (L5)

        Args:
            raw_claim: Raw claim (str, dict, or StandardClaim)
            agent_id: ID of the agent making this claim
            evidence: List of evidence items
            domain: Optional domain override
            parent_trace_id: If building on a prior trace, cite it

        Returns:
            Phase2Result with all L3/L5 processing outputs
        """
        t_start = time.time()
        self._process_count += 1

        # Step 1: Normalize
        normalized = self._normalizer.normalize(raw_claim, domain=domain)

        # Step 2: Add evidence to normalized claim
        if evidence:
            for ev in evidence:
                item = EvidenceItem(
                    source=agent_id,
                    content=ev.get("content", ""),
                    strength=float(ev.get("strength", 0.5)),
                    direction=ev.get("direction", "support"),
                    reliability=float(ev.get("reliability", 1.0)),
                )
                if item.direction == "support":
                    normalized.evidence.append(item)
                else:
                    normalized.counter_evidence.append(item)

        # Step 3: Propagate through debate network
        claim_dict = {
            "claim_id": normalized.claim_id,
            "topic": normalized.domain.value,
            "predicate": normalized.predicate,
            "confidence": normalized.confidence,
        }
        propagation = self._debate_network.propagate_claim(
            claim_dict,
            source_node_id=f"node-{normalized.domain.value}",
        )

        # Step 4: Detect consensus
        consensus = self._debate_network.detect_consensus(normalized.claim_id)

        # Step 5: Validate with neutrosophic logic
        verdict = None
        if self._validator is not None:
            verdict = self._validator.validate(
                claim_dict,
                evidence or [],
                validator_id=agent_id,
            )

        # Step 6: Deposit as stigmergy trace
        import hashlib
        content_hash = hashlib.md5(normalized.predicate.encode()).hexdigest()[:16]
        trace = self._stigmergy.append_trace(
            agent_id=agent_id,
            action_type=f"claim_{normalized.domain.value}",
            content_hash=content_hash,
            quality_score=normalized.confidence,
            evidence_refs=[e.source for e in normalized.evidence],
        )

        # Step 7: Create citation edge
        citation = None
        if parent_trace_id is not None:
            citation = self._stigmergy.cite_trace(
                parent_trace_id=parent_trace_id,
                citing_agent_id=agent_id,
                child_trace_id=trace.trace_id,
            )

        # Step 8: Score behavioral trust
        trust_score = self._stigmergy.score_trust(agent_id)

        # Step 9: Update swarm field with claim position
        if self._swarm is not None:
            # Deposit photormone at a position based on claim domain
            domain_positions = {
                "finance": (0.5, 0.8),
                "medical": (0.3, 0.3),
                "legal": (0.7, 0.2),
                "engineering": (0.8, 0.7),
                "ai_ml": (0.6, 0.5),
                "cybersecurity": (0.2, 0.7),
            }
            pos = domain_positions.get(normalized.domain.value, (0.5, 0.5))
            self._swarm.mark(pos, intensity=normalized.confidence)

        # Step 10: Compute MNIS
        mnis = self._debate_network.compute_mnis()

        # Build result
        latency = (time.time() - t_start) * 1000.0

        result = Phase2Result(
            claim_id=normalized.claim_id,
            normalized_claim=normalized,
            propagation=propagation,
            consensus=consensus,
            verdict=verdict,
            trace=trace,
            citation=citation,
            trust_score=trust_score,
            debate_path=DebatePath.V4_MYCORRHIZAL,
            mnis=mnis,
            latency_ms=round(latency, 2),
            metadata={
                "agent_id": agent_id,
                "domain": normalized.domain.value,
                "evidence_count": len(evidence or []),
            },
        )

        self._results.append(result)

        self._logger.debug("phase2_processed",
                           claim_id=normalized.claim_id,
                           consensus=consensus.value,
                           mnis=round(mnis, 3),
                           trust=round(trust_score.composite, 3) if trust_score else None,
                           latency_ms=round(latency, 2))

        return result

    async def process_claims_batch(
        self,
        claims: list[dict[str, Any]],
        agent_id: str = "batch",
    ) -> list[Phase2Result]:
        """Process a batch of claims."""
        results: list[Phase2Result] = []
        for claim_data in claims:
            result = await self.process_claim(
                claim_data.get("claim"),
                agent_id=claim_data.get("agent_id", agent_id),
                evidence=claim_data.get("evidence"),
                domain=claim_data.get("domain"),
                parent_trace_id=claim_data.get("parent_trace_id"),
            )
            results.append(result)
        return results

    # ── Swarm Control ─────────────────────────────────────────────────

    def set_swarm_phase(self, phase: SwarmPhase) -> None:
        """Set the swarm to a specific phase.

        BUILD → agents construct (deposit traces + cooperate)
        PATROL → agents explore (cooperate, don't deposit)
        AGGREGATE → agents cluster (deposit, don't cooperate)
        DISMANTLE → agents clean up (neither deposit nor cooperate)
        """
        if self._swarm is not None:
            self._swarm.switch_phase(phase)

            # Feedback: swarm phase affects debate topology
            if phase == SwarmPhase.BUILD:
                # Build phase: use small-world for efficient structured debate
                self._debate_network._config.topology = NetworkTopology.SMALL_WORLD
            elif phase == SwarmPhase.DISMANTLE:
                # Dismantle: use hub-spoke for fast broadcast
                self._debate_network._config.topology = NetworkTopology.HUB_SPOKE

            self._logger.info("swarm_phase_set", phase=phase.value)

    def step_swarm(self) -> None:
        """Advance the swarm photormone field one step."""
        if self._swarm is not None:
            self._swarm.step_field()
            self._swarm.nucleate_structure()

    # ── Legacy Compatibility ──────────────────────────────────────────

    def to_legacy_claim(self, result: Phase2Result) -> dict[str, Any]:
        """Convert Phase 2 result to v3.0 ClaimDebateBridge-compatible format.

        The v3.0 ClaimDebateBridge expects: claim_id, topic, description,
        bull_arguments, bear_arguments, status, field_strength.
        """
        # Map consensus to v3.0 ClaimStatus
        status_map = {
            ConsensusState.VERIFIED: "resolved_bull",
            ConsensusState.REJECTED: "resolved_bear",
            ConsensusState.STALEMATE: "stalemate",
            ConsensusState.EXCRETED: "excreted",
            ConsensusState.PENDING: "open",
        }

        bull_score = 0.0
        bear_score = 0.0

        if result.verdict:
            bull_score = result.verdict.truth
            bear_score = result.verdict.falsity
        elif result.consensus == ConsensusState.VERIFIED:
            bull_score = 0.8
        elif result.consensus == ConsensusState.REJECTED:
            bear_score = 0.8

        return {
            "claim_id": result.claim_id,
            "topic": result.normalized_claim.domain.value,
            "description": result.normalized_claim.predicate,
            "bull_arguments": [
                {"content": result.normalized_claim.predicate, "evidence_strength": bull_score}
            ] if bull_score > 0 else [],
            "bear_arguments": [
                {"content": f"Refutation of: {result.normalized_claim.predicate}", "evidence_strength": bear_score}
            ] if bear_score > 0 else [],
            "status": status_map.get(result.consensus, "open"),
            "bull_score": bull_score,
            "bear_score": bear_score,
            "field_strength": result.normalized_claim.confidence,
        }

    def to_mnis_health(self) -> dict[str, float]:
        """Export MNIS health report for monitoring systems."""
        mnis = self._debate_network.compute_mnis()
        history = self._debate_network._mnis_history
        return {
            "current_mnis": mnis,
            "trend": history[-1]["mnis"] - history[-2]["mnis"] if len(history) >= 2 else 0.0,
            "node_count": len(self._debate_network.nodes),
            "claim_count": len(self._debate_network.claims),
        }

    # ── Direct Access ─────────────────────────────────────────────────

    def register_debate_node(self, node_id: str, domain: str, nutrient: float = 0.5) -> None:
        """Register a new debate node in the network."""
        node = DebateNode(
            node_id=node_id,
            domain=domain,
            nutrient_score=nutrient,
            specialization=domain,
        )
        self._debate_network.add_node(node)

    def extract_claims_from_skill(self, skill_text: str, skill_path: str = "") -> list[StandardClaim]:
        """Extract claims from a SKILL.md file."""
        return self._normalizer.extract_from_skill(skill_text, skill_path)

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def normalizer(self) -> CrossDomainClaimNormalizer:
        return self._normalizer

    @property
    def debate_network(self) -> MycorrhizalDebateNetwork:
        return self._debate_network

    @property
    def validator(self) -> NeutrosophicCausalValidator | None:
        return self._validator

    @property
    def stigmergy(self) -> StigmergyFieldV2:
        return self._stigmergy

    @property
    def swarm(self) -> SwarmSelfOrganizer | None:
        return self._swarm

    @property
    def stats(self) -> dict[str, Any]:
        """Bridge-level statistics aggregating all Phase 2 components."""
        stats: dict[str, Any] = {
            "initialized": self._initialized,
            "process_count": self._process_count,
            "enable_validator": self._enable_validator,
            "enable_swarm": self._enable_swarm,
            "l3_normalizer": self._normalizer.stats,
            "l3_debate": self._debate_network.stats,
            "l5_stigmergy": self._stigmergy.stats,
        }
        if self._validator is not None:
            stats["l3_validator"] = self._validator.stats
        if self._swarm is not None:
            stats["l5_swarm"] = self._swarm.stats
        if self._results:
            last = self._results[-1]
            stats["last_result"] = {
                "claim_id": last.claim_id,
                "consensus": last.consensus.value,
                "mnis": round(last.mnis, 4),
                "latency_ms": last.latency_ms,
            }
        return stats

    def reset(self) -> None:
        """Reset all Phase 2 components."""
        self._normalizer.reset()
        self._debate_network.reset()
        if self._validator is not None:
            self._validator.reset()
        self._stigmergy.reset()
        if self._swarm is not None:
            self._swarm.reset()
        self._process_count = 0
        self._results.clear()
        self._logger.debug("phase2_bridge_reset")
