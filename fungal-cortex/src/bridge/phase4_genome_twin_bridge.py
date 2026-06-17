"""Phase 4 Genome-Twin Bridge — L6 Genome Evolution ↔ L7 World Model.

Biological Metaphor:
  The hippocampal-prefrontal axis — hippocampus encodes the world model
  (L7 Digital Twin) while prefrontal cortex simulates counterfactuals and
  plans interventions (L6 Darwinian Gödel Machine). Together they form the
  brain's "simulation loop": perceive → model → simulate → act → learn.

  This bridge connects:
    - L6 DarwinianGodelMachine: genome evolution, mutation, validation
    - L6 MAS2ArchitectureCustomizer: task-specific architecture generation
    - L7 ActiveInferenceAgent: free energy minimization, policy selection
    - L7 DigitalTwinEngine: real-time mirroring, anomaly detection

Architecture:
  Task → MAS² (arch generation) → DGM (evolve genome) → AI Agent (plan)
       → DTE (simulate what-if) → AI Agent (select action) → DTE (sync outcome)
       → DGM (learn from failure/success) → Feedback loop

The bridge runs alongside the existing v3.0 MetaCognitionEngine and
EmergenceCrystallizer without replacing them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.config import L6GenomeConfig, L7WorldModelConfig, get_config
from src.l6.darwinian_godel_machine import (
    AgentGenome,
    DGMConfig,
    DarwinianGodelMachine,
    Gene,
    ImprovedStrategy,
    Mutation,
    MutationType,
    TransferredAgent,
    ValidationResult,
)
from src.l6.mas2_architecture_customizer import (
    ArchitectureBenchmark,
    CustomArchitecture,
    MAS2ArchitectureCustomizer,
    MAS2Config,
    TaskProfile,
)
from src.l7.active_inference_agent import (
    Action,
    ActiveInferenceAgent,
    ActiveInferenceConfig,
    Belief,
    Observation,
    Policy,
    Trajectory,
)
from src.l7.digital_twin_engine import (
    AnomalyReport,
    AnomalySeverity,
    DTEConfig,
    DigitalState,
    DigitalTwinEngine,
    HealthReport,
    InterventionPlan,
    PhysicalState,
    PredictedState,
)
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class EvolutionPath(Enum):
    """Which evolution path was used."""
    V3_STATIC = "v3_static"         # Old static architecture
    V4_DARWINIAN = "v4_darwinian"   # New Darwinian Gödel Machine
    HYBRID = "hybrid"               # Both paths fused


@dataclass
class Phase4Result:
    """Complete Phase 4 processing result — genome + architecture + twin."""

    task_description: str
    architecture: CustomArchitecture | None = None
    genome: AgentGenome | None = None
    action: Action | None = None
    intervention: InterventionPlan | None = None
    anomaly: AnomalyReport | None = None
    health: HealthReport | None = None
    evolution_path: EvolutionPath = EvolutionPath.V4_DARWINIAN
    quality_score: float = 0.0
    free_energy: float = 0.0
    evolution_cycle: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════
# Core Bridge
# ═══════════════════════════════════════════════════════════════════════


class Phase4GenomeTwinBridge:
    """Phase 4 Bridge — L6 Genome Evolution + L7 World Model integration.

    Full processing pipeline:
      Task → MAS² Architecture → DGM Genome → AI Policy → DTE Simulate
           → AI Action → DTE Sync → DGM Learn → Feedback

    The bridge can operate with any subset of components enabled,
    allowing gradual rollout alongside v3.0 infrastructure.
    """

    def __init__(
        self,
        enable_dgm: bool = True,
        enable_mas2: bool = True,
        enable_active_inference: bool = True,
        enable_digital_twin: bool = True,
    ) -> None:
        self._logger = CortexLogger(module="phase4_bridge")
        self._enable_dgm = enable_dgm
        self._enable_mas2 = enable_mas2
        self._enable_ai = enable_active_inference
        self._enable_dte = enable_digital_twin

        # Sub-components (initialized in initialize())
        self.dgm: DarwinianGodelMachine | None = None
        self.mas2: MAS2ArchitectureCustomizer | None = None
        self.ai_agent: ActiveInferenceAgent | None = None
        self.dte: DigitalTwinEngine | None = None

        self._is_initialized: bool = False
        self._process_count: int = 0
        self._results: list[Phase4Result] = []
        self._last_result: Phase4Result | None = None

        # Create sub-components immediately if enabled
        if enable_dgm:
            self.dgm = DarwinianGodelMachine()
        if enable_mas2:
            self.mas2 = MAS2ArchitectureCustomizer()
        if enable_active_inference:
            self.ai_agent = ActiveInferenceAgent()
        if enable_digital_twin:
            self.dte = DigitalTwinEngine()

    # ═══════════════════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════════════════

    async def initialize(self) -> None:
        """Initialize all Phase 4 components.

        Bootstraps:
          - A seed genome in DGM
          - Gene pool in MAS²
          - Initial AI agent belief
          - Initial digital twin state
        """
        # Bootstrap DGM with seed genome
        if self._enable_dgm and self.dgm:
            seed_genes = {
                "gene-reasoning": Gene(
                    gene_id="gene-reasoning", gene_type="function",
                    name="reasoning_core", source_code="def reason(ctx):\n    return analyze(ctx)\n",
                    fitness_score=0.75,
                ),
                "gene-planning": Gene(
                    gene_id="gene-planning", gene_type="function",
                    name="planning_core", source_code="def plan(goal):\n    return decompose(goal)\n",
                    fitness_score=0.70,
                ),
                "gene-execution": Gene(
                    gene_id="gene-execution", gene_type="function",
                    name="execution_core", source_code="def execute(plan):\n    return run(plan)\n",
                    fitness_score=0.80,
                ),
            }
            self.dgm.create_genome("bootstrap-agent", genes=seed_genes)
            # Run initial bootstrap evolution
            self.dgm.propose_mutations(
                self.dgm.get_genome(list(self.dgm._genomes.keys())[0]) if self.dgm._genomes else None or AgentGenome(genome_id="x", agent_name="x"),
            )

        # Bootstrap MAS² gene pool
        if self._enable_mas2 and self.mas2:
            for i in range(10):
                self.mas2.register_gene(f"gene-pool-{i}", {"type": "function", "skill": f"skill_{i}"})

        # Bootstrap digital twin
        if self._enable_dte and self.dte:
            initial_physical = PhysicalState(
                state_id="bootstrap-state",
                vector=np.random.RandomState(42).randn(self.dte._config.state_dim) * 0.5,
            )
            self.dte.synchronize(initial_physical)

        self._is_initialized = True
        self._logger.info("phase4_bridge_initialized", dgm=self._enable_dgm, mas2=self._enable_mas2, ai=self._enable_ai, dte=self._enable_dte)

    async def shutdown(self) -> None:
        """Shutdown all Phase 4 components."""
        self._logger.info("phase4_bridge_shutdown", process_count=self._process_count)
        self._is_initialized = False

    # ═══════════════════════════════════════════════════════════════════
    # Primary Pipeline
    # ═══════════════════════════════════════════════════════════════════

    async def evolve_and_simulate(
        self,
        task_description: str,
        state_vector: np.ndarray | None = None,
        goal_state: np.ndarray | None = None,
        complexity: float = 0.5,
    ) -> Phase4Result:
        """Run the full Phase 4 pipeline: evolve → architect → plan → simulate.

        Args:
            task_description: Natural language description of the task
            state_vector: Current system state (for digital twin)
            goal_state: Desired goal state
            complexity: Task complexity estimate (0-1)

        Returns:
            Phase4Result with all pipeline outputs
        """
        self._process_count += 1

        architecture: CustomArchitecture | None = None
        genome: AgentGenome | None = None
        action: Action | None = None
        intervention: InterventionPlan | None = None
        anomaly: AnomalyReport | None = None
        health: HealthReport | None = None

        # Step 1: Analyze task → generate architecture (MAS²)
        if self._enable_mas2 and self.mas2:
            architecture = self.mas2.generate_architecture(task_description)

        # Step 2: Evolve genome for this task (DGM)
        if self._enable_dgm and self.dgm:
            if self.dgm._genomes:
                genome_id = list(self.dgm._genomes.keys())[0]
                genome = self.dgm.get_genome(genome_id)
                if genome:
                    genome = self.dgm.evolve_genome(genome)

        # Step 3: Synchronize digital twin with physical state
        if self._enable_dte and self.dte and state_vector is not None:
            physical = PhysicalState(state_id=f"task-{self._process_count}", vector=state_vector)
            self.dte.synchronize(physical)

            # Detect anomalies
            anomaly = self.dte.detect_anomaly(physical)

        # Step 4: Plan action via Active Inference
        if self._enable_ai and self.ai_agent:
            if goal_state is not None:
                self.ai_agent.set_goal(goal_state)
            action = self.ai_agent.select_action()

        # Step 5: Recommend intervention via Digital Twin
        if self._enable_dte and self.dte:
            intervention = self.dte.recommend_intervention(
                goal_state=goal_state,
            )

        # Step 6: Health check
        if self._enable_dte and self.dte:
            health = self.dte.structural_health_monitoring()

        # Compute scores
        quality = (
            (architecture.estimated_quality if architecture else 0.5)
            + (action.confidence if action else 0.5)
        ) / 2.0 if (architecture or action) else 0.5

        free_energy = action.expected_free_energy if action else 0.0

        result = Phase4Result(
            task_description=task_description,
            architecture=architecture,
            genome=genome,
            action=action,
            intervention=intervention,
            anomaly=anomaly,
            health=health,
            quality_score=round(quality, 4),
            free_energy=round(free_energy, 4),
            evolution_cycle=self.dgm._evolution_cycle if self.dgm else 0,
            metadata={"complexity": complexity},
        )

        self._results.append(result)
        self._last_result = result
        self._logger.info(
            "evolve_and_simulate_complete",
            task=task_description[:60],
            quality=round(quality, 4),
            free_energy=round(free_energy, 4),
        )
        return result

    # ═══════════════════════════════════════════════════════════════════
    # Cross-Backbone Transfer
    # ═══════════════════════════════════════════════════════════════════

    def transfer_between_backbones(
        self,
        source_backbone: str,
        target_backbone: str,
    ) -> TransferredAgent | None:
        """Transfer genome improvements between LLM backbones.

        Args:
            source_backbone: Source LLM (e.g., "claude")
            target_backbone: Target LLM (e.g., "gpt")

        Returns:
            TransferredAgent or None if no genome available
        """
        if not self._enable_dgm or not self.dgm or not self.dgm._genomes:
            return None

        genome_id = list(self.dgm._genomes.keys())[0]
        genome = self.dgm.get_genome(genome_id)
        if genome is None:
            return None

        return self.dgm.transfer_to_backbone(genome, target_backbone)

    # ═══════════════════════════════════════════════════════════════════
    # Benchmark
    # ═══════════════════════════════════════════════════════════════════

    def benchmark_architecture(self, architecture: CustomArchitecture) -> ArchitectureBenchmark | None:
        """Benchmark a MAS² architecture against baseline."""
        if not self._enable_mas2 or not self.mas2:
            return None
        return self.mas2.benchmark_vs_baseline(architecture)

    # ═══════════════════════════════════════════════════════════════════
    # Twin Operations
    # ═══════════════════════════════════════════════════════════════════

    def sync_physical_state(self, vector: np.ndarray, state_id: str = "") -> DigitalState | None:
        """Synchronize a physical state into the digital twin."""
        if not self._enable_dte or not self.dte:
            return None
        physical = PhysicalState(state_id=state_id or f"ext-{time.time()}", vector=vector)
        return self.dte.synchronize(physical)

    def detect_anomalies(self) -> AnomalyReport | None:
        """Run anomaly detection on current digital twin state."""
        if not self._enable_dte or not self.dte:
            return None
        return self.dte.detect_anomaly()

    # ═══════════════════════════════════════════════════════════════════
    # v3.0 Compatibility
    # ═══════════════════════════════════════════════════════════════════

    def to_legacy_meta_report(self, result: Phase4Result) -> dict[str, Any]:
        """Convert Phase 4 result to v3.0 MetaCognition report format."""
        return {
            "report_id": f"p4-{result.timestamp}",
            "task": result.task_description,
            "architecture_topology": result.architecture.topology if result.architecture else "unknown",
            "architecture_roles": result.architecture.role_count if result.architecture else 0,
            "genome_generation": result.genome.generation if result.genome else 0,
            "genome_genes": result.genome.gene_count if result.genome else 0,
            "action_confidence": result.action.confidence if result.action else 0.0,
            "free_energy": result.free_energy,
            "health_score": result.health.overall_health if result.health else 0.0,
            "anomaly_count": result.health.anomaly_count if result.health else 0,
            "evolution_path": result.evolution_path.value,
            "timestamp": result.timestamp,
        }

    # ═══════════════════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════════════════

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    @property
    def stats(self) -> dict[str, Any]:
        """Aggregated bridge statistics."""
        s: dict[str, Any] = {
            "process_count": self._process_count,
            "is_initialized": self._is_initialized,
            "last_result": self._last_result.task_description[:60] if self._last_result else None,
        }
        if self.dgm:
            s["l6_dgm"] = self.dgm.stats
        if self.mas2:
            s["l6_mas2"] = self.mas2.stats
        if self.ai_agent:
            s["l7_ai"] = self.ai_agent.stats
        if self.dte:
            s["l7_dte"] = self.dte.stats
        return s

    def reset(self) -> None:
        """Reset all Phase 4 components."""
        if self.dgm:
            self.dgm.reset()
        if self.mas2:
            self.mas2.reset()
        if self.ai_agent:
            self.ai_agent.reset()
        if self.dte:
            self.dte.reset()
        self._results.clear()
        self._last_result = None
        self._process_count = 0
        self._is_initialized = False
        self._logger.debug("phase4_bridge_reset")
