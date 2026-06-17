"""Phase 6.3: AutonomousGovernance — "免疫耐受与自体免疫的平衡"(Immune Tolerance vs Autoimmunity).

Biological Metaphor:
  免疫系统的最核心悖论——如何区分"自我"与"非我"?
    过度活跃→自体免疫疾病(攻击自己的组织)
    过度抑制→感染/癌症(不攻击真正的威胁)
    平衡是最难的——这就是为什么免疫系统有Treg(调节T细胞)

  我们映射:
    自体免疫 = 系统过度修改/优化, 破坏了自身稳定的优秀策略
    免疫缺陷 = 系统过于保守, 错过了真正的市场机会/威胁
    Treg = AutonomousGovernance(本模块)的5道检查关卡

  "自身组织" = 已验证的稳定策略/配置/知识
  "病原体" = 需要被修改/替换的缺陷
  "自体免疫反应" = 系统错误地"优化"了本已优秀的策略
  "免疫耐受" = 系统正确地忽略了不构成威胁的微小波动

机制:
  重大变更必须通过5道关卡:
    1. PolicyEngine检查(如同Treg检查: "这会不会攻击自身组织?")
    2. BehaviorMonitor审计(如同NK细胞检查: "正常细胞的MHC-I是否完整?")
    3. L3多Agent辩论(至少3个不同专业)
       如同T细胞激活需要3个信号(MHC-肽+TCR+共刺激)
    4. CounterfactualEngine反事实推演
       如同克隆删除(Clonal Deletion): "如果这个T细胞对所有抗原都反应→删除"
    5. HumanApprovalGate(兜底保留)
       如同你最终还是可以决定: 接种疫苗(主动感染控制量的抗原)

Reference:
  Sakaguchi et al. (2008), "Treg cells", Cell 133:775-787;
  Janeway (2001), "Immunobiology: The Immune System in Health and Disease";
  Matzinger (2002), "The Danger Model", Science 296:301-305
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


# ── Governance Types ──────────────────────────────────────────────────

class GateResult(str, Enum):
    PASSED = "passed"           # Gate approved the change
    FAILED = "failed"            # Gate rejected the change
    DEFERRED = "deferred"        # Gate needs more information
    OVERRIDDEN = "overridden"    # Human overrode the gate decision


class ChangeType(str, Enum):
    """Type of change being proposed."""
    STRATEGY_MODIFICATION = "strategy_modification"
    PARAMETER_UPDATE = "parameter_update"
    AGENT_RECONFIGURATION = "agent_reconfiguration"
    KNOWLEDGE_GRAPH_EDIT = "knowledge_graph_edit"
    BRIDGE_RESET = "bridge_reset"
    POLICY_CHANGE = "policy_change"
    EVOLUTION_LEAP = "evolution_leap"  # Large evolutionary jump


class GovernanceDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"  # Approved with constraints
    ESCALATED = "escalated"      # Needs human review
    QUARANTINED = "quarantined"  # Approved but isolated for observation


# ── Data Classes ──────────────────────────────────────────────────────

@dataclass
class ChangeProposal:
    """A proposed change that must pass governance gates.

    Like an antigen being presented for immune evaluation.
    """

    proposal_id: str
    change_type: ChangeType
    target: str  # What component/parameter is being changed
    proposed_value: Any
    current_value: Any = None
    rationale: str = ""
    risk_level: float = 0.5  # 0-1 estimated risk

    # Source of the proposal
    source_layer: str = ""
    source_component: str = ""
    source_confidence: float = 0.5

    # Change metadata
    impact_scope: list[str] = field(default_factory=list)  # Components affected
    rollback_plan: str = ""  # How to undo if needed

    created_at: float = field(default_factory=time.time)


@dataclass
class GateVerdict:
    """A single gate's verdict on a proposal."""

    gate_name: str
    gate_number: int  # 1-5
    result: GateResult
    confidence: float  # 0-1
    reason: str
    conditions: list[str] = field(default_factory=list)  # If conditional
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class GovernanceDecision_:
    """Final governance decision on a proposal."""

    decision_id: str
    proposal_id: str
    decision: GovernanceDecision

    gate_verdicts: list[GateVerdict] = field(default_factory=list)
    final_reason: str = ""

    # If approved, any constraints
    constraints: list[str] = field(default_factory=list)
    observation_period: float = 0.0  # Seconds to quarantine/observe

    approved_at: float = field(default_factory=time.time)
    reviewed_by_human: bool = False


class AutonomousGovernance:
    """Immune Tolerance Balance: 5-gate governance for major system changes.

    Config:
      - auto_approve_max_risk: proposals with risk below this skip human gate
      - quarantine_default: default observation period when quarantined
      - gate_timeout: max time for a gate to decide before deferring
      - max_deferrals: max times a proposal can be deferred before auto-rejection
    """

    GATE_NAMES = [
        "PolicyEngine",       # Gate 1: Treg — "will this attack self?"
        "BehaviorMonitor",    # Gate 2: NK cell — "is this cell's MHC-I intact?"
        "MultiAgentDebate",   # Gate 3: T cell activation — 3-signal requirement
        "Counterfactual",    # Gate 4: Clonal deletion — "what if this reacts to everything?"
        "HumanApproval",      # Gate 5: Ultimate consent — vaccination decision
    ]

    def __init__(
        self,
        auto_approve_max_risk: float = 0.2,
        quarantine_default: float = 3600.0,  # 1 hour
        gate_timeout: float = 300.0,  # 5 minutes
        max_deferrals: int = 3,
        require_human_above_risk: float = 0.7,
    ) -> None:
        self._auto_approve_max = auto_approve_max_risk
        self._quarantine_default = quarantine_default
        self._gate_timeout = gate_timeout
        self._max_deferrals = max_deferrals
        self._require_human = require_human_above_risk

        # Proposal tracking
        self._proposals: dict[str, ChangeProposal] = {}
        self._decisions: dict[str, GovernanceDecision_] = {}
        self._deferral_counts: dict[str, int] = defaultdict(int)
        self._quarantine_zone: dict[str, dict[str, Any]] = {}  # {(proposal_id): {release_time, constraints}}

        # Governance statistics
        self._gate_stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        self._logger = CortexLogger("autonomous_governance")

    # ── Proposal Submission ──────────────────────────────────────────

    def submit_proposal(self, change_type: ChangeType, target: str,
                        proposed_value: Any, current_value: Any = None,
                        rationale: str = "", risk_level: float = 0.5,
                        source_layer: str = "", source_component: str = "",
                        impact_scope: list[str] | None = None,
                        rollback_plan: str = "") -> ChangeProposal:
        """Submit a change proposal for governance review.

        Like an antigen being presented to the immune system.
        """
        proposal = ChangeProposal(
            proposal_id=self._gen_id("proposal"),
            change_type=change_type,
            target=target,
            proposed_value=proposed_value,
            current_value=current_value,
            rationale=rationale,
            risk_level=risk_level,
            source_layer=source_layer,
            source_component=source_component,
            source_confidence=0.5,
            impact_scope=impact_scope or [],
            rollback_plan=rollback_plan,
        )
        self._proposals[proposal.proposal_id] = proposal
        self._logger.info(
            "proposal_submitted",
            proposal_id=proposal.proposal_id[:16],
            type=change_type.value,
            target=target,
            risk=risk_level,
        )
        return proposal

    # ── 5-Gate Review Pipeline ──────────────────────────────────────

    def review(self, proposal_id: str,
               gate_inputs: dict[str, Any] | None = None) -> GovernanceDecision_:
        """Run the complete 5-gate governance review.

        Like a T cell navigating thymic selection:
          Gate 1 (Treg): Policy check — will this attack self?
          Gate 2 (NK): Behavior check — is this component healthy?
          Gate 3 (T cell): Multi-agent debate — 3 independent perspectives
          Gate 4 (Clonal deletion): Counterfactual — what if this goes wrong?
          Gate 5 (Consent): Human approval — final override
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal {proposal_id} not found")

        inputs = gate_inputs or {}
        verdicts: list[GateVerdict] = []

        # ── Gate 1: PolicyEngine (Treg check) ──────────────────────
        g1 = self._gate_policy_check(proposal, inputs.get("policy", {}))
        verdicts.append(g1)
        self._record_gate_stat(1, g1.result)
        if g1.result == GateResult.FAILED:
            return self._finalize_decision(proposal_id, verdicts, GovernanceDecision.REJECTED)

        # ── Gate 2: BehaviorMonitor (NK cell check) ─────────────────
        g2 = self._gate_behavior_check(proposal, inputs.get("behavior", {}))
        verdicts.append(g2)
        self._record_gate_stat(2, g2.result)
        if g2.result == GateResult.FAILED:
            return self._finalize_decision(proposal_id, verdicts, GovernanceDecision.REJECTED)

        # ── Gate 3: Multi-Agent Debate (T cell 3-signal) ────────────
        g3 = self._gate_debate_check(proposal, inputs.get("debate", {}))
        verdicts.append(g3)
        self._record_gate_stat(3, g3.result)
        if g3.result == GateResult.FAILED:
            return self._finalize_decision(proposal_id, verdicts, GovernanceDecision.REJECTED)

        # ── Gate 4: Counterfactual (Clonal deletion) ─────────────────
        g4 = self._gate_counterfactual_check(proposal, inputs.get("counterfactual", {}))
        verdicts.append(g4)
        self._record_gate_stat(4, g4.result)
        if g4.result == GateResult.FAILED:
            return self._finalize_decision(proposal_id, verdicts, GovernanceDecision.REJECTED)

        # ── Gate 5: Human Approval ──────────────────────────────────
        if proposal.risk_level >= self._require_human:
            g5 = self._gate_human_approval(proposal, inputs.get("human", {}))
            verdicts.append(g5)
            self._record_gate_stat(5, g5.result)
            if g5.result == GateResult.FAILED:
                return self._finalize_decision(proposal_id, verdicts, GovernanceDecision.REJECTED)
        else:
            g5 = GateVerdict(
                gate_name="HumanApproval", gate_number=5,
                result=GateResult.PASSED, confidence=1.0,
                reason=f"Auto-approved: risk {proposal.risk_level:.2f} < {self._require_human}",
            )
            verdicts.append(g5)
            self._record_gate_stat(5, g5.result)

        # Determine final decision
        passed_count = sum(1 for v in verdicts if v.result == GateResult.PASSED)
        deferred = [v for v in verdicts if v.result == GateResult.DEFERRED]

        if len(deferred) > 0:
            decision = GovernanceDecision.CONDITIONAL
        elif passed_count >= 5:
            decision = GovernanceDecision.APPROVED
        else:
            decision = GovernanceDecision.CONDITIONAL

        return self._finalize_decision(proposal_id, verdicts, decision)

    # ── Gate Implementations ─────────────────────────────────────────

    def _gate_policy_check(self, proposal: ChangeProposal,
                           inputs: dict[str, Any]) -> GateVerdict:
        """Gate 1: PolicyEngine — Treg check.

        "Will this change attack our own stable tissue?"
        Like Treg cells preventing autoimmune responses.
        """
        # Check if change violates homeostasis constraints
        if proposal.change_type == ChangeType.PARAMETER_UPDATE:
            try:
                val = float(proposal.proposed_value)
                # Max position check
                if "position" in proposal.target.lower() and val > 0.2:
                    return GateVerdict(
                        gate_name="PolicyEngine", gate_number=1,
                        result=GateResult.FAILED, confidence=0.9,
                        reason=f"Position limit violation: {val} > 0.20 max",
                    )
                # Max stop loss check
                if "stop_loss" in proposal.target.lower() and val > 0.05:
                    return GateVerdict(
                        gate_name="PolicyEngine", gate_number=1,
                        result=GateResult.FAILED, confidence=0.9,
                        reason=f"Stop loss violation: {val} > 0.05 max",
                    )
            except (ValueError, TypeError):
                pass

        # Policy changes themselves need high threshold
        if proposal.change_type == ChangeType.POLICY_CHANGE:
            if proposal.risk_level > 0.3:
                return GateVerdict(
                    gate_name="PolicyEngine", gate_number=1,
                    result=GateResult.DEFERRED, confidence=0.7,
                    reason="Policy changes require additional review",
                    conditions=["Provide impact analysis on all layers"],
                )

        return GateVerdict(
            gate_name="PolicyEngine", gate_number=1,
            result=GateResult.PASSED, confidence=0.85,
            reason="No policy violations detected",
        )

    def _gate_behavior_check(self, proposal: ChangeProposal,
                             inputs: dict[str, Any]) -> GateVerdict:
        """Gate 2: BehaviorMonitor — NK cell check.

        "Is the target component's MHC-I intact?"
        Like NK cells checking for normal self-markers.
        """
        # Check if target component is currently under stress
        abnormal_signals = inputs.get("abnormal_signals", [])
        if abnormal_signals:
            return GateVerdict(
                gate_name="BehaviorMonitor", gate_number=2,
                result=GateResult.DEFERRED, confidence=0.6,
                reason=f"Target has {len(abnormal_signals)} active anomaly alerts",
                conditions=["Resolve anomalies before proceeding"],
                evidence={"alerts": abnormal_signals[:5]},
            )

        # Check for excessive call frequency (model abuse)
        call_count = inputs.get("call_count", 0)
        if call_count > 500:
            return GateVerdict(
                gate_name="BehaviorMonitor", gate_number=2,
                result=GateResult.FAILED, confidence=0.75,
                reason=f"Component overused: {call_count} calls detected",
            )

        # Param drift check
        drift_detected = inputs.get("param_drift", False)
        if drift_detected:
            return GateVerdict(
                gate_name="BehaviorMonitor", gate_number=2,
                result=GateResult.DEFERRED, confidence=0.65,
                reason="Parameter drift detected in target component",
                conditions=["Stabilize parameters before modification"],
            )

        return GateVerdict(
            gate_name="BehaviorMonitor", gate_number=2,
            result=GateResult.PASSED, confidence=0.8,
            reason="Target component behavior is within normal range",
        )

    def _gate_debate_check(self, proposal: ChangeProposal,
                           inputs: dict[str, Any]) -> GateVerdict:
        """Gate 3: Multi-Agent Debate — T cell 3-signal requirement.

        Like T cell activation requiring:
          Signal 1: TCR-MHC-peptide (antigen recognition)
          Signal 2: CD28-B7 (co-stimulation)
          Signal 3: Cytokines (environmental context)
        All three must be present — missing any one → tolerance (anergy).
        """
        debate_results = inputs.get("debate_results", [])
        min_specialties = 3

        if not debate_results:
            # Without debate input, require at least source confidence
            if proposal.source_confidence < 0.6:
                return GateVerdict(
                    gate_name="MultiAgentDebate", gate_number=3,
                    result=GateResult.DEFERRED, confidence=0.5,
                    reason="Insufficient debate: need at least 3 specialty perspectives",
                    conditions=[f"Run debate with >= {min_specialties} specialties"],
                )

        # Check specialty diversity
        specialties = set()
        approvals = 0
        for dr in debate_results:
            specialties.add(dr.get("specialty", "unknown"))
            if dr.get("approved", False):
                approvals += 1

        if len(specialties) < min_specialties:
            return GateVerdict(
                gate_name="MultiAgentDebate", gate_number=3,
                result=GateResult.DEFERRED, confidence=0.55,
                reason=f"Only {len(specialties)}/{min_specialties} specialties represented",
                conditions=["Add more diverse perspectives"],
                evidence={"specialties": list(specialties)},
            )

        # Majority vote required (>= 2/3)
        total = len(debate_results)
        if total > 0 and approvals / total < 0.66:
            return GateVerdict(
                gate_name="MultiAgentDebate", gate_number=3,
                result=GateResult.FAILED, confidence=0.8,
                reason=f"Debate consensus not reached: {approvals}/{total} approved (need >=2/3)",
                evidence={"approvals": approvals, "total": total},
            )

        return GateVerdict(
            gate_name="MultiAgentDebate", gate_number=3,
            result=GateResult.PASSED, confidence=0.75,
            reason=f"Debate passed: {approvals}/{total} approved with {len(specialties)} specialties",
            evidence={"specialties": list(specialties), "approvals": approvals, "total": total},
        )

    def _gate_counterfactual_check(self, proposal: ChangeProposal,
                                   inputs: dict[str, Any]) -> GateVerdict:
        """Gate 4: Counterfactual — Clonal deletion.

        "If we apply this change, what's the worst that could happen?"
        Like clonal deletion in the thymus: T cells that react strongly
        to self-antigens are eliminated before they can cause autoimmunity.
        """
        scenarios = inputs.get("scenarios", [])
        if not scenarios:
            # Run basic counterfactual
            worst_case = self._basic_counterfactual(proposal)
            scenarios = [worst_case]

        # Check if any scenario predicts catastrophic outcome
        for scenario in scenarios:
            impact = scenario.get("worst_case_impact", scenario.get("impact", 0))
            if abs(impact) > 0.5:  # >50% negative impact
                return GateVerdict(
                    gate_name="Counterfactual", gate_number=4,
                    result=GateResult.FAILED, confidence=0.85,
                    reason=f"Counterfactual predicts severe impact: {impact:.2f}",
                    evidence={"scenario": scenario},
                )
            elif abs(impact) > 0.3:
                return GateVerdict(
                    gate_name="Counterfactual", gate_number=4,
                    result=GateResult.DEFERRED, confidence=0.6,
                    reason=f"Counterfactual shows moderate risk: {impact:.2f}",
                    conditions=["Run extended backtest", "Add rollback trigger"],
                    evidence={"scenario": scenario},
                )

        return GateVerdict(
            gate_name="Counterfactual", gate_number=4,
            result=GateResult.PASSED, confidence=0.7,
            reason="Counterfactual analysis shows acceptable risk profile",
        )

    @staticmethod
    def _basic_counterfactual(proposal: ChangeProposal) -> dict[str, Any]:
        """Run a basic counterfactual analysis without external engine."""
        risk = proposal.risk_level
        impact = risk * 1.5  # Worst case is usually worse than estimated risk
        return {
            "scenario": "worst_case_default",
            "description": f"What if {proposal.change_type.value} on {proposal.target} fails?",
            "worst_case_impact": min(1.0, impact),
            "recovery_time_estimate": risk * 3600,  # seconds
            "requires_rollback": risk > 0.3,
        }

    def _gate_human_approval(self, proposal: ChangeProposal,
                             inputs: dict[str, Any]) -> GateVerdict:
        """Gate 5: Human Approval — Ultimate consent.

        Like the final decision to vaccinate: deliberate, informed consent.
        """
        human_approved = inputs.get("approved", False)
        human_notes = inputs.get("notes", "")

        if human_approved:
            return GateVerdict(
                gate_name="HumanApproval", gate_number=5,
                result=GateResult.PASSED, confidence=1.0,
                reason=f"Human approved: {human_notes}" if human_notes else "Human approved",
            )

        # If human explicitly rejected
        if "rejected" in inputs:
            return GateVerdict(
                gate_name="HumanApproval", gate_number=5,
                result=GateResult.FAILED, confidence=1.0,
                reason=f"Human rejected: {human_notes}" if human_notes else "Human rejected",
            )

        # Pending human review
        return GateVerdict(
            gate_name="HumanApproval", gate_number=5,
            result=GateResult.DEFERRED, confidence=1.0,
            reason="Awaiting human review",
            conditions=[f"Risk level {proposal.risk_level:.2f} >= {self._require_human} requires approval"],
        )

    # ── Decision Finalization ────────────────────────────────────────

    def _finalize_decision(self, proposal_id: str,
                           verdicts: list[GateVerdict],
                           decision: GovernanceDecision) -> GovernanceDecision_:
        """Finalize and record the governance decision."""
        constraints: list[str] = []
        for v in verdicts:
            constraints.extend(v.conditions)

        observation_period = 0.0
        if decision == GovernanceDecision.CONDITIONAL or decision == GovernanceDecision.QUARANTINED:
            observation_period = self._quarantine_default

        result = GovernanceDecision_(
            decision_id=self._gen_id("decision"),
            proposal_id=proposal_id,
            decision=decision,
            gate_verdicts=verdicts,
            final_reason=f"Decision: {decision.value} after {len(verdicts)} gates",
            constraints=constraints,
            observation_period=observation_period,
        )

        self._decisions[proposal_id] = result

        # Set up quarantine if needed
        if decision == GovernanceDecision.QUARANTINED:
            self._quarantine_zone[proposal_id] = {
                "release_time": time.time() + observation_period,
                "constraints": constraints,
            }

        self._logger.info(
            "decision_reached",
            proposal_id=proposal_id[:16],
            decision=decision.value,
            gates_passed=sum(1 for v in verdicts if v.result == GateResult.PASSED),
        )
        return result

    # ── Human Override ──────────────────────────────────────────────

    def human_override(self, proposal_id: str, approved: bool,
                       notes: str = "") -> GovernanceDecision_:
        """Human override for any gate decision.

        Like the ultimate medical decision that overrides immune system
        recommendations (e.g., choosing to vaccinate despite risks).
        """
        existing = self._decisions.get(proposal_id)
        if existing:
            override_verdict = GateVerdict(
                gate_name="HumanApproval", gate_number=5,
                result=GateResult.PASSED if approved else GateResult.FAILED,
                confidence=1.0,
                reason=f"Human override: {notes}" if notes else "Human override applied",
            )
            existing.gate_verdicts.append(override_verdict)
            existing.decision = GovernanceDecision.APPROVED if approved else GovernanceDecision.REJECTED
            existing.reviewed_by_human = True
            existing.final_reason = f"Human override: {'approved' if approved else 'rejected'}"
            self._logger.info("human_override", proposal_id=proposal_id[:16], approved=approved)
            return existing

        raise ValueError(f"No existing decision for proposal {proposal_id}")

    # ── Quarantine Management ────────────────────────────────────────

    def check_quarantine(self, proposal_id: str) -> dict[str, Any]:
        """Check if a quarantined proposal can be released."""
        q_info = self._quarantine_zone.get(proposal_id)
        if q_info is None:
            return {"status": "not_quarantined"}

        now = time.time()
        if now >= q_info["release_time"]:
            del self._quarantine_zone[proposal_id]
            return {"status": "released", "time_served": q_info["release_time"]}
        return {
            "status": "quarantined",
            "remaining": round(q_info["release_time"] - now, 1),
            "constraints": q_info["constraints"],
        }

    def release_from_quarantine(self, proposal_id: str) -> bool:
        """Manually release a proposal from quarantine."""
        if proposal_id in self._quarantine_zone:
            del self._quarantine_zone[proposal_id]
            return True
        return False

    # ── Query Interface ─────────────────────────────────────────────

    def get_proposal(self, proposal_id: str) -> ChangeProposal | None:
        return self._proposals.get(proposal_id)

    def get_decision(self, proposal_id: str) -> GovernanceDecision_ | None:
        return self._decisions.get(proposal_id)

    def get_pending_reviews(self) -> list[ChangeProposal]:
        """Get proposals still awaiting human review."""
        pending = []
        for pid, dec in self._decisions.items():
            if dec.decision == GovernanceDecision.ESCALATED:
                prop = self._proposals.get(pid)
                if prop:
                    pending.append(prop)
        return pending

    def get_gate_statistics(self) -> dict[str, dict[str, int]]:
        return {f"Gate{k}": dict(stats) for k, stats in sorted(self._gate_stats.items())}

    def get_quarantined(self) -> list[dict[str, Any]]:
        return [
            {"proposal_id": pid, **info}
            for pid, info in self._quarantine_zone.items()
        ]

    def _record_gate_stat(self, gate_num: int, result: GateResult) -> None:
        self._gate_stats[gate_num][result.value] += 1

    _id_counter: int = 0

    @classmethod
    def _gen_id(cls, prefix: str) -> str:
        cls._id_counter += 1
        return hashlib.md5(f"{prefix}|{time.time()}|{cls._id_counter}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        decisions = list(self._decisions.values())
        return {
            "total_proposals": len(self._proposals),
            "total_decisions": len(decisions),
            "approved": sum(1 for d in decisions if d.decision == GovernanceDecision.APPROVED),
            "rejected": sum(1 for d in decisions if d.decision == GovernanceDecision.REJECTED),
            "conditional": sum(1 for d in decisions if d.decision == GovernanceDecision.CONDITIONAL),
            "escalated": sum(1 for d in decisions if d.decision == GovernanceDecision.ESCALATED),
            "quarantined": len(self._quarantine_zone),
            "gate_stats": self.get_gate_statistics(),
        }
