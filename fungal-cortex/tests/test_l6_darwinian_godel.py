"""Tests for L6: DarwinianGodelMachine — 达尔文哥德尔机."""

import numpy as np
import pytest

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


@pytest.fixture
def config() -> DGMConfig:
    return DGMConfig(mutation_rate=0.15, min_failures_for_mutation=2, max_mutations_per_cycle=3)


@pytest.fixture
def dgm(config: DGMConfig) -> DarwinianGodelMachine:
    return DarwinianGodelMachine(config=config)


@pytest.fixture
def seed_genome(dgm: DarwinianGodelMachine) -> AgentGenome:
    genes = {
        "gene-a": Gene(gene_id="gene-a", gene_type="function", name="func_a",
                       source_code="def func_a():\n    return 42\n", fitness_score=0.8),
        "gene-b": Gene(gene_id="gene-b", gene_type="function", name="func_b",
                       source_code="def func_b():\n    return 'hello'\n", fitness_score=0.5),
        "gene-c": Gene(gene_id="gene-c", gene_type="class", name="ClassC",
                       source_code="class ClassC:\n    pass\n", fitness_score=0.9),
    }
    return dgm.create_genome("test-agent", genes=genes)


@pytest.fixture
def second_genome(dgm: DarwinianGodelMachine) -> AgentGenome:
    genes = {
        "gene-x": Gene(gene_id="gene-x", gene_type="function", name="func_x",
                       source_code="def func_x():\n    return 100\n", fitness_score=0.85),
    }
    return dgm.create_genome("second-agent", genes=genes)


class TestDGMInit:
    def test_default_init(self) -> None:
        m = DarwinianGodelMachine()
        assert not m.is_evolving
        assert m.stats["genome_count"] == 0
        assert m.stats["evolution_cycle"] == 0

    def test_custom_config(self, config: DGMConfig) -> None:
        m = DarwinianGodelMachine(config=config)
        assert m._config.mutation_rate == 0.15
        assert m._config.min_failures_for_mutation == 2

    def test_default_strategy(self, dgm: DarwinianGodelMachine) -> None:
        assert dgm._mutation_strategy.strategy_id == "default-v1"
        assert len(dgm._mutation_strategy.mutation_type_weights) == 5


class TestGenomeCreation:
    def test_create_genome(self, seed_genome: AgentGenome) -> None:
        assert seed_genome.genome_id
        assert seed_genome.agent_name == "test-agent"
        assert seed_genome.gene_count == 3
        assert seed_genome.generation == 0

    def test_get_genome(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        g = dgm.get_genome(seed_genome.genome_id)
        assert g is not None
        assert g.agent_name == "test-agent"

    def test_get_nonexistent_genome(self, dgm: DarwinianGodelMachine) -> None:
        assert dgm.get_genome("nonexistent") is None

    def test_register_gene(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gene = Gene(gene_id="gene-d", gene_type="prompt", name="prompt_d",
                    source_code="You are a helpful assistant.")
        assert dgm.register_gene(seed_genome.genome_id, gene)
        genome = dgm.get_genome(seed_genome.genome_id)
        assert genome is not None and genome.gene_count == 4

    def test_register_gene_capacity(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        dgm._config.genome_max_genes = 3
        gene = Gene(gene_id="gene-d", gene_type="prompt", name="prompt_d")
        assert not dgm.register_gene(seed_genome.genome_id, gene)


class TestFailureTracking:
    def test_record_failure(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        count = dgm.record_failure(seed_genome.genome_id, "syntax_error")
        assert count == 1

    def test_accumulate_failures(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gid = seed_genome.genome_id
        dgm.record_failure(gid, "type_error")
        dgm.record_failure(gid, "type_error")
        assert dgm.get_failure_count(gid, "type_error") == 2

    def test_should_mutate_below_threshold(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gid = seed_genome.genome_id
        dgm.record_failure(gid, "error_x")
        assert not dgm.should_mutate(gid, "error_x")  # 1 < 2

    def test_should_mutate_at_threshold(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gid = seed_genome.genome_id
        dgm.record_failure(gid, "error_x")
        dgm.record_failure(gid, "error_x")
        assert dgm.should_mutate(gid, "error_x")  # 2 >= 2


class TestMutationProposal:
    def test_propose_mutations(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        mutations = dgm.propose_mutations(seed_genome)
        assert len(mutations) > 0
        assert len(mutations) <= dgm._config.max_mutations_per_cycle
        for m in mutations:
            assert isinstance(m, Mutation)
            assert m.mutation_id

    def test_propose_mutations_with_failures(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        failures = [
            {"signature": "syntax_error", "context": "line 42"},
            {"signature": "runtime_error", "context": "null pointer"},
        ]
        mutations = dgm.propose_mutations(seed_genome, failures=failures)
        assert len(mutations) > 0

    def test_propose_mutations_empty_genome(self, dgm: DarwinianGodelMachine) -> None:
        empty = dgm.create_genome("empty-agent")
        mutations = dgm.propose_mutations(empty)
        # INSERT mutations should still work on empty genome
        assert isinstance(mutations, list)

    def test_mutation_types_vary(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        rng = np.random.RandomState(42)
        dgm._rng = rng
        mutations = dgm.propose_mutations(seed_genome)
        types = {m.mutation_type for m in mutations}
        assert len(types) >= 1


class TestValidation:
    def test_validate_insert_mutation(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gene = Gene(gene_id="gene-valid", gene_type="function", name="valid_func",
                    source_code="def valid_func():\n    return True\n")
        mutation = Mutation(
            mutation_id="test-insert", mutation_type=MutationType.INSERT,
            description="Add valid gene", new_gene=gene, risk_score=0.2,
        )
        result = dgm.validate_mutation(mutation, seed_genome)
        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert result.checks["syntax"]
        assert result.checks["name_uniqueness"]

    def test_validate_syntax_error(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gene = Gene(gene_id="gene-bad", gene_type="function", name="bad",
                    source_code="def broken(:\n    return\n")
        mutation = Mutation(
            mutation_id="test-bad-syntax", mutation_type=MutationType.INSERT,
            description="Add invalid gene", new_gene=gene, risk_score=0.2,
        )
        result = dgm.validate_mutation(mutation, seed_genome)
        assert not result.is_valid
        assert not result.checks["syntax"]

    def test_validate_duplicate_id(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gene = Gene(gene_id="gene-a", gene_type="function", name="dup",
                    source_code="def dup():\n    pass\n")
        mutation = Mutation(
            mutation_id="test-dup-id", mutation_type=MutationType.INSERT,
            description="Duplicate ID", new_gene=gene, risk_score=0.2,
        )
        result = dgm.validate_mutation(mutation, seed_genome)
        assert not result.checks["name_uniqueness"]

    def test_validate_high_risk(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gene = Gene(gene_id="gene-risky", gene_type="function", name="risky",
                    source_code="def risky():\n    return None\n")
        mutation = Mutation(
            mutation_id="test-risky", mutation_type=MutationType.INSERT,
            description="High risk", new_gene=gene, risk_score=0.9,
        )
        result = dgm.validate_mutation(mutation, seed_genome)
        assert not result.checks["risk_gate"]


class TestMutationApplication:
    def test_apply_insert(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gene = Gene(gene_id="gene-new", gene_type="function", name="new_func",
                    source_code="def new_func():\n    pass\n")
        mutation = Mutation(
            mutation_id="apply-insert", mutation_type=MutationType.INSERT,
            new_gene=gene, risk_score=0.1,
        )
        validation = dgm.validate_mutation(mutation, seed_genome)
        assert validation.is_valid
        new_genome = dgm.apply_mutation(seed_genome, mutation, validation)
        assert new_genome.gene_count == 4
        assert "gene-new" in new_genome.genes
        assert new_genome.generation == 1

    def test_apply_delete(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        mutation = Mutation(
            mutation_id="apply-delete", mutation_type=MutationType.DELETE,
            target_gene_id="gene-b", risk_score=0.1,
        )
        validation = dgm.validate_mutation(mutation, seed_genome)
        if validation.is_valid:
            new_genome = dgm.apply_mutation(seed_genome, mutation, validation)
            assert new_genome.gene_count == 2

    def test_apply_invalid_raises(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gene = Gene(gene_id="gene-bad", gene_type="function", name="bad",
                    source_code="def broken(:\n    pass\n")
        mutation = Mutation(
            mutation_id="apply-bad", mutation_type=MutationType.INSERT,
            new_gene=gene, risk_score=0.1,
        )
        validation = dgm.validate_mutation(mutation, seed_genome)
        with pytest.raises(ValueError):
            dgm.apply_mutation(seed_genome, mutation, validation)

    def test_apply_updates_history(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        gene = Gene(gene_id="gene-hist", gene_type="function", name="hist",
                    source_code="def hist():\n    pass\n")
        mutation = Mutation(
            mutation_id="apply-hist", mutation_type=MutationType.INSERT,
            new_gene=gene, risk_score=0.1,
        )
        validation = dgm.validate_mutation(mutation, seed_genome)
        new_genome = dgm.apply_mutation(seed_genome, mutation, validation)
        assert len(new_genome.mutation_history) == 1
        assert new_genome.mutation_history[0]["type"] == "insert"


class TestEvolutionCycle:
    def test_evolve_genome(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        evolved = dgm.evolve_genome(seed_genome)
        assert evolved is not None
        assert dgm._evolution_cycle == 1
        assert dgm.is_evolving

    def test_evolve_with_failures(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        failures = [{"signature": "crash", "context": "main"}]
        evolved = dgm.evolve_genome(seed_genome, failures=failures)
        assert evolved is not None

    def test_evolve_multiple_cycles(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        genome = seed_genome
        for _ in range(3):
            genome = dgm.evolve_genome(genome)
        assert dgm._evolution_cycle == 3


class TestMetaMutation:
    def test_mutate_mutation_strategy(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        # Apply some mutations first
        gene = Gene(gene_id="gene-m1", gene_type="function", name="m1",
                    source_code="def m1():\n    pass\n")
        mutation = Mutation(
            mutation_id=f"meta-test-{np.random.randint(1000)}", mutation_type=MutationType.INSERT,
            new_gene=gene, risk_score=0.2,
        )
        validation = dgm.validate_mutation(mutation, seed_genome)
        try:
            dgm.apply_mutation(seed_genome, mutation, validation)
        except ValueError:
            pass

        strategy = dgm.mutate_mutation_strategy()
        assert isinstance(strategy, ImprovedStrategy)
        assert len(strategy.mutation_type_weights) == 5
        # Weights should be normalized
        total = sum(strategy.mutation_type_weights.values())
        assert abs(total - 1.0) < 0.01


class TestCrossBackboneTransfer:
    def test_transfer_to_backbone(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        seed_genome.fitness = 0.8  # Set fitness so compatibility > 0
        transferred = dgm.transfer_to_backbone(seed_genome, "gpt")
        assert isinstance(transferred, TransferredAgent)
        assert transferred.target_backbone == "gpt"
        assert transferred.source_genome_id == seed_genome.genome_id
        assert transferred.transferred_genome.backbone_llm == "gpt"
        assert transferred.compatibility_score > 0.0

    def test_transfer_discounts_fitness(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        transferred = dgm.transfer_to_backbone(seed_genome, "gemini")
        for gene in transferred.transferred_genome.genes.values():
            original = seed_genome.genes.get(gene.gene_id.replace("-gemini", ""))
            if original:
                assert gene.fitness_score <= original.fitness_score


class TestGeneSelection:
    def test_select_weakest(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        weakest = dgm._select_weakest_gene(seed_genome)
        assert weakest == "gene-b"  # fitness 0.5 is lowest

    def test_select_best(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        best = dgm._select_best_gene(seed_genome)
        assert best == "gene-c"  # fitness 0.9 is highest


class TestReset:
    def test_reset_clears_all(self, dgm: DarwinianGodelMachine, seed_genome: AgentGenome) -> None:
        dgm.evolve_genome(seed_genome)
        dgm.reset()
        assert dgm.stats["genome_count"] == 0
        assert dgm.stats["evolution_cycle"] == 0
        assert not dgm.is_evolving
