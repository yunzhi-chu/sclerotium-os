#!/usr/bin/env python
"""Sclerotium OS — Full Organism Launcher.

一键启动所有器官，形成完整的自进化闭环：
  sclerotium-os (TUI) + fungal-cortex (120 organs) + MiroFish (28 organs)

Usage:
  python run_full.py              # 启动完整生命体
  python run_full.py --no-evolve  # 不启动进化引擎（轻量模式）
  python -m cli.app               # 仅启动TUI（传统方式）
"""

import os, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FUNGAL = ROOT / "fungal-cortex"
MIROFISH = ROOT / "MiroFish-main" / "backend"

def check_organ(path: Path, name: str) -> bool:
    if path.exists():
        print(f"  🟢 {name}: found at {path}")
        return True
    else:
        print(f"  🔴 {name}: NOT FOUND at {path}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sclerotium OS Full Organism Launcher")
    parser.add_argument("--no-evolve", action="store_true", help="Skip evolution engine")
    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════╗
║     🧬 SCLEROTIUM OS — Full Organism Launch          ║
║     Electronic Lichen Life Form v0.5.0               ║
╚══════════════════════════════════════════════════════╝
""")

    # Phase 1: Health check
    print("[Phase 1] Scanning organs...")
    has_fungal = check_organ(FUNGAL, "fungal-cortex (120 organs)")
    has_mirofish = check_organ(MIROFISH, "MiroFish (28 organs)")
    check_organ(ROOT, "sclerotium-os (255 organs)")

    # Phase 2: Load evolution bridges
    if not args.no_evolve:
        print("\n[Phase 2] Loading evolution bridges...")
        sys.path.insert(0, str(ROOT))

        if has_fungal:
            try:
                from bridges.fungal_bridge import FungalBridge
                fb = FungalBridge()
                print("  🍄 FungalBridge ready (120 organs)")
            except Exception as e:
                print(f"  ⚠ FungalBridge error: {e}")

        if has_mirofish:
            try:
                from bridges.mirofish_bridge import MiroFishBridge
                mb = MiroFishBridge()
                print("  🐟 MiroFishBridge ready (28 organs)")
            except Exception as e:
                print(f"  ⚠ MiroFishBridge error: {e}")

        try:
            from kernel.evolution_bridge import EvolutionBridge
            eb = EvolutionBridge(str(ROOT))
            print("  🧬 EvolutionBridge ready (FCPI feedback loop)")
        except Exception as e:
            print(f"  ⚠ EvolutionBridge error: {e}")

    # Phase 3: Launch TUI
    print("\n[Phase 3] Starting Sclerotium OS TUI...")
    print("  Type /selftest to verify all systems")
    print("  Type /status to see organ vitals")
    print("  The feedback loop is ACTIVE — code you generate feeds evolution")
    print("  Evolution insights enhance your future code generation\n")

    os.chdir(str(ROOT))
    os.environ["SCLEROTIUM_FULL_ORGANISM"] = "1"  # Signal to TUI: load all bridges

    # Import and run the TUI
    from cli.tui.app import run_tui
    run_tui()

if __name__ == "__main__":
    main()
