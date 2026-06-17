"""CLI Benchmark Screen — Interactive benchmark dashboard.

Displays benchmark results, FCPI vector, global leaderboard comparison,
and historical trends in the Textual TUI.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Header, Footer, Static, Label, ProgressBar


class BenchmarkScreen(Screen):
    """Benchmark dashboard screen for Sclerotium OS TUI."""

    CSS = """
    BenchmarkScreen {
        background: $surface;
    }
    #benchmark-container {
        height: 100%;
        padding: 1;
    }
    #header-section {
        height: 5;
        dock: top;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }
    .section-title {
        text-style: bold;
        color: $accent;
        padding: 1 0;
    }
    #fcpi-section {
        height: 8;
        margin-bottom: 1;
    }
    #scores-section {
        height: auto;
        margin-bottom: 1;
    }
    #leaderboard-section {
        height: auto;
    }
    .score-good { color: $success; }
    .score-warn { color: $warning; }
    .score-bad { color: $error; }
    #btn-run { dock: bottom; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Static("🏆 SCLEROTIUM OS — BENCHMARK DASHBOARD", id="header-title"),
                Static("Benchmarks: SWE-bench Pro · Terminal-Bench 2.0 · MCP Atlas · FCPI 6D · Safety · Memory · Sandstorm · Coordination", id="header-subtitle"),
                id="header-section",
            ),
            Vertical(
                Static("📊 FCPI 6-DIMENSION VECTOR", classes="section-title"),
                Static("Loading FCPI data...", id="fcpi-display"),
                id="fcpi-section",
            ),
            Vertical(
                Static("📋 BENCHMARK SCORES", classes="section-title"),
                Static("Run benchmarks to see scores...", id="scores-display"),
                id="scores-section",
            ),
            Vertical(
                Static("🌍 GLOBAL LEADERBOARD COMPARISON", classes="section-title"),
                Static("Loading leaderboard...", id="leaderboard-display"),
                id="leaderboard-section",
            ),
            Button("▶ Run Full Benchmark Suite", id="btn-run", variant="primary"),
            id="benchmark-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load initial data when screen mounts."""
        self._refresh_fcpi()
        self._refresh_leaderboard()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-run":
            self._run_benchmarks()

    def _refresh_fcpi(self) -> None:
        """Refresh FCPI display."""
        try:
            from kernel.benchmark.fcpi_benchmark import FCPIBenchmark
            bench = FCPIBenchmark(".")
            vector = bench.run()

            dims = [
                ("Coding (C)", vector.coding),
                ("Coordination (Co)", vector.coordination),
                ("Safety (S)", vector.safety),
                ("Decision (D)", vector.decision),
                ("Emergence (E)", vector.emergence),
                ("Performance (P)", vector.performance),
            ]

            lines = []
            for name, score in dims:
                bar_len = int(score * 30)
                bar = "█" * bar_len + "░" * (30 - bar_len)
                css_class = "score-good" if score > 0.6 else ("score-warn" if score > 0.3 else "score-bad")
                lines.append(f"  {name:<18} [{bar}] {score:.2f}")

            lines.append(f"  {'─' * 60}")
            lines.append(f"  {'AGGREGATE':<18} {'':>32} {vector.aggregate():.2f}")

            widget = self.query_one("#fcpi-display", Static)
            widget.update("\n".join(lines))
        except Exception as e:
            widget = self.query_one("#fcpi-display", Static)
            widget.update(f"FCPI Error: {e}")

    def _refresh_leaderboard(self) -> None:
        """Refresh global leaderboard comparison."""
        try:
            from kernel.benchmark.scorer import GlobalLeaderboard

            lines = []
            for category in ["coding", "agent", "terminal"]:
                rankings = GlobalLeaderboard.get_rankings(category)[:3]
                lines.append(f"  [{category.upper()}]")
                for r in rankings:
                    medal = "🥇" if r["rank"] == 1 else "🥈" if r["rank"] == 2 else "🥉"
                    lines.append(f"    {medal} {r['system']:<30} {r['score']}% ({r['benchmark']})")

            widget = self.query_one("#leaderboard-display", Static)
            widget.update("\n".join(lines))
        except Exception as e:
            widget = self.query_one("#leaderboard-display", Static)
            widget.update(f"Leaderboard Error: {e}")

    def _run_benchmarks(self) -> None:
        """Run the full benchmark suite."""
        import asyncio

        widget = self.query_one("#scores-display", Static)
        widget.update("⏳ Running benchmarks...")

        async def _run():
            try:
                from kernel.benchmark.engine import BenchmarkEngine
                engine = BenchmarkEngine()
                engine.register_all()
                suite = await engine.run_full_suite(model="sclerotium-os")

                # Update scores display
                lines = [f"  Suite: {suite.suite_id}"]
                lines.append(f"  Total Score: {suite.total_score:.1f}/100")
                lines.append(f"  Global Percentile: {suite.global_percentile or 0:.1f}%")
                lines.append(f"  Rating: {_get_rating(suite.total_score)}")
                lines.append("")

                for r in suite.results:
                    icon = "✅" if r.status.value == "passed" else "⚠️" if r.status.value == "skipped" else "❌"
                    lines.append(f"  {icon} {r.name:<35} {r.score:>5.1f}%")

                if suite.fcpi_vector:
                    lines.append("")
                    lines.append("  FCPI Vector:")
                    for k, v in suite.fcpi_vector.items():
                        lines.append(f"    {k}: {v:.3f}")

                widget.update("\n".join(lines))

                # Also print report to console
                print(engine.format_report(suite))

            except Exception as e:
                widget.update(f"❌ Benchmark error: {e}")

        asyncio.create_task(_run())


def _get_rating(score: float) -> str:
    if score >= 90: return "S+ (Transcendent)"
    if score >= 85: return "S (World-Class)"
    if score >= 78: return "A+ (Excellent)"
    if score >= 70: return "A (Very Good)"
    if score >= 60: return "B+ (Good)"
    if score >= 50: return "B (Above Average)"
    if score >= 40: return "C (Average)"
    return "F (Needs Improvement)"
