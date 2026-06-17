"""Sclerotium OS CLI — entry point for `python -m cli`.

Usage:
    python -m cli                  # Rich REPL (legacy, full body startup)
    python -m cli --tui            # Claude Code-equivalent Textual TUI
    python -m cli --dashboard      # Rich dashboard
    python -m cli --status         # Quick status
"""

import asyncio
import sys

# Route to the appropriate runner
if "--tui" in sys.argv:
    from cli.tui.app import run_tui
    run_tui()
else:
    from cli.app import SclerotiumCLI
    cli = SclerotiumCLI()
    asyncio.run(cli.run())
