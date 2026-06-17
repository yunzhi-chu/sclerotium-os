"""P3: Domain-Specific Knowledge Engine (BeyondSWE DomainFix grade)."""
from __future__ import annotations
from typing import Any
DOMAINS: dict[str, dict] = {
    "quantum": {"concepts": ["qubit","superposition","entanglement","gate","measurement"], "libraries": ["qiskit","cirq","pennylane"]},
    "bioinfo": {"concepts": ["dna","rna","protein","sequence","alignment","genome"], "libraries": ["biopython","pysam"]},
    "crypto": {"concepts": ["hash","encryption","signature","key","certificate","cipher","aes","rsa"], "libraries": ["cryptography","pycryptodome"]},
    "security": {"concepts": ["security","vulnerability","exploit","xss","sqli","csrf","auth","sandbox","permission","static analysis","sast","bandit","owasp"], "libraries": ["bandit","safety","pip-audit","semgrep","trivy"]},
    "ml": {"concepts": ["model","training","inference","gradient","loss","epoch","neural","deep learning"], "libraries": ["torch","tensorflow","jax"]},
    "distributed": {"concepts": ["shard","replica","consensus","raft","paxos"], "libraries": ["ray","dask"]},
    "graphics": {"concepts": ["shader","texture","render","mesh","pixel","opengl","vulkan"], "libraries": ["opengl","vulkan","pyglet"]},
    "embedded": {"concepts": ["interrupt","register","gpio","timer","dma"], "libraries": ["micropython","circuitpython"]},
    "compiler": {"concepts": ["lexer","parser","ast","ir","codegen","llvm"], "libraries": ["llvmlite","pycparser"]},
    "networking": {"concepts": ["tcp","udp","dns","http","socket","packet"], "libraries": ["scapy","twisted"]},
    "database": {"concepts": ["index","query","transaction","b-tree","wal","sql","nosql"], "libraries": ["sqlalchemy","duckdb"]},
    "robotics": {"concepts": ["kinematics","trajectory","sensor","actuator","odometry"], "libraries": ["ros2","pybullet"]},
    "testing": {"concepts": ["test","pytest","unittest","coverage","mock","fixture","assertion","tdd","fuzzing"], "libraries": ["pytest","hypothesis","coverage","factory-boy"]},
    "devops": {"concepts": ["ci","cd","docker","kubernetes","pipeline","deploy","terraform","ansible","jenkins"], "libraries": ["docker","kubernetes","ansible","fabric"]},
}
class DomainKnowledge:
    def get_domain(self, name: str) -> dict | None: return DOMAINS.get(name)
    def list_domains(self) -> list[str]: return list(DOMAINS.keys())
    def match_domain(self, query: str) -> str | None:
        """BUG#8修复: 多词查询匹配 + 子串部分匹配 + 最佳匹配打分。"""
        q = query.lower()
        best_score = 0
        best_domain = None
        for d, info in DOMAINS.items():
            score = 0
            for c in info["concepts"]:
                # 完整词匹配得分最高
                if c in q:
                    score += 3
                # 部分匹配 (e.g. "security" in "security static analysis")
                elif any(part in c or c in part for part in q.split()):
                    score += 1
            # 也匹配 domain 名称本身
            if d in q:
                score += 5
            if score > best_score:
                best_score = score
                best_domain = d
        return best_domain
    def suggest_libraries(self, domain: str) -> list[str]:
        d = DOMAINS.get(domain, {})
        return d.get("libraries", [])
