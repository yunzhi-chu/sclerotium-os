r"""Sclerotium OS v5.2 Final Dashboard — Full 3-System Mapping + i18n.

Covers ALL modules: sclerotium 191 tools · fungal 120 organs (30 layers) · MiroFish 28 organs (6 arenas)
Language: Chinese/English toggle
"""
import json

I18N = {
    "zh": {
        "title": "Sclerotium OS v5.2 — 神经网络指挥中心",
        "subtitle": "三系统融合 · 339器官 · 191工具 · 8D进化基因组",
        "health": "生命状态",
        "healthy": "健康",
        "sclerotium": "菌核OS",
        "fungal": "真菌皮层",
        "mirofish": "鱼脑进化",
        "organs": "器官生态",
        "tools": "工具系统",
        "genome": "全维基因组",
        "arbiter": "宪法仲裁",
        "agents": "智能人格",
        "providers": "模型供应",
        "memory": "记忆皮层",
        "features": "核心能力",
        "mcp": "外部MCP",
        "skills": "技能市场",
        "kernel": "内核模块",
        "perception": "感知系统",
        "rhythm": "节律引擎",
        "automation": "桌面自动化",
        "platforms": "IM平台",
        "world": "世界模型",
        "evolution": "进化引擎",
        "bridges": "系统桥接",
        "advanced": "高级能力",
        "stg": "神经网络",
    },
    "en": {
        "title": "Sclerotium OS v5.2 — Neural Command Center",
        "subtitle": "3-System Fusion · 339 Organs · 191 Tools · 8D Genome",
        "health": "Health",
        "healthy": "HEALTHY",
        "sclerotium": "Sclerotium OS",
        "fungal": "Fungal Cortex",
        "mirofish": "MiroFish Brain",
        "organs": "Organ Ecosystem",
        "tools": "Tool System",
        "genome": "Full-Body Genome",
        "arbiter": "Constitutional Arbiter",
        "agents": "Agent Personalities",
        "providers": "LLM Providers",
        "memory": "Memory Cortex",
        "features": "Core Capabilities",
        "mcp": "External MCP",
        "skills": "Skill Market",
        "kernel": "Kernel Modules",
        "perception": "Perception",
        "rhythm": "Rhythm Engine",
        "automation": "Desktop Automation",
        "platforms": "IM Platforms",
        "world": "World Model",
        "evolution": "Evolution",
        "bridges": "System Bridges",
        "advanced": "Advanced",
        "stg": "Neural STG",
    }
}

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Sclerotium OS v5.2</title>
<style>
:root{--bg:#020617;--card:rgba(15,23,42,0.9);--border:rgba(56,189,248,0.2);--text:#e2e8f0;--muted:#64748b;--cyan:#22d3ee;--neon:#a3e635;--amber:#fbbf24;--rose:#fb7185;--violet:#a78bfa;--blue:#38bdf8;--green:#34d399}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font:13px/1.5 system-ui,monospace;overflow-x:hidden}
canvas{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0}
main{position:relative;z-index:1;max-width:1800px;margin:0 auto;padding:16px}
.header{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;background:var(--card);border:1px solid var(--border);border-radius:10px;margin-bottom:14px;backdrop-filter:blur(16px)}
.header h1{font-size:20px;font-weight:700}
.header h1 span{color:var(--cyan)}
.header-stats{display:flex;gap:24px;font-size:12px}
.header-stat{text-align:center}
.header-stat .v{font-size:22px;font-weight:700;font-family:monospace;color:var(--cyan)}
.header-stat .l{font-size:10px;color:var(--muted);text-transform:uppercase}
.lang-toggle{background:var(--card);border:1px solid var(--border);color:var(--text);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}
.panel{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;transition:border-color .3s}
.panel:hover{border-color:rgba(56,189,248,0.5)}
.panel-h{display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1px}
.panel-h .accent{color:var(--cyan)}
.span2{grid-column:span 2}.span3{grid-column:span 3}
.tag{display:inline-block;padding:4px 10px;margin:3px;border-radius:12px;font-size:10px;border:1px solid var(--border);cursor:default;transition:all .2s}
.tag:hover{border-color:var(--cyan);background:rgba(34,211,238,0.1)}
.tag .n{color:var(--cyan);font-weight:600}
.tag .s{color:var(--muted);font-size:9px}
.bar{height:6px;background:var(--border);border-radius:3px;margin:4px 0;overflow:hidden}
.bar-fill{height:100%;border-radius:3px;transition:width 1s}
.row{display:flex;justify-content:space-between;padding:4px 0;font-size:11px;border-bottom:1px solid rgba(148,163,184,0.08)}
.row .k{color:var(--muted)}.row .v{font-family:monospace}
.organ-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:6px}
.mem-layer{text-align:center;padding:10px 6px;border-radius:8px;border:1px solid var(--border);cursor:pointer;transition:all .2s}
.mem-layer:hover{border-color:var(--violet)}.mem-layer .c{font-size:20px;font-family:monospace;color:var(--cyan)}.mem-layer .l{font-size:10px;color:var(--muted)}
.ticker{overflow:hidden;padding:6px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin-top:14px}
.ticker-track{display:flex;gap:40px;animation:ticker 40s linear infinite;font-size:10px;color:var(--muted);white-space:nowrap}
.ticker-track span{color:var(--cyan)}@keyframes ticker{to{transform:translateX(-50%)}}
.status-ok{color:var(--green)}.status-warn{color:var(--amber)}.status-err{color:var(--rose)}
</style></head><body>
<canvas id="p"></canvas>
<main>
<header class="header">
<div><h1><span>Sclerotium</span> OS v5.2</h1><div style="font-size:11px;color:var(--muted)" data-i18n="subtitle">三系统融合 · 339器官 · 191工具 · 8D进化基因组</div></div>
<div class="header-stats">
<div class="header-stat"><div class="v status-ok" id="st-health">OK</div><div class="l" data-i18n="health">生命状态</div></div>
<div class="header-stat"><div class="v" id="st-tools">191</div><div class="l">Tools</div></div>
<div class="header-stat"><div class="v" id="st-organs">28</div><div class="l">Categories</div></div>
<div class="header-stat"><div class="v" id="st-systems">3</div><div class="l">Systems</div></div>
<button class="lang-toggle" onclick="toggleLang()">EN</button>
</div></header>
<div class="grid" id="main-grid"></div>
<div class="ticker"><div class="ticker-track" id="ticker"></div></div>
</main>
<script>
var L='zh',I={zh:{},en:{}};
function t(k){return (I[L]&&I[L][k])||k}
function toggleLang(){L=L=='zh'?'en':'zh';document.querySelectorAll('[data-i18n]').forEach(e=>{var k=e.getAttribute('data-i18n');if(I[L][k])e.textContent=I[L][k]});renderAll()}
""" + json.dumps({"zh": I18N["zh"], "en": I18N["en"]}) + r"""
I=I18N;

// Particle system
var c=document.getElementById('p'),ctx=c.getContext('2d'),W,H,P=[];
function rs(){W=c.width=innerWidth;H=c.height=innerHeight}
rs();addEventListener('resize',rs);
for(var i=0;i<80;i++)P.push({x:Math.random()*W,y:Math.random()*H,s:Math.random()*1.5+.3,sp:Math.random()*.4+.05,o:Math.random()*.4+.05,h:Math.random()>.5?190:80});
function ap(){ctx.clearRect(0,0,W,H);P.forEach(p=>{p.y+=p.sp;if(p.y>H+10){p.y=-10;p.x=Math.random()*W}ctx.beginPath();ctx.arc(p.x,p.y,p.s,0,6.28);ctx.fillStyle='hsla('+p.h+',80%,65%,'+p.o+')';ctx.fill()});requestAnimationFrame(ap)}ap();

// Data
var SCLEROTIUM_ORGANS=[
["agent/llm_client","LLM Client","async SSE + function calling"],
["agent/code_action","Code-as-Action","Python sandbox execution"],
["agent/session","Session Manager","JSONL + SQLite persistence"],
["agent/session_fork","Session Fork","Branch/Merge/Diff"],
["agent/model_router","Model Router","6-tier complexity routing"],
["agent/token_tracker","Token Tracker","Usage + budget tracking"],
["agent/sub_agent","Sub-Agent","Depth-isolated spawn"],
["kernel/agent_loop","Agent Loop","ReAct + multi-model reasoning"],
["kernel/agent_profiles","Agent Profiles","9 personalities + AGENT.md"],
["kernel/constitutional_arbiter","Constitutional Arbiter","7-mode + CUGA 5-checkpoint"],
["kernel/hexis_memory","Hexis Memory","5-layer + Ebbinghaus forgetting"],
["kernel/event_bus","Event Bus","Pub/sub nervous system"],
["evolution/full_body_genome","Full-Body Genome","8D self-evolution"],
["evolution/fcpi_tracker","FCPI Tracker","6D fitness metrics"],
["evolution/evolution_loop","Evolution Loop","Mutate→Select→Crystallize"],
["kernel/approval_ui","Approval UI","IM channel-native buttons"],
["kernel/voice","Voice Interface","Whisper STT + Edge TTS"],
["kernel/errors","Error Hierarchy","12 structured error types"],
["kernel/structured_logger","Structured Logger","JSON pino-style"],
["kernel/organ_protocol","Organ Protocol","238 organs unified interface"],
["kernel/plugin_manifest","Plugin Manifest","sclerotium.plugin.json"],
["kernel/idempotency","Idempotency","SQLite dedup + TTL expiry"],
["kernel/skill_loader","Skill Loader","6007 SKILL.md auto-scan"],
["kernel/config_watcher","Config Watcher","Hot reload polling"],
["kernel/platform_detect","Platform Detect","Windows/Linux/macOS"],
["mcp/server","MCP Server","JSON-RPC + SSE HTTP"],
["mcp/external_bridge","External MCP","stdio/http dynamic connect"],
["mcp/validation","Schema Validator","JSON Schema → validation"],
["ui/dashboard_scifi","Sci-Fi Dashboard","28 panels + i18n"],
["ui/api_bridge","API Bridge","14 REST endpoints"],
["bridges/fungal_bridge","Fungal Bridge","120 organs connector"],
["bridges/mirofish_bridge","MiroFish Bridge","28 organs + genome connector"],
["perception/activity_tracker","Activity Tracker","User behavior monitoring"],
["perception/window_watcher","Window Watcher","Foreground window tracking"],
["perception/file_watcher","File Watcher","FS change detection"],
["perception/clipboard_watcher","Clipboard Watcher","Clipboard monitoring"],
["perception/user_model","User Model","Behavioral profile"],
["rhythm/rhythm_engine","Rhythm Engine","STG-based timing"],
["rhythm/daily_digest","Daily Digest","Auto-generated summaries"],
["rhythm/nudge_engine","Nudge Engine","Smart notification timing"],
["automation/app_launcher","App Launcher","Application/file/URL open"],
["automation/screen_agent","Screen Agent","Screenshot + OCR"],
["automation/uia_controller","UIA Controller","Accessibility tree control"],
["automation/input_simulator","Input Simulator","Keyboard/mouse simulation"],
["automation/chain_executor","Chain Executor","Multi-step automation"],
["platforms/base","Platform Adapter","IM abstract interface"],
["platforms/wechat","WeChat Adapter","Gewechat/Wechaty"],
["platforms/qq","QQ Adapter","OneBot v11 WebSocket"],
["platforms/telegram","Telegram Adapter","Bot API"],
["platforms/feishu","Feishu Adapter","Lark open platform"],
["world/digital_twin","Digital Twin","System state mirror"],
["world/active_inference","Active Inference","Predictive processing"],
["kernel/sovereign","Sovereign System","12 tools · system building"],
["kernel/genesis","Genesis Engine","6 tools · genetic programming"],
["kernel/cosmic","Cosmic Engine","6 tools · recursive self"],
["kernel/innovation","Innovation Engine","4 tools · quantum/bio"],
["kernel/apotheosis","Apotheosis","3 tools · immuno/morpho"],
["kernel/omega","Omega Layer","3 tools · p2p/physical"],
["kernel/stg","STG Rhythm","5 CPG neural patterns"],
["field/stigmergy","Stigmergy Field","Environmental signals"],
["gateways/custom_provider","Custom Provider","5 LLM provider chain"],
["gateways/market_hub","Market Hub","Skills + MCP unified market"],
["orchestrator/lifecycle","Lifecycle Manager","Organ lifecycle"],
["scheduler/engine","Scheduler Engine","Cron/interval/date jobs"],
["daemon/service","Daemon Service","Windows service + tray"],
["kernel/code_generation","Code Generation","9-step pipeline"],
["kernel/collaborative","Collaborative Reasoner","Multi-model consensus"],
["kernel/prompt_cache","Prompt Cache","Multi-provider caching"],
["kernel/super_prompt","Super Prompt Factory","Dynamic prompt assembly"],
["kernel/tool_router","Tool Router","Progressive disclosure"],
["kernel/context_compressor","Context Compressor","5-layer compression"],
["kernel/codebase_indexer","Codebase Indexer","Full-text code search"],
["kernel/frontend_bridge","Frontend Bridge","Backend→UI mapping"],
["kernel/self_awareness","Self Awareness","Reflection + introspection"],
["kernel/consciousness","Consciousness Monitor","Awareness metrics"],
["kernel/debate_engine","Debate Engine","Multi-perspective analysis"],
["kernel/immune_gateway","Immune Gateway","3-layer artificial immune"],
["kernel/sandstorm","Sandstorm","L1/L2/L3 isolation sandbox"],
["kernel/hooks","Hook System","PreToolUse/PostToolUse"],
];

var MIROFISH_ORGANS=[
["arenas/coding","Coding Arena","Code quality evaluation"],
["arenas/coordination","Coordination Arena","Multi-tool chain scoring"],
["arenas/safety","Safety Arena","Risk assessment"],
["arenas/decision","Decision Arena","Choice quality"],
["arenas/emergence","Emergence Arena","Novel pattern detection"],
["arenas/performance","Performance Arena","Latency/resource scoring"],
["services/full_body_genome","Full-Body Genome","8D 3-system unified"],
["services/evolution_manager","Evolution Manager","Multi-gen scheduler"],
["services/fitness_extractor","Fitness Extractor","FCPI→DGM signals"],
["services/dgm_bridge","DGM Bridge","Darwinian-Godel machine"],
["services/live_simulator","Live Simulator","Real-time agent sim"],
["services/mycelium_bridge","Mycelium Bridge","fungal-cortex link"],
["services/oasis_bridge","Oasis Bridge","Oasis integration"],
["services/graph_builder","Graph Builder","Knowledge graph"],
["services/ontology_generator","Ontology Generator","Domain ontology"],
["services/report_agent","Report Agent","Auto analysis reports"],
["services/simulation_manager","Simulation Manager","Scenario runner"],
["services/text_processor","Text Processor","NLP pipeline"],
];

var FUNGAL_ORGANS=[
["L0/adaptive","Adaptive Layer (18)","Circuit breaker, drift, hypernetwork, immune, meta-learner"],
["L1/liquid","Liquid Perceptor","Real-time multi-modal perception"],
["L2/router","Multi-Model Router","Routing Decision engine"],
["L3/debate","Mycorrhizal Debate","Multi-agent debate network"],
["L4/autonomous","Autonomous Layer (16)","Audit, behavior, causal, counterfactual, policy"],
["L5/swarm","Swarm Self-Organizer","Pheromone field emergence"],
["L6/meta-cognition","Meta-Cognition (15)","DGM, crystallizer, auto-refactor, ability factory"],
["L7/inference","Active Inference Agent","Policy selection via free energy"],
["L8/compiler","Self-Referential Compiler","System genome synthesis"],
["L9/quantum","Hybrid Quantum Agent","Quantum circuit optimization"],
["L10/conscious","Conscious Kernel","High-level awareness"],
["immune","Immune System (5)","Clonal selection, dendritic, memory, negative selection"],
["field","Field Layer","Stigmergy + geometric field"],
["evolution","Evolution Layer","Agent, architecture, parameter, enforcement"],
["cluster","Cluster Layer (8)","Agent factory, consensus, distributed evolution"],
["dendrite","Dendrite Layer","Coincidence detection, temporal integration"],
["morphogen","Morphogen Layer","Turing patterning, guided self-org"],
["panarchy","Panarchy Layer","Adaptive cycle, resilience, phase transition"],
["holograph","Holograph Layer","Anomaly projection, fractal encoding"],
["autocatalytic","Autocatalytic Layer","Constraint closure, skill catalysis"],
["engine","Engine Layer","Thermodynamic, Hamiltonian, dissipative flows"],
["trading","Trading Layer","Data pipeline, risk gate, portfolio"],
["orchestration","Orchestration","Root agent, cluster manager, cognitive scheduler"],
["bridge","Bridge Layer","L0-L7 pipeline, conscious, skill adapter"],
["security","Security","JWT auth, rate limiter"],
["monitoring","Monitoring","Alerts, Prometheus exporter"],
["quantum","Quantum","Dual mode engine, self-referential switch"],
["skills","Skills Registry","6007 AI skills from global ecosystem"],
];

var MCP_CATEGORIES=["advanced","apotheosis","benchmark","cache","code_analysis","codebase","cosmic","desktop","evolution","files","genesis","git","im","info","innovation","mcp_market","memory","models","omega","os","sandbox","scheduler","shell","skills","skills_market","sovereign","system","web"];
var AGENTS=["sclerotium","jarvis","hackerman","strategist","samantha","code-reviewer","data-scientist","game-designer","security-auditor"];
var PROVIDERS=["DeepSeek","OpenAI","Groq","OpenRouter","Ollama"];
var MEMORY=[["Working","Immediate","#22d3ee"],["Episodic","Events","#a3e635"],["Semantic","Knowledge","#a78bfa"],["Procedural","Skills","#fbbf24"],["Strategic","Insights","#34d399"]];
var FEATURES=["Native Function Calling","SSE Streaming (AG-UI)","5 Provider Fallback Chain","7 Arbiter Modes + CUGA","5-Layer Hexis Memory","8D Full-Body Genome","9 Agent Personalities","External MCP Bridge","Plugin Manifest Auto-Discovery","Session Fork/Branch/Merge","Idempotency Dedup","Voice Interface (STT/TTS)","Docker + docker-compose","Token Economy Tracking","Code-as-Action Sandbox","Model Router 6-Tier","Skill Loader (6007 skills)"];
var ARBITER_MODES=["PLAN","DEFAULT","ACCEPT_EDITS","AUTO","DONT_ASK","BYPASS","BUBBLE"];

function renderAll(){
var g=document.getElementById('main-grid'),h='';

// Panel builder
function P(title,icon,span,body){return '<div class="panel'+(span?' span'+span:'')+'"><div class="panel-h"><span>'+icon+'</span><span>'+t(title)+'</span></div>'+body+'</div>'}

// 1. Organ Ecosystem (sclerotium kernel modules)
var ob='<div class="organ-grid">';
SCLEROTIUM_ORGANS.forEach(function(o){
ob+='<div class="tag"><span class="n">'+o[0]+'</span><br><span class="s">'+o[1]+'</span></div>';
});ob+='</div>';
h+=P('kernel','🧠','span3',ob);

// 2. MCP Tool Categories
var tb='<div class="organ-grid">';
MCP_CATEGORIES.forEach(function(c){
tb+='<div class="tag"><span class="n">'+c+'</span></div>';
});tb+='</div>';
h+=P('tools','🔧','',tb);

// 3. Genome + Evolution
var gb='<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:11px">';
gb+='<div><b>'+t('evolution')+'</b><div style="margin-top:4px">';
["Gen 5 · Fitness 0.828","28 genes · 15 mutations","8 Dimensions","用进废退 (Use/Disuse)","Best: jarvis (0.86)","Provider: deepseek (0.92)"].forEach(function(l){gb+='<div class="row"><span class="k">'+l+'</span></div>'});
gb+='</div></div><div><b>'+t('mirofish')+'</b><div style="margin-top:4px">';
MIROFISH_ORGANS.forEach(function(o){gb+='<div class="tag"><span class="n">'+o[0]+'</span></div>'});
gb+='</div></div></div>';
h+=P('genome','🧬','span2',gb);

// 4. Arbiter
var ab='<div style="font-size:11px">';
ARBITER_MODES.forEach(function(m){
ab+='<div class="row"><span class="k">'+m+'</span><span class="v" style="color:var(--cyan)">active</span></div>';
});
ab+='<div style="margin-top:6px;color:var(--muted);font-size:10px">CUGA 5-Checkpoint · Merkle Audit · Runtime Switch</div></div>';
h+=P('arbiter','⚖️','',ab);

// 5. Agents
var ag='<div style="display:flex;flex-wrap:wrap;gap:6px">';
AGENTS.forEach(function(a){ag+='<span class="tag"><span class="n">'+a+'</span></span>'});
ag+='</div>';
h+=P('agents','👥','',ag);

// 6. Providers
var pv='<div style="display:flex;gap:8px;flex-wrap:wrap;font-size:11px">';
PROVIDERS.forEach(function(p,i){pv+='<span class="tag" style="'+(i==0?'border-color:var(--cyan);color:var(--cyan)':'')+'">'+p+(i<4?' → ':'')+'</span>'});
pv+='<div style="margin-top:6px;font-size:10px;color:var(--muted)">Exponential Backoff · Auto Failover</div></div>';
h+=P('providers','🌐','',pv);

// 7. Memory
var mb='<div style="display:flex;gap:8px">';
MEMORY.forEach(function(m){mb+='<div class="mem-layer"><div class="c">?</div><div class="l">'+m[0]+'</div><div style="font-size:9px;color:'+m[2]+'">'+m[1]+'</div></div>'});
mb+='</div>';
h+=P('memory','💾','span2',mb);

// 8. Features
var fb='<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:11px">';
FEATURES.forEach(function(f){fb+='<div class="tag">'+f+'</div>'});
fb+='</div>';
h+=P('features','⚡','span2',fb);

// 9. Fungal Cortex
var fg='<div class="organ-grid">';
FUNGAL_ORGANS.forEach(function(o){fg+='<div class="tag"><span class="n">'+o[0]+'</span><br><span class="s">'+o[1]+'</span></div>'});
fg+='</div>';
h+=P('fungal','🍄','span3',fg);

// 10. MiroFish
var mf='<div class="organ-grid">';
MIROFISH_ORGANS.forEach(function(o){mf+='<div class="tag"><span class="n">'+o[0]+'</span><br><span class="s">'+o[1]+'</span></div>'});
mf+='</div>';
h+=P('mirofish','🐟','span2',mf);

// 11. External MCP
var ex='<div style="font-size:11px"><div class="row"><span class="k">ext_gsap_animate</span><span class="v">GSAP Animation</span></div><div class="row"><span class="k">ext_impeccable_audit</span><span class="v">UI Audit</span></div><div class="row"><span class="k">ext_taste_design</span><span class="v">Taste Design</span></div><div style="margin-top:6px;font-size:10px;color:var(--cyan)">connect_stdio() · connect_http()</div></div>';
h+=P('mcp','🔌','',ex);

g.innerHTML=h;

// Ticker
var ticker=document.getElementById('ticker'),tk='';
var allMods=[].concat(SCLEROTIUM_ORGANS.map(function(o){return o[0]}),MIROFISH_ORGANS.map(function(o){return o[0]}),FUNGAL_ORGANS.map(function(o){return o[0]}));
for(var i=0;i<2;i++)allMods.forEach(function(m){tk+='<span>▸</span> '+m+' · '});
ticker.innerHTML=tk;

// Update stats
document.getElementById('st-tools').textContent='191';
document.getElementById('st-organs').textContent='28';
document.getElementById('st-systems').textContent='3';
}

renderAll();

// Live data fetch
async function fetchLive(){
try{
var r=await fetch('/data/health');
if(r.ok){var d=await r.json();document.getElementById('st-health').textContent=d.status||'OK';document.getElementById('st-health').className='v status-ok';document.getElementById('st-tools').textContent=d.tool_count||191}
}catch(e){document.getElementById('st-health').className='v status-warn'}
}
fetchLive();setInterval(fetchLive,20000);
</script></body></html>"""
