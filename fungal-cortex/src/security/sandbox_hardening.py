"""Phase 7.2b: SandboxHardening — "胎盘屏障"(Placental Barrier) 沙箱安全加固.

Biological Metaphor:
  胎盘屏障——只允许必需营养通过, 阻止毒素和病原体:
    母体血液与胎儿血液不直接混合 → 网络隔离(network=disabled)
    合体滋养层过滤 → seccomp系统调用白名单
    胎盘厚度≈3.5μm(扩散距离最小化) → 最小化攻击面
    IgG可通过(被动免疫) → 白名单必要能力
    细菌/病毒被阻止 → 黑名单危险操作

  Docker安全配置映射:
    胎盘屏障 → gVisor (用户空间内核, 系统调用拦截)
    合体滋养层 → seccomp profile (系统调用过滤)
    羊水保护 → readonly_rootfs (不可变文件系统)
    胎盘大小限制 → memory/cpu limits
    脐带连接 → 仅允许必需网络连接

Reference:
  Burton & Fowden (2015), "The placenta", Phil Trans R Soc B 370:20140066;
  Docker security best practices; gVisor runtime
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SecurityLevel(str, Enum):
    """Security levels — like the selectivity of different barriers."""
    MINIMAL = "minimal"       # Basic isolation (network only)
    STANDARD = "standard"     # seccomp + readonly rootfs
    STRICT = "strict"         # gVisor + seccomp + no network
    PLACENTAL = "placental"   # Maximum: gVisor + custom seccomp + readonly + limits
    AIRGAPPED = "airgapped"   # Complete physical isolation analog


class SeccompAction(str, Enum):
    """Seccomp filter actions — like placental transport mechanisms."""
    ALLOW = "SCMP_ACT_ALLOW"
    KILL = "SCMP_ACT_KILL"
    ERRNO = "SCMP_ACT_ERRNO"


@dataclass
class SandboxProfile:
    """Docker sandbox security profile — like placental barrier specification."""

    profile_id: str
    security_level: SecurityLevel
    name: str
    description: str

    # Docker runtime options
    runtime: str = "runc"  # runc, gvisor, kata
    network_disabled: bool = True
    readonly_rootfs: bool = True
    no_new_privileges: bool = True

    # Resource limits (placenta size analog)
    memory_limit_mb: int = 256
    cpu_quota: int = 50000  # microseconds per 100ms period (50% CPU)
    pids_limit: int = 32
    disk_limit_mb: int = 512

    # Seccomp profile
    seccomp_profile: dict[str, Any] = field(default_factory=dict)
    allowed_syscalls: list[str] = field(default_factory=list)
    blocked_syscalls: list[str] = field(default_factory=list)

    # Capabilities
    drop_all_capabilities: bool = True
    allowed_capabilities: list[str] = field(default_factory=list)

    # Timeouts
    execution_timeout: float = 30.0  # seconds
    startup_timeout: float = 5.0

    created_at: float = field(default_factory=time.time)


class SandboxHardening:
    """Placental barrier — generates Docker security profiles.

    Config:
      - default_level: default security level for new profiles
      - gvisor_available: whether gVisor runtime is installed
      - allowed_syscalls_base: baseline allowed system calls
    """

    # Essential syscalls for Python sandbox execution (minimal set)
    _BASELINE_SYSCALLS: list[str] = [
        "read", "write", "open", "close", "fstat", "mmap", "mprotect",
        "munmap", "brk", "rt_sigaction", "rt_sigprocmask", "ioctl",
        "pread64", "pwrite64", "sched_getaffinity", "sched_yield",
        "set_robust_list", "futex", "clone", "execve", "exit", "exit_group",
        "getpid", "gettid", "nanosleep", "clock_gettime", "gettimeofday",
    ]

    # Dangerous syscalls always blocked (like placental barrier to pathogens)
    _BLOCKED_SYSCALLS: list[str] = [
        "mount", "umount2", "ptrace", "personality", "reboot",
        "kexec_load", "init_module", "finit_module", "delete_module",
        "iopl", "ioperm", "swapon", "swapoff", "syslog",
        "acct", "add_key", "request_key", "keyctl",
    ]

    def __init__(
        self,
        default_level: SecurityLevel = SecurityLevel.STANDARD,
        gvisor_available: bool = False,
    ) -> None:
        self._default_level = default_level
        self._gvisor_available = gvisor_available
        self._profiles: dict[str, SandboxProfile] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Create default security profiles for each level."""
        for level in SecurityLevel:
            profile = self.create_profile(
                name=f"cortex-{level.value}",
                security_level=level,
                description=f"Default {level.value} security profile for Fungal Cortex sandbox",
            )
            self._profiles[level.value] = profile

    # ── Profile Creation ────────────────────────────────────────────

    def create_profile(self, name: str, security_level: SecurityLevel,
                       description: str = "",
                       memory_limit_mb: int = 256,
                       execution_timeout: float = 30.0) -> SandboxProfile:
        """Create a sandbox security profile — building a placental barrier."""
        profile = SandboxProfile(
            profile_id=self._gen_id("sandbox"),
            security_level=security_level,
            name=name,
            description=description,
            memory_limit_mb=memory_limit_mb,
            execution_timeout=execution_timeout,
        )

        # Configure by security level
        if security_level == SecurityLevel.MINIMAL:
            profile.network_disabled = True
            profile.readonly_rootfs = False
            profile.runtime = "runc"
        elif security_level == SecurityLevel.STANDARD:
            profile.network_disabled = True
            profile.readonly_rootfs = True
            profile.no_new_privileges = True
            profile.runtime = "runc"
            profile.allowed_syscalls = list(self._BASELINE_SYSCALLS)
        elif security_level == SecurityLevel.STRICT:
            profile.network_disabled = True
            profile.readonly_rootfs = True
            profile.no_new_privileges = True
            profile.runtime = "gvisor" if self._gvisor_available else "runc"
            profile.drop_all_capabilities = True
            profile.allowed_syscalls = list(self._BASELINE_SYSCALLS)
            profile.blocked_syscalls = list(self._BLOCKED_SYSCALLS)
            profile.memory_limit_mb = min(memory_limit_mb, 512)
            profile.pids_limit = 16
        elif security_level == SecurityLevel.PLACENTAL:
            profile.network_disabled = True
            profile.readonly_rootfs = True
            profile.no_new_privileges = True
            profile.runtime = "gvisor" if self._gvisor_available else "runc"
            profile.drop_all_capabilities = True
            profile.allowed_capabilities = []  # No extra capabilities
            profile.allowed_syscalls = list(self._BASELINE_SYSCALLS[:20])  # Minimal set
            profile.blocked_syscalls = list(self._BLOCKED_SYSCALLS)
            profile.memory_limit_mb = min(memory_limit_mb, 256)
            profile.cpu_quota = 25000  # 25% CPU max
            profile.pids_limit = 8
            profile.disk_limit_mb = 256
            profile.execution_timeout = min(execution_timeout, 15.0)
        elif security_level == SecurityLevel.AIRGAPPED:
            profile.network_disabled = True
            profile.readonly_rootfs = True
            profile.no_new_privileges = True
            profile.runtime = "gvisor" if self._gvisor_available else "runc"
            profile.drop_all_capabilities = True
            profile.allowed_syscalls = self._BASELINE_SYSCALLS[:12]  # Bare minimum
            profile.blocked_syscalls = list(self._BLOCKED_SYSCALLS)
            profile.memory_limit_mb = min(memory_limit_mb, 128)
            profile.cpu_quota = 10000  # 10% CPU
            profile.pids_limit = 4
            profile.disk_limit_mb = 128

        # Generate seccomp profile JSON
        profile.seccomp_profile = self._generate_seccomp_json(profile)

        self._profiles[profile.profile_id] = profile
        return profile

    # ── Docker Command Generation ───────────────────────────────────

    def generate_docker_args(self, profile: SandboxProfile) -> list[str]:
        """Generate Docker CLI arguments for the profile.

        Like the OB/GYN writing the delivery plan for a high-risk pregnancy.
        """
        args = [
            f"--memory={profile.memory_limit_mb}m",
            f"--cpus={profile.cpu_quota / 100000:.2f}",
            f"--pids-limit={profile.pids_limit}",
            f"--runtime={profile.runtime}",
        ]

        if profile.network_disabled:
            args.append("--network=none")

        if profile.readonly_rootfs:
            args.append("--read-only")
            args.append("--tmpfs=/tmp:rw,noexec,nosuid,size=64m")

        if profile.no_new_privileges:
            args.append("--security-opt=no-new-privileges:true")

        if profile.drop_all_capabilities:
            args.append("--cap-drop=ALL")
            for cap in profile.allowed_capabilities:
                args.append(f"--cap-add={cap}")

        if profile.seccomp_profile:
            # In production, write seccomp JSON to file and reference it
            seccomp_path = f"/tmp/cortex-seccomp-{profile.profile_id}.json"
            args.append(f"--security-opt=seccomp={seccomp_path}")

        return args

    def generate_docker_compose(self, profile: SandboxProfile,
                                image: str = "cortex-sandbox:latest",
                                command: str = "") -> dict[str, Any]:
        """Generate a Docker Compose service definition."""
        service: dict[str, Any] = {
            "image": image,
            "runtime": profile.runtime,
            "mem_limit": f"{profile.memory_limit_mb}M",
            "cpus": round(profile.cpu_quota / 100000, 2),
            "pids_limit": profile.pids_limit,
            "read_only": profile.readonly_rootfs,
            "network_mode": "none" if profile.network_disabled else "bridge",
            "security_opt": [],
            "tmpfs": ["/tmp:rw,noexec,nosuid,size=64m"] if profile.readonly_rootfs else [],
        }

        if profile.no_new_privileges:
            service["security_opt"].append("no-new-privileges:true")

        if profile.drop_all_capabilities:
            service["cap_drop"] = ["ALL"]
            if profile.allowed_capabilities:
                service["cap_add"] = profile.allowed_capabilities

        if command:
            service["command"] = command

        return {"services": {"cortex-sandbox": service}}

    # ── Validation ──────────────────────────────────────────────────

    def validate_profile(self, profile: SandboxProfile) -> tuple[bool, list[str]]:
        """Validate a security profile — check for gaps.

        Like ultrasound checking placental integrity.
        """
        issues: list[str] = []

        if profile.security_level in (SecurityLevel.STRICT, SecurityLevel.PLACENTAL, SecurityLevel.AIRGAPPED):
            if not profile.network_disabled:
                issues.append("Network should be disabled for strict+ levels")
            if not profile.readonly_rootfs:
                issues.append("Rootfs should be readonly for strict+ levels")
            if not profile.no_new_privileges:
                issues.append("New privileges should be blocked for strict+ levels")

        if profile.security_level in (SecurityLevel.PLACENTAL, SecurityLevel.AIRGAPPED):
            if not profile.drop_all_capabilities:
                issues.append("All capabilities should be dropped for placental/airgapped")
            if profile.memory_limit_mb > 256:
                issues.append(f"Memory limit {profile.memory_limit_mb}MB exceeds placental maximum 256MB")

        if profile.security_level == SecurityLevel.AIRGAPPED:
            if profile.pids_limit > 4:
                issues.append(f"PIDs limit {profile.pids_limit} exceeds airgapped maximum 4")

        return len(issues) == 0, issues

    # ── Query Interface ─────────────────────────────────────────────

    def get_profile(self, profile_id: str) -> SandboxProfile | None:
        return self._profiles.get(profile_id)

    def get_default_profile(self, level: SecurityLevel | None = None) -> SandboxProfile:
        level = level or self._default_level
        return self._profiles[level.value]

    def list_profiles(self) -> list[SandboxProfile]:
        return list(self._profiles.values())

    # ── Internal ────────────────────────────────────────────────────

    def _generate_seccomp_json(self, profile: SandboxProfile) -> dict[str, Any]:
        """Generate a seccomp profile JSON — like defining placental transport rules."""
        syscalls: list[dict[str, Any]] = []

        # Allowed syscalls
        for name in profile.allowed_syscalls:
            syscalls.append({
                "names": [name],
                "action": SeccompAction.ALLOW.value,
            })

        # Blocked syscalls (explicitly kill)
        blocked_names = [s for s in profile.blocked_syscalls if s not in profile.allowed_syscalls]
        if blocked_names:
            syscalls.append({
                "names": blocked_names,
                "action": SeccompAction.KILL.value,
            })

        return {
            "defaultAction": SeccompAction.ERRNO.value,
            "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_AARCH64"],
            "syscalls": syscalls,
        }

    @staticmethod
    def _gen_id(prefix: str) -> str:
        return hashlib.md5(f"{prefix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "profiles": len(self._profiles),
            "default_level": self._default_level.value,
            "gvisor_available": self._gvisor_available,
            "by_level": {
                level.value: sum(1 for p in self._profiles.values() if p.security_level == level)
                for level in SecurityLevel
            },
        }
