r"""Sclerotium OS v5.2 — Sci-Fi Command Center.

Powered by: Impeccable · baseline-ui · Taste Skill · GSAP
Aesthetic: Cyber-Organic Fusion (neon bioluminescence + dark matter)
Motion: Staggered reveals · particle streams · holographic depth · magnetic hover
"""

SCIFI_DASHBOARD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sclerotium OS v5.2 — Neural Command Center</title>
<script>
/* Minimal GSAP polyfill for offline/China usage */
window.gsap = {
  from(el, opts) { el.style.opacity = 0; el.style.transform = 'translateY(40px)';
    requestAnimationFrame(() => { el.style.transition = 'all '+(opts.duration||0.7)+'s '+(opts.ease||'ease-out'); el.style.opacity = 1; el.style.transform = 'none'; }); },
  to(el, opts) { el.style.transition = 'all '+(opts.duration||0.5)+'s ease-out';
    Object.keys(opts).filter(k => k !== 'duration' && k !== 'ease').forEach(k => el.style[k] = opts[k]); },
  utils: { toArray(s) { return document.querySelectorAll(s); } },
  registerPlugin() {},
};
window.ScrollTrigger = { create() {}, refresh() {} };
</script>
<style>
/* ═══════════════════════════════════════════════════════════════
   TASTE: DESIGN_VARIANCE=10 MOTION_INTENSITY=9 VISUAL_DENSITY=8
   IMPECCABLE: Anti-slop · Bold · Distinctive · No Inter/Roboto
   BASELINE-UI: compositor-only motion · reduced-motion respect
   ═══════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

:root {
  --bg-deep: #020617;
  --bg-card: rgba(15, 23, 42, 0.85);
  --border-glow: rgba(56, 189, 248, 0.3);
  --border-subtle: rgba(148, 163, 184, 0.1);
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --cyan: #22d3ee;
  --neon: #a3e635;
  --amber: #fbbf24;
  --rose: #fb7185;
  --violet: #a78bfa;
  --blue: #38bdf8;
  --emerald: #34d399;
  --font-mono: 'JetBrains Mono', monospace;
  --font-display: 'Space Grotesk', system-ui, sans-serif;
}

* { margin:0; padding:0; box-sizing:border-box; }

body {
  background: var(--bg-deep);
  color: var(--text-primary);
  font-family: var(--font-display);
  overflow-x: hidden;
  cursor: default;
}

/* ── Particle Canvas ─────────────────────────────────── */
#particles {
  position: fixed; top:0; left:0; width:100%; height:100%;
  pointer-events: none; z-index:0;
}

/* ── Grid Overlay ────────────────────────────────────── */
.grid-overlay {
  position: fixed; top:0; left:0; width:100%; height:100%;
  background-image:
    linear-gradient(rgba(56,189,248,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(56,189,248,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none; z-index:0;
}

/* ── Main Container ──────────────────────────────────── */
main {
  position: relative; z-index:1;
  max-width: 1600px; margin:0 auto; padding: 24px;
}

/* ── Header ──────────────────────────────────────────── */
.header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 24px 32px;
  background: var(--bg-card);
  border: 1px solid var(--border-glow);
  border-radius: 16px;
  backdrop-filter: blur(20px);
  margin-bottom: 24px;
  position: relative; overflow: hidden;
}
.header::before {
  content: '';
  position: absolute; top:0; left:0; right:0; height:1px;
  background: linear-gradient(90deg, transparent, var(--cyan), var(--neon), transparent);
}
.header-left { display:flex; align-items:center; gap:16px; }
.header-logo {
  width:48px; height:48px; border-radius:12px;
  background: radial-gradient(circle at 30% 30%, var(--cyan), var(--violet));
  display:flex; align-items:center; justify-content:center;
  font-size:24px;
}
.header-title h1 { font-size:28px; font-weight:700; letter-spacing:-0.5px; }
.header-title span { color: var(--cyan); }
.header-subtitle { font-size:13px; color:var(--text-secondary); font-family:var(--font-mono); }
.header-stats { display:flex; gap:32px; }
.header-stat { text-align:center; }
.header-stat .val { font-size:28px; font-weight:600; font-family:var(--font-mono); color:var(--cyan); }
.header-stat .lbl { font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; }

/* ── Dashboard Grid ──────────────────────────────────── */
.dash-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 16px;
}

/* ── Panel ───────────────────────────────────────────── */
.panel {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 20px;
  backdrop-filter: blur(12px);
  position: relative;
  transition: border-color 0.3s, box-shadow 0.3s;
}
.panel:hover {
  border-color: var(--border-glow);
  box-shadow: 0 0 30px rgba(56,189,248,0.08);
}
.panel-header {
  display:flex; align-items:center; gap:10px; margin-bottom:16px;
}
.panel-icon { font-size:18px; }
.panel-title { font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:1.5px; color:var(--text-secondary); }
.panel-title .accent { color:var(--cyan); }

/* ── Organ Grid ──────────────────────────────────────── */
.organ-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(140px,1fr));
  gap: 8px;
}
.organ-node {
  padding: 10px 12px; border-radius: 8px;
  border: 1px solid var(--border-subtle);
  font-size: 11px; font-family: var(--font-mono);
  cursor: pointer; transition: all 0.25s;
  position: relative; overflow: hidden;
}
.organ-node:hover {
  border-color: var(--neon);
  box-shadow: 0 0 20px rgba(163,230,53,0.15);
  transform: translateY(-2px);
}
.organ-node .count { color:var(--cyan); font-weight:600; }
.organ-node .name { color:var(--text-secondary); display:block; }
.organ-bar { height:2px; background:var(--border-subtle); margin-top:4px; border-radius:1px; }
.organ-bar-fill { height:100%; border-radius:1px; transition:width 0.8s ease-out; }

/* ── FCPI Radar ──────────────────────────────────────── */
.fcpi-radar {
  display:flex; align-items:center; justify-content:center;
  height:200px; position:relative;
}
.fcpi-ring {
  position:absolute; border-radius:50%; border:1px solid var(--border-subtle);
  animation: fcpiPulse 4s ease-in-out infinite;
}
.fcpi-label {
  position:absolute; font-size:10px; font-family:var(--font-mono);
  color:var(--text-muted);
}
@keyframes fcpiPulse {
  0%,100% { border-color: var(--border-subtle); }
  50% { border-color: var(--cyan); }
}

/* ── Arbiter Lanes ───────────────────────────────────── */
.arbiter-lanes { display:flex; flex-direction:column; gap:8px; }
.arbiter-lane { display:flex; align-items:center; gap:10px; }
.arbiter-lane .mode-name { width:110px; font-size:12px; font-family:var(--font-mono); color:var(--text-secondary); }
.arbiter-lane .mode-bar { flex:1; height:6px; background:var(--border-subtle); border-radius:3px; overflow:hidden; }
.arbiter-lane .mode-fill { height:100%; border-radius:3px; transition:width 1s ease-out; }

/* ── Agent Personality Cards ─────────────────────────── */
.agent-cards { display:flex; flex-wrap:wrap; gap:8px; }
.agent-card {
  padding:10px 14px; border-radius:8px;
  border:1px solid var(--border-subtle);
  cursor:pointer; transition:all 0.3s;
  min-width: 130px;
}
.agent-card:hover { border-color:var(--violet); transform:scale(1.03); }
.agent-card .agent-name { font-size:13px; font-weight:600; }
.agent-card .agent-desc { font-size:10px; color:var(--text-muted); }
.agent-card .agent-temp { font-size:10px; font-family:var(--font-mono); color:var(--amber); }

/* ── Provider Chain ──────────────────────────────────── */
.provider-chain { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
.provider-node {
  padding:6px 12px; border-radius:20px;
  font-size:11px; font-family:var(--font-mono);
  border:1px solid var(--border-subtle);
}
.provider-node.primary { border-color:var(--cyan); color:var(--cyan); }
.provider-node span { color:var(--text-muted); font-size:9px; }
.chain-arrow { color:var(--text-muted); }

/* ── Token Stats ─────────────────────────────────────── */
.token-bars { display:flex; flex-direction:column; gap:10px; }
.token-row { display:flex; align-items:center; gap:12px; }
.token-row .lbl { width:90px; font-size:12px; font-family:var(--font-mono); color:var(--text-secondary); }
.token-row .bar { flex:1; height:8px; background:var(--border-subtle); border-radius:4px; overflow:hidden; }
.token-row .fill { height:100%; border-radius:4px; transition:width 1.5s ease-out; }
.token-row .num { width:50px; font-size:12px; font-family:var(--font-mono); text-align:right; }

/* ── Memory Layers ───────────────────────────────────── */
.memory-layers { display:flex; gap:8px; }
.memory-layer {
  flex:1; text-align:center; padding:12px 8px; border-radius:8px;
  border:1px solid var(--border-subtle); cursor:pointer;
  transition:all 0.3s;
}
.memory-layer:hover { border-color:var(--violet); }
.memory-layer .layer-name { font-size:11px; font-weight:600; }
.memory-layer .layer-count { font-size:18px; font-family:var(--font-mono); color:var(--cyan); }
.memory-layer .layer-label { font-size:9px; color:var(--text-muted); }

/* ── Scrolling Ticker ────────────────────────────────── */
.ticker {
  overflow:hidden; padding:8px 0;
  border-top:1px solid var(--border-subtle);
  border-bottom:1px solid var(--border-subtle);
  margin-top:24px;
}
.ticker-track {
  display:flex; gap:48px;
  animation: ticker 30s linear infinite;
  font-family:var(--font-mono); font-size:11px; color:var(--text-muted);
}
.ticker-track span { color:var(--cyan); }
@keyframes ticker { 100% { transform:translateX(-50%); } }

/* ── Span-full panels ────────────────────────────────── */
.span-2 { grid-column: span 2; }
.span-3 { grid-column: span 3; }

/* ── Glitch effect ───────────────────────────────────── */
@keyframes glitch {
  0%,100% { opacity:1; }
  2% { opacity:0.8; transform: translateX(1px); }
  4% { opacity:1; transform: translateX(-1px); }
  6% { opacity:0.9; }
}

/* ── Responsive ──────────────────────────────────────── */
@media (max-width: 768px) {
  .dash-grid { grid-template-columns: 1fr; }
  .span-2, .span-3 { grid-column: span 1; }
  .header-stats { display:none; }
}

/* ── Chat messages ──────────────────────────────────── */
.msg { padding:8px 12px; border-radius:8px; max-width:85%; word-break:break-word; font-size:13px; line-height:1.5; }
.msg.user { background:var(--accent); color:#000; align-self:flex-end; }
.msg.assistant { background:rgba(22,27,34,0.9); border:1px solid var(--border-subtle); color:var(--text); }
.msg.error { background:rgba(248,81,73,0.15); color:var(--rose); }

/* ── Reduced motion ──────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:0.01ms !important; transition-duration:0.01ms !important; }
}
</style>
</head>
<body>

<canvas id="particles"></canvas>
<div class="grid-overlay"></div>

<main>
  <!-- ═══════ HEADER ═══════ -->
  <header class="header" data-anim="header">
    <div class="header-left">
      <div class="header-logo">🧬</div>
      <div>
        <div class="header-title"><span>Sclerotium</span> OS v5.2</div>
        <div class="header-subtitle">Neural Command Center · 238 Organs · 191 Tools</div>
      </div>
    </div>
    <div class="header-stats">
      <div class="header-stat"><div class="val" id="hdr-tools">191</div><div class="lbl">Tools</div></div>
      <div class="header-stat"><div class="val" id="hdr-organs">28</div><div class="lbl">Categories</div></div>
      <div class="header-stat"><div class="val" id="hdr-providers">5</div><div class="lbl">Providers</div></div>
      <div class="header-stat"><div class="val" id="hdr-agents">9</div><div class="lbl">Personalities</div></div>
      <div class="header-stat"><div class="val" id="hdr-health" style="color:var(--green);">OK</div><div class="lbl">Health</div></div>
    </div>
  </header>

  <div class="dash-grid">

    <!-- ═══════ ORGAN ECOSYSTEM ═══════ -->
    <div class="panel span-3" data-anim="panel">
      <div class="panel-header">
        <span class="panel-icon">🔬</span>
        <span class="panel-title">Organ Ecosystem · <span class="accent">238 Living Modules</span></span>
      </div>
      <div class="organ-grid" id="organ-grid"></div>
    </div>

    <!-- ═══════ FULL-BODY GENOME (8D replaces old 6D FCPI) ═══════ -->
    <div class="panel span-3" data-anim="panel" style="border-color:var(--border-glow);">
      <div class="panel-header">
        <span class="panel-icon">🧬</span>
        <span class="panel-title">8D Full-Body Genome · <span class="accent">MiroFish Powered (sclerotium + fungal + MiroFish)</span></span>
        <span style="margin-left:auto;font-size:11px;font-family:var(--font-mono);color:var(--neon);" id="genome-gen">Gen 5</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;" id="genome-dimensions"></div>
      <div style="margin-top:16px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;">
        <div>
          <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Top Tools (用进废退)</div>
          <div id="genome-tools"></div>
        </div>
        <div>
          <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Personality & Provider</div>
          <div id="genome-best"></div>
        </div>
        <div>
          <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">FCPI Legacy (included in genome)</div>
          <div id="genome-fcpi" style="font-family:var(--font-mono);font-size:10px;"></div>
        </div>
      </div>
    </div>

    <!-- ═══════ ARBITER MODES ═══════ -->
    <div class="panel" data-anim="panel">
      <div class="panel-header">
        <span class="panel-icon">⚖️</span>
        <span class="panel-title">Constitutional Arbiter · <span class="accent">7 Modes + CUGA</span></span>
      </div>
      <div class="arbiter-lanes" id="arbiter-lanes"></div>
      <div style="margin-top:12px; font-size:10px; color:var(--text-muted); font-family:var(--font-mono);">
        CUGA 5-Checkpoint: Intent Guard → Playbook → Tool Guide → Approvals → Output
      </div>
    </div>

    <!-- ═══════ AGENT PERSONALITIES ═══════ -->
    <div class="panel span-2" data-anim="panel">
      <div class="panel-header">
        <span class="panel-icon">👥</span>
        <span class="panel-title">Agent Personalities · <span class="accent">9 Identities</span></span>
      </div>
      <div class="agent-cards" id="agent-cards"></div>
    </div>

    <!-- ═══════ LLM PROVIDER CHAIN ═══════ -->
    <div class="panel" data-anim="panel">
      <div class="panel-header">
        <span class="panel-icon">🌐</span>
        <span class="panel-title">LLM Providers · <span class="accent">5 with Fallback</span></span>
      </div>
      <div class="provider-chain" id="provider-chain"></div>
      <div style="margin-top:14px; font-size:11px; font-family:var(--font-mono); color:var(--text-muted);">
        Retry: Exponential Backoff · Auto Failover
      </div>
    </div>

    <!-- ═══════ TOKEN TRACKER ═══════ -->
    <div class="panel" data-anim="panel">
      <div class="panel-header">
        <span class="panel-icon">💰</span>
        <span class="panel-title">Token Economy · <span class="accent">Cost Tracking</span></span>
      </div>
      <div class="token-bars" id="token-bars"></div>
    </div>

    <!-- ═══════ HEXIS MEMORY ═══════ -->
    <div class="panel span-3" data-anim="panel">
      <div class="panel-header">
        <span class="panel-icon">💾</span>
        <span class="panel-title">Hexis Memory · <span class="accent">5-Layer · Ebbinghaus Forgetting</span></span>
      </div>
      <div class="memory-layers" id="memory-layers"></div>
    </div>

    <!-- ═══════ V5.2 FEATURES ═══════ -->
    <div class="panel span-2" data-anim="panel" style="border-color:var(--border-glow);">
      <div class="panel-header">
        <span class="panel-icon">⚡</span>
        <span class="panel-title">v5.2 Capabilities · <span class="accent">Full Stack</span></span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;" id="features-grid"></div>
    </div>

    <!-- ═══════ EXTERNAL MCP ═══════ -->
    <div class="panel" data-anim="panel">
      <div class="panel-header">
        <span class="panel-icon">🔌</span>
        <span class="panel-title">External MCP Bridge · <span class="accent">Dynamic Connect</span></span>
      </div>
      <div id="ext-mcp" style="font-family:var(--font-mono);font-size:12px;"></div>
    </div>

  </div>

  <!-- ═══════ CHAT + MARKETPLACE ═══════ -->
  <div class="dash-grid" style="margin-bottom:16px;">

    <!-- Chat Dialog -->
    <div class="panel span-2" data-anim="panel">
      <div class="panel-header">
        <span class="panel-icon">💬</span>
        <span class="panel-title">Neural Link · <span class="accent">Send commands to Sclerotium</span></span>
      </div>
      <div class="chat-messages" id="chat-messages" style="max-height:240px;overflow-y:auto;display:flex;flex-direction:column;gap:8px;margin-bottom:10px;">
        <div class="msg assistant">I am Sclerotium OS v5.2. 191 tools · 8D genome · 9 personalities. Ready.</div>
      </div>
      <div style="display:flex;gap:8px;">
        <input id="chat-input" type="text" placeholder="e.g. open notepad, screenshot, search for..." style="flex:1;background:var(--bg-deep);border:1px solid var(--border-subtle);border-radius:6px;padding:8px 12px;color:var(--text-primary);font-size:13px;outline:none;" onkeydown="if(event.key==='Enter')sendMessage()">
        <button onclick="sendMessage()" style="background:var(--cyan);color:#000;border:none;padding:8px 18px;border-radius:6px;cursor:pointer;font-weight:600;">Send</button>
      </div>
    </div>

    <!-- MCP & Skills Marketplace -->
    <div class="panel" data-anim="panel">
      <div class="panel-header">
        <span class="panel-icon">🏪</span>
        <span class="panel-title">Marketplace · <span class="accent">Install MCP + Skills</span></span>
      </div>
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;">Install MCP Server</div>
      <div style="display:flex;gap:6px;margin-bottom:8px;">
        <input id="mcp-name" type="text" placeholder="name" style="width:80px;background:var(--bg-deep);border:1px solid var(--border-subtle);border-radius:4px;padding:4px 8px;color:var(--text-primary);font-size:11px;">
        <input id="mcp-cmd" type="text" placeholder="npx package@latest" style="flex:1;background:var(--bg-deep);border:1px solid var(--border-subtle);border-radius:4px;padding:4px 8px;color:var(--text-primary);font-size:11px;">
        <button onclick="installMCP()" style="background:var(--cyan);color:#000;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600;">Install</button>
      </div>
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;">Install Skill</div>
      <div style="display:flex;gap:6px;margin-bottom:8px;">
        <input id="skill-name" type="text" placeholder="name" style="width:80px;background:var(--bg-deep);border:1px solid var(--border-subtle);border-radius:4px;padding:4px 8px;color:var(--text-primary);font-size:11px;">
        <input id="skill-url" type="text" placeholder="github.com/user/repo" style="flex:1;background:var(--bg-deep);border:1px solid var(--border-subtle);border-radius:4px;padding:4px 8px;color:var(--text-primary);font-size:11px;">
        <button onclick="installSkill()" style="background:var(--neon);color:#000;border:none;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600;">Install</button>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;">
        <button onclick="quickInstallMCP('gsap','bruzethegreat-gsap-master-mcp-server')" class="provider-node" style="cursor:pointer;font-size:10px;padding:3px 8px;">GSAP</button>
        <button onclick="quickInstallMCP('figma','figma-mcp-server')" class="provider-node" style="cursor:pointer;font-size:10px;padding:3px 8px;">Figma</button>
        <button onclick="quickInstallMCP('browser','@anthropic/mcp-server-playwright')" class="provider-node" style="cursor:pointer;font-size:10px;padding:3px 8px;">Browser</button>
        <button onclick="quickInstallSkill('impeccable','pbakaus/impeccable')" class="provider-node" style="cursor:pointer;font-size:10px;padding:3px 8px;border-color:var(--neon);">Impeccable</button>
        <button onclick="quickInstallSkill('taste','Leonxlnx/taste-skill')" class="provider-node" style="cursor:pointer;font-size:10px;padding:3px 8px;border-color:var(--neon);">Taste</button>
      </div>
      <div id="market-status" style="font-size:10px;font-family:var(--font-mono);color:var(--neon);margin-top:8px;"></div>
    </div>
  </div>

  <!-- ═══════ SCROLLING TICKER ═══════ -->
  <div class="ticker">
    <div class="ticker-track">
      <span>▸ Native Function Calling</span> · 191 Tools
      <span>▸ Streaming SSE</span> · AG-UI Protocol
      <span>▸ 5 Providers</span> · Fallback Chain
      <span>▸ 7 Arbiter Modes</span> · CUGA 5-Checkpoint
      <span>▸ Session Fork/Branch</span> · Merge
      <span>▸ Idempotency</span> · Deduplication
      <span>▸ Plugin Manifest</span> · Auto-Discovery
      <span>▸ Docker Deploy</span> · Production Ready
      <span>▸ Voice Interface</span> · Whisper + Edge TTS
      <span>▸ SDK Published</span> · sclerotium_sdk
      <span>▸ 9 Personalities</span> · AGENT.md
      <span>▸ 6007 Skills</span> · Fungal Cortex
      <span>▸ Code-as-Action</span> · Python Sandbox
      <span>▸ Model Router</span> · 6-Tier Complexity
      <!-- repeat -->
      <span>▸ Native Function Calling</span> · 191 Tools
      <span>▸ Streaming SSE</span> · AG-UI Protocol
      <span>▸ 5 Providers</span> · Fallback Chain
      <span>▸ 7 Arbiter Modes</span> · CUGA 5-Checkpoint
      <span>▸ Session Fork/Branch</span> · Merge
      <span>▸ Idempotency</span> · Deduplication
      <span>▸ Plugin Manifest</span> · Auto-Discovery
      <span>▸ Docker Deploy</span> · Production Ready
      <span>▸ Voice Interface</span> · Whisper + Edge TTS
      <span>▸ SDK Published</span> · sclerotium_sdk
    </div>
  </div>
</main>

<script>
/* ═══════════════════════════════════════════════════════════════
   PARTICLE SYSTEM — Bioluminescent neural field
   ═══════════════════════════════════════════════════════════════ */
const canvas = document.getElementById('particles');
const ctx = canvas.getContext('2d');
let W, H, particles = [];

function resize() {
  W = canvas.width = window.innerWidth;
  H = canvas.height = window.innerHeight;
}
resize();
window.addEventListener('resize', resize);

class Particle {
  constructor() {
    this.reset();
    this.y = Math.random() * H;
  }
  reset() {
    this.x = Math.random() * W;
    this.y = -10;
    this.size = Math.random() * 2 + 0.5;
    this.speed = Math.random() * 0.5 + 0.1;
    this.opacity = Math.random() * 0.5 + 0.1;
    this.hue = Math.random() > 0.5 ? 190 : 80;
  }
  update() {
    this.y += this.speed;
    if (this.y > H + 10) { this.reset(); this.y = -10; }
  }
  draw() {
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    ctx.fillStyle = `hsla(${this.hue}, 80%, 65%, ${this.opacity})`;
    ctx.fill();
    // Glow
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size * 3, 0, Math.PI * 2);
    ctx.fillStyle = `hsla(${this.hue}, 80%, 65%, ${this.opacity * 0.15})`;
    ctx.fill();
  }
}

for (let i = 0; i < 120; i++) particles.push(new Particle());

function animateParticles() {
  ctx.clearRect(0, 0, W, H);
  particles.forEach(p => { p.update(); p.draw(); });
  // Draw connections between nearby particles
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x;
      const dy = particles[i].y - particles[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 100) {
        ctx.beginPath();
        ctx.moveTo(particles[i].x, particles[i].y);
        ctx.lineTo(particles[j].x, particles[j].y);
        ctx.strokeStyle = `rgba(56,189,248,${0.04 * (1 - dist / 100)})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }
    }
  }
  requestAnimationFrame(animateParticles);
}
animateParticles();

/* ═══════════════════════════════════════════════════════════════
   DATA — All Sclerotium v5.2 organs & features
   ═══════════════════════════════════════════════════════════════ */

// Organ categories with tool counts
const organs = [
  {cat:'desktop',name:'Desktop Automation',tools:6,color:'#22d3ee'},
  {cat:'shell',name:'Shell Commands',tools:4,color:'#a3e635'},
  {cat:'files',name:'File Operations',tools:7,color:'#38bdf8'},
  {cat:'web',name:'Web Search',tools:2,color:'#fb7185'},
  {cat:'memory',name:'Hexis Memory',tools:4,color:'#a78bfa'},
  {cat:'os',name:'OS Commands',tools:23,color:'#34d399'},
  {cat:'git',name:'Git Integration',tools:7,color:'#fbbf24'},
  {cat:'codebase',name:'Codebase Search',tools:6,color:'#e879f9'},
  {cat:'sandbox',name:'Sandbox',tools:2,color:'#2dd4bf'},
  {cat:'advanced',name:'Advanced Tools',tools:28,color:'#818cf8'},
  {cat:'evolution',name:'Evolution Engine',tools:10,color:'#f472b6'},
  {cat:'sovereign',name:'Sovereign',tools:18,color:'#c084fc'},
  {cat:'genesis',name:'Genesis',tools:6,color:'#fb923c'},
  {cat:'cosmic',name:'Cosmic',tools:6,color:'#67e8f9'},
  {cat:'omega',name:'Omega',tools:3,color:'#f87171'},
  {cat:'innovation',name:'Innovation',tools:4,color:'#a5f3fc'},
  {cat:'apotheosis',name:'Apotheosis',tools:3,color:'#d4d4d8'},
  {cat:'benchmark',name:'Benchmark',tools:6,color:'#fbbf24'},
  {cat:'cache',name:'Cache Engine',tools:4,color:'#93c5fd'},
  {cat:'im',name:'IM Channels',tools:8,color:'#6ee7b7'},
  {cat:'info',name:'Info System',tools:3,color:'#c7d2fe'},
  {cat:'mcp_market',name:'MCP Market',tools:6,color:'#fca5a5'},
  {cat:'skills',name:'Skills Registry',tools:3,color:'#a3e635'},
  {cat:'code_analysis',name:'Code Analysis',tools:2,color:'#f0abfc'},
  {cat:'skills_market',name:'Skills Market',tools:7,color:'#fdba74'},
  {cat:'system',name:'System Core',tools:5,color:'#67e8f9'},
  {cat:'models',name:'Model Gateway',tools:4,color:'#d8b4fe'},
  {cat:'scheduler',name:'Scheduler',tools:4,color:'#fde68a'},
  {cat:'external',name:'External MCP',tools:3,color:'#5eead4'},
];

// Render organ grid
const organGrid = document.getElementById('organ-grid');
organs.forEach(o => {
  const div = document.createElement('div');
  div.className = 'organ-node';
  div.innerHTML = `
    <span class="count">${o.tools}</span>
    <span class="name">${o.name}</span>
    <div class="organ-bar"><div class="organ-bar-fill" style="width:0%;background:${o.color}"></div></div>
  `;
  div.addEventListener('mouseenter', () => {
    gsap.to(div.querySelector('.organ-bar-fill'), {width:'100%', duration:0.5, ease:'power2.out'});
  });
  div.addEventListener('mouseleave', () => {
    const pct = Math.min(100, o.tools / 28 * 100);
    gsap.to(div.querySelector('.organ-bar-fill'), {width:pct+'%', duration:0.8, ease:'power2.out'});
  });
  div.setAttribute('data-color', o.color);
  div.setAttribute('data-pct', Math.min(100, o.tools / 28 * 100));
  organGrid.appendChild(div);
});

// FCPI legacy (shown inside genome panel as reference)
document.getElementById('genome-fcpi').innerHTML = `
  <div style="color:var(--text-muted);">Coding: <span style="color:#22d3ee;">0.82</span></div>
  <div style="color:var(--text-muted);">Coordination: <span style="color:#a3e635;">0.76</span></div>
  <div style="color:var(--text-muted);">Safety: <span style="color:#fb7185;">0.91</span></div>
  <div style="color:var(--text-muted);">Decision: <span style="color:#fbbf24;">0.79</span></div>
  <div style="color:var(--text-muted);">Emergence: <span style="color:#a78bfa;">0.68</span></div>
  <div style="color:var(--text-muted);">Performance: <span style="color:#34d399;">0.85</span></div>
  <div style="margin-top:4px;color:var(--neon);">→ All 6 now in 8D Genome</div>
`;

// Arbiter modes
const arbModes = [
  {name:'PLAN',pct:15,color:'#a78bfa'},
  {name:'DEFAULT',pct:85,color:'#22d3ee'},
  {name:'ACCEPT_EDITS',pct:40,color:'#34d399'},
  {name:'AUTO',pct:25,color:'#fbbf24'},
  {name:"DONT_ASK",pct:10,color:'#fb7185'},
  {name:'BYPASS',pct:5,color:'#f87171'},
  {name:'BUBBLE',pct:60,color:'#a3e635'},
];
const arbDiv = document.getElementById('arbiter-lanes');
arbModes.forEach(m => {
  const lane = document.createElement('div');
  lane.className = 'arbiter-lane';
  lane.innerHTML = `
    <span class="mode-name">${m.name}</span>
    <div class="mode-bar"><div class="mode-fill" style="width:0%;background:${m.color}" data-pct="${m.pct}"></div></div>
    <span style="font-size:10px;font-family:var(--font-mono);color:var(--text-muted);">${m.pct}%</span>
  `;
  arbDiv.appendChild(lane);
});

// Agent cards
const agents = [
  {name:'sclerotium',desc:'Super Electronic Lifeform',temp:0.7,color:'#22d3ee'},
  {name:'jarvis',desc:'Tony Stark AI Butler',temp:0.6,color:'#a3e635'},
  {name:'hackerman',desc:'Extreme Geek Hacker',temp:0.3,color:'#fb7185'},
  {name:'strategist',desc:'Strategic Analyst',temp:0.5,color:'#fbbf24'},
  {name:'samantha',desc:'Empathetic Companion',temp:0.9,color:'#a78bfa'},
  {name:'code-reviewer',desc:'Code Quality Expert',temp:0.2,color:'#34d399'},
  {name:'data-scientist',desc:'ML & Analytics',temp:0.3,color:'#e879f9'},
  {name:'game-designer',desc:'Unity/Unreal Creator',temp:0.8,color:'#fb923c'},
  {name:'security-auditor',desc:'OWASP Security Expert',temp:0.2,color:'#f87171'},
];
const agentDiv = document.getElementById('agent-cards');
agents.forEach(a => {
  const card = document.createElement('div');
  card.className = 'agent-card';
  card.innerHTML = `<div class="agent-name" style="color:${a.color}">${a.name}</div><div class="agent-desc">${a.desc}</div><div class="agent-temp">T=${a.temp}</div>`;
  card.addEventListener('mouseenter', () => gsap.to(card, {scale:1.05, duration:0.2}));
  card.addEventListener('mouseleave', () => gsap.to(card, {scale:1, duration:0.3}));
  agentDiv.appendChild(card);
});

// Provider chain
const providers = [
  {name:'DeepSeek',role:'Primary',primary:true},
  {name:'OpenAI',role:'Fallback 1'},
  {name:'Groq',role:'Fallback 2'},
  {name:'OpenRouter',role:'Fallback 3'},
  {name:'Ollama',role:'Local'},
];
const provDiv = document.getElementById('provider-chain');
providers.forEach((p,i) => {
  const node = document.createElement('span');
  node.className = 'provider-node' + (p.primary ? ' primary' : '');
  node.innerHTML = `${p.name} <span>${p.role}</span>`;
  provDiv.appendChild(node);
  if (i < providers.length - 1) {
    const arrow = document.createElement('span');
    arrow.className = 'chain-arrow'; arrow.textContent = '→';
    provDiv.appendChild(arrow);
  }
});

// Token stats
const tokenData = [
  {label:'Today',val:142000,max:200000,color:'#22d3ee'},
  {label:'Week',val:890000,max:1500000,color:'#a3e635'},
  {label:'Month',val:3200000,max:5000000,color:'#a78bfa'},
  {label:'Cost Today',val:0.14,max:5.0,color:'#fbbf24',prefix:'$'},
];
const tokDiv = document.getElementById('token-bars');
tokenData.forEach(t => {
  const row = document.createElement('div');
  row.className = 'token-row';
  const pct = Math.min(100, t.val / t.max * 100);
  row.innerHTML = `
    <span class="lbl">${t.label}</span>
    <div class="bar"><div class="fill" style="width:0%;background:${t.color}" data-pct="${pct}"></div></div>
    <span class="num">${t.prefix||''}${t.val.toLocaleString()}</span>
  `;
  tokDiv.appendChild(row);
});

// Memory layers
const memLayers = [
  {name:'Working',count:42,desc:'Immediate'},
  {name:'Episodic',count:156,desc:'Events'},
  {name:'Semantic',count:89,desc:'Knowledge'},
  {name:'Procedural',count:34,desc:'Skills'},
  {name:'Strategic',count:12,desc:'Insights'},
];
const memDiv = document.getElementById('memory-layers');
memLayers.forEach(l => {
  const layer = document.createElement('div');
  layer.className = 'memory-layer';
  layer.innerHTML = `<div class="layer-name">${l.name}</div><div class="layer-count">${l.count}</div><div class="layer-label">${l.desc}</div>`;
  layer.addEventListener('mouseenter', () => gsap.to(layer, {y:-4, borderColor:'#a78bfa', duration:0.25}));
  layer.addEventListener('mouseleave', () => gsap.to(layer, {y:0, borderColor:'var(--border-subtle)', duration:0.3}));
  memDiv.appendChild(layer);
});

// v5.2 features
const features = [
  {icon:'🧬',name:'Native Function Calling',desc:'191 tools via LLM tool_calls'},
  {icon:'⚡',name:'SSE Streaming',desc:'AG-UI protocol · /stream toggle'},
  {icon:'🌐',name:'5 Provider Chain',desc:'DeepSeek→OpenAI→Groq→OpenRouter→Ollama'},
  {icon:'⚖️',name:'7 Arbiter Modes',desc:'CUGA 5-Checkpoint · Merkle Audit'},
  {icon:'💾',name:'5-Layer Hexis Memory',desc:'ChromaDB · Ebbinghaus Forgetting'},
  {icon:'🧠',name:'FCPI → 8D Genome',desc:'Original 6D now inside Full-Body Evolution'},
  {icon:'🔌',name:'External MCP Bridge',desc:'stdio/http · Dynamic connect'},
  {icon:'📦',name:'Plugin Manifest',desc:'sclerotium.plugin.json · Auto-discovery'},
  {icon:'👥',name:'9 Agent Personalities',desc:'AGENT.md · Runtime switch'},
  {icon:'🔄',name:'Session Fork/Merge',desc:'JSONL+SQLite · Branch & diff'},
  {icon:'🔑',name:'Idempotency',desc:'SQLite dedup · TTL expire'},
  {icon:'🎤',name:'Voice Interface',desc:'Whisper STT · Edge/OpenAI TTS'},
  {icon:'🐳',name:'Docker Deploy',desc:'Multi-stage · docker-compose'},
  {icon:'📊',name:'Token Economy',desc:'SQLite tracking · Budget alerts'},
  {icon:'🤖',name:'Code-as-Action',desc:'Python sandbox execution'},
  {icon:'🎯',name:'Model Router',desc:'6-tier complexity → optimal model'},
];
const featDiv = document.getElementById('features-grid');
features.forEach(f => {
  const feat = document.createElement('div');
  feat.style.cssText = 'padding:8px 10px;border-radius:6px;border:1px solid var(--border-subtle);font-size:12px;cursor:default;';
  feat.innerHTML = `<span style="font-size:16px;">${f.icon}</span> <strong>${f.name}</strong><br><span style="color:var(--text-muted);font-size:10px;">${f.desc}</span>`;
  feat.addEventListener('mouseenter', () => {
    gsap.to(feat, {borderColor:'var(--cyan)', boxShadow:'0 0 12px rgba(34,211,238,0.15)', duration:0.25});
  });
  feat.addEventListener('mouseleave', () => {
    gsap.to(feat, {borderColor:'var(--border-subtle)', boxShadow:'none', duration:0.3});
  });
  featDiv.appendChild(feat);
});

// ── Full-Body Genome ──────────────────────────────────────
const genomeDims = [
  {name:'Tools',genes:23,fitness:0.92,color:'#22d3ee',icon:'🔧'},
  {name:'Prompts',genes:6,fitness:0.78,color:'#a3e635',icon:'📝'},
  {name:'Personalities',genes:5,fitness:0.76,color:'#a78bfa',icon:'👤'},
  {name:'Memory',genes:7,fitness:0.85,color:'#fbbf24',icon:'💾'},
  {name:'Providers',genes:5,fitness:0.88,color:'#34d399',icon:'🌐'},
  {name:'Skills',genes:5,fitness:0.71,color:'#fb7185',icon:'🎯'},
  {name:'Organs',genes:9,fitness:0.80,color:'#e879f9',icon:'🔬'},
  {name:'Arbiter',genes:7,fitness:0.83,color:'#fb923c',icon:'⚖️'},
];

const gDiv = document.getElementById('genome-dimensions');
genomeDims.forEach(d => {
  const dim = document.createElement('div');
  dim.style.cssText = 'padding:10px;border-radius:8px;border:1px solid var(--border-subtle);text-align:center;cursor:pointer;transition:all 0.3s;';
  dim.innerHTML = `
    <div style="font-size:20px;">${d.icon}</div>
    <div style="font-size:12px;font-weight:600;margin-top:4px;">${d.name}</div>
    <div style="font-size:18px;font-family:var(--font-mono);color:${d.color};margin-top:2px;">${d.genes}</div>
    <div style="font-size:9px;color:var(--text-muted);">genes</div>
    <div style="margin-top:4px;height:3px;background:var(--border-subtle);border-radius:2px;">
      <div style="width:0%;height:100%;background:${d.color};border-radius:2px;transition:width 1.5s;" data-genome="${d.fitness}"></div>
    </div>
    <div style="font-size:9px;font-family:var(--font-mono);color:${d.color};margin-top:2px;">${(d.fitness*100).toFixed(0)}%</div>
  `;
  dim.addEventListener('mouseenter', () => { gsap.to(dim, {y:-3, borderColor:d.color, duration:0.2}); });
  dim.addEventListener('mouseleave', () => { gsap.to(dim, {y:0, borderColor:'var(--border-subtle)', duration:0.3}); });
  gDiv.appendChild(dim);
});

// Top tools
const topTools = [
  ['desktop_open',1.00],['file_read',1.00],['file_write',1.00],
  ['bash_execute',0.98],['memory_store',0.95],
];
document.getElementById('genome-tools').innerHTML = topTools.map(([t,w]) =>
  `<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:11px;font-family:var(--font-mono);">
    <span style="color:var(--text-secondary);">${t}</span>
    <span style="color:var(--neon);">${w.toFixed(2)}</span>
  </div>`
).join('');

// Best personality & provider
document.getElementById('genome-best').innerHTML = `
  <div style="font-size:11px;margin-bottom:6px;">
    <span style="color:var(--text-muted);">Personality:</span>
    <span style="color:var(--violet);font-family:var(--font-mono);">hackerman</span>
    <span style="color:var(--neon);font-size:10px;"> (0.76)</span>
  </div>
  <div style="font-size:11px;">
    <span style="color:var(--text-muted);">Provider:</span>
    <span style="color:var(--cyan);font-family:var(--font-mono);">groq</span>
    <span style="color:var(--neon);font-size:10px;"> (0.92)</span>
  </div>
  <div style="margin-top:8px;font-size:10px;color:var(--text-muted);">
    Fitness: 0.709 · Generations: 5 · Mutations: 45
  </div>
`;

// Animate genome bars after load
setTimeout(() => {
  document.querySelectorAll('[data-genome]').forEach(el => {
    gsap.to(el, {width: el.dataset.genome * 100 + '%', duration:1.5, ease:'power3.out', delay:Math.random()*0.5});
  });
}, 1200);

// External MCP
document.getElementById('ext-mcp').innerHTML = `
  <div style="padding:8px;border:1px solid var(--border-subtle);border-radius:6px;margin-bottom:6px;">ext_gsap_animate <span style="color:var(--text-muted);">— GSAP Animation</span></div>
  <div style="padding:8px;border:1px solid var(--border-subtle);border-radius:6px;margin-bottom:6px;">ext_impeccable_audit <span style="color:var(--text-muted);">— UI Audit</span></div>
  <div style="padding:8px;border:1px solid var(--border-subtle);border-radius:6px;">ext_taste_design <span style="color:var(--text-muted);">— Taste Design</span></div>
  <div style="margin-top:8px;font-size:10px;color:var(--cyan);">connect_stdio() · connect_http()</div>
`;

/* ═══════════════════════════════════════════════════════════════
   LIVE DATA FETCH — Pull real backend data
   ═══════════════════════════════════════════════════════════════ */
async function fetchLiveData() {
  try {
    const resp = await fetch('/data/all');
    const data = await resp.json();
    updateFromLiveData(data);
    document.getElementById('refresh-time').textContent = new Date().toLocaleTimeString();
    document.getElementById('status-dot').className = 'online';
  } catch(e) {
    document.getElementById('status-dot').className = 'offline';
  }
}

function updateFromLiveData(data) {
  // Health
  if (data.health) {
    document.getElementById('hdr-tools').textContent = data.health.tool_count || 191;
    var h = document.getElementById('hdr-health');
    if (h) {
      h.textContent = data.health.status || 'OK';
      h.style.color = data.health.status === 'healthy' ? 'var(--green)' : 'var(--red)';
    }
  }

  // Organs
  if (data.organs && data.organs.categories) {
    document.getElementById('hdr-organs').textContent = data.organs.total_organs || 28;
    document.getElementById('hdr-tools').textContent = data.organs.total_tools || 191;
    updateOrganGrid(data.organs.categories);
  }

  // Genome
  if (data.genome) {
    document.getElementById('genome-gen').textContent = 'Gen ' + (data.genome.generation || 0);
    updateGenomePanel(data.genome);
  }

  // FCPI
  if (data.fcpi && data.fcpi.dimensions) {
    updateFCPI(data.fcpi);
  }

  // Arbiter
  if (data.arbiter && data.arbiter.modes) {
    updateArbiter(data.arbiter);
  }

  // Agents
  if (data.agents && data.agents.agents) {
    document.getElementById('hdr-agents').textContent = data.agents.agents.length;
    updateAgents(data.agents);
  }

  // Memory
  if (data.memory && data.memory.layers) {
    updateMemory(data.memory);
  }

  // Tokens
  if (data.tokens) {
    updateTokens(data.tokens);
  }
}

function updateOrganGrid(categories) {
  const grid = document.getElementById('organ-grid');
  grid.innerHTML = '';
  const colors = ['#22d3ee','#a3e635','#38bdf8','#fb7185','#a78bfa','#34d399','#fbbf24',
    '#e879f9','#2dd4bf','#818cf8','#f472b6','#c084fc','#fb923c','#67e8f9','#f87171',
    '#a5f3fc','#d4d4d8','#fbbf24','#93c5fd','#6ee7b7','#c7d2fe','#fca5a5','#a3e635',
    '#fdba74','#67e8f9','#d8b4fe','#fde68a','#f0abfc','#5eead4'];
  categories.forEach((o, i) => {
    const div = document.createElement('div');
    div.className = 'organ-node';
    const color = o.color || colors[i % colors.length];
    div.innerHTML = `<span class="count">${o.tools}</span><span class="name">${o.name}</span>
      <div class="organ-bar"><div class="organ-bar-fill" style="width:0%;background:${color}"></div></div>`;
    div.addEventListener('mouseenter', () => { gsap.to(div.querySelector('.organ-bar-fill'), {width:'100%', duration:0.5}); });
    div.addEventListener('mouseleave', () => { gsap.to(div.querySelector('.organ-bar-fill'), {width:Math.min(100,o.tools/28*100)+'%', duration:0.8}); });
    grid.appendChild(div);
  });
  setTimeout(() => {
    document.querySelectorAll('#organ-grid .organ-bar-fill').forEach((bar, i) => {
      const cats = categories;
      const pct = Math.min(100, (cats[i]?.tools || 1) / 28 * 100);
      gsap.to(bar, {width: pct+'%', duration:1, delay: i*0.03, ease:'power2.out'});
    });
  }, 300);
}

function updateGenomePanel(genome) {
  if (genome.dimensions) {
    const gDiv = document.getElementById('genome-dimensions');
    gDiv.innerHTML = '';
    genome.dimensions.forEach(d => {
      const dim = document.createElement('div');
      dim.style.cssText = 'padding:10px;border-radius:8px;border:1px solid var(--border-subtle);text-align:center;cursor:pointer;';
      dim.innerHTML = `<div style="font-size:20px;">${d.icon||'•'}</div>
        <div style="font-size:12px;font-weight:600;">${d.name}</div>
        <div style="font-size:18px;font-family:var(--font-mono);color:${d.color};">${d.genes}</div>
        <div style="font-size:9px;color:var(--text-muted);">genes</div>`;
      gDiv.appendChild(dim);
    });
  }
  if (genome.top_tools) {
    document.getElementById('genome-tools').innerHTML = genome.top_tools.map(t =>
      `<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:11px;font-family:var(--font-mono);">
        <span style="color:var(--text-secondary);">${t.name}</span>
        <span style="color:var(--neon);">${t.weight.toFixed(2)}</span></div>`
    ).join('');
  }
  if (genome.best_personality && genome.best_provider) {
    document.getElementById('genome-best').innerHTML = `
      <div style="font-size:11px;margin-bottom:6px;"><span style="color:var(--text-muted);">Personality:</span>
        <span style="color:var(--violet);">${genome.best_personality.name}</span> (${genome.best_personality.score})</div>
      <div style="font-size:11px;"><span style="color:var(--text-muted);">Provider:</span>
        <span style="color:var(--cyan);">${genome.best_provider.name}</span> (${genome.best_provider.score})</div>
      <div style="margin-top:8px;font-size:10px;color:var(--text-muted);">
        Fitness: ${genome.total_fitness} · Gen ${genome.generation} · Mutations: ${genome.total_mutations}</div>`;
  }
}

function updateFCPI(fcpi) {
  const div = document.getElementById('fcpi-metrics');
  div.innerHTML = '';
  fcpi.dimensions.forEach(d => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:8px;font-size:11px;';
    row.innerHTML = `<span style="color:${d.color};font-family:var(--font-mono);width:90px;">${d.name}</span>
      <div style="flex:1;height:4px;background:var(--border-subtle);border-radius:2px;">
        <div style="width:0%;height:100%;background:${d.color};border-radius:2px;" data-fcpi="${d.value}"></div></div>
      <span style="font-family:var(--font-mono);width:35px;text-align:right;color:var(--text-secondary);">${(d.value*100).toFixed(0)}%</span>`;
    div.appendChild(row);
  });
  setTimeout(() => { document.querySelectorAll('[data-fcpi]').forEach(el => {
    gsap.to(el, {width: el.dataset.fcpi*100+'%', duration:1.5, ease:'power3.out'});
  });}, 500);
}

function updateArbiter(arbiter) {
  const div = document.getElementById('arbiter-lanes');
  div.innerHTML = '';
  arbiter.modes.forEach(m => {
    const lane = document.createElement('div');
    lane.className = 'arbiter-lane';
    lane.innerHTML = `<span class="mode-name">${m.name}</span>
      <div class="mode-bar"><div class="mode-fill" style="width:0%;background:${m.color}" data-pct="${m.pct}"></div></div>
      <span style="font-size:10px;font-family:var(--font-mono);color:var(--text-muted);">${m.pct}%</span>`;
    div.appendChild(lane);
  });
  setTimeout(() => { document.querySelectorAll('[data-pct]').forEach(el => {
    gsap.to(el, {width: el.dataset.pct+'%', duration:1.2, ease:'power3.out', delay:Math.random()*0.3});
  });}, 800);
}

function updateAgents(agents) {
  const div = document.getElementById('agent-cards');
  div.innerHTML = '';
  const colorMap = {'jarvis':'#a3e635','hackerman':'#fb7185','samantha':'#a78bfa','strategist':'#fbbf24',
    'sclerotium':'#22d3ee','code-reviewer':'#34d399','data-scientist':'#e879f9',
    'game-designer':'#fb923c','security-auditor':'#f87171'};
  agents.agents.forEach(a => {
    const card = document.createElement('div');
    card.className = 'agent-card';
    const color = colorMap[a.name] || '#94a3b8';
    card.innerHTML = `<div class="agent-name" style="color:${color}">${a.name}${a.active?' ←':''}</div>
      <div class="agent-desc">${(a.description||'').slice(0,40)}</div>`;
    card.addEventListener('mouseenter', () => gsap.to(card, {scale:1.05, duration:0.2}));
    card.addEventListener('mouseleave', () => gsap.to(card, {scale:1, duration:0.3}));
    div.appendChild(card);
  });
}

function updateMemory(memory) {
  const div = document.getElementById('memory-layers');
  div.innerHTML = '';
  if (memory.layers) memory.layers.forEach(l => {
    const layer = document.createElement('div');
    layer.className = 'memory-layer';
    layer.innerHTML = `<div class="layer-name">${l.name}</div><div class="layer-count">${l.count}</div>
      <div class="layer-label">${l.desc}</div>`;
    layer.addEventListener('mouseenter', () => gsap.to(layer, {y:-4, borderColor:'#a78bfa', duration:0.25}));
    layer.addEventListener('mouseleave', () => gsap.to(layer, {y:0, borderColor:'var(--border-subtle)', duration:0.3}));
    div.appendChild(layer);
  });
}

function updateTokens(tokens) {
  const div = document.getElementById('token-bars');
  div.innerHTML = '';
  const bars = [
    {label:'Today', val: tokens.daily?.tokens_today || 0, max:200000, color:'#22d3ee'},
    {label:'Week', val: (tokens.daily?.tokens_today || 0) * 7, max:1500000, color:'#a3e635'},
    {label:'Month', val: tokens.monthly?.tokens_month || 0, max:5000000, color:'#a78bfa'},
    {label:'Cost', val: tokens.daily?.cost_today_usd || 0, max: tokens.daily?.budget_usd || 5, color:'#fbbf24', prefix:'$'},
  ];
  bars.forEach(b => {
    const row = document.createElement('div');
    row.className = 'token-row';
    const pct = Math.min(100, b.val/b.max*100);
    row.innerHTML = `<span class="lbl">${b.label}</span>
      <div class="bar"><div class="fill" style="width:0%;background:${b.color}" data-pct="${pct}"></div></div>
      <span class="num">${b.prefix||''}${b.val.toLocaleString()}</span>`;
    div.appendChild(row);
  });
  setTimeout(() => { document.querySelectorAll('.token-row .fill[data-pct]').forEach(el => {
    gsap.to(el, {width: el.dataset.pct+'%', duration:1.5, ease:'power3.out'});
  });}, 600);
}

/* ═══════════════════════════════════════════════════════════════
   GSAP ANIMATIONS — Staggered reveals with sci-fi feel
   ═══════════════════════════════════════════════════════════════ */
gsap.registerPlugin(ScrollTrigger);

// Header comes in first
gsap.from('[data-anim="header"]', {
  y: -60, opacity: 0, duration: 1, ease: 'power3.out',
});

// Panels stagger in
gsap.utils.toArray('[data-anim="panel"]').forEach((panel, i) => {
  gsap.from(panel, {
    scrollTrigger: { trigger: panel, start: 'top 90%', toggleActions: 'play none none none' },
    y: 40, opacity: 0, duration: 0.7, delay: i * 0.06, ease: 'power2.out',
  });
});

// Animate arbiter mode fills
setTimeout(() => {
  document.querySelectorAll('[data-pct]').forEach(el => {
    gsap.to(el, { width: el.dataset.pct + '%', duration: 1.2, ease: 'power3.out', delay: Math.random() * 0.3 });
  });
}, 800);

// Animate organ bar fills
setTimeout(() => {
  document.querySelectorAll('.organ-node').forEach(node => {
    const pct = node.dataset.pct || 50;
    const bar = node.querySelector('.organ-bar-fill');
    if (bar) gsap.to(bar, { width: pct + '%', duration: 1, ease: 'power2.out', delay: Math.random() * 0.5 });
  });
}, 1000);

// Pulse header stats
function pulseStats() {
  gsap.to('#hdr-tools', { scale: 1.05, duration: 0.3, yoyo: true, repeat: 1, ease: 'power2.inOut' });
}
setInterval(pulseStats, 5000);

// ── Chat ──────────────────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  input.disabled = true;
  const msgs = document.getElementById('chat-messages');
  msgs.innerHTML += `<div class="msg user">${msg}</div>`;
  msgs.innerHTML += '<div class="msg assistant" style="opacity:0.5;">Thinking...</div>';
  msgs.scrollTop = msgs.scrollHeight;
  try {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg}),
    });
    const data = await resp.json();
    const reply = data.content || data.result?.content?.[0]?.text || JSON.stringify(data).slice(0, 300);
    const last = msgs.querySelector('.msg.assistant:last-child');
    if (last) last.remove();
    msgs.innerHTML += `<div class="msg assistant">${reply}</div>`;
  } catch(e) {
    const last = msgs.querySelector('.msg.assistant:last-child');
    if (last) last.remove();
    msgs.innerHTML += `<div class="msg error">Connection failed. Is the server running?</div>`;
  }
  msgs.scrollTop = msgs.scrollHeight;
  input.disabled = false;
  input.focus();
  fetchLiveData(); // Refresh dashboard after command
}

// ── MCP & Skills Marketplace ─────────────────────────────
function installMCP() {
  const name = document.getElementById('mcp-name').value.trim();
  const cmd = document.getElementById('mcp-cmd').value.trim();
  if (!name || !cmd) { document.getElementById('market-status').textContent = 'Please enter name and package'; return; }
  document.getElementById('market-status').textContent = `Connecting MCP server "${name}" via: ${cmd}...`;
  fetch('/mcp/install', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,command:cmd})})
    .then(r => r.json()).then(d => {
      document.getElementById('market-status').textContent = d.ok ? `Installed! ${d.tools||0} tools available` : `Failed: ${d.error}`;
      fetchLiveData();
    }).catch(e => { document.getElementById('market-status').textContent = 'Backend API not available'; });
}

function installSkill() {
  const name = document.getElementById('skill-name').value.trim();
  const url = document.getElementById('skill-url').value.trim();
  if (!name || !url) { document.getElementById('market-status').textContent = 'Please enter name and URL'; return; }
  document.getElementById('market-status').textContent = `Installing skill "${name}" from ${url}...`;
  fetch('/skills/install', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,url})})
    .then(r => r.json()).then(d => {
      document.getElementById('market-status').textContent = d.ok ? `Skill "${name}" installed!` : `Failed: ${d.error}`;
      fetchLiveData();
    }).catch(e => { document.getElementById('market-status').textContent = 'Backend API not available'; });
}

function quickInstallMCP(name, pkg) {
  document.getElementById('mcp-name').value = name;
  document.getElementById('mcp-cmd').value = `npx ${pkg}`;
  installMCP();
}
function quickInstallSkill(name, repo) {
  document.getElementById('skill-name').value = name;
  document.getElementById('skill-url').value = `https://github.com/${repo}`;
  installSkill();
}

// ── Live API Data Fetch (updates dashboard with real backend data) ──
fetchLiveData().then(() => {
  // Re-animate after live data loads
  setTimeout(() => {
    document.querySelectorAll('[data-fcpi]').forEach(el => {
      gsap.to(el, {width: el.dataset.fcpi*100+'%', duration:1.5, ease:'power3.out'});
    });
  }, 600);
}).catch(() => console.log('Backend API not available — using cached data'));
// Refresh every 20 seconds
setInterval(fetchLiveData, 20000);

console.log('%c🧬 Sclerotium OS v5.2 Neural Command Center %cONLINE',
  'color:#22d3ee;font-size:18px;', 'color:#a3e635;');
console.log('%c238 Organs · 191 Tools · 5 Providers · 9 Personalities · 7 Arbiter Modes',
  'color:#94a3b8;');
console.log('%cPowered by: Impeccable · baseline-ui · Taste Skill · GSAP',
  'color:#64748b;font-size:10px;');
</script>
</body>
</html>"""


class ScifiDashboard:
    """Sci-fi neural command center dashboard."""

    def __init__(self) -> None:
        pass

    async def handle_dashboard(self, request):
        from aiohttp import web
        return web.Response(
            text=SCIFI_DASHBOARD,
            content_type="text/html",
            charset="utf-8",
        )

    def mount(self, app):
        app.router.add_get("/scifi", self.handle_dashboard)
        # Also serve as root for full experience
        app.router.add_get("/", self.handle_dashboard)
