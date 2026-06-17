"""Tests for L4: AdaptOrchTopologyRouter — 自适应拓扑路由器."""

import numpy as np
import pytest

from src.l4.adapt_orch_topology_router import (
    AdaptOrchTopologyRouter,
    DAGNode,
    OrchestrationTopology,
    TaskDAG,
    TopologyConstraint,
    TopologyRouterConfig,
    TopologyType,
)


@pytest.fixture
def config() -> TopologyRouterConfig:
    return TopologyRouterConfig(max_parallel_workers=4)


@pytest.fixture
def router(config: TopologyRouterConfig) -> AdaptOrchTopologyRouter:
    return AdaptOrchTopologyRouter(config=config)


@pytest.fixture
def linear_dag() -> TaskDAG:
    """A → B → C (sequential chain)."""
    dag = TaskDAG(dag_id="linear")
    dag.add_node(DAGNode(node_id="a", task_description="Step A", estimated_latency_ms=100))
    dag.add_node(DAGNode(node_id="b", task_description="Step B", estimated_latency_ms=200))
    dag.add_node(DAGNode(node_id="c", task_description="Step C", estimated_latency_ms=150))
    dag.add_edge("a", "b")
    dag.add_edge("b", "c")
    dag.update_entry_exit()
    return dag


@pytest.fixture
def parallel_dag() -> TaskDAG:
    """A, B, C independent (parallel)."""
    dag = TaskDAG(dag_id="parallel")
    dag.add_node(DAGNode(node_id="a", task_description="Task A", estimated_latency_ms=100))
    dag.add_node(DAGNode(node_id="b", task_description="Task B", estimated_latency_ms=150))
    dag.add_node(DAGNode(node_id="c", task_description="Task C", estimated_latency_ms=200))
    dag.update_entry_exit()
    return dag


@pytest.fixture
def mixed_dag() -> TaskDAG:
    """A → (B ‖ C) → D."""
    dag = TaskDAG(dag_id="mixed")
    dag.add_node(DAGNode(node_id="a", task_description="Start", estimated_latency_ms=100))
    dag.add_node(DAGNode(node_id="b", task_description="Branch 1", estimated_latency_ms=200))
    dag.add_node(DAGNode(node_id="c", task_description="Branch 2", estimated_latency_ms=250))
    dag.add_node(DAGNode(node_id="d", task_description="Merge", estimated_latency_ms=150))
    dag.add_edge("a", "b")
    dag.add_edge("a", "c")
    dag.add_edge("b", "d")
    dag.add_edge("c", "d")
    dag.update_entry_exit()
    return dag


class TestRouterInit:
    def test_default_init(self) -> None:
        r = AdaptOrchTopologyRouter()
        assert r.stats["route_count"] == 0
        assert r.stats["adaptation_count"] == 0

    def test_custom_config(self, router: AdaptOrchTopologyRouter) -> None:
        assert router._config.max_parallel_workers == 4


class TestTaskDAG:
    def test_create_dag(self) -> None:
        dag = TaskDAG(dag_id="test")
        assert dag.node_count == 0
        assert dag.edge_count == 0

    def test_add_node(self) -> None:
        dag = TaskDAG(dag_id="test")
        dag.add_node(DAGNode(node_id="n1", task_description="Task 1"))
        assert dag.node_count == 1

    def test_add_edge(self) -> None:
        dag = TaskDAG(dag_id="test")
        dag.add_node(DAGNode(node_id="a", task_description="A"))
        dag.add_node(DAGNode(node_id="b", task_description="B"))
        dag.add_edge("a", "b")
        assert dag.nodes["b"].dependencies == ["a"]
        assert dag.nodes["a"].dependents == ["b"]

    def test_entry_exit_nodes(self, linear_dag: TaskDAG) -> None:
        assert linear_dag.entry_nodes == ["a"]
        assert linear_dag.exit_nodes == ["c"]

    def test_parallel_entry_exit(self, parallel_dag: TaskDAG) -> None:
        assert len(parallel_dag.entry_nodes) == 3
        assert len(parallel_dag.exit_nodes) == 3


class TestDAGToTopology:
    def test_map_linear_dag(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(linear_dag)
        assert isinstance(topology, OrchestrationTopology)
        assert topology.topology_type in (TopologyType.SEQUENTIAL, TopologyType.HYBRID)

    def test_map_parallel_dag(self, router: AdaptOrchTopologyRouter, parallel_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(parallel_dag)
        assert topology.topology_type in (TopologyType.PARALLEL, TopologyType.HYBRID)

    def test_map_mixed_dag(self, router: AdaptOrchTopologyRouter, mixed_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(mixed_dag)
        assert topology.stage_count > 0
        assert topology.total_nodes > 0

    def test_topology_estimates_metrics(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(linear_dag)
        assert topology.total_estimated_latency_ms > 0
        assert topology.total_estimated_cost_usd > 0
        assert 0.0 <= topology.estimated_quality <= 1.0

    def test_map_empty_dag(self, router: AdaptOrchTopologyRouter) -> None:
        dag = TaskDAG(dag_id="empty")
        topology = router.map_dag_to_topology(dag)
        assert topology.topology_type == TopologyType.SEQUENTIAL
        assert topology.stage_count == 0

    def test_increments_route_count(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        router.map_dag_to_topology(linear_dag)
        assert router.stats["route_count"] >= 1


class TestConstraintOptimization:
    def test_optimize_for_latency(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(linear_dag)
        optimized = router.optimize_for_constraint(topology, TopologyConstraint.MIN_LATENCY)
        assert isinstance(optimized, OrchestrationTopology)

    def test_optimize_for_cost(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(linear_dag)
        optimized = router.optimize_for_constraint(topology, TopologyConstraint.MIN_COST)
        assert optimized.topology_type == TopologyType.SEQUENTIAL

    def test_optimize_for_quality(self, router: AdaptOrchTopologyRouter, parallel_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(parallel_dag)
        optimized = router.optimize_for_constraint(topology, TopologyConstraint.MAX_QUALITY)
        assert isinstance(optimized, OrchestrationTopology)

    def test_pareto_optimal(self, router: AdaptOrchTopologyRouter, mixed_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(mixed_dag)
        optimized = router.optimize_for_constraint(topology, TopologyConstraint.PARETO_OPTIMAL)
        assert optimized.topology_type == TopologyType.HYBRID


class TestCriticalPath:
    def test_compute_critical_path(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        path, latency = router.compute_critical_path(linear_dag)
        assert len(path) >= 1
        assert latency > 0

    def test_critical_path_empty(self, router: AdaptOrchTopologyRouter) -> None:
        dag = TaskDAG(dag_id="empty")
        path, latency = router.compute_critical_path(dag)
        assert path == []
        assert latency == 0.0


class TestRuntimeAdaptation:
    def test_adapt_slow_worker(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(linear_dag)
        adapted = router.adapt_at_runtime(topology, {"worker_slow": "a"})
        assert isinstance(adapted, OrchestrationTopology)

    def test_adapt_high_quality_worker(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(linear_dag)
        adapted = router.adapt_at_runtime(topology, {"high_quality": "b"})
        assert isinstance(adapted, OrchestrationTopology)

    def test_adapt_failed_worker(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(linear_dag)
        adapted = router.adapt_at_runtime(topology, {"worker_failed": "b"})
        assert isinstance(adapted, OrchestrationTopology)

    def test_adapt_no_change(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        topology = router.map_dag_to_topology(linear_dag)
        adapted = router.adapt_at_runtime(topology, {})
        assert isinstance(adapted, OrchestrationTopology)


class TestWorkerMetrics:
    def test_update_worker_metrics(self, router: AdaptOrchTopologyRouter) -> None:
        router.update_worker_metrics("w1", 500, 0.9, 0.01)
        router.update_worker_metrics("w1", 600, 0.8, 0.02)
        assert router.stats["tracked_workers"] >= 1


class TestReset:
    def test_reset_clears_all(self, router: AdaptOrchTopologyRouter, linear_dag: TaskDAG) -> None:
        router.map_dag_to_topology(linear_dag)
        router.reset()
        assert router.stats["route_count"] == 0
        assert router.stats["adaptation_count"] == 0
