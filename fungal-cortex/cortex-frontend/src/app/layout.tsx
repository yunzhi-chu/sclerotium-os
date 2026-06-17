import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QuantMind Cortex",
  description: "Fungal Cortex v2.0 — L6 Cognitive Operating System",
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="h-screen bg-cortex-bg text-gray-200 font-sans antialiased">
        {/* Global Navigation */}
        <nav className="fixed top-0 left-0 right-0 z-50 h-12 bg-cortex-surface border-b border-cortex-border flex items-center px-4 gap-4">
          <a href="/" className="text-cortex-primary font-mono text-sm font-bold tracking-wider">
            QuantMind Cortex
          </a>
          <div className="h-4 w-px bg-cortex-border" />
          <div className="flex gap-1">
            {[
              ["/", "Command"],
              ["/pipeline", "Pipeline"],
              ["/agents", "Agents"],
              ["/field", "Field"],
              ["/l6", "L6"],
              ["/trading", "Trading"],
              ["/skills", "Skills"],
              ["/audit", "Audit"],
              ["/market", "Market"],
              ["/backtest", "Backtest"],
            ].map(([href, label]) => (
              <a
                key={href}
                href={href}
                className="px-3 py-1 text-xs rounded hover:bg-cortex-border/50 text-gray-400 hover:text-white transition-colors"
              >
                {label}
              </a>
            ))}
          </div>
          <div className="flex-1" />
          <div className="flex items-center gap-3 text-xs text-gray-500 font-mono">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <span>L6 Active</span>
            <span className="text-gray-700">|</span>
            <span id="header-clock">--:--:--</span>
          </div>
        </nav>

        {/* Main Content */}
        <main className="pt-12 h-full overflow-hidden">
          {children}
        </main>
      </body>
    </html>
  );
}
