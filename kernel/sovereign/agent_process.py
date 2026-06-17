"""P3: Agent as Native OS Process (Quine POSIX fork/exec/exit).

Every agent is a real OS process with:
  - PID-based identity (kernel-assigned, unforgeable)
  - stdin/stdout/stderr IPC
  - fork/exec/exit lifecycle
  - Recursive self-spawning (same executable image)
  - Signal-based supervision tree

Reference: Quine (arXiv 2603.18030), Namzu SDK, POSIX process model.
"""

from __future__ import annotations
import os, signal, subprocess, sys, uuid
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentProcess:
    agent_id: str; pid: int
    parent_pid: int = 0
    status: str = "spawned"  # spawned, running, waiting, terminated
    exit_code: int | None = None
    children: list[str] = field(default_factory=list)

class AgentProcessManager:
    """Manage agents as native OS processes (Quine model).

    Hierarchy:
      Root Agent (PID 1000)
        ├── Sub-Agent A (PID 1001) — spawned via fork/exec
        │   └── Worker A1 (PID 1003)
        └── Sub-Agent B (PID 1002)
    """

    # 主权#6修复: 模块级共享注册表, agent_spawn 和 agent_tree 使用同一实例
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, '_agents'):
            self._agents: dict[str, AgentProcess] = {}
            self._self_pid = os.getpid()

    def spawn(self, code: str, parent_id: str = "", role: str = "worker") -> AgentProcess:
        """Spawn a new agent as an OS process."""
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        import tempfile

        tmp = tempfile.mkdtemp(prefix=f"sclerotium_{agent_id}_")
        script = os.path.join(tmp, "agent_main.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(f'"""Agent: {agent_id} | Role: {role}"""\n')
            f.write(code)

        try:
            proc = subprocess.Popen(
                [sys.executable, script],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, cwd=tmp,
            )
            agent = AgentProcess(
                agent_id=agent_id, pid=proc.pid,
                parent_pid=self._agents[parent_id].pid if parent_id in self._agents else self._self_pid,
                status="running",
            )
            self._agents[agent_id] = agent
            if parent_id and parent_id in self._agents:
                self._agents[parent_id].children.append(agent_id)
            return agent
        except Exception as e:
            agent = AgentProcess(agent_id=agent_id, pid=-1, status="terminated")
            self._agents[agent_id] = agent
            return agent

    def fork_self(self, new_role: str) -> AgentProcess:
        """Self-fork: spawn a copy of this agent with a new role (Quine model)."""
        import inspect
        caller_frame = inspect.currentframe()
        if caller_frame and caller_frame.f_back:
            caller_file = caller_frame.f_back.f_code.co_filename
            with open(caller_file, encoding="utf-8") as f:
                own_code = f.read()
            return self.spawn(own_code, role=new_role)
        return AgentProcess(agent_id="fork_failed", pid=-1, status="error")

    def signal_agent(self, agent_id: str, sig: int = signal.SIGTERM) -> dict:
        """Send signal to an agent process."""
        agent = self._agents.get(agent_id)
        if agent is None or agent.pid < 0:
            return {"status": "error", "reason": "Agent not found"}
        try:
            os.kill(agent.pid, sig)
            if sig == signal.SIGTERM or sig == signal.SIGKILL:
                agent.status = "terminated"
            return {"status": "signalled", "agent_id": agent_id, "signal": sig}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def signal_tree(self, root_agent_id: str, sig: int = signal.SIGTERM) -> dict:
        """Signal an entire agent tree (parent + all children recursively)."""
        root = self._agents.get(root_agent_id)
        if root is None:
            return {"status": "error", "reason": "Root agent not found"}
        signalled = [root_agent_id]
        queue = list(root.children)
        while queue:
            child_id = queue.pop(0)
            signalled.append(child_id)
            child = self._agents.get(child_id)
            if child:
                queue.extend(child.children)
        for aid in signalled:
            self.signal_agent(aid, sig)
        return {"root": root_agent_id, "signalled_count": len(signalled), "agents": signalled}

    def list_agents(self) -> list[dict]:
        return [{"agent_id": a.agent_id, "pid": a.pid, "parent_pid": a.parent_pid,
                 "status": a.status, "children": len(a.children)} for a in self._agents.values()]

    def get_tree(self) -> dict:
        """Get agent process tree visualization."""
        roots = [a for a in self._agents.values() if a.parent_pid == self._self_pid]
        def build_node(a):
            return {"agent_id": a.agent_id, "pid": a.pid, "status": a.status,
                    "children": [build_node(self._agents[c]) for c in a.children if c in self._agents]}
        return {"root_pid": self._self_pid, "agents": [build_node(r) for r in roots],
                "total_agents": len(self._agents)}
