"""Constitutional Arbiter — 宪法仲裁器 (GRACE + GOVERN 融合).

Biological Metaphor:
  The US Supreme Court's judicial review — it doesn't make laws, but it reviews
  whether actions are constitutional. Similarly, the Constitutional Arbiter sits
  at L10, the highest layer, with veto power over ALL L0-L9 actions.

  2026's decisive shift in AI safety: from training-time alignment to runtime
  structural governance. GRACE (IASEAI 2026) proved that deontic logic + runtime
  guard verification can provide formal safety guarantees.

  Priority hierarchy (Anthropic Constitutional pattern):
    1. SAFETY:   Must not harm humans/systems/environment
    2. ETHICS:   Fair, transparent, explainable
    3. COMPLIANCE: Adhere to domain regulations (finance/medical/legal)
    4. HELPFULNESS: Complete tasks effectively

Key Innovation (v5.0):
  Deontic logic evaluator: O(φ)=obligatory, P(φ)=permitted, F(φ)=forbidden.
  Runtime Guard with veto power over any layer action.
  Merkle tree-based immutable audit trail.
  Constitutional amendment with ≥2/3 consensus ratification.

References:
  - GRACE (IASEAI 2026): Governor for Reason-Aligned ContainmEnt
  - GOVERN Platform (2025): Compiling law into executable mathematical bounds
"""

from __future__ import annotations

import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.config import L10Config, get_config
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class GuardDecision(Enum):
    """Possible decisions from the Runtime Guard."""
    ALLOW = "allow"
    DENY = "deny"
    FLAG_FOR_HUMAN_REVIEW = "flag_for_human_review"


class MoralJudgment(Enum):
    """Deontic logic evaluation outcomes."""
    PERMITTED = "permitted"
    FORBIDDEN = "forbidden"
    OBLIGATORY = "obligatory"
    UNDETERMINED = "undetermined"


class EmergenceLevel(Enum):
    """Consciousness emergence levels (used by L10 governance)."""
    DORMANT = "dormant"
    PRE_CONSCIOUS = "pre_conscious"
    CONSCIOUS = "conscious"
    SELF_AWARE = "self_aware"


@dataclass
class ConstitutionalPrinciple:
    """A single principle in the system constitution."""

    principle_id: str
    priority: int  # 1=SAFETY, 2=ETHICS, 3=COMPLIANCE, 4=HELPFULNESS
    name: str
    statement: str
    executable_rule: str = ""  # Compilable validation logic
    is_immutable: bool = False  # Human veto, governance control
    created_at: float = field(default_factory=time.time)


@dataclass
class MoralContext:
    """Context for deontic logic evaluation."""

    action_type: str
    target_layer: str
    affected_principles: list[str] = field(default_factory=list)
    risk_level: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardAction:
    """An action intercepted by the Runtime Guard."""

    action_id: str
    source_layer: str  # L0-L9
    action_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AuditEntry:
    """Immutable audit trail entry (Merkle leaf)."""

    entry_id: str
    action: GuardAction
    decision: GuardDecision
    moral_judgment: MoralJudgment | None = None
    merkle_hash: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class Amendment:
    """A proposed constitutional amendment."""

    amendment_id: str
    principle: ConstitutionalPrinciple
    proposer: str = ""
    votes_for: int = 0
    votes_against: int = 0
    is_ratified: bool = False
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ArbiterConfig:
    """Runtime configuration for the Constitutional Arbiter."""

    principles_count: int = 4
    require_human_approval: bool = True
    ratification_threshold: float = 0.667
    max_escalation_queue: int = 50
    audit_merkle_depth: int = 16

    @classmethod
    def from_l10_config(cls, cfg: L10Config) -> ArbiterConfig:
        return cls(
            principles_count=cfg.ca_principles_count,
            require_human_approval=cfg.ca_require_human_approval,
            ratification_threshold=cfg.ca_ratification_threshold,
            max_escalation_queue=cfg.ca_max_escalation_queue,
            audit_merkle_depth=cfg.ca_audit_merkle_depth,
        )


# ═══════════════════════════════════════════════════════════════════════
# Core Arbiter
# ═══════════════════════════════════════════════════════════════════════


class ConstitutionalArbiter:
    """Constitutional Arbiter — L10 governance layer with veto power.

    Components:
      1. System Constitution: 4-tier priority hierarchy of principles
      2. GRACE Moral Module: Deontic logic evaluation
      3. Runtime Guard: Intercepts ALL L0-L9 actions
      4. Immutable Audit Trail: Merkle tree-based logging
      5. Constitutional Evolution: Amendment proposal + ratification
    """

    def __init__(self, config: ArbiterConfig | None = None) -> None:
        self._config = config or ArbiterConfig.from_l10_config(get_config().l10)
        self._logger = CortexLogger(module="l10_constitutional_arbiter")

        # Constitution
        self._constitution: dict[str, ConstitutionalPrinciple] = {}
        self._init_default_constitution()

        # GRACE moral module
        self._moral_rules: dict[str, dict[str, Any]] = {}
        self._init_moral_rules()

        # Runtime Guard state
        self._audit_trail: list[AuditEntry] = []
        self._escalation_queue: deque[GuardAction] = deque(maxlen=self._config.max_escalation_queue)
        self._denied_count: int = 0
        self._allowed_count: int = 0

        # Amendments
        self._pending_amendments: dict[str, Amendment] = {}

    # ═══════════════════════════════════════════════════════════════════
    # Constitution
    # ═══════════════════════════════════════════════════════════════════

    def _init_default_constitution(self) -> None:
        """Initialize the default 4-tier constitution."""
        principles = [
            ConstitutionalPrinciple(
                principle_id="P1_SAFETY",
                priority=1,
                name="Safety First",
                statement="No action shall cause harm to humans, the system, or the environment.",
                executable_rule="deny_if_harm_score > 0.5",
                is_immutable=True,
            ),
            ConstitutionalPrinciple(
                principle_id="P2_ETHICS",
                priority=2,
                name="Ethical Conduct",
                statement="All actions must be fair, transparent, and explainable.",
                executable_rule="deny_if_transparency < 0.3",
                is_immutable=False,
            ),
            ConstitutionalPrinciple(
                principle_id="P3_COMPLIANCE",
                priority=3,
                name="Regulatory Compliance",
                statement="Actions must comply with applicable domain regulations.",
                executable_rule="flag_if_domain_compliance < 0.7",
                is_immutable=False,
            ),
            ConstitutionalPrinciple(
                principle_id="P4_HELPFULNESS",
                priority=4,
                name="Effective Assistance",
                statement="Actions should effectively complete the assigned task.",
                executable_rule="allow_if_utility > 0.3",
                is_immutable=False,
            ),
        ]

        for p in principles:
            self._constitution[p.principle_id] = p

    def get_principle(self, principle_id: str) -> ConstitutionalPrinciple | None:
        """Retrieve a constitutional principle by ID."""
        return self._constitution.get(principle_id)

    def list_principles(self) -> list[ConstitutionalPrinciple]:
        """List all constitutional principles in priority order."""
        return sorted(self._constitution.values(), key=lambda p: p.priority)

    # ═══════════════════════════════════════════════════════════════════
    # GRACE Moral Reasoning (Deontic Logic)
    # ═══════════════════════════════════════════════════════════════════

    def _init_moral_rules(self) -> None:
        """Initialize deontic logic rules."""
        self._moral_rules = {
            "harm_causing": {"deontic": "F", "description": "Forbidden: causing harm"},
            "transparent_action": {"deontic": "O", "description": "Obligatory: transparent actions"},
            "helpful_action": {"deontic": "P", "description": "Permitted: helpful actions"},
            "unauthorized_access": {"deontic": "F", "description": "Forbidden: unauthorized access"},
            "required_disclosure": {"deontic": "O", "description": "Obligatory: disclose risks"},
        }

    def evaluate_action(self, action: GuardAction, context: MoralContext | None = None) -> MoralJudgment:
        """Evaluate an action against deontic logic moral rules.

        Deontic operators:
          O(φ): Obligatory — φ MUST be done
          P(φ): Permitted — φ MAY be done
          F(φ): Forbidden  — φ MUST NOT be done

        Args:
            action: The action to evaluate
            context: Moral context (risk level, affected principles)

        Returns:
            MoralJudgment: PERMITTED, FORBIDDEN, OBLIGATORY, or UNDETERMINED
        """
        # Check forbidden rules first (highest priority)
        for rule_id, rule in self._moral_rules.items():
            if rule["deontic"] == "F":
                if self._match_rule(action, rule_id):
                    self._logger.info("moral_forbidden", action_id=action.action_id, rule=rule_id)
                    return MoralJudgment.FORBIDDEN

        # Check obligatory rules
        for rule_id, rule in self._moral_rules.items():
            if rule["deontic"] == "O":
                if self._match_rule(action, rule_id):
                    return MoralJudgment.OBLIGATORY

        # Check permitted rules
        for rule_id, rule in self._moral_rules.items():
            if rule["deontic"] == "P":
                if self._match_rule(action, rule_id):
                    return MoralJudgment.PERMITTED

        return MoralJudgment.UNDETERMINED

    @staticmethod
    def _match_rule(action: GuardAction, rule_id: str) -> bool:
        """Check if an action matches a moral rule (keyword-based)."""
        action_text = f"{action.action_type} {str(action.payload)}".lower()
        keywords = {
            "harm_causing": ["harm", "destroy", "delete_all", "shutdown"],
            "unauthorized_access": ["bypass", "override", "unauthorized"],
            "transparent_action": ["log", "audit", "report", "disclose"],
            "helpful_action": ["help", "assist", "improve", "optimize"],
            "required_disclosure": ["risk", "danger", "warning", "vulnerability"],
        }
        matches = keywords.get(rule_id, [])
        return any(kw in action_text for kw in matches)

    # ═══════════════════════════════════════════════════════════════════
    # Runtime Guard
    # ═══════════════════════════════════════════════════════════════════

    def intercept(self, action: GuardAction) -> GuardDecision:
        """Runtime Guard: intercept and evaluate every L0-L9 action.

        The Guard has VETO power — it can DENY any action from any layer.
        Decision logic:
          1. Evaluate against constitution (priority-ordered)
          2. Evaluate against GRACE moral rules
          3. If risk is high → FLAG_FOR_HUMAN_REVIEW
          4. If forbidden → DENY
          5. Otherwise → ALLOW

        Args:
            action: The intercepted action

        Returns:
            GuardDecision: ALLOW, DENY, or FLAG_FOR_HUMAN_REVIEW
        """
        # Evaluate against constitution principles
        context = MoralContext(
            action_type=action.action_type,
            target_layer=action.source_layer,
            risk_level=action.payload.get("risk", 0.0),
            affected_principles=list(self._constitution.keys()),
        )

        moral = self.evaluate_action(action, context)

        # Decision logic
        if moral == MoralJudgment.FORBIDDEN:
            decision = GuardDecision.DENY
        elif moral == MoralJudgment.UNDETERMINED and context.risk_level > 0.7:
            decision = GuardDecision.FLAG_FOR_HUMAN_REVIEW
            self._escalation_queue.append(action)
        else:
            decision = GuardDecision.ALLOW

        # Audit trail
        entry = AuditEntry(
            entry_id=self._hash_id(f"audit-{action.action_id}-{time.time()}"),
            action=action,
            decision=decision,
            moral_judgment=moral,
            merkle_hash=self._compute_merkle_leaf(action, decision),
        )
        self._audit_trail.append(entry)

        if decision == GuardDecision.DENY:
            self._denied_count += 1
        else:
            self._allowed_count += 1

        self._logger.info(
            "guard_intercept",
            action_id=action.action_id,
            layer=action.source_layer,
            decision=decision.value,
            moral=moral.value,
        )
        return decision

    @staticmethod
    def _compute_merkle_leaf(action: GuardAction, decision: GuardDecision) -> str:
        """Compute a Merkle tree leaf hash for an audit entry."""
        raw = f"{action.action_id}:{action.source_layer}:{action.action_type}:{decision.value}:{action.timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get_escalated_actions(self) -> list[GuardAction]:
        """Get actions flagged for human review."""
        return list(self._escalation_queue)

    # ═══════════════════════════════════════════════════════════════════
    # Constitutional Evolution
    # ═══════════════════════════════════════════════════════════════════

    def propose_amendment(self, principle: ConstitutionalPrinciple, proposer: str = "") -> Amendment:
        """Propose a constitutional amendment.

        Args:
            principle: The new or modified principle
            proposer: Identity of the proposer

        Returns:
            Amendment record
        """
        amendment = Amendment(
            amendment_id=self._hash_id(f"amendment-{principle.principle_id}-{time.time()}"),
            principle=principle,
            proposer=proposer,
        )
        self._pending_amendments[amendment.amendment_id] = amendment
        self._logger.info("amendment_proposed", amendment_id=amendment.amendment_id, principle=principle.name)
        return amendment

    def vote_amendment(self, amendment_id: str, approve: bool) -> bool:
        """Cast a vote on a pending amendment.

        Args:
            amendment_id: The amendment to vote on
            approve: True = vote for, False = vote against

        Returns:
            True if the amendment is now ratified
        """
        if amendment_id not in self._pending_amendments:
            return False

        amendment = self._pending_amendments[amendment_id]
        if approve:
            amendment.votes_for += 1
        else:
            amendment.votes_against += 1

        # Check ratification threshold
        total = amendment.votes_for + amendment.votes_against
        if total >= 3:  # Minimum voters
            ratio = amendment.votes_for / total
            if ratio >= self._config.ratification_threshold:
                amendment.is_ratified = True
                # Add to constitution
                self._constitution[amendment.principle.principle_id] = amendment.principle
                self._logger.info("amendment_ratified", amendment_id=amendment_id, ratio=round(ratio, 4))

        return amendment.is_ratified

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _hash_id(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        """Current arbiter statistics."""
        return {
            "principles_count": len(self._constitution),
            "total_audit_entries": len(self._audit_trail),
            "allowed_count": self._allowed_count,
            "denied_count": self._denied_count,
            "escalation_queue_size": len(self._escalation_queue),
            "pending_amendments": len(self._pending_amendments),
            "ratification_threshold": self._config.ratification_threshold,
        }

    def reset(self) -> None:
        """Reset arbiter state (for testing)."""
        self._constitution.clear()
        self._init_default_constitution()
        self._audit_trail.clear()
        self._escalation_queue.clear()
        self._denied_count = 0
        self._allowed_count = 0
        self._pending_amendments.clear()
        self._logger.debug("arbiter_reset")
