"""OasisBridge — Arena → OASIS 真实仿真桥接.

将竞技场的 Agent Profile 和仿真配置转换为 OASIS 格式,
启动子进程运行真实社会仿真,监控完成,读取动作日志。

流程:
    Arena.build_agent_profiles()  →  OASIS Profile (CSV/JSON)
    Arena.build_simulation_config() →  simulation_config.json
    OasisBridge.run_simulation()  →  子进程 run_parallel_simulation.py
    OasisBridge.wait_for_completion() →  读取 actions.jsonl
    Arena.extract_fitness(action_logs) →  FitnessVector
"""

from __future__ import annotations

import csv
import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════════════


class SimulationStatus(Enum):
    """OASIS 仿真状态."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class OasisSimulationResult:
    """OASIS 仿真运行结果."""
    status: SimulationStatus
    action_logs: list[dict[str, Any]] = field(default_factory=list)
    total_actions: int = 0
    total_rounds: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
    simulation_dir: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# OasisBridge
# ═══════════════════════════════════════════════════════════════════════════════


class OasisBridge:
    """Arena ↔ OASIS 仿真桥接器.

    将竞技场输出转换为 OASIS 可执行的仿真,
    并从中提取动作日志反馈给适应度提取器。

    Usage:
        bridge = OasisBridge(scripts_dir="backend/scripts")
        profiles = arena.build_agent_profiles(genome_context)
        config = arena.build_simulation_config(profiles, genome_context)

        result = bridge.run_simulation(
            simulation_id="arena_coding_gen5",
            agent_profiles=profiles,
            simulation_config=config,
            platform="reddit",
            max_rounds=30,
            timeout_seconds=600,
        )

        if result.status == SimulationStatus.COMPLETED:
            fitness = arena.extract_fitness(result.action_logs, profiles, ctx)
    """

    def __init__(
        self,
        scripts_dir: str | None = None,
        uploads_dir: str | None = None,
    ) -> None:
        """初始化桥接器.

        Args:
            scripts_dir: OASIS 脚本目录 (run_parallel_simulation.py 所在)
            uploads_dir: 上传/仿真数据目录
        """
        backend = Path(__file__).parent.parent
        self.scripts_dir = Path(scripts_dir) if scripts_dir else backend / "scripts"
        self.uploads_dir = Path(uploads_dir) if uploads_dir else backend / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

        # 运行时状态
        self._running_processes: dict[str, subprocess.Popen] = {}
        self._monitor_threads: dict[str, threading.Thread] = {}

    # ── 核心 API ────────────────────────────────────────────────────────

    def run_simulation(
        self,
        simulation_id: str,
        agent_profiles: list[dict[str, Any]],
        simulation_config: dict[str, Any],
        platform: str = "reddit",
        max_rounds: int | None = None,
        timeout_seconds: int = 1800,
        wait_for_completion: bool = True,
    ) -> OasisSimulationResult:
        """运行一次 OASIS 社会仿真.

        Args:
            simulation_id: 仿真唯一 ID
            agent_profiles: Arena 生成的 Agent Profile 列表
            simulation_config: Arena 生成的仿真配置
            platform: "twitter" / "reddit" / "parallel"
            max_rounds: 最大轮次限制
            timeout_seconds: 超时 (秒)
            wait_for_completion: 是否等待完成 (False = 启动后立即返回)

        Returns:
            OasisSimulationResult 包含动作日志
        """
        sim_dir = self._prepare_simulation_dir(simulation_id)
        start_time = time.monotonic()

        try:
            # Step 1: 写入 Agent Profile (OASIS 格式)
            self._write_agent_profiles(agent_profiles, sim_dir, platform)

            # Step 2: 写入仿真配置
            config_path = sim_dir / "simulation_config.json"
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(simulation_config, f, ensure_ascii=False, indent=2)

            logger.info(
                "OasisBridge: prepared simulation '%s' in %s "
                "(%d agents, platform=%s)",
                simulation_id, sim_dir, len(agent_profiles), platform,
            )

            # Step 3: 选择脚本
            script_path = self._select_script(platform)

            # Step 4: 构建命令
            cmd = [
                sys.executable,
                str(script_path),
                "--config", str(config_path),
            ]
            if platform == "twitter":
                cmd.append("--twitter-only")
            elif platform == "reddit":
                cmd.append("--reddit-only")
            if max_rounds:
                cmd.extend(["--max-rounds", str(max_rounds)])
            # 自动化模式: 完成后不等待 Interview
            cmd.append("--no-wait")

            # Step 5: 启动子进程
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            process = subprocess.Popen(
                cmd,
                cwd=str(sim_dir),
                stdout=open(sim_dir / "simulation.log", "w", encoding="utf-8"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=env,
            )
            self._running_processes[simulation_id] = process

            logger.info(
                "OasisBridge: started simulation '%s' (pid=%d)",
                simulation_id, process.pid,
            )

            if not wait_for_completion:
                return OasisSimulationResult(
                    status=SimulationStatus.RUNNING,
                    simulation_dir=str(sim_dir),
                )

            # Step 6: 等待完成
            return self._wait_for_completion(
                simulation_id, sim_dir, process, start_time, timeout_seconds,
            )

        except Exception as exc:
            logger.exception("OasisBridge: simulation '%s' failed", simulation_id)
            return OasisSimulationResult(
                status=SimulationStatus.FAILED,
                error=str(exc),
                duration_seconds=time.monotonic() - start_time,
                simulation_dir=str(sim_dir),
            )

    def is_running(self, simulation_id: str) -> bool:
        """检查仿真是否仍在运行."""
        process = self._running_processes.get(simulation_id)
        return process is not None and process.poll() is None

    def stop_simulation(self, simulation_id: str) -> None:
        """停止仿真进程."""
        process = self._running_processes.pop(simulation_id, None)
        if process and process.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                    )
                else:
                    import signal
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except Exception as exc:
                logger.warning("Failed to kill process %d: %s", process.pid, exc)

    def cleanup_simulation(self, simulation_id: str) -> None:
        """清理仿真文件和进程."""
        self.stop_simulation(simulation_id)

    # ── 内部方法 ────────────────────────────────────────────────────────

    def _prepare_simulation_dir(self, simulation_id: str) -> Path:
        """准备仿真目录."""
        sim_dir = self.uploads_dir / "simulations" / simulation_id
        sim_dir.mkdir(parents=True, exist_ok=True)
        return sim_dir

    def _write_agent_profiles(
        self,
        profiles: list[dict[str, Any]],
        sim_dir: Path,
        platform: str,
    ) -> None:
        """将 Agent Profile 写入 OASIS 格式文件.

        Twitter: CSV (user_id, name, username, user_char, description)
        Reddit:  JSON 对象数组
        """
        if platform in ("twitter", "parallel"):
            self._write_twitter_profiles(profiles, sim_dir)
        if platform in ("reddit", "parallel"):
            self._write_reddit_profiles(profiles, sim_dir)

    def _write_twitter_profiles(
        self, profiles: list[dict[str, Any]], sim_dir: Path
    ) -> None:
        """写入 Twitter CSV Profile."""
        path = sim_dir / "twitter_profiles.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "name", "username", "user_char", "description"])
            for p in profiles:
                user_id = p.get("user_id", 0)
                name = p.get("name", f"Agent_{user_id}")
                username = p.get("user_name", f"agent_{user_id}")
                user_char = p.get("persona", p.get("bio", ""))
                description = p.get("bio", "")[:200]
                writer.writerow([user_id, name, username, user_char, description])
        logger.info("Wrote %d Twitter profiles to %s", len(profiles), path)

    def _write_reddit_profiles(
        self, profiles: list[dict[str, Any]], sim_dir: Path
    ) -> None:
        """写入 Reddit JSON Profile."""
        path = sim_dir / "reddit_profiles.json"
        reddit_profiles = []
        for p in profiles:
            reddit_profiles.append({
                "user_id": p.get("user_id", 0),
                "username": p.get("user_name", f"agent_{p.get('user_id', 0)}"),
                "name": p.get("name", ""),
                "bio": p.get("bio", ""),
                "persona": p.get("persona", ""),
                "karma": p.get("karma", 500),
                "created_at": "2026-01-01",
                "age": p.get("age", 30),
                "gender": p.get("gender", "non-binary"),
                "mbti": p.get("mbti", "INTJ"),
                "country": p.get("country", "Global"),
                "profession": p.get("profession", ""),
                "interested_topics": p.get("interested_topics", []),
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(reddit_profiles, f, ensure_ascii=False, indent=2)
        logger.info("Wrote %d Reddit profiles to %s", len(reddit_profiles), path)

    def _select_script(self, platform: str) -> Path:
        """选择对应平台的 OASIS 脚本."""
        script_map = {
            "twitter": "run_twitter_simulation.py",
            "reddit": "run_reddit_simulation.py",
            "parallel": "run_parallel_simulation.py",
        }
        script_name = script_map.get(platform, "run_parallel_simulation.py")
        script_path = self.scripts_dir / script_name
        if not script_path.exists():
            raise FileNotFoundError(f"OASIS script not found: {script_path}")
        return script_path

    def _wait_for_completion(
        self,
        simulation_id: str,
        sim_dir: Path,
        process: subprocess.Popen,
        start_time: float,
        timeout_seconds: int,
    ) -> OasisSimulationResult:
        """等待仿真完成并收集结果."""
        try:
            returncode = process.wait(timeout=timeout_seconds)
            duration = time.monotonic() - start_time

            if returncode != 0:
                error_msg = self._read_error_log(sim_dir)
                logger.error(
                    "Simulation '%s' failed (exit=%d): %s",
                    simulation_id, returncode, error_msg,
                )
                return OasisSimulationResult(
                    status=SimulationStatus.FAILED,
                    error=f"Exit code {returncode}: {error_msg}",
                    duration_seconds=duration,
                    simulation_dir=str(sim_dir),
                )

            # 读取动作日志
            action_logs = self._read_action_logs(sim_dir)
            total_actions = len(action_logs)

            logger.info(
                "Simulation '%s' completed: %d actions in %.1fs",
                simulation_id, total_actions, duration,
            )

            return OasisSimulationResult(
                status=SimulationStatus.COMPLETED,
                action_logs=action_logs,
                total_actions=total_actions,
                total_rounds=self._count_rounds(action_logs),
                duration_seconds=duration,
                simulation_dir=str(sim_dir),
            )

        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start_time
            logger.error("Simulation '%s' timed out after %ds", simulation_id, timeout_seconds)
            self.stop_simulation(simulation_id)
            # 尝试读取已有的日志
            partial_logs = self._read_action_logs(sim_dir)
            return OasisSimulationResult(
                status=SimulationStatus.TIMEOUT,
                action_logs=partial_logs,
                total_actions=len(partial_logs),
                duration_seconds=duration,
                error=f"Timeout after {timeout_seconds}s",
                simulation_dir=str(sim_dir),
            )

        finally:
            self._running_processes.pop(simulation_id, None)

    # ── 日志读取 ────────────────────────────────────────────────────────

    @staticmethod
    def _read_action_logs(sim_dir: Path) -> list[dict[str, Any]]:
        """从 actions.jsonl 读取所有动作日志.

        扫描 twitter/ 和 reddit/ 子目录。
        """
        actions: list[dict[str, Any]] = []
        for platform_dir in ("twitter", "reddit"):
            log_path = sim_dir / platform_dir / "actions.jsonl"
            if not log_path.exists():
                continue
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            # 添加平台标记
                            if "platform" not in entry:
                                entry["platform"] = platform_dir
                            # 跳过事件记录，只保留 Agent 动作
                            if "event_type" not in entry:
                                actions.append(entry)
                        except json.JSONDecodeError:
                            continue
            except Exception as exc:
                logger.warning("Failed to read %s: %s", log_path, exc)

        # 按时间戳排序
        actions.sort(key=lambda a: (a.get("round", 0), a.get("timestamp", "")))
        return actions

    @staticmethod
    def _count_rounds(action_logs: list[dict[str, Any]]) -> int:
        """统计总轮次."""
        rounds = {a.get("round", 0) for a in action_logs}
        return len(rounds)

    @staticmethod
    def _read_error_log(sim_dir: Path) -> str:
        """读取仿真错误日志 (最后 2000 字符)."""
        log_path = sim_dir / "simulation.log"
        if not log_path.exists():
            return "No log file found"
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                return content[-2000:] if len(content) > 2000 else content
        except Exception:
            return "Failed to read log file"


# ═══════════════════════════════════════════════════════════════════════════════
# 便捷: 从 SimulationRunner 读取 (兼容 MiroFish 现有 API)
# ═══════════════════════════════════════════════════════════════════════════════

class SimulationRunnerAdapter:
    """适配 MiroFish 现有 SimulationRunner API.

    当 OASIS 仿真已经通过 MiroFish 的 SimulationRunner 启动时,
    使用此适配器读取结果,无需 OasisBridge 重复启停。
    """

    @staticmethod
    def read_action_logs_from_runner(
        simulation_id: str,
        uploads_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        """通过 MiroFish SimulationRunner API 读取动作日志.

        仅当 simulation_id 是通过 SimulationRunner 启动时使用。
        """
        try:
            # 动态导入避免循环依赖
            from app.services.simulation_runner import SimulationRunner
            actions = SimulationRunner.get_all_actions(simulation_id)
            return [
                {
                    "round": a.round_num,
                    "timestamp": a.timestamp,
                    "agent_id": a.agent_id,
                    "agent_name": a.name,
                    "action_type": a.action_type,
                    "action_args": a.args or {},
                    "platform": a.platform,
                    "success": True,
                }
                for a in actions
            ]
        except ImportError:
            # 回退: 直接读取文件
            uploads = Path(uploads_dir) if uploads_dir else Path("uploads")
            sim_dir = uploads / "simulations" / simulation_id
            return OasisBridge._read_action_logs(sim_dir)

    @staticmethod
    def get_run_state(simulation_id: str) -> dict[str, Any] | None:
        """获取仿真运行状态."""
        try:
            from app.services.simulation_runner import SimulationRunner
            state = SimulationRunner.get_run_state(simulation_id)
            return state.to_dict() if state else None
        except ImportError:
            return None
