#!/usr/bin/env python3
"""Sclerotium OS — Daemon Launcher.

The single entry point that brings the electronic organism to life.

Usage:
    # Run in foreground (debug mode — see all logs)
    python daemon_launcher.py

    # Run in headless mode (no tray icon)
    python daemon_launcher.py --headless

    # Run with custom home directory
    python daemon_launcher.py --home "D:/my-sclerotium"

    # Show status
    python daemon_launcher.py --status

    # Windows service management (requires admin)
    python daemon_launcher.py --install    # Install as Windows service
    python daemon_launcher.py --start      # Start the service
    python daemon_launcher.py --stop       # Stop the service
    python daemon_launcher.py --remove     # Remove the service
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the daemon."""
    fmt = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
        ],
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(
        description="Sclerotium OS — Electronic Lifeform Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--home", default=os.path.expanduser("~/.sclerotium"),
        help="Sclerotium home directory (default: ~/.sclerotium)",
    )
    p.add_argument(
        "--headless", action="store_true",
        help="Run without system tray icon",
    )
    p.add_argument(
        "--debug", action="store_true",
        help="Enable debug-level logging",
    )
    p.add_argument(
        "--status", action="store_true",
        help="Print current organism status and exit",
    )
    p.add_argument(
        "--install", action="store_true",
        help="Install as Windows service",
    )
    p.add_argument(
        "--start", action="store_true",
        help="Start the Windows service",
    )
    p.add_argument(
        "--stop", action="store_true",
        help="Stop the Windows service",
    )
    p.add_argument(
        "--remove", action="store_true",
        help="Remove the Windows service",
    )
    p.add_argument(
        "--service", action="store_true",
        help="Run as Windows service (invoked by SCM)",
    )
    return p.parse_args(argv)


def handle_windows_service(args: argparse.Namespace) -> bool:
    """Handle Windows service commands. Returns True if a service command was processed."""
    from daemon.service import HAS_WIN32_SERVICE, SclerotiumWindowsService

    if not HAS_WIN32_SERVICE:
        print("Windows service support requires pywin32. Install with: pip install pywin32")
        return True  # It was a service command, but we can't fulfill it

    try:
        if args.install:
            win32serviceutil.InstallService(
                None, SclerotiumWindowsService._svc_name_,
                SclerotiumWindowsService._svc_display_name_,
                exeName=sys.executable,
            )
            print("✅ Sclerotium OS service installed.")
            return True

        if args.remove:
            win32serviceutil.RemoveService(SclerotiumWindowsService._svc_name_)
            print("✅ Sclerotium OS service removed.")
            return True

        if args.start:
            win32serviceutil.StartService(SclerotiumWindowsService._svc_name_)
            print("✅ Sclerotium OS service started.")
            return True

        if args.stop:
            win32serviceutil.StopService(SclerotiumWindowsService._svc_name_)
            print("✅ Sclerotium OS service stopped.")
            return True
    except Exception as e:
        print(f"❌ Service operation failed: {e}")
        return True

    return False


def run_status_only(home_dir: str) -> None:
    """Print organism status and exit."""
    from orchestrator.lifecycle import LifecycleManager

    lm = LifecycleManager(home_dir=home_dir, headless=True)
    state = lm.status()

    print(f"╔════════════════════════════════════╗")
    print(f"║  🧬 Sclerotium OS v{state.version}          ║")
    print(f"╠════════════════════════════════════╣")
    print(f"║  Phase:    {state.phase.value:<24s} ║")
    print(f"║  Organs:   {len(state.organs):>3d} total             ║")
    print(f"║  Mode:     {state.mode:<24s} ║")
    if state.uptime_seconds > 0:
        print(f"║  Uptime:   {state.uptime_seconds:.0f}s{'':>19s} ║")
    print(f"╚════════════════════════════════════╝")


def run_foreground(args: argparse.Namespace) -> None:
    """Run the daemon in the foreground."""
    from daemon.service import SclerotiumDaemon

    logger = logging.getLogger("sclerotium")
    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║  🧬 Sclerotium OS — Electronic Lifeform  ║")
    logger.info("║  Booting organism...                     ║")
    logger.info("╚══════════════════════════════════════════╝")

    daemon = SclerotiumDaemon(
        home_dir=args.home,
        project_root=PROJECT_ROOT,
        headless=args.headless,
    )

    # Start tray icon if not headless
    tray = None
    if not args.headless:
        try:
            from daemon.tray_icon import TrayController, is_tray_available

            if is_tray_available():
                def on_quit():
                    daemon.stop()
                    # Give threads a moment to clean up
                    time.sleep(0.5)

                tray = TrayController(
                    lifecycle=daemon.lifecycle,
                    on_show_status=lambda: (
                        f"Phase: {daemon.lifecycle.phase.value}\n"
                        f"Organs: {daemon.lifecycle.organ_count}\n"
                        f"Healthy: {daemon.lifecycle.healthy_count}/{daemon.lifecycle.organ_count}"
                    ),
                    on_quit=on_quit,
                )
                daemon.tray = tray

                # Start tray in a background thread
                import threading
                tray_thread = threading.Thread(
                    target=tray.start,
                    name="sclerotium-tray",
                    daemon=True,
                )
                tray_thread.start()
                logger.info("System tray icon started.")
            else:
                logger.warning("System tray not available (pystray/Pillow not installed).")
        except Exception as e:
            logger.warning("Could not start system tray: %s", e)

    # Run the daemon (blocks until shutdown)
    try:
        daemon.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if tray:
            try:
                tray.stop()
            except Exception:
                pass
        logger.info("Organism shutdown complete.")


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = parse_args(argv)

    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)

    # Handle --status (one-shot status check)
    if args.status:
        run_status_only(args.home)
        return 0

    # Handle Windows service commands
    if any([args.install, args.start, args.stop, args.remove]):
        return 0 if handle_windows_service(args) else 1

    # Handle --service (Windows SCM invocation)
    if args.service:
        import daemon.service as svc_mod
        if svc_mod.HAS_WIN32_SERVICE:
            svc_mod.SclerotiumWindowsService.run_as_service()
        else:
            print("ERROR: pywin32 not installed for Windows service")
            # Fallback: run headless daemon
            args.headless = True
            run_foreground(args)
        return 0

    # Run the organism
    run_foreground(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
