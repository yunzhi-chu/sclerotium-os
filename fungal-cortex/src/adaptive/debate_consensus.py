"""L3/2.3: DebateConsensusEngine — "免疫突触 + 耐受机制" (Immunological Synapse + Tolerance).

Biological Metaphor:
  免疫突触(Immunological Synapse)——T细胞与APC之间的分子界面
  双方通过多种受体-配体对进行"对话", 最终决定激活或耐受

  机制:
  - 3-5个独立验证Agent(每个来自不同专业):
    如同T细胞激活需要三个信号:
    信号1: TCR-MHC-肽段(抗原识别)
    信号2: CD28-B7(共刺激)
    信号3: 细胞因子(环境上下文)
    三个信号都通过→T细胞激活; 缺任意一个→耐受(anergy)

  - 逆智慧定律防护(Inverse-Wisdom Law):
    Tribalism检测: 同专业占比>60%→稀释权重
      如同免疫系统需要多种免疫细胞(Th1/Th2/Th17/Treg)协作,
      任何单一类型过度增殖=淋巴增生性疾病
    Sycophancy监控: 权重>0.7→警告
      如同Treg细胞过度活跃→免疫抑制(对一切都不反应)
    Heterogeneity Mandate: 至少3个不同专业
      如同免疫系统的多样性是健康的基础

  - 综合判定(如同免疫决策):
    ≥2/3验证通过→确认(免疫激活: Th细胞决定"这确实是病原体")
    ≥2/3驳倒→拒绝(免疫耐受: Treg细胞决定"这是自己人")
    其他→搁置("需要更多树突状细胞采集抗原信息")

Reference:
  Inverse-Wisdom Law (arXiv 2604.27274, April 2026);
  LAC-MAS (arXiv 2605.00691, May 2026)
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


# ── Data Classes ────────────────────────────────────────────────────────

@dataclass
class VerificationAgent:
    """An independent verification agent — like a distinct immune cell type.

    Each agent represents a different "specialty" or perspective,
    analogous to different T cell subsets (Th1, Th2, Th17, Treg, CTL).
    """

    agent_id: str
    specialty: str  # "fundamental", "technical", "sentiment", "risk", "macro"
    perspective_weight: float  # 0-1, importance of this perspective
    verification_history: list[dict[str, Any]] = field(default_factory=list)
    accuracy: float = 0.5  # historical verification accuracy
    total_verifications: int = 0
    correct_verifications: int = 0


@dataclass
class ImmuneSynapse:
    """The immunological synapse between a claim and its verifiers.

    Like the organized molecular interface between a T cell and an APC,
    where receptors, co-receptors, adhesion molecules, and signaling
    molecules cluster into a structured contact zone.
    """

    claim_id: str
    signal_1_strength: float  # TCR-MHC-peptide recognition strength
    signal_2_strength: float  # CD28-B7 co-stimulation strength
    signal_3_strength: float  # Cytokine context signal strength
    verifier_votes: dict[str, str]  # agent_id → "verify"/"refute"/"abstain"
    final_decision: str  # "activate" (confirm), "tolerate" (reject), "anergy" (defer)
    synapse_stability: float  # 0-1, how stable the synaptic contact is
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConsensusReport:
    """Complete consensus determination report."""

    claim_id: str
    total_verifiers: int
    verify_count: int
    refute_count: int
    abstain_count: int
    consensus_reached: bool
    decision: str  # "confirmed", "refuted", "deferred"
    confidence: float  # 0-1
    tribalism_detected: bool
    sycophancy_detected: bool
    heterogeneity_score: float  # 0-1, diversity of verifier specialties
    immune_synapse: ImmuneSynapse | None = None
    minority_report: str | None = None  # dissenting opinion if close vote
    timestamp: float = field(default_factory=time.time)


class DebateConsensusEngine:
    """Multi-agent debate consensus engine — the immunological synapse.

    The "lymph node germinal center" of the adaptive engine — where
    T cells (verification agents) form immunological synapses with
    APCs (claims), integrating three signals to decide activation vs tolerance.

    Architecture:
      - 3-5 independent verification agents with diverse specialties
      - Three-signal model: Antigen recognition + Co-stimulation + Cytokine context
      - Inverse-Wisdom Law protections: anti-tribalism, anti-sycophancy, heterogeneity
      - Consensus: ≥2/3 verify → confirm, ≥2/3 refute → reject, else defer
    """

    MIN_VERIFIERS = 3
    MAX_VERIFIERS = 5
    CONSENSUS_THRESHOLD = 2.0 / 3.0  # ≥2/3 for consensus

    # Inverse-Wisdom Law thresholds
    TRIBALISM_THRESHOLD = 0.6  # >60% same specialty → tribalism risk
    SYCOPHANCY_THRESHOLD = 0.7  # single agent weight >0.7 → sycophancy
    HETEROGENEITY_MIN = 3  # minimum distinct specialties for valid debate

    # Three-signal thresholds
    SIGNAL_1_THRESHOLD = 0.3  # min TCR-MHC-peptide recognition
    SIGNAL_2_THRESHOLD = 0.2  # min co-stimulation
    SIGNAL_3_THRESHOLD = 0.15  # min cytokine context

    SPECIALTIES = [
        "fundamental",    # Th1 — cellular immunity, macro/fundamental analysis
        "technical",      # Th2 — humoral immunity, price/indicator analysis
        "sentiment",      # Th17 — inflammatory, sentiment/market emotion
        "risk",           # Treg — regulatory, risk control perspective
        "macro",          # CTL — cytotoxic, macro event detection
    ]

    def __init__(self, n_verifiers: int | None = None) -> None:
        self._logger = CortexLogger("debate_consensus")

        # Create verification agents
        n = n_verifiers or self.MIN_VERIFIERS
        n = max(self.MIN_VERIFIERS, min(self.MAX_VERIFIERS, n))

        self._agents: dict[str, VerificationAgent] = {}
        for i in range(n):
            specialty = self.SPECIALTIES[i % len(self.SPECIALTIES)]
            agent = VerificationAgent(
                agent_id=f"verifier_{specialty}_{i:02d}",
                specialty=specialty,
                perspective_weight=1.0 / n,
            )
            self._agents[agent.agent_id] = agent

        # Debate history
        self._debate_history: list[ConsensusReport] = []
        self._synapse_history: list[ImmuneSynapse] = []

        # Statistics
        self._debate_count: int = 0
        self._consensus_rate: float = 0.0

        self._last_report: ConsensusReport | None = None

    # ── Agent Management ─────────────────────────────────────────────────

    def add_verifier(self, specialty: str) -> VerificationAgent:
        """Add a new verification agent with a given specialty.

        Like the thymus releasing newly educated T cells to the periphery.
        """
        if len(self._agents) >= self.MAX_VERIFIERS:
            # Remove lowest-accuracy agent (apoptosis of ineffective T cells)
            worst = min(self._agents.values(), key=lambda a: a.accuracy)
            del self._agents[worst.agent_id]

        agent_id = f"verifier_{specialty}_{uuid.uuid4().hex[:6]}"
        agent = VerificationAgent(
            agent_id=agent_id,
            specialty=specialty,
            perspective_weight=1.0 / (len(self._agents) + 1),
        )
        self._agents[agent_id] = agent

        # Rebalance weights
        self._rebalance_weights()

        self._logger.info("verifier_added",
                         agent_id=agent_id,
                         specialty=specialty,
                         total=len(self._agents))

        return agent

    def remove_verifier(self, agent_id: str) -> bool:
        """Remove a verification agent.

        Like clonal deletion of self-reactive T cells.
        """
        if agent_id in self._agents and len(self._agents) > self.MIN_VERIFIERS:
            del self._agents[agent_id]
            self._rebalance_weights()
            return True
        return False

    def _rebalance_weights(self) -> None:
        """Rebalance perspective weights after agent changes.

        Weights are proportional to historical accuracy.
        """
        agents = list(self._agents.values())
        total_acc = sum(a.accuracy for a in agents)
        for agent in agents:
            if total_acc > 0:
                agent.perspective_weight = agent.accuracy / total_acc
            else:
                agent.perspective_weight = 1.0 / len(agents)

    # ── Inverse-Wisdom Law Checks ───────────────────────────────────────

    def check_tribalism(self) -> dict[str, Any]:
        """Check for tribalism: >60% of verifiers from same specialty.

        Like detecting monoclonal expansion in lymphoid tissue —
        any single T cell clone dominating is pathological.
        """
        specialty_counts: dict[str, int] = {}
        for agent in self._agents.values():
            specialty_counts[agent.specialty] = specialty_counts.get(agent.specialty, 0) + 1

        total = len(self._agents)
        max_specialty = max(specialty_counts.values()) if specialty_counts else 0
        max_ratio = max_specialty / total if total > 0 else 0

        is_tribal = max_ratio > self.TRIBALISM_THRESHOLD
        dominant_specialty = max(specialty_counts, key=specialty_counts.get) if specialty_counts else "none"

        return {
            "tribalism_detected": is_tribal,
            "dominant_specialty": dominant_specialty,
            "dominant_ratio": round(max_ratio, 3),
            "specialty_distribution": specialty_counts,
            "recommendation": (
                f"稀释{dominant_specialty}权重, 增加其他专业视角"
                if is_tribal else "专业分布健康"
            ),
        }

    def check_sycophancy(self) -> dict[str, Any]:
        """Check for sycophancy: any single agent with >0.7 weight.

        Like detecting Treg dominance → systemic immune suppression.
        """
        max_weight = 0.0
        max_agent: str | None = None
        for agent in self._agents.values():
            if agent.perspective_weight > max_weight:
                max_weight = agent.perspective_weight
                max_agent = agent.agent_id

        is_sycophant = max_weight > self.SYCOPHANCY_THRESHOLD

        return {
            "sycophancy_detected": is_sycophant,
            "max_weight_agent": max_agent,
            "max_weight": round(max_weight, 3),
            "recommendation": (
                f"Agent {max_agent}权重过高({max_weight:.2%})→限制其影响力"
                if is_sycophant else "权重分布健康"
            ),
        }

    def check_heterogeneity(self) -> dict[str, Any]:
        """Check for minimum specialty heterogeneity.

        Like ensuring the immune system has Th1, Th2, Th17, and Treg —
        not just one type of T cell.
        """
        specialties = {agent.specialty for agent in self._agents.values()}
        n_specialties = len(specialties)
        meets_mandate = n_specialties >= self.HETEROGENEITY_MIN

        return {
            "heterogeneity_met": meets_mandate,
            "distinct_specialties": n_specialties,
            "specialties_present": list(specialties),
            "recommendation": (
                f"需要至少{self.HETEROGENEITY_MIN}个专业, 当前仅{n_specialties}个"
                if not meets_mandate else "异质性达标"
            ),
        }

    def apply_inverse_wisdom_protections(
        self,
        agent_votes: dict[str, str],
    ) -> dict[str, float]:
        """Apply Inverse-Wisdom Law protections to adjust voting weights.

        Returns adjusted weight for each agent_id:
          - Tribalism: dilute dominant specialty weights
          - Sycophancy: cap excessive individual agent weights (post-normalization)
          - Heterogeneity: boost underrepresented specialties
        """
        # Get current weights
        weights = {aid: agent.perspective_weight for aid, agent in self._agents.items()}

        # Check tribalism
        tribalism = self.check_tribalism()
        if tribalism["tribalism_detected"]:
            dominant = tribalism["dominant_specialty"]
            penalty = 0.7  # 30% weight reduction for dominant specialty
            for aid, agent in self._agents.items():
                if agent.specialty == dominant:
                    weights[aid] *= penalty

        # First normalization pass
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        # Sycophancy check AFTER normalization (prevents cap defeat by re-normalization)
        max_weight = max(weights.values()) if weights else 0.0
        if max_weight > self.SYCOPHANCY_THRESHOLD:
            # Find the dominant agent and redistribute excess weight
            max_agent = max(weights, key=lambda k: weights[k])
            excess = max_weight - self.SYCOPHANCY_THRESHOLD
            weights[max_agent] = self.SYCOPHANCY_THRESHOLD
            # Redistribute excess to other agents proportionally
            others = {k: v for k, v in weights.items() if k != max_agent}
            other_total = sum(others.values())
            if other_total > 0:
                for k in others:
                    weights[k] += excess * (others[k] / other_total)

        return weights

    # ── Three-Signal Model ───────────────────────────────────────────────

    def compute_three_signals(
        self,
        claim_confidence: float,
        market_context: dict[str, float] | None = None,
        regime_stability: float = 0.5,
    ) -> dict[str, float]:
        """Compute the three activation signals for a claim.

        Like the three-signal model of T cell activation:

        Signal 1 (TCR-MHC-peptide): Antigen recognition = claim confidence
          — how well does the TCR recognize the peptide-MHC complex?

        Signal 2 (CD28-B7): Co-stimulation = market context support
          — is there sufficient co-stimulation from the environment?

        Signal 3 (Cytokines): Environmental context = regime stability
          — is the cytokine milieu supportive of activation?

        All three signals must exceed thresholds, or the T cell
        becomes anergic (tolerant) rather than activated.
        """
        ctx = market_context or {}

        # Signal 1: Claim confidence as antigen recognition strength
        s1 = claim_confidence

        # Signal 2: Market context as co-stimulation
        # Multiple context factors → stronger co-stimulation
        volume_support = ctx.get("volume_support", 0.5)
        trend_alignment = ctx.get("trend_alignment", 0.5)
        liquidity_quality = ctx.get("liquidity_quality", 0.5)

        s2 = (volume_support * 0.35 + trend_alignment * 0.35 + liquidity_quality * 0.30)

        # Signal 3: Regime stability as cytokine context
        # Stable regimes → permissive cytokine milieu
        # Volatile regimes → suppressive (IL-10, TGF-β dominant)
        s3 = regime_stability

        return {
            "signal_1_tcr_recognition": round(s1, 4),
            "signal_2_costimulation": round(s2, 4),
            "signal_3_cytokine_context": round(s3, 4),
            "all_signals_pass": (
                s1 >= self.SIGNAL_1_THRESHOLD
                and s2 >= self.SIGNAL_2_THRESHOLD
                and s3 >= self.SIGNAL_3_THRESHOLD
            ),
            "activation_likelihood": round((s1 + s2 + s3) / 3, 4),
        }

    # ── Agent Voting ─────────────────────────────────────────────────────

    def _agent_vote(
        self,
        agent: VerificationAgent,
        claim: dict[str, Any],
        signals: dict[str, float],
    ) -> tuple[str, float]:
        """Have a single agent vote on a claim.

        Each agent's vote is influenced by:
        - Its specialty perspective on the claim
        - The three activation signals
        - Its historical accuracy (confidence calibration)

        Returns:
            (vote: "verify"/"refute"/"abstain", vote_confidence)
        """
        claim_type = claim.get("claim_type", "neutral")
        claim_confidence = claim.get("confidence", 0.5)

        # Specialty-based perspective adjustment
        specialty_multiplier = 1.0
        if agent.specialty == "fundamental":
            # Fundamentals-focused: favors trend claims
            if claim_type == "bullish" or claim_type == "bearish":
                specialty_multiplier = 1.2
        elif agent.specialty == "technical":
            # Technical: more skeptical, requires stronger signal
            specialty_multiplier = 0.9
        elif agent.specialty == "sentiment":
            # Sentiment: responsive to confidence level
            specialty_multiplier = 0.7 + 0.6 * claim_confidence
        elif agent.specialty == "risk":
            # Risk-focused: inherently cautious
            specialty_multiplier = 0.7
        elif agent.specialty == "macro":
            # Macro: sensitive to signal 3 (cytokine/environment)
            specialty_multiplier = 0.6 + 0.8 * signals.get("signal_3_cytokine_context", 0.5)

        # Vote confidence = signal_strength × specialty_perspective × agent_accuracy
        signal_strength = signals.get("activation_likelihood", 0.5)
        vote_confidence = signal_strength * specialty_multiplier * (0.5 + 0.5 * agent.accuracy)

        # Determine vote
        if vote_confidence > 0.55:
            vote = "verify"
        elif vote_confidence < 0.35:
            vote = "refute"
        else:
            vote = "abstain"

        return vote, round(vote_confidence, 4)

    # ── Consensus Determination ─────────────────────────────────────────

    def debate(
        self,
        claim: dict[str, Any],
        market_context: dict[str, float] | None = None,
        regime_stability: float = 0.5,
    ) -> ConsensusReport:
        """Execute a full debate on a single claim.

        Like the formation of an immunological synapse:
        1. Verifier agents (T cells) inspect the claim (MHC-peptide)
        2. Three signals are computed
        3. Each agent votes based on its specialty
        4. Inverse-Wisdom Law protections are applied
        5. Consensus is determined

        Args:
            claim: claim dict with claim_id, claim_type, confidence
            market_context: dict with volume_support, trend_alignment, liquidity_quality
            regime_stability: 0-1, stability of current regime

        Returns:
            ConsensusReport with the debate outcome
        """
        self._debate_count += 1

        claim_id = claim.get("claim_id", f"claim_{self._debate_count}")
        claim_confidence = claim.get("confidence", 0.5)

        # 1. Compute three activation signals
        signals = self.compute_three_signals(claim_confidence, market_context, regime_stability)

        # 2. Each agent votes
        agent_votes: dict[str, str] = {}
        vote_confidences: dict[str, float] = {}
        for agent in self._agents.values():
            vote, confidence = self._agent_vote(agent, claim, signals)
            agent_votes[agent.agent_id] = vote
            vote_confidences[agent.agent_id] = confidence

        # 3. Apply Inverse-Wisdom Law protections
        adjusted_weights = self.apply_inverse_wisdom_protections(agent_votes)

        # 4. Weighted vote counting
        verify_weight = 0.0
        refute_weight = 0.0
        abstain_weight = 0.0

        verify_count = 0
        refute_count = 0
        abstain_count = 0

        for aid, vote in agent_votes.items():
            weight = adjusted_weights.get(aid, 1.0 / len(self._agents))
            if vote == "verify":
                verify_weight += weight
                verify_count += 1
            elif vote == "refute":
                refute_weight += weight
                refute_count += 1
            else:
                abstain_weight += weight
                abstain_count += 1

        # 5. Consensus determination (weighted)
        total_voting = verify_weight + refute_weight  # abstain excluded
        consensus_reached = False
        decision = "deferred"
        verify_ratio = 0.0
        refute_ratio = 0.0

        if total_voting > 0:
            verify_ratio = verify_weight / total_voting
            refute_ratio = refute_weight / total_voting

            if verify_ratio >= self.CONSENSUS_THRESHOLD:
                consensus_reached = True
                decision = "confirmed"
                confidence = verify_ratio
            elif refute_ratio >= self.CONSENSUS_THRESHOLD:
                consensus_reached = True
                decision = "refuted"
                confidence = refute_ratio
            else:
                # Deferred — need more evidence
                decision = "deferred"
                confidence = max(verify_ratio, refute_ratio)
        else:
            confidence = 0.0

        # 6. Inverse-Wisdom checks
        tribalism = self.check_tribalism()
        sycophancy = self.check_sycophancy()
        heterogeneity = self.check_heterogeneity()

        # Heterogeneity score: normalized diversity, capped at 1.0
        n_specialties = heterogeneity["distinct_specialties"]
        heterogeneity_score = min(1.0, n_specialties / self.HETEROGENEITY_MIN)

        # 7. Build immune synapse
        synapse = ImmuneSynapse(
            claim_id=claim_id,
            signal_1_strength=signals["signal_1_tcr_recognition"],
            signal_2_strength=signals["signal_2_costimulation"],
            signal_3_strength=signals["signal_3_cytokine_context"],
            verifier_votes=dict(agent_votes),
            final_decision=(
                "activate" if decision == "confirmed"
                else "tolerate" if decision == "refuted"
                else "anergy"
            ),
            synapse_stability=round(confidence, 4),
        )
        self._synapse_history.append(synapse)

        # 8. Minority report for close debates
        minority_report: str | None = None
        if 0.4 < verify_ratio < 0.6 and total_voting > 0:
            minority_votes = [
                f"{aid}({vote})"
                for aid, vote in agent_votes.items()
                if (verify_ratio >= 0.5 and vote != "verify")
                or (verify_ratio < 0.5 and vote == "verify")
            ]
            minority_report = f"Close vote ({verify_ratio:.1%} verify). Minority: {', '.join(minority_votes[:3])}"

        report = ConsensusReport(
            claim_id=claim_id,
            total_verifiers=len(self._agents),
            verify_count=verify_count,
            refute_count=refute_count,
            abstain_count=abstain_count,
            consensus_reached=consensus_reached,
            decision=decision,
            confidence=round(confidence, 4),
            tribalism_detected=tribalism["tribalism_detected"],
            sycophancy_detected=sycophancy["sycophancy_detected"],
            heterogeneity_score=round(heterogeneity_score, 3),
            immune_synapse=synapse,
            minority_report=minority_report,
        )
        self._debate_history.append(report)
        if len(self._debate_history) > 500:
            self._debate_history = self._debate_history[-500:]
        self._last_report = report

        # Update agent accuracy tracking
        self._update_agent_accuracy(agent_votes, decision)

        self._logger.info("debate_complete",
                         claim=claim_id,
                         decision=decision,
                         confidence=round(confidence, 3),
                         consensus=consensus_reached,
                         verify=verify_count,
                         refute=refute_count,
                         tribal=tribalism["tribalism_detected"],
                         sycophant=sycophancy["sycophancy_detected"])

        return report

    def batch_debate(
        self,
        claims: list[dict[str, Any]],
        market_context: dict[str, float] | None = None,
        regime_stability: float = 0.5,
    ) -> list[ConsensusReport]:
        """Debate multiple claims in batch.

        Like a lymph node processing multiple antigens simultaneously.
        """
        reports = []
        for claim in claims:
            report = self.debate(claim, market_context, regime_stability)
            reports.append(report)
        return reports

    def synthesize_global_decision(
        self,
        reports: list[ConsensusReport],
        risk_tolerance: float = 0.5,
    ) -> dict[str, Any]:
        """Synthesize a global trading decision from multiple debate reports.

        Like integrating multiple immunological synapses to determine
        the overall immune response direction.
        """
        confirmed = [r for r in reports if r.decision == "confirmed"]
        refuted = [r for r in reports if r.decision == "refuted"]
        deferred = [r for r in reports if r.decision == "deferred"]

        # Weighted scores
        buy_score = sum(r.confidence for r in confirmed) * (1.0 - 0.3 * (1 - risk_tolerance))
        sell_score = sum(r.confidence for r in refuted) * (1.0 - 0.3 * risk_tolerance)
        uncertain_penalty = len(deferred) * 0.1

        buy_score -= uncertain_penalty
        sell_score -= uncertain_penalty

        if buy_score > sell_score and buy_score > 0.3:
            action = "BUY"
            confidence = buy_score / (buy_score + sell_score + uncertain_penalty + 1e-10)
        elif sell_score > buy_score and sell_score > 0.3:
            action = "SELL"
            confidence = sell_score / (buy_score + sell_score + uncertain_penalty + 1e-10)
        else:
            action = "HOLD"
            if len(reports) == 0:
                confidence = 0.3  # no data → low confidence, not 1.0
            else:
                confidence = max(0.3, 1.0 - uncertain_penalty)

        # Overall quality metrics
        consensus_rate = len([r for r in reports if r.consensus_reached]) / max(len(reports), 1)
        avg_heterogeneity = sum(r.heterogeneity_score for r in reports) / max(len(reports), 1)

        return {
            "action": action,
            "confidence": round(min(confidence, 1.0), 4),
            "confirmed_claims": len(confirmed),
            "refuted_claims": len(refuted),
            "deferred_claims": len(deferred),
            "consensus_rate": round(consensus_rate, 3),
            "avg_heterogeneity": round(avg_heterogeneity, 3),
            "tribalism_flagged": any(r.tribalism_detected for r in reports),
            "sycophancy_flagged": any(r.sycophancy_detected for r in reports),
        }

    # ── Agent Accuracy Tracking ──────────────────────────────────────────

    def _update_agent_accuracy(
        self,
        agent_votes: dict[str, str],
        final_decision: str,
    ) -> None:
        """Update agent accuracy based on debate outcome.

        Currently uses self-consistency (agreement with consensus)
        as a proxy for accuracy. Can be extended with ground-truth feedback.

        Like B cells that survive affinity selection in the germinal center
        increasing their representation in the repertoire.
        """
        majority_vote = "verify" if final_decision == "confirmed" else "refute"
        if final_decision == "deferred":
            return  # no feedback for deferred decisions

        for aid, vote in agent_votes.items():
            if aid in self._agents:
                agent = self._agents[aid]
                agent.total_verifications += 1
                if vote == majority_vote:
                    agent.correct_verifications += 1
                agent.accuracy = (
                    agent.correct_verifications / agent.total_verifications
                    if agent.total_verifications > 0
                    else 0.5
                )
                agent.verification_history.append({
                    "vote": vote,
                    "consensus": majority_vote,
                    "correct": vote == majority_vote,
                    "timestamp": time.time(),
                })
                # Cap history to prevent unbounded growth
                if len(agent.verification_history) > 500:
                    agent.verification_history = agent.verification_history[-500:]

    # ── Helpers ──────────────────────────────────────────────────────────

    def get_verifier_diversity_report(self) -> dict[str, Any]:
        """Get a comprehensive diversity report."""
        tribalism = self.check_tribalism()
        sycophancy = self.check_sycophancy()
        heterogeneity = self.check_heterogeneity()

        return {
            "n_verifiers": len(self._agents),
            "specialties": {a.specialty for a in self._agents.values()},
            "tribalism": tribalism,
            "sycophancy": sycophancy,
            "heterogeneity": heterogeneity,
            "weights": {
                aid: round(a.perspective_weight, 3)
                for aid, a in self._agents.items()
            },
            "accuracies": {
                aid: round(a.accuracy, 3)
                for aid, a in self._agents.items()
            },
            "health_status": (
                "healthy" if (
                    not tribalism["tribalism_detected"]
                    and not sycophancy["sycophancy_detected"]
                    and heterogeneity["heterogeneity_met"]
                ) else "needs_attention"
            ),
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "debate_count": self._debate_count,
            "n_verifiers": len(self._agents),
            "consensus_rate": round(self._consensus_rate, 3),
            "last_decision": (
                self._last_report.decision if self._last_report else "none"
            ),
            "last_confidence": (
                self._last_report.confidence if self._last_report else 0.0
            ),
            "specialties": list({a.specialty for a in self._agents.values()}),
            "avg_accuracy": round(
                sum(a.accuracy for a in self._agents.values()) / max(len(self._agents), 1), 3
            ),
            "synapse_history_size": len(self._synapse_history),
        }
