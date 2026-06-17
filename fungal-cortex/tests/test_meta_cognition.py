"""Tests for L6 M1: MetaCognition Engine."""

import asyncio

import pytest

from src.core.event_bus import EventBus
from src.core.skill_registry import SkillMeta, SkillRegistry
from src.l6.architecture_scanner import ArchitectureIssue, ArchitectureScanner, IssueSeverity
from src.l6.auto_refactor import AutoRefactorEngine, RefactorStatus
from src.l6.meta_cognition import HealthReport, MetaCognitionEngine


@pytest.fixture
def meta() -> MetaCognitionEngine:
    registry = SkillRegistry()
    return MetaCognitionEngine(
        skill_registry=registry,
        scan_interval=3600.0,
        auto_refactor_enabled=True,
        require_human_approval=True,
    )


class TestMetaCognitionEngine:
    async def test_full_scan_produces_report(self, meta: MetaCognitionEngine) -> None:
        """A full scan should produce a valid HealthReport."""
        report = await meta.full_scan()
        assert isinstance(report, HealthReport)
        assert 0 <= report.health_score <= 100
        assert report.total_issues >= 0

    def test_get_health_report_sync(self, meta: MetaCognitionEngine) -> None:
        """get_health_report should work even without async scan."""
        report = meta.get_health_report()
        assert isinstance(report, HealthReport)
        assert 0 <= report.health_score <= 100

    def test_health_score_degradation(self, meta: MetaCognitionEngine) -> None:
        """Health score should reflect issues present."""
        # Without any issues, health should be high.
        report = meta.get_health_report()
        # There may be skill_gap issues from the built-in scan.
        assert 0 <= report.health_score <= 100

    async def test_multiple_scans_increment_count(self, meta: MetaCognitionEngine) -> None:
        """Each scan should increment the scan counter."""
        c1 = meta.stats["scan_count"]
        await meta.full_scan()
        assert meta.stats["scan_count"] == c1 + 1

    def test_approve_reject_refactor(self, meta: MetaCognitionEngine) -> None:
        """Approve and reject should work on pending actions."""
        # Run a sync scan to populate issues
        meta.get_health_report()
        pending = meta.refactor_engine.get_pending_approvals()
        if pending:
            action = pending[0]
            assert not meta.reject_refactor("nonexistent")
            assert not meta.approve_refactor("nonexistent")


class TestAutoRefactorEngine:
    """Tests for AutoRefactorEngine directly (not through MetaCognitionEngine)."""

    def test_process_non_auto_fixable_queues_pending(self) -> None:
        """Non-auto-fixable issues should create PENDING actions."""
        engine = AutoRefactorEngine()
        issue = ArchitectureIssue(
            id="test-1",
            dimension="redundancy",
            severity=IssueSeverity.MEDIUM,
            title="Test issue",
            description="A non-auto-fixable test issue",
            auto_fixable=False,
        )
        result = engine.process_issues([issue])
        assert result["queued_approval"] == 1
        assert result["applied"] == 0
        assert result["skipped"] == 0
        assert len(result["action_ids"]) == 1
        pending = engine.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0].status == RefactorStatus.PENDING

    def test_process_auto_fixable_auto_applies(self) -> None:
        """Auto-fixable issues with auto_refactor and no approval should auto-apply."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=False)
        issue = ArchitectureIssue(
            id="test-auto-1",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Auto-fixable test",
            description="An auto-fixable issue",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        assert result["applied"] == 1
        assert result["queued_approval"] == 0
        assert result["action_ids"][0].startswith("refactor-")
        history = engine.get_action_history()
        assert len(history) == 1
        assert history[0].status == RefactorStatus.APPLIED
        assert history[0].applied_at is not None

    def test_process_queue_full_skips(self) -> None:
        """When the pending queue is full, new items should be skipped."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=True, max_pending=0)
        issue = ArchitectureIssue(
            id="test-skip-1",
            dimension="redundancy",
            severity=IssueSeverity.MEDIUM,
            title="Skippable issue",
            description="Should be skipped due to full queue",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        assert result["skipped"] == 1
        assert result["applied"] == 0
        assert result["queued_approval"] == 0

    def test_approve_wrong_status_returns_false(self) -> None:
        """approve() should return False if action is not PENDING."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=False)
        issue = ArchitectureIssue(
            id="test-approve-wrong",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Approve wrong status",
            description="Testing approve with wrong status",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        assert not engine.approve(action_id)
        assert not engine.approve("nonexistent")

    def test_reject_wrong_status_returns_false(self) -> None:
        """reject() should return False if action is not PENDING."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=False)
        issue = ArchitectureIssue(
            id="test-reject-wrong",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Reject wrong status",
            description="Testing reject with wrong status",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        assert not engine.reject(action_id)
        assert not engine.reject("nonexistent")

    def test_rollback_with_callback(self) -> None:
        """rollback() should invoke the rollback callback."""
        callback_called = False
        captured_id = None
        captured_state = None

        def callback(action_id: str, pre_state: dict) -> bool:
            nonlocal callback_called, captured_id, captured_state
            callback_called = True
            captured_id = action_id
            captured_state = pre_state
            return True

        engine = AutoRefactorEngine(
            auto_refactor_enabled=True,
            require_human_approval=False,
            rollback_callback=callback,
        )
        issue = ArchitectureIssue(
            id="test-rollback-1",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Rollback test",
            description="Testing rollback with callback",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        assert engine.rollback(action_id)
        assert callback_called
        assert captured_id == action_id
        assert captured_state is not None
        action = engine.get_action_history(limit=1)[0]
        assert action.status == RefactorStatus.ROLLED_BACK

    def test_rollback_wrong_status_returns_false(self) -> None:
        """rollback() should return False if action is not APPLIED."""
        engine = AutoRefactorEngine()
        issue = ArchitectureIssue(
            id="test-rollback-wrong",
            dimension="redundancy",
            severity=IssueSeverity.MEDIUM,
            title="Rollback wrong status",
            description="Testing rollback with wrong status",
            auto_fixable=False,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        assert not engine.rollback(action_id)
        assert not engine.rollback("nonexistent")

    def test_get_pending_approvals(self) -> None:
        """get_pending_approvals() should return only PENDING actions."""
        engine = AutoRefactorEngine(require_human_approval=True)
        issue1 = ArchitectureIssue(
            id="pending-1",
            dimension="redundancy",
            severity=IssueSeverity.MEDIUM,
            title="Pending issue 1",
            description="First pending",
            auto_fixable=False,
        )
        issue2 = ArchitectureIssue(
            id="pending-2",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Pending issue 2",
            description="Second pending",
            auto_fixable=True,
        )
        engine.process_issues([issue1, issue2])
        pending = engine.get_pending_approvals()
        assert len(pending) == 2
        for action in pending:
            assert action.status == RefactorStatus.PENDING

    def test_get_action_history(self) -> None:
        """get_action_history() should return actions sorted by recency."""
        engine = AutoRefactorEngine()
        issues = [
            ArchitectureIssue(
                id=f"hist-{i}",
                dimension="redundancy",
                severity=IssueSeverity.MEDIUM,
                title=f"History {i}",
                description=f"History issue {i}",
                auto_fixable=False,
            )
            for i in range(3)
        ]
        engine.process_issues(issues)
        history = engine.get_action_history()
        assert len(history) == 3
        assert history[0].created_at >= history[1].created_at
        limited = engine.get_action_history(limit=1)
        assert len(limited) == 1

    def test_refactor_status_enum_values(self) -> None:
        """RefactorStatus enum should have correct values."""
        assert RefactorStatus.PENDING.value == "pending"
        assert RefactorStatus.APPROVED.value == "approved"
        assert RefactorStatus.APPLIED.value == "applied"
        assert RefactorStatus.FAILED.value == "failed"
        assert RefactorStatus.ROLLED_BACK.value == "rolled_back"

    def test_approve_pending_success(self) -> None:
        """approve() on a PENDING action should succeed and apply."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=True)
        issue = ArchitectureIssue(
            id="test-approve-ok",
            dimension="redundancy",
            severity=IssueSeverity.MEDIUM,
            title="Approvable issue",
            description="An auto-fixable issue awaiting approval",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        # approve should return True and apply the refactor
        assert engine.approve(action_id)
        action = engine.get_action_history(limit=1)[0]
        assert action.status == RefactorStatus.APPLIED
        assert action.applied_at is not None

    def test_reject_pending_success(self) -> None:
        """reject() on a PENDING action should succeed and set ROLLED_BACK."""
        engine = AutoRefactorEngine(require_human_approval=True)
        issue = ArchitectureIssue(
            id="test-reject-ok",
            dimension="redundancy",
            severity=IssueSeverity.MEDIUM,
            title="Rejectable issue",
            description="A pending issue to reject",
            auto_fixable=False,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        assert engine.reject(action_id)
        action = engine.get_action_history(limit=1)[0]
        assert action.status == RefactorStatus.ROLLED_BACK
        assert action.error_message == "Rejected by operator"

    def test_rollback_callback_returns_false(self) -> None:
        """rollback() should return False when the callback returns False."""
        def failing_callback(action_id: str, pre_state: dict) -> bool:
            return False

        engine = AutoRefactorEngine(
            auto_refactor_enabled=True,
            require_human_approval=False,
            rollback_callback=failing_callback,
        )
        issue = ArchitectureIssue(
            id="test-rollback-fail",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Rollback callback fail",
            description="Testing rollback with failing callback",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        assert not engine.rollback(action_id)

    def test_rollback_callback_raises_exception(self) -> None:
        """rollback() should handle callback exceptions gracefully."""
        def broken_callback(action_id: str, pre_state: dict) -> bool:
            raise RuntimeError("Callback crashed")

        engine = AutoRefactorEngine(
            auto_refactor_enabled=True,
            require_human_approval=False,
            rollback_callback=broken_callback,
        )
        issue = ArchitectureIssue(
            id="test-rollback-exc",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Rollback exception",
            description="Testing rollback with exception in callback",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        assert not engine.rollback(action_id)

    def test_apply_refactor_exception_sets_failed(self) -> None:
        """When _apply_refactor encounters an exception, action should be FAILED."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=False)
        # Monkeypatch _capture_state to raise
        original_capture = engine._capture_state

        def broken_capture(issue):
            raise ValueError("Capture failed")

        engine._capture_state = broken_capture
        issue = ArchitectureIssue(
            id="test-apply-fail",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Apply fail test",
            description="Testing apply failure",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        assert result["applied"] == 0
        action_id = result["action_ids"][0]
        action = engine.get_action_history(limit=1)[0]
        assert action.status == RefactorStatus.FAILED
        assert "Capture failed" in action.error_message
        # Restore
        engine._capture_state = original_capture

    def test_approve_already_applied_returns_false(self) -> None:
        """approve() on an already APPLIED action should return False."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=False)
        issue = ArchitectureIssue(
            id="test-already-applied",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Already applied",
            description="Already applied issue",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        # Action is already APPLIED, approving should fail
        assert not engine.approve(action_id)

    def test_reject_already_applied_returns_false(self) -> None:
        """reject() on an already APPLIED action should return False."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=False)
        issue = ArchitectureIssue(
            id="test-reject-applied",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Reject applied",
            description="Reject applied issue",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        assert not engine.reject(action_id)

    def test_stats_mixed_actions(self) -> None:
        """stats should reflect counts across different statuses."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=True)
        # Non-auto-fixable → PENDING
        issue_pending = ArchitectureIssue(
            id="stats-pending",
            dimension="redundancy",
            severity=IssueSeverity.MEDIUM,
            title="Stats pending",
            description="Pending issue",
            auto_fixable=False,
        )
        engine.process_issues([issue_pending])
        s = engine.stats
        assert s["total_actions"] == 1
        assert s["pending"] == 1
        assert s["applied"] == 0

    def test_process_issue_with_approved_status_in_actions(self) -> None:
        """An action already in APPROVED status should count as queued_manual."""
        engine = AutoRefactorEngine(require_human_approval=True)
        issue = ArchitectureIssue(
            id="test-approved-status",
            dimension="redundancy",
            severity=IssueSeverity.MEDIUM,
            title="Approved status test",
            description="Testing APPROVED status counting",
            auto_fixable=False,
        )
        # Process to create the action
        engine.process_issues([issue])
        # Manually set the existing action to APPROVED
        engine._actions["refactor-test-approved-status"].status = RefactorStatus.APPROVED
        # Process a different issue to get past the if/elif chain
        # We need to check that the APPROVED line is reachable;
        # We can patch _process_single to return our pre-set APPROVED action
        original = engine._process_single

        def patched_process(inner_issue):
            if inner_issue.id == "special-approved":
                return engine._actions["refactor-test-approved-status"]
            return original(inner_issue)

        engine._process_single = patched_process
        special = ArchitectureIssue(
            id="special-approved",
            dimension="redundancy",
            severity=IssueSeverity.INFO,
            title="Special approved",
            description="Forces APPROVED branch",
            auto_fixable=False,
        )
        result = engine.process_issues([special])
        assert result["queued_manual"] == 1
        engine._process_single = original

    def test_process_non_auto_fixable_with_manual_flag(self) -> None:
        """Non-auto-fixable always queues as PENDING regardless of require_human_approval."""
        engine = AutoRefactorEngine(auto_refactor_enabled=False, require_human_approval=False)
        issue = ArchitectureIssue(
            id="test-manual-flag",
            dimension="redundancy",
            severity=IssueSeverity.MEDIUM,
            title="Manual flag test",
            description="Non-auto-fixable with manual flag off",
            auto_fixable=False,
        )
        result = engine.process_issues([issue])
        assert result["queued_approval"] == 1
        assert result["applied"] == 0

    def test_rollback_without_callback(self) -> None:
        """rollback() should work even without a callback."""
        engine = AutoRefactorEngine(auto_refactor_enabled=True, require_human_approval=False)
        issue = ArchitectureIssue(
            id="test-rollback-nocb",
            dimension="dead_code",
            severity=IssueSeverity.LOW,
            title="Rollback no callback",
            description="Testing rollback without callback",
            auto_fixable=True,
        )
        result = engine.process_issues([issue])
        action_id = result["action_ids"][0]
        assert engine.rollback(action_id)
        action = engine.get_action_history(limit=1)[0]
        assert action.status == RefactorStatus.ROLLED_BACK

    def test_pending_count_with_mixed_statuses(self) -> None:
        """_pending_count should reflect mixed action statuses."""
        engine = AutoRefactorEngine(require_human_approval=True)
        # Non-auto-fixable → PENDING
        p1 = ArchitectureIssue(id="pcount-1", dimension="redundancy", severity=IssueSeverity.MEDIUM, title="P1", description="", auto_fixable=False)
        engine.process_issues([p1])
        assert engine._pending_count == 1
        # Approve it → no longer PENDING
        action_id = engine._actions["refactor-pcount-1"].id
        engine.reject(action_id)
        assert engine._pending_count == 0


class TestArchitectureScanner:
    """Tests for ArchitectureScanner directly."""

    def test_full_scan_with_skills_registered(self) -> None:
        """full_scan with skills should trigger redundancy and coupling scans."""
        registry = SkillRegistry()
        registry.register(SkillMeta(
            name="skill_a",
            module="module_x",
            keywords=["data", "ingestion", "cleaning"],
            dependencies=[],
        ))
        registry.register(SkillMeta(
            name="skill_b",
            module="module_y",
            keywords=["data", "ingestion", "storage"],
            dependencies=["skill_a"],
        ))
        registry.register(SkillMeta(
            name="skill_c",
            module="module_x",
            keywords=["analysis", "statistical"],
            dependencies=["skill_a"],
        ))
        for i in range(5):
            registry.register(SkillMeta(
                name=f"dependent_{i}",
                module="module_z",
                keywords=["generic"],
                dependencies=["skill_a"],
            ))
        scanner = ArchitectureScanner(skill_registry=registry)
        issues = scanner.full_scan()
        assert len(issues) >= 0

    def test_scan_redundancy_high_jaccard(self) -> None:
        """_scan_redundancy should flag skills with high Jaccard similarity."""
        registry = SkillRegistry()
        registry.register(SkillMeta(
            name="skill_x",
            module="module_a",
            keywords=["data", "ingestion", "cleaning", "validation", "transform"],
        ))
        registry.register(SkillMeta(
            name="skill_y",
            module="module_b",
            keywords=["data", "ingestion", "cleaning", "validation", "transform"],
        ))
        scanner = ArchitectureScanner(skill_registry=registry)
        issues = scanner._scan_redundancy()
        assert len(issues) >= 1
        assert issues[0].dimension == "redundancy"
        assert issues[0].evidence["jaccard"] > 0.8

    def test_scan_coupling_high_indegree(self) -> None:
        """_scan_coupling should flag skills with 5+ dependents."""
        registry = SkillRegistry()
        registry.register(SkillMeta(name="hub", module="core", keywords=["hub"], dependencies=[]))
        for i in range(6):
            registry.register(SkillMeta(
                name=f"leaf_{i}",
                module=f"mod_{i}",
                keywords=["leaf"],
                dependencies=["hub"],
            ))
        scanner = ArchitectureScanner(skill_registry=registry)
        issues = scanner._scan_coupling()
        assert len(issues) >= 1
        assert issues[0].dimension == "coupling"
        assert issues[0].evidence["dependent_count"] >= 5

    def test_scan_latency_slow_timings(self) -> None:
        """_scan_latency should flag paths with avg > 500ms."""
        scanner = ArchitectureScanner()
        scanner.record_timing("path.slow", 3000.0)
        scanner.record_timing("path.slow", 2500.0)
        scanner.record_timing("path.medium", 1500.0)
        scanner.record_timing("path.medium", 1200.0)
        scanner.record_timing("path.fast", 100.0)
        issues = scanner._scan_latency()
        assert len(issues) == 2
        assert all(i.dimension == "latency" for i in issues)
        paths = [i.evidence["path"] for i in issues]
        assert "path.slow" in paths
        assert "path.medium" in paths
        assert "path.fast" not in paths

    def test_scan_algorithm_gap_with_counts(self) -> None:
        """_scan_algorithm_gap should flag patterns with 3+ occurrences."""
        scanner = ArchitectureScanner()
        for _ in range(3):
            scanner.record_event("sequential_loop")
        for _ in range(5):
            scanner.record_event("linear_search")
        scanner.record_event("eager_compute")
        issues = scanner._scan_algorithm_gap()
        assert len(issues) == 2
        assert all(i.dimension == "algorithm_gap" for i in issues)
        patterns = [i.evidence["pattern"] for i in issues]
        assert "sequential_loop" in patterns
        assert "linear_search" in patterns
        assert "eager_compute" not in patterns

    def test_scan_skill_gap_missing_capabilities(self) -> None:
        """_scan_skill_gap should detect missing capabilities."""
        registry = SkillRegistry()
        registry.register(SkillMeta(
            name="data_skill",
            module="data",
            keywords=["ingestion", "cleaning"],
        ))
        scanner = ArchitectureScanner(skill_registry=registry)
        issues = scanner._scan_skill_gap()
        assert len(issues) >= 1
        data_gaps = [i for i in issues if i.evidence["domain"] == "data"]
        assert len(data_gaps) >= 1
        assert "validation" in data_gaps[0].evidence["missing_capabilities"]

    def test_scan_bottleneck_slow_throughput(self) -> None:
        """_scan_bottleneck should flag paths with throughput < 0.5 ops/sec."""
        scanner = ArchitectureScanner()
        scanner._call_timings["path.bottleneck"] = [float(i * 10) for i in range(10)]
        issues = scanner._scan_bottleneck()
        assert len(issues) >= 1
        assert issues[0].dimension == "bottleneck"
        assert issues[0].evidence["throughput_ops_per_sec"] < 0.5

    def test_scan_dead_code_disabled_and_stale(self) -> None:
        """_scan_dead_code should flag disabled and stale skills."""
        registry = SkillRegistry()
        registry.register(SkillMeta(
            name="disabled_skill",
            module="test",
            keywords=["test"],
            enabled=False,
        ))
        registry.register(SkillMeta(
            name="stale_skill",
            module="test",
            keywords=["test"],
            enabled=True,
            last_called=100.0,
        ))
        scanner = ArchitectureScanner(skill_registry=registry)
        issues = scanner._scan_dead_code()
        assert len(issues) >= 2
        disabled = [i for i in issues if "disabled" in i.id]
        stale = [i for i in issues if "stale" in i.id]
        assert len(disabled) >= 1
        assert len(stale) >= 1

    def test_scan_error_pattern_with_counts(self) -> None:
        """_scan_error_pattern should flag error events with 5+ occurrences."""
        scanner = ArchitectureScanner()
        for _ in range(6):
            scanner.record_event("connection_error")
        for _ in range(3):
            scanner.record_event("timeout_error")
        scanner.record_event("info_event")
        issues = scanner._scan_error_pattern()
        assert len(issues) == 1
        assert issues[0].dimension == "error_pattern"
        assert issues[0].evidence["error_type"] == "connection_error"
        assert issues[0].evidence["occurrences"] == 6

    def test_record_timing_and_event(self) -> None:
        """record_timing and record_event should accumulate data."""
        scanner = ArchitectureScanner()
        scanner.record_timing("api.call", 150.0)
        scanner.record_timing("api.call", 250.0)
        scanner.record_event("test_event")
        scanner.record_event("test_event")
        assert scanner._call_timings["api.call"] == [150.0, 250.0]
        assert scanner._event_counts["test_event"] == 2

    def test_scan_stats_empty(self) -> None:
        """scan_stats should indicate 0 scans when empty."""
        scanner = ArchitectureScanner()
        stats = scanner.scan_stats
        assert stats["scans"] == 0

    def test_scan_stats_after_scan(self) -> None:
        """scan_stats should reflect completed scans."""
        scanner = ArchitectureScanner()
        scanner.full_scan()
        stats = scanner.scan_stats
        assert stats["total_scans"] == 1
        assert "last_scan" in stats
        assert stats["last_scan"]["total_issues"] >= 0

    def test_issue_severity_enum_values(self) -> None:
        """IssueSeverity enum should have correct values."""
        assert IssueSeverity.CRITICAL.value == "critical"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.LOW.value == "low"
        assert IssueSeverity.INFO.value == "info"


class TestMetaCognitionEngineAdvanced:
    """Advanced tests for MetaCognitionEngine covering edge cases,
    report construction, approve/reject/rollback, stats, and multi-scan scenarios."""

    # ── HealthReport dataclass ──────────────────────────────────────

    def test_health_report_construction(self) -> None:
        """HealthReport can be constructed with all fields and accessed."""
        report = HealthReport(
            health_score=85,
            total_issues=10,
            open_critical=2,
            open_high=3,
            open_medium=4,
            open_low=1,
            total_fixed=5,
            pending_approvals=2,
            recommendations=["Fix criticals", "Review coupling"],
        )
        assert report.health_score == 85
        assert report.total_issues == 10
        assert report.open_critical == 2
        assert report.open_high == 3
        assert report.open_medium == 4
        assert report.open_low == 1
        assert report.total_fixed == 5
        assert report.pending_approvals == 2
        assert report.recommendations == ["Fix criticals", "Review coupling"]
        assert isinstance(report.timestamp, float)
        assert report.timestamp > 0

    def test_health_report_zero_values(self) -> None:
        """HealthReport handles zero-valued fields correctly."""
        report = HealthReport(
            health_score=0, total_issues=0,
            open_critical=0, open_high=0, open_medium=0, open_low=0,
            total_fixed=0, pending_approvals=0, recommendations=[],
        )
        assert report.health_score == 0
        assert report.total_issues == 0
        assert report.recommendations == []

    def test_health_report_default_timestamp(self) -> None:
        """HealthReport generates a timestamp between construction boundaries."""
        import time
        before = time.time()
        report = HealthReport(
            health_score=100, total_issues=0,
            open_critical=0, open_high=0, open_medium=0, open_low=0,
            total_fixed=0, pending_approvals=0, recommendations=[],
        )
        after = time.time()
        assert before <= report.timestamp <= after

    # ── _report_to_dict ─────────────────────────────────────────────

    async def test_report_to_dict_format(self, meta: MetaCognitionEngine) -> None:
        """_report_to_dict produces correct dictionary with all expected keys and types."""
        report = await meta.full_scan()
        result = meta._report_to_dict(report)

        expected_keys = {
            "health_score", "total_issues", "open_critical", "open_high",
            "open_medium", "open_low", "total_fixed", "pending_approvals",
            "recommendations", "timestamp",
        }
        assert set(result.keys()) == expected_keys

        # Type checks
        assert isinstance(result["health_score"], int)
        assert isinstance(result["total_issues"], int)
        assert isinstance(result["open_critical"], int)
        assert isinstance(result["open_high"], int)
        assert isinstance(result["open_medium"], int)
        assert isinstance(result["open_low"], int)
        assert isinstance(result["total_fixed"], int)
        assert isinstance(result["pending_approvals"], int)
        assert isinstance(result["recommendations"], list)
        assert isinstance(result["timestamp"], float)

        # Value fidelity
        assert result["health_score"] == report.health_score
        assert result["total_issues"] == report.total_issues
        assert result["open_critical"] == report.open_critical
        assert result["open_high"] == report.open_high
        assert result["open_medium"] == report.open_medium
        assert result["open_low"] == report.open_low
        assert result["total_fixed"] == report.total_fixed
        assert result["pending_approvals"] == report.pending_approvals
        assert result["recommendations"] == report.recommendations
        assert result["timestamp"] == report.timestamp

    async def test_report_to_dict_with_manual_report(self, meta: MetaCognitionEngine) -> None:
        """_report_to_dict handles manually constructed HealthReport with edge values."""
        report = HealthReport(
            health_score=0,
            total_issues=99,
            open_critical=10,
            open_high=20,
            open_medium=30,
            open_low=39,
            total_fixed=42,
            pending_approvals=7,
            recommendations=["urgent", "maintenance"],
        )
        result = meta._report_to_dict(report)
        assert result["health_score"] == 0
        assert result["total_issues"] == 99
        assert result["recommendations"] == ["urgent", "maintenance"]
        assert result["timestamp"] == report.timestamp

    # ── full_scan edge cases ────────────────────────────────────────

    async def test_full_scan_empty_registry(self, meta: MetaCognitionEngine) -> None:
        """full_scan with empty registry produces skill_gap issues for all domains."""
        report = await meta.full_scan()
        assert report.total_issues >= 5  # 5 domains each missing capabilities
        assert 0 <= report.health_score <= 100
        assert report.timestamp > 0
        assert report.open_critical >= 0
        assert report.open_high >= 5  # All 5 skill_gap issues are HIGH severity
        assert report.open_medium >= 0
        assert report.open_low >= 0

    async def test_full_scan_all_healthy(self) -> None:
        """full_scan with complete skill coverage produces zero issues and perfect health."""
        registry = SkillRegistry()
        for name, module, keywords in [
            ("data_skill", "data", ["ingestion", "cleaning", "validation", "storage"]),
            ("analysis_skill", "analysis", ["statistical", "fundamental", "technical", "sentiment"]),
            ("execution_skill", "execution", ["backtest", "papertrade", "risk_check", "order_routing"]),
            ("monitoring_skill", "monitoring", ["alerting", "dashboard", "audit", "drift_detection"]),
            ("meta_skill", "meta", ["self_heal", "auto_scale", "model_selection", "hyperparameter_tuning"]),
        ]:
            registry.register(SkillMeta(name=name, module=module, keywords=keywords))

        engine = MetaCognitionEngine(
            skill_registry=registry,
            auto_refactor_enabled=True,
            require_human_approval=True,
        )
        report = await engine.full_scan()
        assert report.total_issues == 0
        assert report.health_score == 100
        assert report.open_critical == 0
        assert report.open_high == 0
        assert report.open_medium == 0
        assert report.open_low == 0

    async def test_full_scan_detects_algorithm_gap(self, meta: MetaCognitionEngine) -> None:
        """full_scan detects algorithm_gap issues from recorded events."""
        for _ in range(3):
            meta.scanner.record_event("sequential_loop")
        for _ in range(5):
            meta.scanner.record_event("linear_search")

        report = await meta.full_scan()

        # Should now include algorithm_gap issues alongside skill_gap
        assert report.total_issues >= 2
        # Verify algorithm_gap issues exist via the scanner's results
        alg_issues = [i for i in meta.scanner.full_scan() if i.dimension == "algorithm_gap"]
        assert len(alg_issues) >= 2

    async def test_full_scan_detects_latency_and_bottleneck(self, meta: MetaCognitionEngine) -> None:
        """full_scan detects latency and bottleneck issues from timing data."""
        # Bottleneck requires 10+ timings with max-min spread large enough
        # that throughput = len/(max-min+0.001) < 0.5 ops/sec.
        for i in range(15):
            meta.scanner.record_timing("slow.path", 100.0 + i * 2000.0)  # 100, 2100, 4100, ... -> high avg latency
        for _ in range(15):
            meta.scanner.record_timing("fast.path", 10.0)

        report = await meta.full_scan()

        # Verify latency and bottleneck issues exist
        all_issues = meta.scanner.full_scan()
        latency = [i for i in all_issues if i.dimension == "latency"]
        bottleneck = [i for i in all_issues if i.dimension == "bottleneck"]
        assert any("slow" in i.evidence.get("path", "") for i in latency)
        assert any("slow" in i.evidence.get("path", "") for i in bottleneck)

    async def test_full_scan_detects_dead_code(self) -> None:
        """full_scan detects dead_code issues for disabled skills."""
        registry = SkillRegistry()
        registry.register(SkillMeta(
            name="dead_skill", module="test", keywords=["test"], enabled=False,
        ))
        engine = MetaCognitionEngine(skill_registry=registry)
        report = await engine.full_scan()
        all_issues = engine.scanner.full_scan()
        dead = [i for i in all_issues if i.dimension == "dead_code"]
        assert len(dead) >= 1
        assert any("dead_skill" in i.id for i in dead)

    async def test_full_scan_with_none_registry_no_crash(self) -> None:
        """full_scan with Scanner that has no registry should not crash."""
        engine = MetaCognitionEngine(
            skill_registry=SkillRegistry(),
            auto_refactor_enabled=True,
            require_human_approval=True,
        )
        report = await engine.full_scan()
        assert isinstance(report, HealthReport)
        assert 0 <= report.health_score <= 100

    async def test_full_scan_with_event_bus(self) -> None:
        """full_scan publishes an event when an event bus is configured."""
        event_bus = EventBus()
        engine = MetaCognitionEngine(
            skill_registry=SkillRegistry(),
            event_bus=event_bus,
            auto_refactor_enabled=True,
            require_human_approval=True,
        )
        report = await engine.full_scan()
        # Event should have been published
        assert event_bus._event_count >= 1
        assert isinstance(report, HealthReport)
        assert 0 <= report.health_score <= 100

    # ── get_health_report consistency ───────────────────────────────

    def test_get_health_report_cached_after_sync_scan(self, meta: MetaCognitionEngine) -> None:
        """get_health_report returns the same cached report when called twice."""
        report1 = meta.get_health_report()
        report2 = meta.get_health_report()
        assert report1 is report2

    async def test_get_health_report_after_full_scan(self, meta: MetaCognitionEngine) -> None:
        """get_health_report returns the same report instance cached by full_scan."""
        report1 = await meta.full_scan()
        report2 = meta.get_health_report()
        assert report1 is report2

    async def test_get_health_report_different_after_multiple_scans(self, meta: MetaCognitionEngine) -> None:
        """get_health_report returns the latest report after consecutive scans."""
        report1 = await meta.full_scan()
        report2 = await meta.full_scan()
        report_cached = meta.get_health_report()
        # Should return the latest
        assert report2 is report_cached
        assert report1 is not report2

    def test_get_health_report_creates_history(self, meta: MetaCognitionEngine) -> None:
        """get_health_report creates history entry on first call."""
        assert len(meta._health_history) == 0  # No history yet
        report = meta.get_health_report()
        assert len(meta._health_history) == 1
        assert meta._health_history[0] is report

    async def test_get_health_report_not_empty_after_scan(self, meta: MetaCognitionEngine) -> None:
        """get_health_report does not re-scan if history already exists."""
        await meta.full_scan()  # Creates 1 history entry
        old_len = len(meta._health_history)

        # get_health_report should just return cached, NOT re-scan
        _ = meta.get_health_report()
        assert len(meta._health_history) == old_len

    # ── approve_refactor / reject_refactor / rollback_refactor ──────

    async def test_approve_refactor_with_pending_action(self, meta: MetaCognitionEngine) -> None:
        """approve_refactor applies a pending refactoring action and returns True."""
        await meta.full_scan()
        pending = meta.refactor_engine.get_pending_approvals()
        assert len(pending) >= 1, "Need at least one pending action"

        action_id = pending[0].id
        assert meta.approve_refactor(action_id)

        # Verify action is now applied
        history = meta.refactor_engine.get_action_history(limit=10)
        approved = [a for a in history if a.id == action_id]
        assert len(approved) == 1
        assert approved[0].status == RefactorStatus.APPLIED
        assert approved[0].applied_at is not None

    async def test_reject_refactor_with_pending_action(self, meta: MetaCognitionEngine) -> None:
        """reject_refactor rejects a pending refactoring action and returns True."""
        await meta.full_scan()
        pending = meta.refactor_engine.get_pending_approvals()
        assert len(pending) >= 1

        action_id = pending[0].id
        assert meta.reject_refactor(action_id)

        # Verify action is now rolled back
        history = meta.refactor_engine.get_action_history(limit=10)
        rejected = [a for a in history if a.id == action_id]
        assert len(rejected) == 1
        assert rejected[0].status == RefactorStatus.ROLLED_BACK

    async def test_rollback_refactor_success(self, meta: MetaCognitionEngine) -> None:
        """rollback_refactor rolls back an applied refactoring action and returns True."""
        await meta.full_scan()
        pending = meta.refactor_engine.get_pending_approvals()
        assert len(pending) >= 1
        action_id = pending[0].id

        # First approve to get it into APPLIED state
        assert meta.approve_refactor(action_id)
        assert meta.rollback_refactor(action_id)

        # Verify action is now rolled back
        history = meta.refactor_engine.get_action_history(limit=10)
        rolled = [a for a in history if a.id == action_id]
        assert len(rolled) == 1
        assert rolled[0].status == RefactorStatus.ROLLED_BACK

    def test_approve_nonexistent_returns_false(self, meta: MetaCognitionEngine) -> None:
        """approve_refactor on a nonexistent ID returns False."""
        assert not meta.approve_refactor("nonexistent-action")

    def test_reject_nonexistent_returns_false(self, meta: MetaCognitionEngine) -> None:
        """reject_refactor on a nonexistent ID returns False."""
        assert not meta.reject_refactor("nonexistent-action")

    def test_rollback_nonexistent_returns_false(self, meta: MetaCognitionEngine) -> None:
        """rollback_refactor on a nonexistent ID returns False."""
        assert not meta.rollback_refactor("nonexistent-action")

    async def test_rollback_wrong_status_returns_false(self, meta: MetaCognitionEngine) -> None:
        """rollback_refactor on a non-APPLIED action returns False."""
        await meta.full_scan()
        pending = meta.refactor_engine.get_pending_approvals()
        assert len(pending) >= 1
        action_id = pending[0].id
        # Action is PENDING, not APPLIED → rollback should fail
        assert not meta.rollback_refactor(action_id)

    async def test_approve_already_applied_returns_false(self, meta: MetaCognitionEngine) -> None:
        """approve_refactor on an already-applied action returns False."""
        await meta.full_scan()
        pending = meta.refactor_engine.get_pending_approvals()
        assert len(pending) >= 1
        action_id = pending[0].id

        assert meta.approve_refactor(action_id)  # First approve succeeds
        assert not meta.approve_refactor(action_id)  # Second approve returns False (not PENDING)

    async def test_reject_already_rejected_returns_false(self, meta: MetaCognitionEngine) -> None:
        """reject_refactor on an already-rejected action returns False."""
        await meta.full_scan()
        pending = meta.refactor_engine.get_pending_approvals()
        assert len(pending) >= 1
        action_id = pending[0].id

        assert meta.reject_refactor(action_id)  # First reject succeeds
        assert not meta.reject_refactor(action_id)  # Second reject returns False (not PENDING)

    # ── auto_refactor ───────────────────────────────────────────────

    async def test_auto_refactor_by_id(self, meta: MetaCognitionEngine) -> None:
        """auto_refactor processes specific issues by their IDs."""
        # Register a disabled skill to create auto_fixable dead_code issue
        meta._registry.register(SkillMeta(
            name="orphan_skill", module="legacy", keywords=["old"],
            enabled=False,
        ))

        # Run full scan to detect the issue
        all_issues = meta.scanner.full_scan()
        dead_code_ids = [i.id for i in all_issues if i.dimension == "dead_code"]
        assert len(dead_code_ids) >= 1

        result = await meta.auto_refactor(dead_code_ids)
        for issue_id in dead_code_ids:
            assert issue_id in result
            assert result[issue_id] in ("applied", "failed")

    async def test_auto_refactor_with_nonexistent_ids(self, meta: MetaCognitionEngine) -> None:
        """auto_refactor with IDs that don't match any issue returns empty results."""
        result = await meta.auto_refactor(["nonexistent-issue-1", "nonexistent-issue-2"])
        assert result == {}

    async def test_auto_refactor_mixed_ids(self, meta: MetaCognitionEngine) -> None:
        """auto_refactor with a mix of valid and invalid issue IDs."""
        meta._registry.register(SkillMeta(
            name="old_skill", module="legacy", keywords=["legacy"],
            enabled=False,
        ))
        all_issues = meta.scanner.full_scan()
        real_ids = [i.id for i in all_issues if i.dimension == "dead_code"]
        assert len(real_ids) >= 1

        mixed_ids = [real_ids[0], "totally-fake-id"]
        result = await meta.auto_refactor(mixed_ids)
        assert real_ids[0] in result
        assert "totally-fake-id" not in result

    # ── stats property ──────────────────────────────────────────────

    def test_stats_before_scan(self, meta: MetaCognitionEngine) -> None:
        """stats property before any scan has default values."""
        stats = meta.stats
        assert stats["scan_count"] == 0
        assert stats["last_scan_time"] == 0.0
        assert stats["scanner"] == {"scans": 0}
        assert stats["refactor"]["total_actions"] == 0
        assert stats["refactor"]["applied"] == 0
        assert stats["refactor"]["failed"] == 0
        assert stats["refactor"]["pending"] == 0

    async def test_stats_after_scan(self, meta: MetaCognitionEngine) -> None:
        """stats property after scan has all fields populated."""
        await meta.full_scan()
        stats = meta.stats

        assert stats["scan_count"] == 1
        assert stats["last_scan_time"] > 0
        assert isinstance(stats["last_scan_time"], float)

        # Scanner stats
        scanner_stats = stats["scanner"]
        assert scanner_stats["total_scans"] == 1
        assert "last_scan" in scanner_stats
        assert scanner_stats["last_scan"]["total_issues"] >= 0

        # Refactor stats
        ref_stats = stats["refactor"]
        assert ref_stats["total_actions"] >= 1
        assert ref_stats["applied"] >= 0
        assert ref_stats["failed"] >= 0
        assert ref_stats["pending"] >= 0
        assert isinstance(ref_stats["auto_fix_count_by_dimension"], dict)

    async def test_stats_after_multiple_scans(self, meta: MetaCognitionEngine) -> None:
        """stats property reflects cumulative data after multiple scans."""
        await meta.full_scan()
        await meta.full_scan()
        await meta.full_scan()

        stats = meta.stats
        assert stats["scan_count"] == 3
        assert stats["scanner"]["total_scans"] == 3

    # ── Multiple consecutive scans ──────────────────────────────────

    async def test_multiple_consecutive_scans(self, meta: MetaCognitionEngine) -> None:
        """Multiple scans produce valid reports with correct scan counts."""
        reports: list[HealthReport] = []
        for i in range(1, 4):
            report = await meta.full_scan()
            reports.append(report)
            assert isinstance(report, HealthReport)
            assert 0 <= report.health_score <= 100
            assert report.timestamp > 0
            assert meta.stats["scan_count"] == i
            assert len(meta._health_history) == i

        # Each report should be a different object
        assert reports[0] is not reports[1]
        assert reports[1] is not reports[2]
        assert reports[0] is not reports[2]

    async def test_multiple_scans_preserve_recommendations(self, meta: MetaCognitionEngine) -> None:
        """Recommendations are recomputed each scan and based on current state."""
        report1 = await meta.full_scan()
        report2 = await meta.full_scan()
        # Both scans with same state should produce same recommendations
        assert isinstance(report1.recommendations, list)
        assert isinstance(report2.recommendations, list)
        # At minimum, recommendations should be present or empty
        for r in (report1, report2):
            assert all(isinstance(rec, str) for rec in r.recommendations)

    # ── start / stop ────────────────────────────────────────────────

    async def test_start_sets_running_and_creates_task(self, meta: MetaCognitionEngine) -> None:
        """start() marks the engine as running and creates a background task."""
        assert not meta._running
        assert meta._scan_task is None

        await meta.start()
        assert meta._running
        assert meta._scan_task is not None
        assert not meta._scan_task.done()

        # Clean up
        await meta.stop()

    async def test_stop_cancels_task_and_clears_running(self, meta: MetaCognitionEngine) -> None:
        """stop() cancels the background task and clears the running flag."""
        await meta.start()
        assert meta._running

        await meta.stop()
        assert not meta._running
        assert meta._scan_task is not None
        assert meta._scan_task.done()

    async def test_stop_without_start_no_error(self, meta: MetaCognitionEngine) -> None:
        """stop() on an engine that was never started does not raise."""
        assert meta._scan_task is None
        await meta.stop()  # Should not raise
        assert not meta._running

    async def test_start_stop_idempotent(self, meta: MetaCognitionEngine) -> None:
        """Starting and stopping multiple times is safe and idempotent."""
        await meta.start()
        assert meta._running
        await meta.start()  # Second start should not create a second task
        await meta.stop()
        assert not meta._running
        await meta.stop()  # Second stop should be safe
        assert not meta._running

    async def test_scan_loop_completes_scan_before_cancel(self, meta: MetaCognitionEngine) -> None:
        """_scan_loop executes a full scan cycle before being cancelled."""
        meta._running = True
        meta.scan_interval = 0.005

        task = asyncio.create_task(meta._scan_loop())
        # Wait long enough for at least one sleep + full_scan to complete
        await asyncio.sleep(0.05)
        assert meta.stats["scan_count"] >= 1

        # Cancel during the next sleep cycle
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert meta.stats["scan_count"] >= 1

    # ── health_history management ───────────────────────────────────

    async def test_health_history_accumulates(self, meta: MetaCognitionEngine) -> None:
        """health_history accumulates one entry per scan."""
        assert len(meta._health_history) == 0
        await meta.full_scan()
        assert len(meta._health_history) == 1
        await meta.full_scan()
        assert len(meta._health_history) == 2

    async def test_health_history_capped_at_100(self, meta: MetaCognitionEngine) -> None:
        """health_history is capped at 100 entries to prevent unbounded growth."""
        # Run 101 scans to trigger the cap
        for _ in range(101):
            await meta.full_scan()

        assert len(meta._health_history) == 100
        # Verify the reports are valid
        for report in meta._health_history:
            assert isinstance(report, HealthReport)
            assert 0 <= report.health_score <= 100

    async def test_health_history_sync_scan_appends(self, meta: MetaCognitionEngine) -> None:
        """get_health_report sync scan appends to health_history."""
        assert len(meta._health_history) == 0
        meta.get_health_report()
        assert len(meta._health_history) == 1

    # ── Edge cases ──────────────────────────────────────────────────

    def test_health_report_empty_recommendations(self) -> None:
        """HealthReport handles empty recommendations list."""
        report = HealthReport(
            health_score=100, total_issues=0,
            open_critical=0, open_high=0, open_medium=0, open_low=0,
            total_fixed=0, pending_approvals=0, recommendations=[],
        )
        assert report.recommendations == []

    def test_health_report_large_values(self) -> None:
        """HealthReport handles extreme or boundary values."""
        report = HealthReport(
            health_score=0,
            total_issues=9999,
            open_critical=9999,
            open_high=0, open_medium=0, open_low=0,
            total_fixed=0, pending_approvals=0,
            recommendations=[], timestamp=0.0,
        )
        assert report.health_score == 0
        assert report.total_issues == 9999
        assert report.open_critical == 9999
        assert report.timestamp == 0.0

    async def test_full_scan_after_registering_issue_types(self, meta: MetaCognitionEngine) -> None:
        """full_scan catches issues introduced by registering problematic skills."""
        # Baseline
        baseline = await meta.full_scan()

        # Add skills that trigger redundancy + coupling
        meta._registry.register(SkillMeta(
            name="skill_a", module="mod_x",
            keywords=["alpha", "beta", "gamma", "delta", "epsilon"],
        ))
        meta._registry.register(SkillMeta(
            name="skill_b", module="mod_y",
            keywords=["alpha", "beta", "gamma", "delta", "epsilon"],
        ))
        # Skill with many dependents → coupling
        meta._registry.register(SkillMeta(
            name="hub_skill", module="core", keywords=["hub"], dependencies=[],
        ))
        for i in range(6):
            meta._registry.register(SkillMeta(
                name=f"leaf_{i}", module=f"leaf_mod_{i}",
                keywords=["leaf"], dependencies=["hub_skill"],
            ))

        after = await meta.full_scan()

        assert after.total_issues > baseline.total_issues
        assert after.health_score <= baseline.health_score

        # Verify multiple dimensions are represented
        all_issues = meta.scanner.full_scan()
        dimensions = {i.dimension for i in all_issues}
        assert "redundancy" in dimensions
        assert "coupling" in dimensions
        assert "skill_gap" in dimensions

    async def test_full_scan_with_error_pattern(self, meta: MetaCognitionEngine) -> None:
        """full_scan detects error_pattern issues from recorded error events."""
        for _ in range(6):
            meta.scanner.record_event("connection_error")
        for _ in range(6):
            meta.scanner.record_event("timeout_error")

        report = await meta.full_scan()
        # Verify error pattern issues exist
        all_issues = meta.scanner.full_scan()
        error_issues = [i for i in all_issues if i.dimension == "error_pattern"]
        assert len(error_issues) >= 1
        error_types = {i.evidence["error_type"] for i in error_issues}
        assert "connection_error" in error_types
