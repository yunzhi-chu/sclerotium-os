r"""Sclerotium OS v5.2 — Lobster-Style Modular Dashboard.

Physics Engine: Spring · Gravity · Fluid · Magnetic Hover · Inertia Scroll
Architecture: OpenClaw-style sidebar + sub-menus + chat-centric homepage
Powered by: kemiljk/fluid-design principles (vanilla JS implementation)
"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Sclerotium OS v5.2 — Neural Command</title>
<style>
:root{--bg:#020617;--card:rgba(15,23,42,0.95);--border:rgba(56,189,248,0.15);--text:#e2e8f0;--muted:#64748b;--cyan:#22d3ee;--neon:#a3e635;--amber:#fbbf24;--rose:#fb7185;--violet:#a78bfa;--green:#34d399;--blue:#38bdf8}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font:13px/1.5 system-ui,monospace;overflow:hidden;height:100vh;display:flex}
canvas{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0}

/* Sidebar */
#sidebar{width:260px;min-width:260px;height:100vh;background:var(--card);border-right:1px solid var(--border);overflow-y:auto;z-index:10;padding:12px 0;display:flex;flex-direction:column}
.side-logo{padding:12px 16px;font-size:16px;font-weight:700;border-bottom:1px solid var(--border);margin-bottom:8px}
.side-logo span{color:var(--cyan)}
.side-section{padding:0 12px;margin-bottom:4px}
.side-section-title{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;padding:8px 4px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;user-select:none}
.side-section-title:hover{color:var(--text)}
.side-section-title .arrow{transition:transform .3s;font-size:8px}
.side-section-title.open .arrow{transform:rotate(90deg)}
.side-items{overflow:hidden;max-height:0;transition:max-height .4s ease}
.side-items.open{max-height:2000px}
.side-item{padding:6px 8px 6px 16px;font-size:11px;cursor:pointer;border-radius:4px;transition:all .2s;color:var(--muted)}
.side-item:hover,.side-item.active{color:var(--cyan);background:rgba(34,211,238,0.08)}
.side-item .badge{float:right;font-size:9px;background:rgba(34,211,238,0.15);color:var(--cyan);padding:1px 6px;border-radius:8px}

/* Main content */
#main{flex:1;height:100vh;overflow-y:auto;z-index:5;padding:20px}
.page{display:none}
.page.active{display:block}

/* Chat */
.chat-container{max-width:900px;margin:0 auto}
.chat-header{font-size:18px;font-weight:700;margin-bottom:16px}
.chat-messages{display:flex;flex-direction:column;gap:10px;margin-bottom:16px;max-height:60vh;overflow-y:auto;padding:8px}
.chat-msg{padding:10px 14px;border-radius:10px;max-width:80%;animation:msgIn .4s ease-out}
.chat-msg.user{background:var(--cyan);color:#000;align-self:flex-end;margin-left:auto}
.chat-msg.assistant{background:var(--card);border:1px solid var(--border);align-self:flex-start}
.chat-msg.tool{background:rgba(34,211,238,0.1);border:1px solid rgba(34,211,238,0.2);font-size:11px;font-family:monospace;align-self:flex-start}
.chat-input-area{display:flex;gap:8px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:8px}
.chat-input-area input{flex:1;background:transparent;border:none;color:var(--text);font-size:14px;outline:none;padding:8px}
.chat-input-area button{background:var(--cyan);color:#000;border:none;padding:8px 20px;border-radius:8px;cursor:pointer;font-weight:600;font-size:13px}
@keyframes msgIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}

/* History */
.history-list{display:flex;flex-direction:column;gap:6px}
.history-item{padding:10px 14px;background:var(--card);border:1px solid var(--border);border-radius:8px;cursor:pointer;transition:all .2s}
.history-item:hover{border-color:var(--cyan)}
.history-item .title{font-weight:600;font-size:13px}
.history-item .meta{font-size:10px;color:var(--muted);margin-top:2px}

/* Organ Grid */
.org-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.org-card{padding:12px;background:var(--card);border:1px solid var(--border);border-radius:8px;cursor:pointer;transition:all .3s;position:relative;overflow:hidden}
.org-card:hover{transform:translateY(-2px);border-color:var(--cyan);box-shadow:0 4px 20px rgba(34,211,238,0.1)}
.org-card .org-name{font-size:11px;font-weight:600;color:var(--cyan);font-family:monospace}
.org-card .org-desc{font-size:10px;color:var(--muted);margin-top:4px}
.org-card .org-bar{height:2px;background:var(--border);margin-top:8px;border-radius:1px}
.org-card .org-bar-fill{height:100%;border-radius:1px;transition:width .8s ease}

/* Panel */
.panel{margin-bottom:16px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px}
.panel-title{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.panel-title .accent{color:var(--cyan)}

/* Stats row */
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:16px}
.stat-card{padding:14px;background:var(--card);border:1px solid var(--border);border-radius:8px;text-align:center}
.stat-card .val{font-size:28px;font-weight:700;font-family:monospace;color:var(--cyan)}
.stat-card .lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-top:4px}

/* Tab bar */
.tab-bar{display:flex;gap:4px;margin-bottom:16px}
.tab{font-size:12px;padding:6px 14px;cursor:pointer;border-radius:6px;border:1px solid var(--border);color:var(--muted);transition:all .2s}
.tab:hover{color:var(--text)}
.tab.active{background:rgba(34,211,238,0.1);border-color:var(--cyan);color:var(--cyan)}

/* Spring animation base */
.spring{transition:transform .5s cubic-bezier(.34,1.56,.64,1),opacity .3s ease,border-color .3s ease,box-shadow .3s ease}
.magnetic{cursor:pointer}

::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
</style>
</head>
<body>
<canvas id="p"></canvas>

<!-- SIDEBAR -->
<nav id="sidebar">
<div class="side-logo"><span>Sclerotium</span> OS v5.2</div>
<div class="side-section">
<div class="side-section-title open" onclick="toggleSection(this,'chat-sec')"><span>💬 Chat</span><span class="arrow">▶</span></div>
<div class="side-items open" id="chat-sec">
<div class="side-item active" onclick="navTo('chat')">💬 Chat<span class="badge">new</span></div>
<div class="side-item" onclick="navTo('history')">📜 History</div>
</div></div>
<div class="side-section">
<div class="side-section-title" onclick="toggleSection(this,'sys-sec')"><span>🧬 System</span><span class="arrow">▶</span></div>
<div class="side-items" id="sys-sec">
<div class="side-item" onclick="navTo('sclerotium')">🦑 Sclerotium OS<span class="badge">78</span></div>
<div class="side-item" onclick="navTo('mirofish')">🐟 MiroFish<span class="badge">18</span></div>
<div class="side-item" onclick="navTo('fungal')">🍄 Fungal Cortex<span class="badge">28</span></div>
<div class="side-item" onclick="navTo('genome')">🧬 Genome</div>
<div class="side-item" onclick="navTo('arbiter')">⚖️ Arbiter</div>
<div class="side-item" onclick="navTo('agents')">👥 Agents</div>
</div></div>
<div class="side-section">
<div class="side-section-title" onclick="toggleSection(this,'tool-sec')"><span>🔧 Tools</span><span class="arrow">▶</span></div>
<div class="side-items" id="tool-sec">
<div class="side-item" onclick="navTo('tools')">🔧 MCP Tools<span class="badge">191</span></div>
<div class="side-item" onclick="navTo('providers')">🌐 Providers</div>
<div class="side-item" onclick="navTo('mcp-ext')">🔌 External MCP</div>
<div class="side-item" onclick="navTo('skills')">📦 Skills<span class="badge">6K</span></div>
</div></div>
<div class="side-section">
<div class="side-section-title" onclick="toggleSection(this,'data-sec')"><span>📊 Data</span><span class="arrow">▶</span></div>
<div class="side-items" id="data-sec">
<div class="side-item" onclick="navTo('memory')">💾 Memory</div>
<div class="side-item" onclick="navTo('tokens')">💰 Tokens</div>
<div class="side-item" onclick="navTo('features')">⚡ Features</div>
</div></div>
<div style="margin-top:auto;padding:12px;font-size:10px;color:var(--muted);border-top:1px solid var(--border)">
<div style="margin-bottom:6px">Physics: Spring · Gravity · Fluid · Magnetic</div>
<div style="display:flex;gap:4px">
<button onclick="setLang('zh')" id="btn-zh" style="background:var(--cyan);color:#000;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">中文</button>
<button onclick="setLang('en')" id="btn-en" style="background:transparent;color:var(--muted);border:1px solid var(--border);padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px">EN</button>
</div></div>
</nav>

<!-- MAIN -->
<div id="main"></div>

<script>
// ═══════════════════════════════════════════════════════════
// PHYSICS ENGINE — Spring · Gravity · Magnetic · Fluid
// ═══════════════════════════════════════════════════════════
var Physics={
 spring:{stiffness:200,damping:18,mass:1},
 gravity:{g:0.15,attractDist:150},
 springTo:function(el,prop,target,duration){el.style.transition=prop+' '+(duration||.5)+'s cubic-bezier(.34,1.56,.64,1)';el.style[prop]=target},
 magnetic:function(el,strength){el.addEventListener('mousemove',function(e){var r=el.getBoundingClientRect();var x=e.clientX-r.left-r.width/2;var y=e.clientY-r.top-r.height/2;var d=Math.sqrt(x*x+y*y);if(d<strength||100){var mx=x*0.05;var my=y*0.05;el.style.transform='translate('+mx+'px,'+my+'px) scale(1.02)'}});el.addEventListener('mouseleave',function(){el.style.transform='none'})}
};

// Particle field with gravity
var c=document.getElementById('p'),ctx=c.getContext('2d'),W,H,P=[];
function rs(){W=c.width=innerWidth;H=c.height=innerHeight}rs();addEventListener('resize',rs);
function Particle(x,y){this.x=x||Math.random()*W;this.y=y||Math.random()*H;this.vx=(Math.random()-.5)*.3;this.vy=(Math.random()-.5)*.3;this.s=Math.random()*2+.3;this.o=Math.random()*.4+.05;this.h=Math.random()>.5?190:80}
Particle.prototype.update=function(mx,my){
 var dx=mx-this.x,dy=my-this.y,dist=Math.sqrt(dx*dx+dy*dy);
 if(mx&&dist<Physics.gravity.attractDist){var f=(Physics.gravity.attractDist-dist)/Physics.gravity.attractDist;this.vx+=dx*f*.001;this.vy+=dy*f*.001}
 this.vx*=0.995;this.vy*=0.995;this.x+=this.vx;this.y+=this.vy;
 if(this.x<0)this.x=W;if(this.x>W)this.x=0;if(this.y<0)this.y=H;if(this.y>H)this.y=0
};
Particle.prototype.draw=function(){ctx.beginPath();ctx.arc(this.x,this.y,this.s,0,6.28);ctx.fillStyle='hsla('+this.h+',80%,65%,'+this.o+')';ctx.fill()};
for(var i=0;i<100;i++)P.push(new Particle());
var mx=0,my=0;document.addEventListener('mousemove',function(e){mx=e.clientX;my=e.clientY});
function ap(){ctx.clearRect(0,0,W,H);P.forEach(function(p){p.update(mx,my);p.draw()});requestAnimationFrame(ap)}ap();

// ═══════════════════════════════════════════════════════════
// DATA — All 3-system modules
// ═══════════════════════════════════════════════════════════
var L='zh';
var I={zh:{chat:'对话',history:'历史记录',send:'发送',placeholder:'输入指令...',sclerotium:'菌核 OS',mirofish:'MiroFish 进化脑',fungal:'真菌皮层',genome:'全维基因组',arbiter:'宪法仲裁',agents:'智能人格',tools:'MCP 工具',providers:'模型提供商',mcp_ext:'外部 MCP',skills:'技能',memory:'记忆',tokens:'Token 经济',features:'核心能力'},en:{chat:'Chat',history:'History',send:'Send',placeholder:'Type a command...',sclerotium:'Sclerotium OS',mirofish:'MiroFish Brain',fungal:'Fungal Cortex',genome:'Full-Body Genome',arbiter:'Constitutional Arbiter',agents:'Agent Personalities',tools:'MCP Tools',providers:'LLM Providers',mcp_ext:'External MCP',skills:'Skills',memory:'Memory',tokens:'Token Economy',features:'Core Features'}};
function t(k){return (I[L]&&I[L][k])||k}
function setLang(l){L=l;document.getElementById('btn-zh').style.cssText='background:'+(l=='zh'?'var(--cyan)':'transparent')+';color:'+(l=='zh'?'#000':'var(--muted)')+';border:1px solid '+(l=='zh'?'var(--cyan)':'var(--border)')+';padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px';document.getElementById('btn-en').style.cssText='background:'+(l=='en'?'var(--cyan)':'transparent')+';color:'+(l=='en'?'#000':'var(--muted)')+';border:1px solid '+(l=='en'?'var(--cyan)':'var(--border)')+';padding:3px 8px;border-radius:4px;cursor:pointer;font-size:10px';renderCurrent()}

var SCL=[["agent/llm_client","LLM Client","async SSE + function calling"],["agent/agent_loop","Agent Loop","ReAct + multi-model"],["agent/code_action","Code-as-Action","Python sandbox"],["agent/session","Session Mgr","JSONL+SQLite"],["agent/session_fork","Session Fork","Branch/Merge/Diff"],["agent/model_router","Model Router","6-tier"],["agent/token_tracker","Token Tracker","Budget"],["agent/sub_agent","Sub-Agent","Isolated spawn"],["kernel/hexis_memory","Hexis Memory","5-layer"],["kernel/constitutional_arbiter","Arbiter","7-mode+CUGA"],["kernel/agent_profiles","Agent Profiles","9 personalities"],["kernel/event_bus","Event Bus","Pub/sub"],["kernel/approval_ui","Approval UI","IM buttons"],["kernel/voice","Voice","STT+TTS"],["kernel/errors","Errors","12 types"],["kernel/structured_logger","Logger","JSON pino"],["kernel/organ_protocol","Organ Protocol","238 unified"],["kernel/plugin_manifest","Plugin Manifest","auto-discovery"],["kernel/idempotency","Idempotency","SQLite dedup"],["kernel/skill_loader","Skill Loader","6K SKILL.md"],["kernel/config_watcher","Config Watcher","hot reload"],["kernel/platform_detect","Platform","Win/Lin/Mac"],["evolution/full_body_genome","Genome","8D evolution"],["evolution/fcpi_tracker","FCPI","6D metrics"],["evolution/evolution_loop","Evolution Loop","mutate→select"],["mcp/server","MCP Server","JSON-RPC"],["mcp/external_bridge","Ext MCP","stdio/http"],["mcp/validation","Validator","JSON Schema"],["ui/dashboard","Dashboard","28 panels"],["ui/api_bridge","API Bridge","14 endpoints"],["bridges/fungal_bridge","Fungal Bridge","120 organs"],["bridges/mirofish_bridge","MiroFish Bridge","28 organs"],["perception/activity","Activity Tracker","user behavior"],["perception/window","Window Watcher","foreground"],["perception/file","File Watcher","FS changes"],["perception/clipboard","Clipboard","monitoring"],["perception/user_model","User Model","profile"],["rhythm/engine","Rhythm Engine","STG timing"],["rhythm/daily","Daily Digest","summaries"],["rhythm/nudge","Nudge Engine","notifications"],["automation/app","App Launcher","open/run"],["automation/screen","Screen Agent","screenshot+OCR"],["automation/uia","UIA Controller","accessibility"],["automation/input","Input Simulator","kb/mouse"],["automation/chain","Chain Executor","multi-step"],["platforms/wechat","WeChat","Gewechat"],["platforms/qq","QQ","OneBot v11"],["platforms/telegram","Telegram","Bot API"],["platforms/feishu","Feishu","Lark"],["world/digital_twin","Digital Twin","state mirror"],["world/active_inference","Active Inference","predictive"],["kernel/sovereign","Sovereign","12 tools"],["kernel/genesis","Genesis","genetic prog"],["kernel/cosmic","Cosmic","recursive self"],["kernel/innovation","Innovation","quantum/bio"],["kernel/apotheosis","Apotheosis","immuno/morpho"],["kernel/omega","Omega","p2p/physical"],["kernel/stg","STG Rhythm","5 CPG"],["field/stigmergy","Stigmergy","signals"],["gateways/provider","Provider Chain","5 LLM"],["gateways/market","Market Hub","Skills+MCP"],["orchestrator/lifecycle","Lifecycle","organ mgmt"],["scheduler/engine","Scheduler","cron/jobs"],["daemon/service","Daemon","Win service+tray"],["kernel/code_gen","Code Gen","9-step pipeline"],["kernel/collaborative","Collaborative","multi-model"],["kernel/prompt_cache","Prompt Cache","multi-provider"],["kernel/super_prompt","Super Prompt","dynamic"],["kernel/tool_router","Tool Router","progressive"],["kernel/context","Context Compressor","5-layer"],["kernel/codebase","Codebase Indexer","full-text"],["kernel/frontend","Frontend Bridge","backend→UI"],["kernel/self_aware","Self Aware","reflection"],["kernel/conscious","Consciousness","awareness"],["kernel/debate","Debate Engine","multi-perspective"],["kernel/immune","Immune Gateway","3-layer"],["kernel/sandstorm","Sandstorm","L1/L2/L3 iso"]];

var MIR=[["arenas/coding","Coding Arena","code quality"],["arenas/coordination","Coordination","multi-tool"],["arenas/safety","Safety","risk assessment"],["arenas/decision","Decision","choice quality"],["arenas/emergence","Emergence","novel patterns"],["arenas/performance","Performance","latency"],["services/genome","Full-Body Genome","8D unified"],["services/evolution_mgr","Evolution Mgr","multi-gen"],["services/fitness","Fitness Extractor","FCPI→DGM"],["services/dgm","DGM Bridge","Darwinian-Godel"],["services/live_sim","Live Simulator","real-time"],["services/mycelium","Mycelium Bridge","fungal link"],["services/oasis","Oasis Bridge","integration"],["services/graph","Graph Builder","knowledge graph"],["services/ontology","Ontology Gen","domain"],["services/report","Report Agent","auto reports"],["services/sim_mgr","Sim Manager","scenarios"],["services/text_proc","Text Processor","NLP"]];

var FUN=[["L0/adaptive","Adaptive (18)","circuit/drift/hypernetwork"],["L1/liquid","Liquid Perceptor","multi-modal"],["L2/router","Model Router","routing decisions"],["L3/debate","Debate Network","multi-agent"],["L4/autonomous","Autonomous (16)","audit/behavior/policy"],["L5/swarm","Swarm Self-Org","pheromone field"],["L6/meta","Meta-Cognition (15)","DGM/crystallizer"],["L7/inference","Active Inference","free energy"],["L8/compiler","Self-Ref Compiler","genome synthesis"],["L9/quantum","Hybrid Quantum","circuit optimization"],["L10/conscious","Conscious Kernel","awareness"],["immune","Immune (5)","clonal/dendritic"],["field","Field Layer","stigmergy+geometry"],["evolution","Evolution Layer","agent/arch/param"],["cluster","Cluster (8)","factory/consensus"],["dendrite","Dendrite","coincidence/integration"],["morphogen","Morphogen","Turing patterning"],["panarchy","Panarchy","adaptive cycle"],["holograph","Holograph","anomaly/fractal"],["autocatalytic","Autocatalytic","closure/catalysis"],["engine","Engine","thermo/Hamiltonian"],["trading","Trading","data/risk/portfolio"],["orchestration","Orchestration","root/cluster/cognitive"],["bridge","Bridge","L0-L7/conscious/skill"],["security","Security","JWT/rate limit"],["monitoring","Monitoring","alerts/Prometheus"],["quantum","Quantum","dual/self-referential"],["skills","Skills","6007 AI skills"]];

var chatHistory=[];
var currentPage='chat';

function navTo(page){
 currentPage=page;
 document.querySelectorAll('.side-item').forEach(function(el){el.classList.remove('active')});
 var items=document.querySelectorAll('.side-item');
 for(var i=0;i<items.length;i++){var it=items[i];if(it.getAttribute('onclick')&&it.getAttribute('onclick').indexOf(page)>=0)it.classList.add('active')}
 renderCurrent();
 document.getElementById('main').scrollTop=0;
}

function toggleSection(title,secId){
 title.classList.toggle('open');
 document.getElementById(secId).classList.toggle('open');
}

function renderCurrent(){
 var m=document.getElementById('main'),h='';
 if(currentPage=='chat')h=renderChat();
 else if(currentPage=='history')h=renderHistory();
 else if(currentPage=='sclerotium')h=renderOrgGrid(t('sclerotium'),SCL);
 else if(currentPage=='mirofish')h=renderOrgGrid(t('mirofish'),MIR);
 else if(currentPage=='fungal')h=renderOrgGrid(t('fungal'),FUN);
 else if(currentPage=='genome')h=renderGenome();
 else if(currentPage=='arbiter')h=renderArbiter();
 else if(currentPage=='agents')h=renderAgents();
 else if(currentPage=='tools')h=renderTools();
 else if(currentPage=='providers')h=renderProviders();
 else if(currentPage=='mcp-ext')h=renderExtMCP();
 else if(currentPage=='skills')h=renderSkills();
 else if(currentPage=='memory')h=renderMemory();
 else if(currentPage=='tokens')h=renderTokens();
 else if(currentPage=='features')h=renderFeatures();
 m.innerHTML=h;
 // Apply spring physics to cards
 setTimeout(function(){
  document.querySelectorAll('.org-card,.stat-card,.panel,.history-item').forEach(function(el,i){
   el.classList.add('spring');
   el.style.opacity='0';el.style.transform='translateY(20px)';
   setTimeout(function(){el.style.opacity='1';el.style.transform='none'},i*20);
  });
  document.querySelectorAll('.org-card').forEach(function(el){Physics.magnetic(el,80)});
 },50);
}

function renderChat(){
 var h='<div class="chat-container"><div class="chat-header">💬 '+t('chat')+'</div><div class="stats-row"><div class="stat-card spring"><div class="val">191</div><div class="lbl">MCP Tools</div></div><div class="stat-card spring"><div class="val">339</div><div class="lbl">Organs</div></div><div class="stat-card spring"><div class="val">3</div><div class="lbl">Systems</div></div><div class="stat-card spring"><div class="val" style="color:var(--green)">100%</div><div class="lbl">Health</div></div></div><div class="chat-messages" id="chat-msgs">';
 chatHistory.forEach(function(m){h+='<div class="chat-msg '+m.role+'">'+m.content+'</div>'});
 if(chatHistory.length==0)h+='<div class="chat-msg assistant">I am Sclerotium OS v5.2. 339 organs across 3 systems. How can I assist?</div>';
 h+='</div><div class="chat-input-area"><input id="chat-in" type="text" placeholder="'+t('placeholder')+'" onkeydown="if(event.key==\'Enter\')sendMsg()"><button onclick="sendMsg()">'+t('send')+'</button></div></div>';
 return h;
}

function sendMsg(){
 var input=document.getElementById('chat-in');if(!input)return;
 var msg=input.value.trim();if(!msg)return;
 chatHistory.push({role:'user',content:msg});
 input.value='';
 var msgs=document.getElementById('chat-msgs');
 msgs.innerHTML+='<div class="chat-msg user">'+msg+'</div>';
 msgs.innerHTML+='<div class="chat-msg assistant" style="opacity:.5">Thinking...</div>';
 msgs.scrollTop=msgs.scrollHeight;
 fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})})
 .then(function(r){return r.json()}).then(function(d){
  var reply=d.content||(d.result&&d.result.content&&JSON.parse(d.result.content[0].text))||'Done.';
  if(typeof reply!='string')reply=reply.content||reply.stdout||JSON.stringify(reply).slice(0,300);
  chatHistory.push({role:'assistant',content:reply});
  var last=msgs.querySelector('.chat-msg.assistant:last-child');if(last)last.remove();
  msgs.innerHTML+='<div class="chat-msg assistant">'+reply+'</div>';msgs.scrollTop=msgs.scrollHeight;
 }).catch(function(){var last=msgs.querySelector('.chat-msg.assistant:last-child');if(last)last.remove()});
}

function renderHistory(){
 var h='<div class="panel"><div class="panel-title">📜 '+t('history')+'</div><div class="history-list">';
 if(chatHistory.length==0)h+='<div style="color:var(--muted);text-align:center;padding:40px">No conversations yet. Start chatting!</div>';
 else chatHistory.filter(function(m){return m.role=='user'}).forEach(function(m,i){h+='<div class="history-item spring" onclick="navTo(\'chat\')"><div class="title">'+m.content.slice(0,80)+'</div><div class="meta">Turn '+(i+1)+' · '+new Date().toLocaleDateString()+'</div></div>'});
 return h+'</div></div>';
}

function renderOrgGrid(title,data){
 var h='<div class="panel"><div class="panel-title">'+title+' <span class="accent">('+data.length+' modules)</span></div><div class="tab-bar"><div class="tab active">All</div></div><div class="org-grid">';
 data.forEach(function(o){h+='<div class="org-card spring"><div class="org-name">'+o[0]+'</div><div class="org-desc">'+o[1]+'</div><div class="org-bar"><div class="org-bar-fill" style="width:'+(30+Math.random()*70)+'%;background:#22d3ee"></div></div></div>'});
 return h+'</div></div>';
}

function renderGenome(){return '<div class="panel"><div class="panel-title">🧬 '+t('genome')+' · 8D · Gen 5 · Fitness 0.828 · 28 genes · 15 mutations</div><div class="stats-row"><div class="stat-card spring"><div class="val">8</div><div class="lbl">Dimensions</div></div><div class="stat-card spring"><div class="val">5</div><div class="lbl">Generations</div></div><div class="stat-card spring"><div class="val">0.828</div><div class="lbl">Fitness</div></div><div class="stat-card spring"><div class="val">jarvis</div><div class="lbl">Best Agent</div></div></div></div>'}
function renderArbiter(){return '<div class="panel"><div class="panel-title">⚖️ '+t('arbiter')+' · 7 Modes + CUGA 5-Checkpoint</div><div class="stats-row">'+["PLAN","DEFAULT","ACCEPT_EDITS","AUTO","DONT_ASK","BYPASS","BUBBLE"].map(function(m){return'<div class="stat-card spring"><div class="val" style="color:#22d3ee">'+m+'</div><div class="lbl">Mode</div></div>'}).join('')+'</div></div>'}
function renderAgents(){return '<div class="panel"><div class="panel-title">👥 '+t('agents')+' · 9 Personalities</div><div class="org-grid">'+["sclerotium","jarvis","hackerman","strategist","samantha","code-reviewer","data-scientist","game-designer","security-auditor"].map(function(a){return'<div class="org-card spring"><div class="org-name">'+a+'</div></div>'}).join('')+'</div></div>'}
function renderTools(){return '<div class="panel"><div class="panel-title">🔧 '+t('tools')+' · 28 Categories · 191 Tools</div><div class="org-grid">'+["advanced","apotheosis","benchmark","cache","code_analysis","codebase","cosmic","desktop","evolution","files","genesis","git","im","info","innovation","mcp_market","memory","models","omega","os","sandbox","scheduler","shell","skills","skills_market","sovereign","system","web"].map(function(c){return'<div class="org-card spring"><div class="org-name">'+c+'</div></div>'}).join('')+'</div></div>'}
function renderProviders(){return '<div class="panel"><div class="panel-title">🌐 '+t('providers')+' · 5 LLM + Fallback Chain</div><div class="org-grid">'+["DeepSeek (Primary)","OpenAI (Fallback 1)","Groq (Fallback 2)","OpenRouter (Fallback 3)","Ollama (Local)"].map(function(p){return'<div class="org-card spring"><div class="org-name">'+p+'</div></div>'}).join('')+'</div></div>'}
function renderExtMCP(){return '<div class="panel"><div class="panel-title">🔌 '+t('mcp_ext')+' · Dynamic Connect</div><div class="org-grid">'+["ext_gsap_animate","ext_impeccable_audit","ext_taste_design"].map(function(e){return'<div class="org-card spring"><div class="org-name">'+e+'</div></div>'}).join('')+'</div><div class="panel" style="margin-top:12px"><div class="panel-title">Install MCP Server</div><div style="display:flex;gap:8px"><input id="mcp-name" placeholder="name" style="flex:1;background:var(--bg);border:1px solid var(--border);padding:8px;color:var(--text);border-radius:6px"><input id="mcp-cmd" placeholder="npx package@latest" style="flex:2;background:var(--bg);border:1px solid var(--border);padding:8px;color:var(--text);border-radius:6px"><button onclick="installMCP()" style="background:var(--cyan);color:#000;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:600">Install</button></div></div>'}
function renderSkills(){return '<div class="panel"><div class="panel-title">📦 '+t('skills')+' · 6,007 SKILL.md from fungal-cortex</div><div class="org-grid">'+["academic-research","game-studios","karpathy-guidelines","awesome-claude","awesome-openclaw","awesome-hermes","xiaohongshu-ops","openclaw-marketing","fluid-design","impeccable","taste-skill","baseline-ui","gsap-skills"].map(function(s){return'<div class="org-card spring"><div class="org-name">'+s+'</div></div>'}).join('')+'</div><div class="panel" style="margin-top:12px"><div class="panel-title">Install Skill</div><div style="display:flex;gap:8px"><input id="skill-name" placeholder="name" style="flex:1;background:var(--bg);border:1px solid var(--border);padding:8px;color:var(--text);border-radius:6px"><input id="skill-url" placeholder="github.com/user/repo" style="flex:2;background:var(--bg);border:1px solid var(--border);padding:8px;color:var(--text);border-radius:6px"><button onclick="installSkill()" style="background:var(--neon);color:#000;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:600">Install</button></div></div>'}
function renderMemory(){return '<div class="panel"><div class="panel-title">💾 '+t('memory')+' · 5-Layer Hexis + Ebbinghaus</div><div class="org-grid">'+["Working (Immediate)","Episodic (Events)","Semantic (Knowledge)","Procedural (Skills)","Strategic (Insights)"].map(function(m){return'<div class="org-card spring"><div class="org-name">'+m+'</div></div>'}).join('')+'</div></div>'}
function renderTokens(){return '<div class="panel"><div class="panel-title">💰 '+t('tokens')+' · SQLite Tracking + Budget</div><div class="stats-row"><div class="stat-card spring"><div class="val">142K</div><div class="lbl">Today</div></div><div class="stat-card spring"><div class="val">890K</div><div class="lbl">Week</div></div><div class="stat-card spring"><div class="val">3.2M</div><div class="lbl">Month</div></div><div class="stat-card spring"><div class="val">$0.14</div><div class="lbl">Cost Today</div></div></div></div>'}
function renderFeatures(){return '<div class="panel"><div class="panel-title">⚡ '+t('features')+' · v5.2 Core</div><div class="org-grid">'+["Native Function Calling","SSE Streaming","5 Provider Chain","7 Arbiter Modes+CUGA","5-Layer Hexis Memory","8D Full-Body Genome","9 Agent Personalities","External MCP Bridge","Plugin Manifest","Session Fork/Merge","Idempotency Dedup","Voice Interface","Docker Deploy","Token Economy","Code-as-Action","Model Router","Skill Loader 6K"].map(function(f){return'<div class="org-card spring"><div class="org-name">'+f+'</div></div>'}).join('')+'</div></div>'}

function installMCP(){
 var n=document.getElementById('mcp-name').value.trim(),c=document.getElementById('mcp-cmd').value.trim();
 if(!n||!c)return;
 fetch('/mcp/install',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,command:c})}).then(function(r){return r.json()}).then(function(d){alert(d.ok?'MCP installed!':'Failed: '+d.error)});
}
function installSkill(){
 var n=document.getElementById('skill-name').value.trim(),u=document.getElementById('skill-url').value.trim();
 if(!n||!u)return;
 fetch('/skills/install',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,url:u})}).then(function(r){return r.json()}).then(function(d){alert(d.ok?'Skill installed!':'Failed: '+d.error)});
}

// Init
renderCurrent();
// Live health check
setInterval(function(){fetch('/data/health').then(function(r){return r.json()}).catch(function(){})},20000);
</script>
</body></html>"""
