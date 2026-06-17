#!/usr/bin/env python3
"""Fungal Cortex v2.0 — One-Click Startup Launcher.

Starts the full Fungal Cortex stack:
  1. Backend  (FastAPI + Uvicorn)     → http://localhost:8000
  2. Frontend (Next.js dev server)    → http://localhost:3000
  3. ChromaDB (optional, via Docker)  → http://localhost:8001

Usage:
  python start.py              # Start all services
  python start.py --no-frontend  # Backend only
  python start.py --no-chroma    # Skip ChromaDB
  python start.py --check        # Check prerequisites only
  python start.py --seed         # Start + seed 22 demo skills
  python start.py --stop         # Stop all running services
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT
FRONTEND_DIR = ROOT / "cortex-frontend"

BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", "3000"))
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8001"))

BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"

# Colors for terminal output
C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
    "dim": "\033[2m",
}


def supports_color() -> bool:
    """Check if terminal supports ANSI colors."""
    if os.name == "nt":
        # Windows Terminal and modern conhost support ANSI
        return "WT_SESSION" in os.environ or os.environ.get("TERM_PROGRAM") == "vscode"
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def color(text: str, c: str) -> str:
    if not supports_color():
        return text
    return f"{C.get(c, '')}{text}{C['reset']}"


def banner() -> None:
    print()
    if supports_color():
        print(color("  ╔══════════════════════════════════════════════════╗", "cyan"))
        print(color("  ║   Fungal Cortex v2.0 — L6-Complete Agent OS    ║", "cyan"))
        print(color("  ║          One-Click Startup Launcher              ║", "cyan"))
        print(color("  ╚══════════════════════════════════════════════════╝", "cyan"))
    else:
        print("  ==================================================")
        print("  |  Fungal Cortex v2.0 — L6-Complete Agent OS    |")
        print("  |        One-Click Startup Launcher              |")
        print("  ==================================================")
    print()


def section(title: str) -> None:
    print(f"\n{color('--', 'dim')} {color(title, 'bold')} {color('--', 'dim')}")


def ok(msg: str) -> None:
    print(f"  {color('[OK]', 'green')} {msg}")


def warn(msg: str) -> None:
    print(f"  {color('[WARN]', 'yellow')} {msg}")


def fail(msg: str) -> None:
    print(f"  {color('[FAIL]', 'red')} {msg}")


def info(msg: str) -> None:
    print(f"  {color('[ .. ]', 'dim')} {msg}")


# ── Prerequisite Checks ────────────────────────────────────────────────


def check_python() -> bool:
    """Verify Python 3.10+ is available."""
    v = sys.version_info
    if v >= (3, 10):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    fail(f"Python {v.major}.{v.minor} — need 3.10+")
    return False


def _run_cmd(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a command, falling back to shell=True on Windows if needed."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10, **kwargs)
    except FileNotFoundError:
        if os.name == "nt":
            return subprocess.run(" ".join(cmd), capture_output=True, text=True, timeout=10, shell=True, **kwargs)  # type: ignore[arg-type]
        raise


def check_node() -> bool:
    """Verify Node.js 18+ is available."""
    try:
        r = _run_cmd(["node", "--version"])
        ver = r.stdout.strip().lstrip("v")
        major = int(ver.split(".")[0])
        if major >= 18:
            ok(f"Node.js {ver}")
            return True
        fail(f"Node.js {ver} — need 18+")
        return False
    except FileNotFoundError:
        fail("Node.js not found — install from https://nodejs.org")
        return False
    except Exception as e:
        fail(f"Node.js check failed: {e}")
        return False


def check_npm() -> bool:
    """Verify npm is available."""
    try:
        r = _run_cmd(["npm", "--version"])
        ok(f"npm {r.stdout.strip()}")
        return True
    except FileNotFoundError:
        fail("npm not found")
        return False
    except Exception as e:
        fail(f"npm check failed: {e}")
        return False


def check_port(port: int) -> bool:
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            return result != 0
    except Exception:
        return True


def check_docker() -> bool:
    """Check if Docker is available (optional, for ChromaDB)."""
    try:
        subprocess.run(["docker", "--version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


# ── Dependency Installation ────────────────────────────────────────────


def install_python_deps() -> bool:
    """Verify Python dependencies by importing key modules. Fast path."""
    info("Checking Python dependencies...")
    # Quick import test — if all key modules import, deps are fine
    key_modules = [
        "pydantic",
        "yaml",
        "numpy",
        "fastapi",
        "uvicorn",
        "src.config",
        "src.main",
    ]
    missing: list[str] = []
    for mod in key_modules:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)

    if not missing:
        ok("Python dependencies ready")
        return True

    # Some modules missing — attempt install
    warn(f"Missing modules: {missing}")
    info("Installing Python dependencies (no timeout, large downloads may take a while)...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(BACKEND_DIR)],
            cwd=str(BACKEND_DIR),
            check=True,
        )
        ok("Python dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        fail(f"pip install failed: {e}")
        return False


def install_node_deps() -> bool:
    """Verify Node.js dependencies. Only install if node_modules missing."""
    node_modules = FRONTEND_DIR / "node_modules"
    package_json = FRONTEND_DIR / "package.json"

    if not package_json.exists():
        warn("package.json not found, skipping Node deps")
        return True

    if node_modules.exists() and any(node_modules.iterdir()):
        ok("Node.js dependencies ready")
        return True

    info("Installing Node.js dependencies (no timeout, this may take a while)...")
    try:
        _run_cmd(
            ["npm", "install", "--legacy-peer-deps"],
            cwd=str(FRONTEND_DIR),
            check=True,
        )
        ok("Node.js dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        fail(f"npm install failed: {e}")
        return False


# ── Service Management ─────────────────────────────────────────────────


class ServiceManager:
    """Manages subprocess services with graceful shutdown and log rotation."""

    LOGS_DIR = ROOT / "logs"
    MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
    MAX_LOG_FILES = 5

    def __init__(self) -> None:
        self._processes: dict[str, subprocess.Popen[bytes]] = {}
        self._log_files: dict[str, Path] = {}
        self._shutdown = False
        # Ensure logs directory exists
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self, name: str) -> Path:
        """Get the log file path for a service, with rotation support."""
        base = self.LOGS_DIR / f"{name}.log"
        # Rotate if file is too large
        if base.exists() and base.stat().st_size > self.MAX_LOG_SIZE:
            for i in range(self.MAX_LOG_FILES - 1, 0, -1):
                old = self.LOGS_DIR / f"{name}.{i}.log"
                new = self.LOGS_DIR / f"{name}.{i + 1}.log"
                if old.exists():
                    if new.exists():
                        new.unlink()
                    old.rename(new)
            rotated = self.LOGS_DIR / f"{name}.1.log"
            if rotated.exists():
                rotated.unlink()
            base.rename(rotated)
        return base

    def start(self, name: str, cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.Popen[bytes] | None:
        """Start a service subprocess with log file output."""
        try:
            proc_env = os.environ.copy()
            if env:
                proc_env.update(env)

            # Open log file for output
            log_path = self._get_log_path(name)
            log_fh = open(str(log_path), "a", encoding="utf-8")
            self._log_files[name] = log_path

            popen_kwargs: dict[str, Any] = {
                "cwd": str(cwd) if cwd else None,
                "env": proc_env,
                "stdout": log_fh,
                "stderr": subprocess.STDOUT,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
            }
            if os.name == "nt" and cmd[0] in ("npm", "npx"):
                popen_kwargs["shell"] = True
                cmd_str = " ".join(cmd)
                proc = subprocess.Popen(cmd_str, **popen_kwargs)
            else:
                proc = subprocess.Popen(cmd, **popen_kwargs)
            self._processes[name] = proc
            info(f"Starting {name} (PID {proc.pid}) — logging to {log_path}")
            return proc
        except Exception as e:
            fail(f"Failed to start {name}: {e}")
            return None

    def stop(self, name: str) -> None:
        """Stop a service gracefully."""
        proc = self._processes.get(name)
        if proc is None or proc.poll() is not None:
            return
        info(f"Stopping {name} (PID {proc.pid})...")
        try:
            if os.name == "nt":
                proc.terminate()
            else:
                proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
                ok(f"{name} stopped gracefully")
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                warn(f"{name} killed (timeout)")
        except Exception as e:
            warn(f"Error stopping {name}: {e}")

    def stop_all(self) -> None:
        """Stop all running services."""
        if self._shutdown:
            return
        self._shutdown = True
        print()
        section("Shutting Down")
        for name in list(self._processes.keys()):
            self.stop(name)
        print()

    def wait_for_health(self, url: str, timeout: float = 30.0, label: str = "") -> bool:
        """Poll a health endpoint until it responds 200."""
        import urllib.request
        import urllib.error

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        ok(f"{label or url} is ready")
                        return True
            except Exception:
                pass
            time.sleep(1.0)
        fail(f"{label or url} did not become healthy within {timeout}s")
        return False


# ── Main Startup Flow ──────────────────────────────────────────────────


def start_backend(mgr: ServiceManager) -> bool:
    """Start the FastAPI backend server."""
    section("Backend (FastAPI)")
    if not check_port(BACKEND_PORT):
        warn(f"Port {BACKEND_PORT} is already in use — backend may already be running")
        return True

    proc = mgr.start(
        "backend",
        [
            sys.executable, "-m", "uvicorn", "src.main:app",
            "--host", BACKEND_HOST,
            "--port", str(BACKEND_PORT),
            "--log-level", os.environ.get("LOG_LEVEL", "info"),
        ],
        cwd=BACKEND_DIR,
    )
    if proc is None:
        return False

    healthy = mgr.wait_for_health(f"{BACKEND_URL}/api/health", timeout=20.0, label="Backend")
    if healthy:
        # Print one sample health check
        try:
            import urllib.request
            with urllib.request.urlopen(f"{BACKEND_URL}/api/health") as r:
                data = json.loads(r.read())
                h = data.get("data", data)
                print(f"         Health Score: {h.get('health_score', '?')}")
                print(f"         Version:      {h.get('version', '?')}")
                print(f"         Phase:        {h.get('phase', '?')}")
        except Exception:
            pass
    return healthy


def start_frontend(mgr: ServiceManager) -> bool:
    """Start the Next.js frontend dev server."""
    section("Frontend (Next.js)")
    if not check_port(FRONTEND_PORT):
        warn(f"Port {FRONTEND_PORT} is already in use — frontend may already be running")
        return True

    backend_api = os.environ.get("NEXT_PUBLIC_API_URL", BACKEND_URL)
    backend_ws = os.environ.get("NEXT_PUBLIC_WS_URL", f"ws://{BACKEND_HOST}:{BACKEND_PORT}")

    proc = mgr.start(
        "frontend",
        [
            "npm", "run", "dev", "--",
            "--port", str(FRONTEND_PORT),
            "--hostname", "0.0.0.0",
        ],
        cwd=FRONTEND_DIR,
        env={
            "NEXT_PUBLIC_API_URL": backend_api,
            "NEXT_PUBLIC_WS_URL": backend_ws,
        },
    )
    if proc is None:
        return False

    healthy = mgr.wait_for_health(FRONTEND_URL, timeout=30.0, label="Frontend")
    return healthy


def start_chromadb(mgr: ServiceManager) -> bool:
    """Start ChromaDB via Docker (optional)."""
    section("ChromaDB (Docker)")
    if not check_docker():
        warn("Docker not available — skipping ChromaDB")
        return True

    if not check_port(CHROMA_PORT):
        warn(f"Port {CHROMA_PORT} is already in use — ChromaDB may already be running")
        return True

    info("Starting ChromaDB container...")
    proc = mgr.start(
        "chromadb",
        [
            "docker", "run", "--rm",
            "--name", "cortex-chromadb",
            "-p", f"{CHROMA_PORT}:8000",
            "-e", "IS_PERSISTENT=TRUE",
            "-e", "ANONYMIZED_TELEMETRY=False",
            "chromadb/chroma:latest",
        ],
    )
    if proc is None:
        warn("Failed to start ChromaDB — continuing without it")
        return True

    healthy = mgr.wait_for_health(f"http://localhost:{CHROMA_PORT}/api/v1/heartbeat", timeout=30.0, label="ChromaDB")
    if not healthy:
        warn("ChromaDB did not respond — continuing without it")
    return True


def seed_skills() -> None:
    """Run the seed script to import 22 demo skills."""
    section("Seed Skills")
    seed_script = FRONTEND_DIR / "scripts" / "seed_skills.py"
    if not seed_script.exists():
        warn(f"Seed script not found: {seed_script}")
        return
    info("Importing 22 demo skills...")
    try:
        subprocess.run(
            [sys.executable, str(seed_script), "--api-url", BACKEND_URL],
            timeout=60,
            check=True,
        )
        ok("22 demo skills imported")
    except Exception as e:
        warn(f"Seed failed: {e}")


def stop_services() -> None:
    """Stop all services identified by port."""
    section("Stopping")
    import urllib.request

    for name, port, stop_url in [
        ("frontend", FRONTEND_PORT, None),
        ("backend", BACKEND_PORT, None),
    ]:
        if not check_port(port):
            info(f"{name} (port {port}) is running —")
            # Can't really stop remote processes from here; just inform
            print(f"         Use Task Manager / kill to stop PID on port {port}")


def print_dashboard(args: argparse.Namespace) -> None:
    """Print the final dashboard with all service URLs."""
    print()
    if supports_color():
        print(color("  ╔══════════════════════════════════════════════════╗", "green"))
        print(color("  ║          All Services Ready!                     ║", "green"))
        print(color("  ╚══════════════════════════════════════════════════╝", "green"))
    else:
        print("  ==================================================")
        print("  |        All Services Ready!                     |")
        print("  ==================================================")
    print()
    print(f"  {color('Backend API:', 'bold')}   {BACKEND_URL}")
    print(f"  {color('API Docs:', 'bold')}     {BACKEND_URL}/docs")
    print(f"  {color('ReDoc:', 'bold')}        {BACKEND_URL}/redoc")
    print(f"  {color('Health:', 'bold')}       {BACKEND_URL}/api/health")
    print()
    if not args.no_frontend:
        print(f"  {color('Frontend:', 'bold')}    {FRONTEND_URL}")
        print(f"  {color('Pages:', 'bold')}       {FRONTEND_URL}/pipeline")
        print(f"  {color('', 'bold')}             {FRONTEND_URL}/agents")
        print(f"  {color('', 'bold')}             {FRONTEND_URL}/trading")
    print()
    if not args.no_chroma:
        print(f"  {color('ChromaDB:', 'bold')}    http://localhost:{CHROMA_PORT}")
    print()
    print(f"  {color('Press Ctrl+C to stop all services', 'dim')}")
    print()


# ── CLI Entry Point ────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fungal Cortex v2.0 — One-Click Startup Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start.py                 Start all services
  python start.py --no-frontend   Backend + ChromaDB only
  python start.py --no-chroma     Skip ChromaDB
  python start.py --check         Check prerequisites only
  python start.py --seed          Start and import 22 demo skills
  python start.py --stop          Show how to stop running services
        """,
    )
    parser.add_argument("--no-frontend", action="store_true", help="Skip frontend dev server")
    parser.add_argument("--no-chroma", action="store_true", help="Skip ChromaDB container")
    parser.add_argument("--check", action="store_true", help="Check prerequisites only, don't start")
    parser.add_argument("--seed", action="store_true", help="Seed 22 demo skills after startup")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument("--stop", action="store_true", help="Show instructions to stop running services")
    args = parser.parse_args()

    banner()

    if args.stop:
        stop_services()
        return

    # ── Prerequisites ──────────────────────────────────────────────────
    section("Prerequisites")
    all_ok = True
    all_ok &= check_python()
    if not args.no_frontend:
        all_ok &= check_node()
        all_ok &= check_npm()

    if args.check:
        print()
        if all_ok:
            ok("All prerequisites satisfied")
        else:
            fail("Some prerequisites are missing")
        return

    if not all_ok:
        fail("Please install missing prerequisites and try again")
        sys.exit(1)

    # ── Dependencies ───────────────────────────────────────────────────
    if not args.skip_deps:
        section("Dependencies")
        if not install_python_deps():
            sys.exit(1)
        if not args.no_frontend:
            if not install_node_deps():
                sys.exit(1)

    # ── Port Check ─────────────────────────────────────────────────────
    section("Port Availability")
    for name, port in [("Backend", BACKEND_PORT), ("Frontend", FRONTEND_PORT)]:
        if check_port(port):
            ok(f"{name} port {port} available")
        else:
            warn(f"{name} port {port} is in use — skipping")

    # ── Start Services ─────────────────────────────────────────────────
    mgr = ServiceManager()

    # Register signal handlers for graceful shutdown
    def shutdown_handler(sig, frame):
        mgr.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        # 1. ChromaDB (optional)
        if not args.no_chroma:
            start_chromadb(mgr)

        # 2. Backend
        backend_ok = start_backend(mgr)
        if not backend_ok:
            fail("Backend failed to start — aborting")
            mgr.stop_all()
            sys.exit(1)

        # 3. Frontend
        if not args.no_frontend:
            start_frontend(mgr)

        # 4. Seed skills (optional)
        if args.seed:
            seed_skills()

        # 5. Dashboard
        print_dashboard(args)

        # 6. Keep running with health monitoring and auto-restart
        health_failures = {"backend": 0}
        max_failures = 3
        health_interval = 30.0

        def check_and_restart():
            nonlocal backend_ok
            try:
                import urllib.request
                req = urllib.request.Request(f"{BACKEND_URL}/api/health")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        health_failures["backend"] = 0
                        return True
            except Exception:
                pass
            health_failures["backend"] += 1
            return False

        while True:
            time.sleep(health_interval)
            if not check_and_restart():
                if health_failures["backend"] >= max_failures:
                    warn(f"Backend health check failed {max_failures} times — restarting...")
                    mgr.stop("backend")
                    time.sleep(2)
                    backend_ok = start_backend(mgr)
                    health_failures["backend"] = 0
                    if not backend_ok:
                        fail("Backend restart failed")
                else:
                    warn(f"Backend health check failed ({health_failures['backend']}/{max_failures})")

    except KeyboardInterrupt:
        pass
    finally:
        mgr.stop_all()


if __name__ == "__main__":
    main()
