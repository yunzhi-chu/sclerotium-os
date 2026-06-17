"""Sclerotium OS Windows Service Entry Point.

SCM invokes this script without extra arguments.
When no args: start the daemon directly as a service.
When args: delegate to win32serviceutil (install/start/stop/remove).
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_daemon():
    """Run the organism as a headless daemon (service mode)."""
    from daemon.service import SclerotiumDaemon
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("sclerotium")

    logger.info("Sclerotium OS Boot: Service mode")
    daemon = SclerotiumDaemon(headless=True)
    daemon.start()
    logger.info("Organism running. Service alive.")

    try:
        while True:
            time.sleep(10)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        daemon.stop()
        logger.info("Organism shutdown clean.")


if __name__ == "__main__":
    # If SCM calls us with no args → run daemon directly
    if len(sys.argv) <= 1:
        run_daemon()
    else:
        # Delegate to win32serviceutil (install/start/stop/remove/debug)
        try:
            from daemon.service import SclerotiumWindowsService, HAS_WIN32_SERVICE
            if HAS_WIN32_SERVICE:
                import win32serviceutil
                win32serviceutil.HandleCommandLine(SclerotiumWindowsService)
            else:
                print("pywin32 not installed — running as headless daemon")
                run_daemon()
        except ImportError:
            print("pywin32 not installed — running as headless daemon")
            run_daemon()
