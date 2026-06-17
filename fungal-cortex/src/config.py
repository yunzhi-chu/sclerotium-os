"""Global configuration — YAML + Pydantic v2 with full type safety."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class FieldConfig(BaseModel):
    """Stigmergy field PDE parameters."""

    diffusion_rate_signal: float = Field(default=0.1, ge=0.0, description="D_s: signal diffusion coefficient")
    diffusion_rate_nutrient: float = Field(default=0.05, ge=0.0, description="D_n: nutrient diffusion coefficient")
    diffusion_rate_damage: float = Field(default=0.02, ge=0.0, description="D_d: damage diffusion coefficient")
    reaction_rate: float = Field(default=0.3, ge=0.0, le=1.0, description="Reaction term strength")
    decay_rate: float = Field(default=0.01, ge=0.0, description="Signal decay rate")
    grid_size: tuple[int, int] = Field(default=(256, 256), description="PDE grid dimensions")
    dt: float = Field(default=0.01, ge=1e-6, description="PDE timestep")
    spectral_method: bool = Field(default=True, description="Use FFT spectral method (fast) vs finite difference")


class AgentConfig(BaseModel):
    """Hyphal agent configuration."""

    max_agents: int = Field(default=100, ge=1, description="Maximum agent count")
    branch_probability: float = Field(default=0.05, ge=0.0, le=1.0, description="p_branch: probability of branching per step")
    apoptose_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Nutrient level below which agent apoptoses")
    myelinate_threshold: int = Field(default=100, ge=1, description="Message count to trigger myelination")
    enactive_temperature: float = Field(default=1.0, ge=0.0, description="Temperature for enactive inference exploration")
    prediction_horizon: int = Field(default=10, ge=1, description="Steps to predict forward in enactive loop")


class L6Config(BaseModel):
    """L6 cognitive platform configuration."""

    # M1: MetaCognition
    scan_interval_seconds: int = Field(default=3600, ge=60, description="Seconds between full architecture scans")
    auto_refactor_enabled: bool = Field(default=True, description="Enable automatic refactoring for auto_fixable issues")
    require_human_approval: bool = Field(default=True, description="Require human approval for non-auto_fixable changes")
    max_pending_approvals: int = Field(default=10, ge=1, description="Max pending approval queue size")

    # M2: AbilityCreationFactory
    max_generation_retries: int = Field(default=3, ge=1, description="Max LLM code generation retries")
    sandbox_timeout_seconds: int = Field(default=300, ge=60, description="Sandbox execution timeout")
    min_backtest_sharpe: float = Field(default=0.3, description="Minimum Sharpe ratio to pass sandbox")
    trial_days: int = Field(default=7, ge=1, description="Trial period in sandbox")

    # M4: GlobalGoalExpander
    exploration_domains_count: int = Field(default=19, ge=1, description="Known (7) + exploration (12) domains")
    feasibility_data_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    feasibility_compute_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    feasibility_contribution_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    feasibility_risk_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    feasibility_novelty_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    goal_decomposition_count: int = Field(default=5, ge=1, description="Sub-tasks per goal")

    # M5: SecurityGateway
    rate_limit_per_minute: int = Field(default=60, ge=1)
    rate_limit_per_hour: int = Field(default=1000, ge=1)
    token_bucket_size: int = Field(default=100, ge=1)
    token_refill_rate: float = Field(default=1.0, ge=0.0)

    # M6: RuleEvolution
    ab_test_duration_hours: int = Field(default=48, ge=1, description="Hours for A/B test comparison")
    rule_sharpe_high: float = Field(default=2.0, ge=0.0)
    rule_sharpe_medium: float = Field(default=1.0, ge=0.0)
    rule_max_pos_high: float = Field(default=0.25, ge=0.0, le=1.0)
    rule_max_pos_medium: float = Field(default=0.15, ge=0.0, le=1.0)
    rule_max_pos_low: float = Field(default=0.08, ge=0.0, le=1.0)

    # M7: EmergenceCapture
    interaction_stream_size: int = Field(default=10000, ge=100, description="Max interaction events retained")
    emergence_min_agents: int = Field(default=3, ge=2, description="Minimum independent agents for emergence detection")
    emergence_min_collaborations: int = Field(default=10, ge=1, description="Minimum collaborations for emergence detection")
    crystallize_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Confidence threshold to crystallize")

    # ⑦: Immune Layer
    immune_self_radius: float = Field(default=0.1, ge=0.0, description="Self-set boundary radius in feature space")
    immune_detector_count: int = Field(default=1000, ge=10, description="Initial negative selection detectors")
    immune_detector_coverage: float = Field(default=0.99, ge=0.0, le=1.0, description="Target Nonself coverage")
    immune_memory_retention_days: int = Field(default=90, ge=1, description="Days to retain immune memory")
    immune_false_positive_target: float = Field(default=0.05, ge=0.0, le=1.0)

    # M3: ClusterSelfOrganizer
    cluster_eval_cycle_days: int = Field(default=7, ge=1, description="Days between full agent performance evaluations")
    cluster_success_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    cluster_efficiency_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    cluster_quality_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    cluster_resource_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    cluster_excellent_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    cluster_underperforming_threshold: float = Field(default=0.40, ge=0.0, le=1.0)
    cluster_underperforming_strikes: int = Field(default=3, ge=1, description="Consecutive underperforming evals before destroy")
    cluster_coordinator_min_same: int = Field(default=3, ge=2, description="Min same-specialty agents to elect coordinator")

    # ⑤: Holographic Metacognition
    holo_compression_target_ratio: float = Field(default=100.0, ge=1.0, description="Target compression ratio for event→interference pattern")
    holo_interference_bits: int = Field(default=10 * 1024 * 8, ge=1024, description="Interference pattern size in bits (default 10KB)")
    holo_frequency_bands: int = Field(default=8, ge=2, description="Number of frequency bands for holographic encoding")
    holo_coherence_decay: float = Field(default=0.01, ge=0.0, le=1.0, description="Per-step coherence decay rate")
    holo_anomaly_sigma: float = Field(default=3.0, ge=1.0, description="Sigma threshold for anomaly detection")

    # ④: Thermodynamic Engine
    thermo_temperature_initial: float = Field(default=1.0, ge=0.0, description="Initial thermodynamic temperature")
    thermo_temperature_min: float = Field(default=0.01, ge=1e-6)
    thermo_temperature_max: float = Field(default=10.0, ge=0.0)
    thermo_noise_scale: float = Field(default=0.1, ge=0.0, description="Langevin noise amplitude")
    thermo_dissipation_budget: float = Field(default=0.1, ge=0.0, le=1.0, description="Q_budget: fraction of steps allocated to exploration")
    thermo_spectrum_bins: int = Field(default=64, ge=8, description="Kolmogorov spectrum frequency bins")
    thermo_spectrum_exponent_target: float = Field(default=-1.67, description="Target Kolmogorov exponent (-5/3)")

    # ⑥: Quantum-Classical Dual-Mode
    quantum_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Confidence below this → quantum mode exploration")
    quantum_superposition_states: int = Field(default=8, ge=2, description="Number of parallel hypothesis states in quantum mode")
    quantum_decoherence_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    quantum_recurrence_depth: int = Field(default=3, ge=1, description="Revisits to possibility space before collapse")
    quantum_superradiance_boost: float = Field(default=2.0, ge=1.0, description="Speedup factor in quantum mode")

    # ③: Dendritic Integration
    dendrite_branching_factor: float = Field(default=3.0, ge=1.0, description="Average child branches per dendritic node")
    dendrite_max_depth: int = Field(default=6, ge=1, description="Max dendritic tree depth")
    dendrite_coincidence_window_ms: float = Field(default=25.0, ge=1.0, description="Δt window for coincidence detection (ms)")
    dendrite_supralinear_exponent: float = Field(default=1.5, ge=1.0, description="Supralinear activation exponent (Ca²⁺ cooperativity)")
    dendrite_integration_window_ms: float = Field(default=500.0, ge=10.0, description="BMP-style temporal integration window (ms)")

    # ⑨: Morphogen Patterning
    morphogen_gradient_length: float = Field(default=1.0, ge=0.1, description="Global morphogen gradient spatial scale")
    morphogen_activator_rate: float = Field(default=0.5, ge=0.0, description="Turing activator production rate")
    morphogen_inhibitor_rate: float = Field(default=0.3, ge=0.0, description="Turing inhibitor production rate")
    morphogen_activator_diffusion: float = Field(default=0.01, ge=0.0, description="Activator diffusion coefficient (short range)")
    morphogen_inhibitor_diffusion: float = Field(default=0.1, ge=0.0, description="Inhibitor diffusion coefficient (long range)")
    morphogen_pattern_scale: int = Field(default=32, ge=4, description="Turing pattern grid size")

    # ⑩: Synaptive Multilevel Evolution
    evo_l1_population_size: int = Field(default=50, ge=4, description="L1 parameter evolution population")
    evo_l1_mutation_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    evo_l1_generations: int = Field(default=20, ge=1)
    evo_l2_success_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Agent success threshold for proliferation")
    evo_l2_apoptose_threshold: float = Field(default=0.2, ge=0.0, le=1.0, description="Agent failure threshold for apoptosis")
    evo_l3_architecture_mutation_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    evo_enforcement_penalty: float = Field(default=0.3, ge=0.0, le=1.0, description="Enforcement agent penalty for ego-deviation")

    # ⑫: Panarchy Resilience
    panarchy_r_phase_duration: int = Field(default=30, ge=1, description="Growth (r) phase typical duration (days)")
    panarchy_k_phase_duration: int = Field(default=90, ge=1, description="Conservation (K) phase typical duration (days)")
    panarchy_omega_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Connectedness level triggering Ω release")
    panarchy_revolt_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Revolt cascade trigger threshold")
    panarchy_remember_strength: float = Field(default=0.3, ge=0.0, le=1.0, description="Remember constraint strength from higher level")
    panarchy_intermediate_disturbance: float = Field(default=0.15, ge=0.0, le=1.0, description="Optimal intermediate disturbance level")


class PipelineConfig(BaseModel):
    """L0→L7 8-layer cognitive pipeline configuration."""

    max_pipeline_depth: int = Field(default=8, ge=1, le=8)
    layer_timeout_seconds: float = Field(default=30.0, ge=1.0)
    pipeline_tick_interval: float = Field(default=0.1, ge=0.01)
    l0_adaptive_engine_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    l3_debate_max_rounds: int = Field(default=5, ge=1, description="Max BULL/BEAR debate rounds")
    l6_risk_faction_count: int = Field(default=3, ge=1, description="Aggressive/Conservative/Neutral")


class BridgeConfig(BaseModel):
    """Bridge layer configuration — Fungal Cortex ↔ QuantMind OS."""

    skill_adapter_batch_size: int = Field(default=50, ge=1)
    skill_adapter_retry_count: int = Field(default=3, ge=1)
    dna_vector_dimensions: int = Field(default=6, ge=1, description="Strategy DNA vector dimension count")
    dna_loader_batch_size: int = Field(default=100, ge=1)
    indicator_compile_timeout: float = Field(default=10.0, ge=1.0)
    ktd_fin_barra_factors: int = Field(default=7, ge=1, description="Barra risk factor count")
    final_bench_ma_threshold: float = Field(default=0.694, ge=0.0)
    final_bench_er_threshold: float = Field(default=0.302, ge=0.0)
    final_bench_gap_max: float = Field(default=0.3, ge=0.0)
    claim_debate_max_claims: int = Field(default=10, ge=1)


class AutocatalyticConfig(BaseModel):
    """Autocatalytic closure configuration."""

    catalysis_ring_min_size: int = Field(default=3, ge=2, description="Minimum ring size for catalysis detection")
    catalysis_graph_max_nodes: int = Field(default=500, ge=10)
    phase_transition_n_crit: int = Field(default=10, ge=1, description="Critical catalytic ring count for phase transition")
    constraint_closure_check_interval: int = Field(default=3600, ge=60)
    raf_set_max_size: int = Field(default=100, ge=10)


class TradingConfig(BaseModel):
    """Trading layer configuration."""

    data_pipeline_tick_buffer: int = Field(default=10000, ge=100)
    data_pipeline_markets: list[str] = Field(default=["cn", "hk", "us"])
    risk_gate_count: int = Field(default=5, ge=1)
    risk_gate_factions: list[str] = Field(default=["aggressive", "conservative", "neutral"])
    portfolio_max_positions: int = Field(default=50, ge=1)
    portfolio_rebalance_interval_hours: int = Field(default=24, ge=1)
    portfolio_max_single_position: float = Field(default=0.25, ge=0.0, le=1.0)


class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""

    prometheus_port: int = Field(default=9090, ge=1024, le=65535)
    prometheus_collect_interval: int = Field(default=15, ge=1, description="Seconds between metric collection")
    alert_check_interval: int = Field(default=60, ge=1)
    alert_max_history: int = Field(default=1000, ge=10)
    grafana_dashboard_dir: str = Field(default="monitoring/grafana_dashboards")


class LLMConfig(BaseModel):
    """LLM routing configuration."""

    deep_think_model: str = Field(default="deepseek-pro", description="Model for complex reasoning")
    quick_think_model: str = Field(default="deepseek-flash", description="Model for fast responses")
    fallback_model: str = Field(default="deepseek-pro", description="Fallback model")
    max_tokens_deep: int = Field(default=8192, ge=1)
    max_tokens_quick: int = Field(default=2048, ge=1)
    temperature_deep: float = Field(default=0.3, ge=0.0, le=2.0)
    temperature_quick: float = Field(default=0.7, ge=0.0, le=2.0)


class CoreConfig(BaseModel):
    """Core infrastructure configuration."""

    event_bus_backlog: int = Field(default=10000, ge=100, description="Max queued events before backpressure")
    skill_registry_auto_reload: bool = Field(default=True, description="Auto-reload skills on file change")
    cognitive_depth_default: int = Field(default=3, ge=1, le=6, description="Default cognitive depth (L1-L6)")


class L1Config(BaseModel):
    """L1: Liquid Perception Layer configuration (Phase 1 v4.0)."""

    # LiquidPerceptor
    lnn_n_hidden: int = Field(default=64, ge=8, description="Hidden state dimension for LNN ODE")
    lnn_tau_default: float = Field(default=1.0, ge=0.1, le=5.0, description="Default liquid time constant")
    lnn_tau_min: float = Field(default=0.1, ge=0.01, description="Minimum time constant")
    lnn_tau_max: float = Field(default=5.0, ge=0.5, description="Maximum time constant")
    lnn_solver_steps_min: int = Field(default=4, ge=1, description="Minimum ODE solver steps")
    lnn_solver_steps_max: int = Field(default=64, ge=4, description="Maximum ODE solver steps")
    lnn_surprise_ema_alpha: float = Field(default=0.1, ge=0.0, le=1.0)
    lnn_confidence_ema_alpha: float = Field(default=0.05, ge=0.0, le=1.0)
    lnn_adaptation_threshold: float = Field(default=0.15, ge=0.0, le=1.0)

    # SNN Encoder
    snn_n_neurons: int = Field(default=128, ge=8, description="Number of encoding neurons")
    snn_duration_ms: float = Field(default=100.0, ge=10.0, description="Spike encoding window (ms)")
    snn_rate_max_hz: float = Field(default=200.0, ge=10.0, description="Maximum firing rate")
    snn_lif_tau_m: float = Field(default=20.0, ge=1.0, description="Membrane time constant (ms)")
    snn_lif_v_threshold: float = Field(default=-50.0, description="Firing threshold (mV)")


class L2Config(BaseModel):
    """L2: Liquid Routing + Multi-Model Orchestration config (Phase 1 v4.0)."""

    # LiquidTimeConstantNet
    ltn_input_dim: int = Field(default=64, ge=8, description="Input dimension (from LiquidPerceptor)")
    ltn_hidden_dim: int = Field(default=64, ge=8, description="Hidden embedding dimension")
    ltn_n_strategies: int = Field(default=12, ge=2, description="Number of strategy types")
    ltn_n_indicators: int = Field(default=32, ge=4, description="Number of indicator params")
    ltn_n_safety_gates: int = Field(default=8, ge=2, description="Number of safety gates")
    ltn_tau_default: float = Field(default=0.5, ge=0.05, le=1.0)
    ltn_alpha_surprise: float = Field(default=0.3, ge=0.0, le=1.0)
    ltn_beta_confidence: float = Field(default=0.15, ge=0.0, le=1.0)
    ltn_tau_ema_alpha: float = Field(default=0.1, ge=0.0, le=1.0)
    ltn_jit_enabled: bool = Field(default=True)

    # MultiModelRouter
    router_top_k: int = Field(default=3, ge=1, description="Number of models to select per query")
    router_quality_weight: float = Field(default=0.40, ge=0.0, le=1.0)
    router_cost_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    router_latency_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    router_reliability_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    router_max_cost_per_query: float = Field(default=0.10, ge=0.0)


class L3Config(BaseModel):
    """L3: Mycorrhizal Debate Network configuration (Phase 2 v4.0).

    Inspired by MNIS (Nature Micro 2026) — 8-parameter mycorrhizal network
    intelligence scoring with 91.8% predictive accuracy and 42-day early warning.
    """

    # MycorrhizalDebateNetwork
    mdn_topology: str = Field(default="small_world", description="Network topology: hub_spoke, mesh, small_world")
    mdn_hub_count: int = Field(default=3, ge=1, description="Number of hub nodes (hub-spoke topology)")
    mdn_mesh_degree: int = Field(default=4, ge=2, description="Average degree in mesh topology")
    mdn_small_world_rewiring: float = Field(default=0.1, ge=0.0, le=1.0, description="Small-world rewiring probability")
    mdn_consensus_threshold: float = Field(default=0.667, ge=0.5, le=1.0, description="≥2/3 consensus threshold")
    mdn_mnis_weights: list[float] = Field(default=[0.15,0.15,0.1,0.1,0.15,0.1,0.1,0.15], description="8-parameter MNIS weights")
    mdn_propagation_steps: int = Field(default=5, ge=1, description="Max claim propagation hops")
    mdn_nutrient_decay: float = Field(default=0.05, ge=0.0, le=1.0, description="Node nutrient decay per propagation step")

    # NeutrosophicCausalValidator
    ncv_accept_t: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum truth threshold T")
    ncv_accept_f: float = Field(default=0.2, ge=0.0, le=1.0, description="Maximum falsity threshold F")
    ncv_accept_i: float = Field(default=0.3, ge=0.0, le=1.0, description="Maximum indeterminacy threshold I")
    ncv_do_intervention_samples: int = Field(default=1000, ge=100, description="Monte Carlo samples for do-operator")
    ncv_merge_method: str = Field(default="weighted_average", description="Verdict merge: weighted_average, min_max, dempster_shafer")

    # CrossDomainClaimNormalizer
    cdn_default_domain: str = Field(default="finance", description="Default domain for unclassified claims")
    cdn_max_claims_per_skill: int = Field(default=10, ge=1, description="Max claims extracted per SKILL.md")
    cdn_domain_detection_confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="Min confidence for auto domain detection")
    cdn_supported_domains: list[str] = Field(default=["finance","medical","legal","engineering","ai_ml","cybersecurity"])


class L5Config(BaseModel):
    """L5: Stigmergy Field v2.0 + Swarm Self-Organization (Phase 2 v4.0).

    Inspired by 70-day 18-agent experiment (Mycel Network 2026) —
    Stigmergy solved 32× more problems than hierarchy, tolerated 45% bad actors.
    Harvard RAnts (PRX Life 2026) — Exbodied Intelligence through two-parameter control.
    """

    # StigmergyFieldV2
    stg_trace_grid_size: int = Field(default=1024, ge=64, description="Trace grid dimension (N×N)")
    stg_citation_halflife_hours: float = Field(default=24.0, ge=0.1, description="Citation decay half-life (hours)")
    stg_niche_overlap_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Jaccard threshold for niche overlap")
    stg_trust_history_window: int = Field(default=100, ge=10, description="Behavior history window for trust scoring")
    stg_trust_citation_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    stg_trust_consistency_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    stg_trust_contribution_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    stg_resilience_bad_actor_ratio: float = Field(default=0.45, ge=0.0, le=1.0, description="Bad actor ratio for resilience testing")
    stg_norm_propagation_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Adoption threshold for norm propagation")
    stg_max_trace_age_days: int = Field(default=90, ge=1, description="Max trace retention (days)")

    # SwarmSelfOrganizer
    sso_cooperation_default: float = Field(default=0.5, ge=-1.0, le=1.0, description="Default cooperation strength")
    sso_deposition_default: float = Field(default=0.5, ge=-1.0, le=1.0, description="Default deposition rate")
    sso_nucleation_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Pheromone concentration threshold for nucleation")
    sso_phase_hysteresis: float = Field(default=0.1, ge=0.0, le=0.5, description="Hysteresis margin for phase switching")
    sso_photormone_decay_rate: float = Field(default=0.01, ge=0.0, le=1.0, description="Photormone decay per step")


class L4Config(BaseModel):
    """L4: RL Conductor + Causal Debug Engine configuration (Phase 3 v4.0).

    Inspired by Sakana AI RL Conductor (2026) — 7B model RL-trained to orchestrate
    GPT-5+Claude+Gemini achieving 93.3% AIME25. Causal-Agent-Replay (CAR 2025) —
    SCM + do-calculus for precise agent failure attribution.
    AdaptOrch (Feb 2026) — topology optimization O(|V|+|E|).
    """

    # RLConductorOrchestrator
    rl_training_episodes: int = Field(default=1000, ge=10, description="RL training episodes for orchestration policy")
    rl_learning_rate: float = Field(default=0.001, ge=1e-6, le=0.1, description="RL policy learning rate")
    rl_discount_factor: float = Field(default=0.95, ge=0.5, le=1.0, description="RL discount factor γ")
    rl_exploration_epsilon: float = Field(default=0.1, ge=0.0, le=1.0, description="ε-greedy exploration rate")
    rl_state_dim: int = Field(default=128, ge=16, description="RL state embedding dimension")
    rl_action_pool_size: int = Field(default=10, ge=2, description="Number of candidate actions (model+topology choices)")
    rl_reward_quality_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    rl_reward_cost_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    rl_reward_latency_weight: float = Field(default=0.2, ge=0.0, le=1.0)

    # AdaptOrchTopologyRouter
    aot_topology_types: list[str] = Field(default=["sequential","parallel","hierarchical","hybrid"])
    aot_default_timeout_ms: float = Field(default=30000.0, ge=100.0, description="Default topology stage timeout (ms)")
    aot_max_parallel_workers: int = Field(default=8, ge=1, description="Max parallel workers in PARALLEL topology")
    aot_adaptive_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Threshold for runtime topology adaptation")

    # CausalDebugEngine
    cde_max_scm_nodes: int = Field(default=100, ge=10, description="Max nodes in SCM graph")
    cde_do_resample_count: int = Field(default=100, ge=10, description="Monte Carlo resamples for do-operator")
    cde_shapley_samples: int = Field(default=500, ge=50, description="Shapley value estimation samples")
    cde_attribution_confidence: float = Field(default=0.95, ge=0.5, le=1.0, description="Confidence level for causal attribution")
    cde_min_effect_size: float = Field(default=0.1, ge=0.0, le=1.0, description="Minimum causal effect size to report")


class L6GenomeConfig(BaseModel):
    """L6: Genome Evolution configuration (Phase 4 v4.0).

    Inspired by Hyperagents/Darwinian Gödel Machine (ICLR 2026) —
    recursive self-modification with formal verification, Git-backed genome,
    5 mutation types, cross-backbone transfer.

    MAS² (ICLR 2026) — dynamic multi-agent architecture generation
    with Generator+Implementer+Rectifier collaboration, +19.6% SOTA.
    """

    # DarwinianGodelMachine
    dgm_mutation_rate: float = Field(default=0.1, ge=0.0, le=1.0, description="Base mutation probability per gene")
    dgm_min_failures_for_mutation: int = Field(default=3, ge=1, description="Consecutive failures to trigger mutation")
    dgm_validation_confidence: float = Field(default=0.95, ge=0.5, le=1.0, description="Required validation confidence")
    dgm_max_mutations_per_cycle: int = Field(default=5, ge=1, description="Max mutations per evolution cycle")
    dgm_genome_max_genes: int = Field(default=500, ge=10, description="Max genes (functions/classes) in genome")
    dgm_crossover_probability: float = Field(default=0.2, ge=0.0, le=1.0, description="Probability of CROSSOVER mutation")
    dgm_duplicate_probability: float = Field(default=0.15, ge=0.0, le=1.0, description="Probability of DUPLICATE mutation")
    dgm_meta_mutation_interval: int = Field(default=50, ge=10, description="Cycles between meta-strategy mutations")
    dgm_transfer_confidence_discount: float = Field(default=0.8, ge=0.0, le=1.0, description="Initial confidence discount for cross-backbone transfer")

    # MAS²ArchitectureCustomizer
    mas2_min_agents_per_arch: int = Field(default=2, ge=1, description="Minimum agents in generated architecture")
    mas2_max_agents_per_arch: int = Field(default=10, ge=2, description="Maximum agents in generated architecture")
    mas2_rectifier_max_iterations: int = Field(default=5, ge=1, description="Max rectify-test cycles")
    mas2_rectifier_quality_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="Quality threshold to stop rectification")
    mas2_benchmark_samples: int = Field(default=50, ge=10, description="Benchmark evaluation samples")


class L7WorldModelConfig(BaseModel):
    """L7: World Model + Digital Twin configuration (Phase 4 v4.0).

    Inspired by Active Digital Twin (PoliMi 2025-2026) — POMDP world model
    with Active Inference engine, predictive coding, and free energy minimization.

    Active Inference for IoT (ACM 2025) — expected free energy for action
    selection, balancing pragmatic value + epistemic value.
    """

    # ActiveInferenceAgent
    ai_hidden_state_dim: int = Field(default=128, ge=16, description="Hidden state dimension for generative model")
    ai_observation_dim: int = Field(default=64, ge=8, description="Observation embedding dimension")
    ai_policy_horizon: int = Field(default=5, ge=1, description="Number of future steps to evaluate per policy")
    ai_epistemic_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for epistemic value (uncertainty reduction)")
    ai_pragmatic_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for pragmatic value (goal achievement)")
    ai_learning_rate: float = Field(default=0.01, ge=1e-6, le=0.1, description="Generative model learning rate")
    ai_belief_update_steps: int = Field(default=10, ge=1, description="Gradient steps per belief update")
    ai_free_energy_tolerance: float = Field(default=0.001, ge=1e-6, description="Free energy convergence tolerance")
    ai_precision_default: float = Field(default=1.0, ge=0.1, description="Default sensory precision (inverse variance)")

    # DigitalTwinEngine
    dt_sync_interval_ms: float = Field(default=100.0, ge=10.0, description="Physical-digital sync interval (ms)")
    dt_simulation_horizon_steps: int = Field(default=100, ge=10, description="Default forward simulation steps")
    dt_anomaly_threshold_sigma: float = Field(default=3.0, ge=1.0, description="Sigma threshold for anomaly detection")
    dt_min_anomaly_probability: float = Field(default=0.01, ge=0.0, le=1.0, description="Min tail probability for anomaly flag")
    dt_max_interventions_per_cycle: int = Field(default=5, ge=1, description="Max interventions evaluated per cycle")
    dt_health_check_interval_steps: int = Field(default=50, ge=10, description="Steps between health monitoring checks")


class L8Config(BaseModel):
    """L8: Self-Referential Evolution Compiler configuration (Phase 5 v4.0).

    Inspired by Hyperagents DGM-H (ICLR 2026) — full-system genome serialization,
    recursive self-improvement cycle, safety invariant checking.
    """

    src_monitor_interval_seconds: int = Field(default=3600, ge=60, description="Full-system monitoring interval (seconds)")
    src_max_chromosomes: int = Field(default=200, ge=10, description="Max files (chromosomes) in system genome")
    src_improve_cycle_phases: int = Field(default=6, ge=3, description="Number of phases in self-improve cycle")
    src_invariant_check_count: int = Field(default=4, ge=1, description="Number of safety invariants to verify")
    src_meta_learn_memory_size: int = Field(default=100, ge=10, description="Meta-learning strategy memory size")
    src_export_backbones: list[str] = Field(default=["claude", "gpt", "gemini", "deepseek"], description="Supported export backbones")
    src_apply_atomic: bool = Field(default=True, description="Apply improvements atomically (all-or-nothing)")
    src_rollback_on_invariant_violation: bool = Field(default=True, description="Auto-rollback on invariant violation")


class L9Config(BaseModel):
    """L9: Edge Mesh + Quantum Bridge configuration (Phase 5 v4.0).

    Inspired by Totoro+ P2P FL (IEEE TPDS 2026) — DHT-based P2P model sync,
    O(log N) hop propagation, differential privacy aggregation.

    Hybrid QRL (Quantum ML Intelligence 2026) — VQC actor + classical critic,
    NISQ-era compatible shallow circuits.
    """

    # P2P Mesh
    p2p_max_peers: int = Field(default=100, ge=2, description="Maximum P2P peers in mesh")
    p2p_gossip_ttl_default: int = Field(default=3, ge=1, description="Default Gossip TTL (hops)")
    p2p_gossip_target_coverage: float = Field(default=0.8, ge=0.0, le=1.0, description="Target coverage ratio for Gossip")
    p2p_kademlia_k: int = Field(default=20, ge=2, description="Kademlia DHT k-bucket size")
    p2p_dp_epsilon: float = Field(default=1.0, ge=0.01, description="Differential privacy ε budget")
    p2p_dp_delta: float = Field(default=1e-5, ge=1e-10, description="Differential privacy δ parameter")
    p2p_knowledge_aggregation_k: int = Field(default=5, ge=1, description="KNN neighbors for knowledge aggregation")

    # Hybrid Quantum Agent
    hqa_qubits: int = Field(default=8, ge=2, description="Number of qubits in VQC circuit")
    hqa_vqc_layers: int = Field(default=4, ge=1, description="Variational layers in quantum circuit")
    hqa_classical_hidden_dim: int = Field(default=64, ge=8, description="Classical critic hidden dimension")
    hqa_ppo_clip_epsilon: float = Field(default=0.2, ge=0.01, le=1.0, description="PPO clipping epsilon")
    hqa_anneal_reads: int = Field(default=1000, ge=100, description="Quantum annealing read count")
    hqa_backend: str = Field(default="simulator", description="Quantum backend: simulator, ibmq, ionq, rigetti")


class L10Config(BaseModel):
    """L10: Constitutional Governance + Conscious Kernel configuration (Phase 5 v4.0).

    Inspired by GRACE (IASEAI 2026) — deontic logic + runtime guard verification.
    Phua (2025) — synthetic neurophenomenology, IIT+GWT+HOT unification.
    ACI (Escolà-Gascón 2025) — attributed consciousness index.
    """

    # ConstitutionalArbiter
    ca_principles_count: int = Field(default=4, ge=2, description="Number of constitutional principles")
    ca_require_human_approval: bool = Field(default=True, description="Require human approval for amendments")
    ca_ratification_threshold: float = Field(default=0.667, ge=0.5, le=1.0, description="≥2/3 consensus for ratification")
    ca_max_escalation_queue: int = Field(default=50, ge=10, description="Max human review escalation queue")
    ca_audit_merkle_depth: int = Field(default=16, ge=4, description="Merkle tree depth for audit trail")

    # ConsciousKernel
    ck_phi_computation_depth: int = Field(default=3, ge=1, description="MIP search depth for Φ computation")
    ck_gwt_processor_count: int = Field(default=12, ge=2, description="Number of competing processors in GWT")
    ck_hot_meta_levels: int = Field(default=2, ge=1, description="Higher-order representation levels")
    ck_aci_emergence_threshold: float = Field(default=10.0, ge=0.0, description="ACI threshold for SELF_AWARE emergence")
    ck_phenomenal_dimensions: int = Field(default=4, ge=2, description="Phenomenal experience dimensions (flow/tone/surprisal/integration)")
    ck_causal_ablation_trials: int = Field(default=100, ge=10, description="Trials per causal ablation test")


class AppConfig(BaseModel):
    """Root configuration aggregating all sub-configs."""

    field: FieldConfig = Field(default_factory=FieldConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    l1: L1Config = Field(default_factory=L1Config)
    l2: L2Config = Field(default_factory=L2Config)
    l3: L3Config = Field(default_factory=L3Config)
    l4: L4Config = Field(default_factory=L4Config)
    l5: L5Config = Field(default_factory=L5Config)
    l6: L6Config = Field(default_factory=L6Config)
    l6_genome: L6GenomeConfig = Field(default_factory=L6GenomeConfig)
    l7: L7WorldModelConfig = Field(default_factory=L7WorldModelConfig)
    l8: L8Config = Field(default_factory=L8Config)
    l9: L9Config = Field(default_factory=L9Config)
    l10: L10Config = Field(default_factory=L10Config)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    core: CoreConfig = Field(default_factory=CoreConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    bridge: BridgeConfig = Field(default_factory=BridgeConfig)
    autocatalytic: AutocatalyticConfig = Field(default_factory=AutocatalyticConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    @classmethod
    def from_yaml(cls, path: Optional[Path] = None) -> AppConfig:
        """Load config from YAML file, falling back to env vars and defaults."""
        if path is None:
            path = Path(os.environ.get("FUNGAL_CORTEX_CONFIG", "config.yaml"))
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        return cls(**data)

    def to_yaml(self, path: Path) -> None:
        """Persist current config to YAML file."""
        with open(path, "w") as f:
            yaml.safe_dump(self.model_dump(), f, default_flow_style=False)


# Global singleton (replaced during DI in production)
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global config singleton. Initializes with defaults if not set."""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def set_config(config: AppConfig) -> None:
    """Set the global config singleton (use for testing / DI)."""
    global _config
    _config = config
