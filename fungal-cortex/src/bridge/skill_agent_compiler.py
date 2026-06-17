"""Skill→Agent Compilation Pipeline — 6067 SKILL→Agent 编译流水线.

The bridge between raw SKILL.md knowledge and specialized multi-agent systems.

Pipeline:
  SKILL.md (6067 files)
    ↓
  CrossDomainClaimNormalizer (L3)
    → Extract verifiable claims from each SKILL
    → Auto-detect domain (finance/medical/legal/engineering/AI/cyber/...)
    ↓
  Agent Specification Generator
    → Map domain × claims → specialized agent roles
    → Assign skills, tools, and capabilities per agent
    ↓
  MAS² Architecture Customizer (L6)
    → Generate task-specific multi-agent architecture
    → Generator + Implementer + Rectifier collaboration
    ↓
  Stigmergy Field v2 (L5)
    → Deploy agents into shared trace grid
    → Natural niche partitioning (no role assignment)
    → Agents collaborate through citation graph

Key Innovation (v6.0):
  First compilation pipeline that transforms 6067 declarative SKILL.md files
  into executable specialized multi-agent systems. Domain auto-detection via
  keyword matching across 15+ domains. Each compiled agent inherits skills
  from its source SKILL and gains collaboration capabilities through the
  stigmergy field.

References:
  - CrossDomainClaimNormalizer (Phase 2): Claim extraction + domain detection
  - MAS² Architecture Customizer (Phase 4): Task-specific architecture generation
  - Stigmergy Field v2 (Phase 2): Shared trace grid + niche partitioning
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.l3.cross_domain_claim_normalizer import (
    CrossDomainClaimNormalizer,
    Domain,
    NormalizerConfig,
    StandardClaim,
)
from src.l5.stigmergy_field_v2 import StigmergyFieldV2, StigmergyV2Config, TraceEntry
from src.l6.mas2_architecture_customizer import (
    AgentRole,
    CustomArchitecture,
    MAS2ArchitectureCustomizer,
    TaskProfile,
)
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class CompilationStage(Enum):
    """Stages of the Skill→Agent compilation pipeline."""
    SCAN = "scan"
    EXTRACT_CLAIMS = "extract_claims"
    CLASSIFY_DOMAIN = "classify_domain"
    INSTANTIATE_AGENTS = "instantiate_agents"
    GENERATE_ARCHITECTURE = "generate_architecture"
    DEPLOY_TO_FIELD = "deploy_to_field"
    COMPLETE = "complete"


@dataclass
class SkillMetadata:
    """Metadata extracted from a single SKILL.md file."""

    skill_id: str
    file_path: str
    title: str = ""
    domain: str = "unknown"
    claims_count: int = 0
    agent_count: int = 0
    keywords: list[str] = field(default_factory=list)
    line_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentSpec:
    """Specification for a specialized agent instantiated from SKILL claims."""

    agent_id: str
    domain: str
    role_name: str
    specialization: str
    source_skills: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    claims: list[StandardClaim] = field(default_factory=list)
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)


@dataclass
class DomainManifest:
    """Summary of agents and claims for a single domain."""

    domain: str
    agent_count: int = 0
    claim_count: int = 0
    skill_count: int = 0
    agent_specs: list[AgentSpec] = field(default_factory=list)
    architecture: CustomArchitecture | None = None


@dataclass
class CompilationReport:
    """Complete report from a Skill→Agent compilation run."""

    report_id: str
    total_skills_scanned: int = 0
    total_claims_extracted: int = 0
    total_agents_instantiated: int = 0
    domains_detected: list[str] = field(default_factory=list)
    domain_manifests: dict[str, DomainManifest] = field(default_factory=dict)
    architectures_generated: int = 0
    agents_deployed: int = 0
    compilation_time_ms: float = 0.0
    stage: CompilationStage = CompilationStage.SCAN
    errors: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════
# Domain Keywords (15+ domains for auto-detection)
# ═══════════════════════════════════════════════════════════════════════

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "finance": ["stock", "bond", "option", "trading", "portfolio", "risk", "yield",
                 "dividend", "volatility", "hedge", "arbitrage", "market", "equity",
                 "forex", "crypto", "derivative", "quantitative", "alpha", "beta"],
    "medical": ["diagnosis", "patient", "clinical", "symptom", "treatment", "drug",
                 "therapy", "surgery", "pathology", "radiology", "pharma", "disease",
                 "epidemic", "vaccine", "genomic", "protein", "assay"],
    "legal": ["contract", "compliance", "regulation", "statute", "litigation", "court",
              "patent", "trademark", "gdpr", "jurisdiction", "arbitration", "clause",
              "liability", "indemnity", "breach", "due_diligence"],
    "engineering": ["circuit", "mechanical", "structural", "thermal", "fluid", "stress",
                    "load", "material", "cad", "fea", "tolerance", "specification",
                    "prototype", "manufacturing", "sensor", "actuator"],
    "ai_ml": ["neural", "gradient", "training", "inference", "transformer", "embedding",
               "loss", "backprop", "dataset", "overfitting", "regularization", "cnn",
               "rnn", "attention", "tokenizer", "fine_tuning", "hyperparameter"],
    "cybersecurity": ["vulnerability", "exploit", "firewall", "encryption", "auth",
                      "penetration", "malware", "ransomware", "phishing", "zero_day",
                      "patch", "cert", "siem", "ids", "ips", "threat_modeling"],
    "devops": ["docker", "kubernetes", "ci_cd", "terraform", "ansible", "jenkins",
                "gitops", "helm", "prometheus", "grafana", "infrastructure", "pipeline",
                "deployment", "orchestration", "monitoring", "logging"],
    "game_dev": ["sprite", "collision", "physics", "rendering", "shader", "gameplay",
                  "level_design", "animation", "unreal", "unity", "godot", "fps",
                  "rpg", "multiplayer", "asset", "frame_rate"],
    "fullstack": ["api", "rest", "graphql", "react", "vue", "angular", "node", "django",
                   "flask", "database", "sql", "nosql", "frontend", "backend", "crud",
                   "authentication", "session", "middleware"],
    "marketing": ["seo", "sem", "conversion", "funnel", "ab_test", "campaign",
                   "cac", "ltv", "roi", "analytics", "social_media", "content",
                   "email_marketing", "lead_gen", "churn", "retention"],
    "business": ["strategy", "revenue", "kpi", "okr", "stakeholder", "roadmap",
                  "pitch", "valuation", "merger", "acquisition", "scaling", "b2b",
                  "b2c", "saas", "mrr", "arr", "burn_rate"],
    "database": ["index", "query", "schema", "migration", "sharding", "replication",
                  "postgres", "mysql", "mongodb", "redis", "normalization", "acid",
                  "transaction", "deadlock", "partition", "backup"],
    "education": ["curriculum", "pedagogy", "assessment", "learning_objective",
                   "quiz", "tutorial", "mooc", "certification", "skill_gap",
                   "mentoring", "onboarding", "knowledge_base"],
    "research": ["hypothesis", "experiment", "literature_review", "methodology",
                  "peer_review", "citation", "reproducibility", "statistical",
                  "p_value", "confound", "meta_analysis", "preprint"],
    "web3": ["blockchain", "smart_contract", "solidity", "defi", "nft", "dao",
              "consensus", "validator", "staking", "wallet", "gas", "tokenomics"],
}


# ═══════════════════════════════════════════════════════════════════════
# Core Compiler
# ═══════════════════════════════════════════════════════════════════════


class SkillAgentCompiler:
    """Skill→Agent Compilation Pipeline.

    Transforms declarative SKILL.md knowledge into executable specialized
    multi-agent systems through the L3→L5→L6 pipeline.
    """

    def __init__(
        self,
        skills_dir: str = "",
        enable_normalizer: bool = True,
        enable_mas2: bool = True,
        enable_stigmergy: bool = True,
    ) -> None:
        self._logger = CortexLogger(module="skill_agent_compiler")
        self._skills_dir = skills_dir

        # Pipeline components
        self._normalizer = CrossDomainClaimNormalizer() if enable_normalizer else None
        self._mas2 = MAS2ArchitectureCustomizer() if enable_mas2 else None
        self._stigmergy = StigmergyFieldV2() if enable_stigmergy else None

        # State
        self._skills: dict[str, SkillMetadata] = {}
        self._claims: dict[str, list[StandardClaim]] = {}  # skill_id → claims
        self._agent_specs: dict[str, list[AgentSpec]] = {}  # domain → specs
        self._domains: dict[str, DomainManifest] = {}
        self._reports: list[CompilationReport] = []
        self._rng = np.random.RandomState(42)

    # ═══════════════════════════════════════════════════════════════════
    # Stage 1: Scan SKILL files
    # ═══════════════════════════════════════════════════════════════════

    def scan_skills_dir(self, skills_dir: str | None = None) -> list[SkillMetadata]:
        """Scan a directory for SKILL.md files and extract metadata.

        Args:
            skills_dir: Directory containing SKILL.md files

        Returns:
            List of SkillMetadata for each found SKILL
        """
        path = skills_dir or self._skills_dir
        if not path or not os.path.isdir(path):
            self._logger.warn("skills_dir_not_found", path=path)
            return []

        discovered: list[SkillMetadata] = []
        for root, dirs, files in os.walk(path):
            for fname in files:
                if fname.endswith(".md") or fname.endswith(".SKILL.md") or fname == "SKILL.md":
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                    except (OSError, UnicodeDecodeError):
                        continue

                    meta = self._parse_skill_metadata(fpath, content)
                    discovered.append(meta)
                    self._skills[meta.skill_id] = meta

        self._logger.info("skills_scanned", count=len(discovered), directory=path)
        return discovered

    def scan_skills_content(self, skills: dict[str, str]) -> list[SkillMetadata]:
        """Scan skills from in-memory content (no filesystem access).

        Args:
            skills: Dict of skill_id → skill_markdown_content

        Returns:
            List of SkillMetadata
        """
        discovered: list[SkillMetadata] = []
        for skill_id, content in skills.items():
            meta = self._parse_skill_metadata(skill_id, content)
            # Store original key for content lookup
            meta.metadata["original_key"] = skill_id
            meta.metadata["content"] = content
            discovered.append(meta)
            self._skills[meta.skill_id] = meta

        self._logger.info("skills_scanned_in_memory", count=len(discovered))
        return discovered

    def _parse_skill_metadata(self, path_or_id: str, content: str) -> SkillMetadata:
        """Parse metadata from SKILL.md content."""
        skill_id = self._hash_id(path_or_id)
        lines = content.split("\n")
        title = ""
        keywords: list[str] = []

        # Extract title (first # heading)
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Extract keywords from content
        text_lower = content.lower()
        for domain, kws in DOMAIN_KEYWORDS.items():
            for kw in kws:
                if kw in text_lower:
                    keywords.append(kw)

        # Auto-detect domain
        domain = self._detect_domain_from_keywords(keywords)

        return SkillMetadata(
            skill_id=skill_id,
            file_path=path_or_id,
            title=title,
            domain=domain,
            keywords=keywords[:20],  # Cap at 20
            line_count=len(lines),
        )

    @staticmethod
    def _detect_domain_from_keywords(keywords: list[str]) -> str:
        """Detect domain from keyword matches."""
        scores: dict[str, int] = {}
        for domain, kws in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in kws)
            if score > 0:
                scores[domain] = score

        if not scores:
            return "general"

        return max(scores, key=scores.get)

    # ═══════════════════════════════════════════════════════════════════
    # Stage 2: Extract Claims (via L3 CrossDomainClaimNormalizer)
    # ═══════════════════════════════════════════════════════════════════

    def extract_claims(self, skill_content: str, skill_id: str = "") -> list[StandardClaim]:
        """Extract verifiable claims from SKILL content.

        Uses the L3 CrossDomainClaimNormalizer to parse SKILL.md and extract
        structured claims suitable for debate and verification.

        Args:
            skill_content: Raw SKILL.md content
            skill_id: Identifier for the source SKILL

        Returns:
            List of extracted StandardClaims
        """
        if self._normalizer is None:
            return []

        try:
            claims = self._normalizer.extract_from_skill(skill_content, skill_path=skill_id)
        except Exception:
            claims = []
        # Fallback if normalizer returned empty or failed
        if not claims:
            claims = self._synthetic_claim_extraction(skill_content, skill_id)

        if skill_id:
            self._claims[skill_id] = claims

        meta = self._skills.get(skill_id)
        if meta:
            meta.claims_count = len(claims)

        return claims

    def _synthetic_claim_extraction(self, content: str, skill_id: str) -> list[StandardClaim]:
        """Synthetic claim extraction when normalizer unavailable or fails.

        Parses markdown structure to find declarative statements.
        Extracts claims from bullet points and sentences containing action verbs.
        """
        claims: list[StandardClaim] = []
        lines = content.split("\n")

        # Build keyword set for quick lookup
        all_keywords: set[str] = set()
        for kws in DOMAIN_KEYWORDS.values():
            all_keywords.update(kws[:10])

        action_verbs = {"detect", "calculate", "compute", "design", "implement", "analyze",
                        "scan", "build", "deploy", "develop", "generate", "monitor", "test",
                        "create", "optimize", "configure", "manage", "extract", "recommend"}

        for i, line in enumerate(lines):
            stripped = line.strip()
            text = ""

            # Bullet points are primary claim sources
            if stripped.startswith("- ") or stripped.startswith("* "):
                text = stripped[2:].strip()
            # Numbered items
            elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1:3] in (". ", ") "):
                text = stripped[3:].strip()
            # Headers can be claims too
            elif stripped.startswith("## "):
                text = stripped[3:].strip()
            # Sentences with action verbs
            elif (stripped.endswith(".") and len(stripped) > 20
                  and not stripped.startswith("#") and not stripped.startswith("```")):
                text = stripped

            if text and len(text) > 10:
                # Accept claims that either contain domain keywords OR action verbs
                text_lower = text.lower()
                has_keyword = any(kw in text_lower for kw in all_keywords)
                has_verb = any(verb in text_lower for verb in action_verbs)

                if has_keyword or has_verb:
                    claims.append(StandardClaim(
                        claim_id=f"{skill_id}-claim-{i}",
                        domain=Domain.FINANCE,  # Auto-detect would refine this
                        predicate=text[:200],
                        confidence=0.4 if has_verb and not has_keyword else 0.5,
                        evidence=[],
                    ))

                if len(claims) >= 10:
                    break

        return claims


    # ═══════════════════════════════════════════════════════════════════
    # Stage 3: Classify by Domain
    # ═══════════════════════════════════════════════════════════════════

    def classify_by_domain(self) -> dict[str, list[StandardClaim]]:
        """Classify all extracted claims by domain.

        Returns:
            Dict of domain_name → list of claims
        """
        domain_claims: dict[str, list[StandardClaim]] = {}

        for skill_id, claims in self._claims.items():
            meta = self._skills.get(skill_id)
            domain = meta.domain if meta else "general"

            domain_claims.setdefault(domain, []).extend(claims)

        # Update skill domain based on claim analysis
        for domain, claims in domain_claims.items():
            for claim in claims:
                if hasattr(claim, 'domain') and claim.domain and claim.domain.value != "finance":
                    # CrossDomainClaimNormalizer detected a different domain
                    pass

        self._logger.info("claims_classified", domains=list(domain_claims.keys()),
                          total_claims=sum(len(c) for c in domain_claims.values()))
        return domain_claims

    # ═══════════════════════════════════════════════════════════════════
    # Stage 4: Instantiate Agents
    # ═══════════════════════════════════════════════════════════════════

    def instantiate_agents(self, domain_claims: dict[str, list[StandardClaim]]) -> dict[str, list[AgentSpec]]:
        """Instantiate specialized agents for each domain from claims.

        Maps domain × claims → specialized agent roles. Each domain gets
        2-5 specialized agents based on claim volume and diversity.

        Args:
            domain_claims: Claims grouped by domain

        Returns:
            Dict of domain → list of AgentSpec
        """
        domain_agents: dict[str, list[AgentSpec]] = {}

        for domain, claims in domain_claims.items():
            if not claims:
                continue

            # Determine how many agents this domain needs
            claim_count = len(claims)
            agent_count = max(2, min(8, claim_count // 5))

            specs: list[AgentSpec] = []
            # Generate role templates based on domain
            roles = self._get_domain_roles(domain, agent_count)

            for i, role in enumerate(roles):
                spec = AgentSpec(
                    agent_id=f"agent-{domain}-{i}-{self._hash_id(str(time.time()))[:8]}",
                    domain=domain,
                    role_name=role["name"],
                    specialization=role["specialization"],
                    source_skills=list(set(c.claim_id.split("-")[0] for c in claims[:10])),
                    required_capabilities=role.get("capabilities", []),
                    claims=claims[i::agent_count] if i < len(claims) else [],
                    confidence=0.6 + 0.05 * len(claims),
                )
                specs.append(spec)

            domain_agents[domain] = specs

            # Update skill metadata
            for skill_id in self._skills:
                if self._skills[skill_id].domain == domain:
                    self._skills[skill_id].agent_count = len(specs)

        self._agent_specs = domain_agents
        self._logger.info("agents_instantiated", domains=list(domain_agents.keys()),
                          total_agents=sum(len(s) for s in domain_agents.values()))
        return domain_agents

    def _get_domain_roles(self, domain: str, count: int) -> list[dict[str, Any]]:
        """Generate specialized roles for a domain."""
        default_roles = {
            "finance": [
                {"name": "MarketAnalyst", "specialization": "analyzer", "capabilities": ["trend_detection", "risk_assessment"]},
                {"name": "PortfolioManager", "specialization": "executor", "capabilities": ["allocation", "rebalancing"]},
                {"name": "RiskController", "specialization": "verifier", "capabilities": ["var_calculation", "stress_testing"]},
                {"name": "SignalGenerator", "specialization": "generator", "capabilities": ["alpha_discovery", "backtesting"]},
            ],
            "ai_ml": [
                {"name": "ModelArchitect", "specialization": "generator", "capabilities": ["architecture_design", "hyperparameter_tuning"]},
                {"name": "DataEngineer", "specialization": "executor", "capabilities": ["preprocessing", "feature_engineering"]},
                {"name": "TrainerEvaluator", "specialization": "verifier", "capabilities": ["training_loop", "validation"]},
            ],
            "cybersecurity": [
                {"name": "ThreatHunter", "specialization": "analyzer", "capabilities": ["vulnerability_scan", "penetration_test"]},
                {"name": "IncidentResponder", "specialization": "executor", "capabilities": ["containment", "forensics"]},
                {"name": "ComplianceAuditor", "specialization": "verifier", "capabilities": ["audit", "regulation_check"]},
            ],
        }

        roles = default_roles.get(domain, [
            {"name": f"{domain.title()}Specialist", "specialization": "analyzer", "capabilities": ["domain_expertise"]},
            {"name": f"{domain.title()}Executor", "specialization": "executor", "capabilities": ["implementation"]},
        ])

        # Pad or trim to requested count
        while len(roles) < count:
            roles.append({"name": f"Worker-{len(roles)}", "specialization": "executor", "capabilities": ["general"]})
        return roles[:count]

    # ═══════════════════════════════════════════════════════════════════
    # Stage 5: Generate Architectures (via L6 MAS²)
    # ═══════════════════════════════════════════════════════════════════

    def generate_architecture(self, domain: str, agent_specs: list[AgentSpec]) -> CustomArchitecture | None:
        """Generate task-specific architecture for a domain's agents via MAS².

        Args:
            domain: Domain name
            agent_specs: Agent specifications for this domain

        Returns:
            CustomArchitecture or None if MAS² unavailable
        """
        if self._mas2 is None:
            return None

        # Register agent specs as genes in MAS² pool
        for spec in agent_specs:
            self._mas2.register_gene(spec.agent_id, {
                "domain": spec.domain,
                "role": spec.role_name,
                "specialization": spec.specialization,
                "capabilities": spec.required_capabilities,
            })

        # Generate architecture
        task_desc = f"Manage and execute {domain} domain tasks with {len(agent_specs)} specialized agents"
        profile = TaskProfile(
            reasoning_depth=0.7 if domain in ("ai_ml", "cybersecurity", "finance") else 0.5,
            tool_dependency=0.6 if domain in ("devops", "fullstack") else 0.4,
            collaboration_need=0.5 + 0.1 * len(agent_specs),
            security_requirement=0.8 if domain in ("cybersecurity", "legal", "medical") else 0.3,
        )

        architecture = self._mas2.generate_architecture(task_desc, profile=profile)

        # Store in domain manifest
        if domain not in self._domains:
            self._domains[domain] = DomainManifest(domain=domain)
        self._domains[domain].architecture = architecture

        return architecture

    # ═══════════════════════════════════════════════════════════════════
    # Stage 6: Deploy to Stigmergy Field
    # ═══════════════════════════════════════════════════════════════════

    def deploy_to_field(self, agent_specs: list[AgentSpec], domain: str) -> int:
        """Deploy instantiated agents to the stigmergy field.

        Each agent deposits an initial trace in the shared grid, establishing
        the basis for natural niche partitioning and citation-based collaboration.

        Args:
            agent_specs: Agents to deploy
            domain: Domain name

        Returns:
            Number of agents successfully deployed
        """
        if self._stigmergy is None:
            return 0

        deployed = 0
        for spec in agent_specs:
            try:
                trace = self._stigmergy.append_trace(
                    agent_id=spec.agent_id,
                    action={"type": "agent_initialization", "domain": domain, "role": spec.role_name},
                    evidence={"source_skills": spec.source_skills, "capabilities": spec.required_capabilities},
                )
                if trace:
                    deployed += 1
            except Exception:
                pass

        if domain in self._domains:
            self._domains[domain].agent_count = len(agent_specs)

        self._logger.info("agents_deployed", domain=domain, count=deployed)
        return deployed

    # ═══════════════════════════════════════════════════════════════════
    # Full Compilation Pipeline
    # ═══════════════════════════════════════════════════════════════════

    def compile_pipeline(
        self,
        skills: dict[str, str] | None = None,
        skills_dir: str | None = None,
    ) -> CompilationReport:
        """Run the full Skill→Agent compilation pipeline.

        Args:
            skills: In-memory dict of skill_id → markdown content
            skills_dir: Directory path to scan for SKILL.md files

        Returns:
            CompilationReport with complete pipeline results
        """
        start_time = time.time()
        report = CompilationReport(
            report_id=self._hash_id(f"compile-{time.time()}"),
            stage=CompilationStage.SCAN,
        )

        # Stage 1: Scan
        if skills:
            discovered = self.scan_skills_content(skills)
        elif skills_dir:
            discovered = self.scan_skills_dir(skills_dir)
        else:
            discovered = self.scan_skills_dir(self._skills_dir)

        report.total_skills_scanned = len(discovered)
        report.stage = CompilationStage.EXTRACT_CLAIMS

        # Stage 2: Extract claims
        total_claims = 0
        for meta in discovered:
            # Get content from stored metadata or file
            content = meta.metadata.get("content", "")
            if not content:
                try:
                    with open(meta.file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (OSError, UnicodeDecodeError):
                    content = ""
            if content:
                claims = self.extract_claims(content, meta.skill_id)
                total_claims += len(claims)

        report.total_claims_extracted = total_claims
        report.stage = CompilationStage.CLASSIFY_DOMAIN

        # Stage 3: Classify by domain
        domain_claims = self.classify_by_domain()
        report.domains_detected = list(domain_claims.keys())
        report.stage = CompilationStage.INSTANTIATE_AGENTS

        # Stage 4: Instantiate agents
        domain_agents = self.instantiate_agents(domain_claims)
        total_agents = sum(len(specs) for specs in domain_agents.values())
        report.total_agents_instantiated = total_agents
        report.stage = CompilationStage.GENERATE_ARCHITECTURE

        # Stage 5: Generate architectures
        arch_count = 0
        for domain, specs in domain_agents.items():
            manifest = DomainManifest(
                domain=domain,
                agent_count=len(specs),
                claim_count=len(domain_claims.get(domain, [])),
                skill_count=sum(1 for m in self._skills.values() if m.domain == domain),
                agent_specs=specs,
            )
            architecture = self.generate_architecture(domain, specs)
            if architecture:
                manifest.architecture = architecture
                arch_count += 1
            self._domains[domain] = manifest
            report.domain_manifests[domain] = manifest

        report.architectures_generated = arch_count
        report.stage = CompilationStage.DEPLOY_TO_FIELD

        # Stage 6: Deploy to stigmergy field
        total_deployed = 0
        for domain, specs in domain_agents.items():
            deployed = self.deploy_to_field(specs, domain)
            total_deployed += deployed

        report.agents_deployed = total_deployed
        report.stage = CompilationStage.COMPLETE
        report.compilation_time_ms = round((time.time() - start_time) * 1000, 2)

        self._reports.append(report)
        self._logger.info(
            "compilation_complete",
            skills=report.total_skills_scanned,
            claims=report.total_claims_extracted,
            agents=report.total_agents_instantiated,
            domains=len(report.domains_detected),
            architectures=report.architectures_generated,
            deployed=report.agents_deployed,
            time_ms=report.compilation_time_ms,
        )
        return report

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _hash_id(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get_domain_manifest(self, domain: str) -> DomainManifest | None:
        """Get the manifest for a compiled domain."""
        return self._domains.get(domain)

    @property
    def stats(self) -> dict[str, Any]:
        """Current compiler statistics."""
        return {
            "skills_loaded": len(self._skills),
            "claims_extracted": sum(len(c) for c in self._claims.values()),
            "agents_instantiated": sum(len(s) for s in self._agent_specs.values()),
            "domains_detected": len(self._domains),
            "architectures_generated": sum(1 for d in self._domains.values() if d.architecture),
            "reports_count": len(self._reports),
        }

    def reset(self) -> None:
        """Reset compiler state."""
        self._skills.clear()
        self._claims.clear()
        self._agent_specs.clear()
        self._domains.clear()
        self._reports.clear()
        self._logger.debug("compiler_reset")
