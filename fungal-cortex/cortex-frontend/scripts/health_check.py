#!/usr/bin/env python3
"""Comprehensive health check for Fungal Cortex v2.0 services.

Checks backend API, frontend, ChromaDB, WebSocket connectivity, and system
resources (disk, memory).  Outputs either colour-coded terminal output
(default) or structured JSON (``--json`` flag).

Exit codes::

    0  all healthy
    1  degraded (one or more non-critical checks failed)
    2  critical (at least one essential service is down)

Usage::

    python scripts/health_check.py
    python scripts/health_check.py --json
    python scripts/health_check.py --timeout 15
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 10  # seconds per check

EXIT_OK = 0
EXIT_DEGRADED = 1
EXIT_CRITICAL = 2

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_COLOUR_SUPPORT = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _colour(code: int, text: str) -> str:
    if _COLOUR_SUPPORT:
        return f"\033[{code}m{text}\033[0m"
    return text


def green(text: str) -> str:
    return _colour(32, text)


def yellow(text: str) -> str:
    return _colour(33, text)


def red(text: str) -> str:
    return _colour(31, text)


def bold(text: str) -> str:
    return _colour(1, text)


# ---------------------------------------------------------------------------
# Check result type
# ---------------------------------------------------------------------------


class CheckResult:
    """Outcome of a single health check."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"

    STATUS_ORDER = {HEALTHY: 0, DEGRADED: 1, DOWN: 2}

    def __init__(
        self,
        name: str,
        status: str = HEALTHY,
        detail: str = "",
        metric: Optional[float] = None,
    ) -> None:
        self.name = name
        self.status = status
        self.detail = detail
        self.metric = metric

    @property
    def is_critical(self) -> bool:
        return self.status == self.DOWN

    def merge(self, other: CheckResult) -> CheckResult:
        """Combine two results: the worst status wins."""
        if self.STATUS_ORDER.get(other.status, 0) > self.STATUS_ORDER.get(self.status, 0):
            self.status = other.status
        if other.detail:
            self.detail = f"{self.detail}; {other.detail}".strip("; ")
        return self

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }
        if self.metric is not None:
            d["metric"] = self.metric
        return d

    @classmethod
    def ok(cls, name: str, detail: str = "", metric: Optional[float] = None) -> CheckResult:
        return cls(name, cls.HEALTHY, detail, metric)

    @classmethod
    def degraded(cls, name: str, detail: str = "", metric: Optional[float] = None) -> CheckResult:
        return cls(name, cls.DEGRADED, detail, metric)

    @classmethod
    def down(cls, name: str, detail: str = "", metric: Optional[float] = None) -> CheckResult:
        return cls(name, cls.DOWN, detail, metric)


# ---------------------------------------------------------------------------
# Colour-terminal rendering
# ---------------------------------------------------------------------------


def _colour_status(status: str) -> str:
    mapper = {
        CheckResult.HEALTHY: green,
        CheckResult.DEGRADED: yellow,
        CheckResult.DOWN: red,
    }
    return mapper.get(status, lambda s: s)(status.upper())


def print_terminal(results: List[CheckResult], elapsed: float) -> None:
    """Print colour-coded per-check results to terminal."""
    print(bold("Fungal Cortex v2.0  —  Health Check"))
    print("-" * 56)

    overall = CheckResult.ok("overall")
    for r in results:
        overall.merge(r)
        label = _colour_status(r.status)
        detail = f"  --  {r.detail}" if r.detail else ""
        print(f"  {label:>10}  {r.name}{detail}")

    print("-" * 56)
    overall_label = _colour_status(overall.status)
    print(f"  Overall:  {overall_label}   ({len(results)} checks in {elapsed:.2f}s)")


# ---------------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------------


def print_json(results: List[CheckResult], elapsed: float) -> None:
    """Print results as a structured JSON document."""
    overall = CheckResult.ok("overall")
    for r in results:
        overall.merge(r)

    payload: Dict[str, Any] = {
        "service": "fungal-cortex",
        "version": "2.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed_seconds": round(elapsed, 3),
        "overall_status": overall.status,
        "checks": [r.to_dict() for r in results],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _http_get(url: str, timeout: float) -> Tuple[int, Optional[str]]:
    """Perform an HTTP GET and return ``(status_code, body_or_error).``"""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.reason
    except urllib.error.URLError as e:
        return 0, str(e.reason)
    except (OSError, socket.timeout) as e:
        return 0, str(e)


def check_backend(api_url: str, timeout: float) -> CheckResult:
    """Check ``GET /api/health`` returns 200 with ``health_score > 0``."""
    url = f"{api_url.rstrip('/')}/api/health"
    status, body = _http_get(url, timeout)

    if status != 200:
        detail = body or f"HTTP {status}"
        return CheckResult.down("backend", detail)

    score = 0.0
    try:
        data = json.loads(body) if body else {}
        inner = data.get("data", data)
        score = float(inner.get("health_score", inner.get("score", 0)))
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    if score <= 0:
        return CheckResult.degraded("backend", f"health_score={score} (expected > 0)", metric=score)

    return CheckResult.ok("backend", f"HTTP {status}, health_score={score}", metric=score)


def check_frontend(frontend_url: str, timeout: float) -> CheckResult:
    """Check the Next.js frontend returns 200 on ``/``."""
    url = frontend_url.rstrip("/") + "/"
    status, body = _http_get(url, timeout)

    if status != 200:
        detail = body or f"HTTP {status}"
        return CheckResult.down("frontend", detail)

    return CheckResult.ok("frontend", f"HTTP {status}")


def check_chromadb(chroma_url: str, timeout: float) -> CheckResult:
    """Check ChromaDB heartbeat at ``/api/v1/heartbeat``."""
    url = f"{chroma_url.rstrip('/')}/api/v1/heartbeat"
    status, body = _http_get(url, timeout)

    if status != 200:
        detail = body or f"HTTP {status}"
        return CheckResult.down("chromadb", detail)

    return CheckResult.ok("chromadb", f"HTTP {status}")


def check_websocket(ws_url: str, timeout: float) -> CheckResult:
    """Check WebSocket connectivity to ``/ws/health`` with a 5-second message window.

    Uses a plain TCP socket with an HTTP Upgrade handshake to verify the
    endpoint responds.  This avoids external dependencies (no ``websockets``
    package required).
    """
    parsed = _parse_ws_url(ws_url)
    if parsed is None:
        return CheckResult.degraded("websocket", "invalid URL")

    host, port, path = parsed
    ws_timeout = min(timeout, 5.0)  # cap at 5 s for WebSocket

    try:
        sock = socket.create_connection((host, port), timeout=ws_timeout)
    except (OSError, socket.timeout) as e:
        return CheckResult.down("websocket", str(e))

    try:
        sock.settimeout(ws_timeout)

        # Send minimal WebSocket upgrade handshake
        key = "dGhlIHNhbXBsZSBub25jZQ=="  # RFC-6455 example key
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("utf-8"))

        # Read response
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk

        status_line = response.split(b"\r\n")[0].decode("utf-8", errors="replace")
        if "101" not in status_line:
            sock.close()
            return CheckResult.degraded("websocket", f"handshake failed: {status_line}")

        # Wait for first frame (masked client→server or unmasked server→client)
        # We just check that data arrives within the timeout.
        sock.settimeout(ws_timeout)
        try:
            data = sock.recv(4096)
            if data:
                sock.close()
                return CheckResult.ok("websocket", "connected, received data")
            else:
                sock.close()
                return CheckResult.ok("websocket", "connected (empty frame)")
        except socket.timeout:
            sock.close()
            return CheckResult.degraded("websocket", "connected but no data within 5 s")

    except (OSError, socket.timeout) as e:
        return CheckResult.down("websocket", str(e))
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _parse_ws_url(url: str) -> Optional[Tuple[str, int, str]]:
    """Parse a ``ws://`` or ``wss://`` URL into ``(host, port, path)``."""
    url = url.strip()
    ssl = False
    if url.startswith("wss://"):
        ssl = True
        url = url[6:]
    elif url.startswith("ws://"):
        url = url[5:]
    else:
        return None

    if "/" in url:
        host_part, _, path = url.partition("/")
        path = "/" + path
    else:
        host_part = url
        path = "/ws/health"

    if ":" in host_part:
        host, _, port_str = host_part.partition(":")
        try:
            port = int(port_str)
        except ValueError:
            return None
    else:
        host = host_part
        port = 443 if ssl else 80

    return host, port, path


def check_disk(path: str = "/", min_free_pct: float = 10.0) -> CheckResult:
    """Check disk space at ``path`` has at least ``min_free_pct`` free."""
    try:
        usage = shutil.disk_usage(path)
        free_pct = usage.free / usage.total * 100
    except PermissionError:
        return CheckResult.degraded("disk", "permission denied")
    except FileNotFoundError:
        return CheckResult.degraded("disk", f"path not found: {path}")
    except OSError as e:
        return CheckResult.degraded("disk", str(e))

    free_gb = usage.free / (1024 ** 3)
    if free_pct < min_free_pct:
        return CheckResult.degraded(
            "disk",
            f"{free_gb:.1f} GiB free ({free_pct:.1f}%) — below {min_free_pct:.0f}% threshold",
            metric=free_pct,
        )

    return CheckResult.ok(
        "disk",
        f"{free_gb:.1f} GiB free ({free_pct:.1f}%)",
        metric=free_pct,
    )


def check_memory(min_free_mb: float = 256.0) -> CheckResult:
    """Check available memory exceeds ``min_free_mb``.

    Uses ``/proc/meminfo`` on Linux, ``sysctl`` on macOS, and
    ``GlobalMemoryStatusEx`` via ctypes on Windows.  Falls back to a
    degraded result with a warning if the platform is unrecognised.
    """
    free_mb = _get_free_memory_mb()

    if free_mb is None:
        return CheckResult.degraded("memory", "unable to determine (unsupported platform)")

    if free_mb < min_free_mb:
        return CheckResult.degraded(
            "memory",
            f"{free_mb:.0f} MiB free — below {min_free_mb:.0f} MiB threshold",
            metric=free_mb,
        )

    return CheckResult.ok("memory", f"{free_mb:.0f} MiB free", metric=free_mb)


def _get_free_memory_mb() -> Optional[float]:
    """Return available/free memory in MiB, or ``None`` if detection fails."""
    system = sys.platform.lower()

    if system == "linux":
        return _get_free_memory_linux()
    elif system == "darwin":
        return _get_free_memory_macos()
    elif system == "win32":
        return _get_free_memory_windows()
    else:
        return None


def _get_free_memory_linux() -> Optional[float]:
    """Parse ``/proc/meminfo`` for ``MemAvailable``."""
    try:
        with open("/proc/meminfo", "r") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    parts = line.split()
                    kb = int(parts[1])
                    return kb / 1024.0
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        pass
    return None


def _get_free_memory_macos() -> Optional[float]:
    """Use ``sysctl hw.memsize`` as a rough upper bound, then estimate free pages."""
    try:
        import subprocess

        # Try vm_stat for free pages
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            free_pages = 0
            for line in result.stdout.splitlines():
                if "free" in line.lower():
                    parts = line.split(":")
                    if len(parts) == 2:
                        try:
                            free_pages += int(parts[1].strip().rstrip("."))
                        except ValueError:
                            continue
            return free_pages * 16384 / (1024 * 1024)  # 16 KiB page → MiB
    except Exception:
        pass
    return None


def _get_free_memory_windows() -> Optional[float]:
    """Use ctypes to call ``GlobalMemoryStatusEx``."""
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32 = ctypes.windll.kernel32
        if kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            return mem.ullAvailPhys / (1024 * 1024)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprehensive health check for Fungal Cortex v2.0 services.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as structured JSON instead of coloured terminal text",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout per check in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("BACKEND_URL", "http://localhost:8000"),
        help="Backend API URL (default: http://localhost:8000, or BACKEND_URL env)",
    )
    parser.add_argument(
        "--frontend-url",
        default=os.environ.get("FRONTEND_URL", "http://localhost:3000"),
        help="Frontend URL (default: http://localhost:3000, or FRONTEND_URL env)",
    )
    parser.add_argument(
        "--chroma-url",
        default=os.environ.get("CHROMA_URL", "http://localhost:8001"),
        help="ChromaDB URL (default: http://localhost:8001, or CHROMA_URL env)",
    )
    parser.add_argument(
        "--ws-url",
        default=os.environ.get("WS_URL", "ws://localhost:8000/ws/health"),
        help="WebSocket URL (default: ws://localhost:8000/ws/health, or WS_URL env)",
    )
    parser.add_argument(
        "--disk-path",
        default=os.environ.get("DISK_CHECK_PATH", "/"),
        help="Filesystem path for disk usage check (default: /, or DISK_CHECK_PATH env)",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    timeout = max(args.timeout, 1.0)

    checks: List[CheckResult] = []

    # Run all checks ------------------------------------------------
    start = time.perf_counter()

    checks.append(check_backend(args.api_url, timeout))
    checks.append(check_frontend(args.frontend_url, timeout))
    checks.append(check_chromadb(args.chroma_url, timeout))
    checks.append(check_websocket(args.ws_url, timeout))
    checks.append(check_disk(args.disk_path))
    checks.append(check_memory())

    elapsed = time.perf_counter() - start

    # Render output ------------------------------------------------
    if args.json:
        print_json(checks, elapsed)
    else:
        print_terminal(checks, elapsed)

    # Determine exit code ------------------------------------------
    has_critical = any(r.is_critical for r in checks)
    has_degraded = any(r.status == CheckResult.DEGRADED for r in checks)

    if has_critical:
        sys.exit(EXIT_CRITICAL)
    elif has_degraded:
        sys.exit(EXIT_DEGRADED)
    else:
        sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
