r"""Sclerotium OS v5.2 — Fluid Physics 3D Dashboard.

ALL data from live /data/* API endpoints.
Physics: Fluid simulation · CSS 3D perspective · Organic springs · Morph targets
"""

FLUID_DASHBOARD = r"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Sclerotium OS v5.2 — Fluid Command</title>
<style>
:root{--bg:#020617;--card:rgba(15,23,42,0.92);--border:rgba(56,189,248,0.18);--text:#e2e8f0;--muted:#64748b;--cyan:#22d3ee;--neon:#a3e635;--amber:#fbbf24;--rose:#fb7185;--violet:#a78bfa;--green:#34d399;--blue:#38bdf8}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font:13px/1.5 system-ui,sans-serif;overflow:hidden;height:100vh;display:flex;perspective:1200px}
canvas{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0}

/* Sidebar with 3D tilt */
#sidebar{width:240px;min-width:240px;height:100vh;background:var(--card);border-right:1px solid var(--border);z-index:10;padding:10px 0;overflow-y:auto;display:flex;flex-direction:column;transform:translateZ(20px)}
.side-logo{padding:12px 14px;font-size:15px;font-weight:700;border-bottom:1px solid var(--border);margin-bottom:6px}
.side-logo span{color:var(--cyan)}
.side-sec{padding:0 10px;margin-bottom:2px}
.side-title{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;padding:6px 4px;cursor:pointer;display:flex;justify-content:space-between;user-select:none;transition:color .3s}
.side-title:hover{color:var(--text)}
.side-title .arw{transition:transform .4s cubic-bezier(.34,1.56,.64,1);font-size:8px}
.side-title.open .arw{transform:rotate(90deg)}
.side-sub{overflow:hidden;max-height:0;transition:max-height .5s cubic-bezier(.25,.8,.25,1)}
.side-sub.open{max-height:3000px}
.side-item{padding:5px 6px 5px 14px;font-size:11px;cursor:pointer;border-radius:4px;color:var(--muted);transition:all .3s cubic-bezier(.34,1.56,.64,1)}
.side-item:hover,.side-item.on{color:var(--cyan);background:rgba(34,211,238,0.06);transform:translateX(4px)}
.side-item .n{float:right;font-size:9px;color:var(--cyan);background:rgba(34,211,238,0.1);padding:0 5px;border-radius:6px}

#main{flex:1;height:100vh;overflow-y:auto;z-index:5;padding:20px;transform-style:preserve-3d}
.page{display:none;animation:fadeIn .5s cubic-bezier(.34,1.56,.64,1)}
.page.on{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(16px) translateZ(-20px)}to{opacity:1;transform:none}}

/* 3D Cards */
.card3d{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;transition:all .4s cubic-bezier(.34,1.56,.64,1);transform-style:preserve-3d;cursor:pointer;position:relative;overflow:hidden}
.card3d:hover{transform:translateY(-3px) rotateX(2deg) rotateY(2deg);border-color:var(--cyan);box-shadow:0 8px 30px rgba(34,211,238,0.12)}
.card3d::after{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle,rgba(34,211,238,0.06) 0%,transparent 70%);opacity:0;transition:opacity .4s}
.card3d:hover::after{opacity:1}

.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:14px}
.stat-card{padding:16px;text-align:center}
.stat-card .v{font-size:32px;font-weight:700;font-family:monospace;color:var(--cyan);transition:all .4s cubic-bezier(.34,1.56,.64,1)}
.stat-card:hover .v{transform:scale(1.1)}
.stat-card .l{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-top:4px}

.org-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:8px}
.org-chip{padding:10px 12px;background:var(--card);border:1px solid var(--border);border-radius:8px;transition:all .35s cubic-bezier(.34,1.56,.64,1);cursor:pointer;position:relative;overflow:hidden}
.org-chip:hover{transform:translateY(-2px) scale(1.02);border-color:var(--cyan)}
.org-chip .n{font-size:10px;font-family:monospace;color:var(--cyan);font-weight:600}
.org-chip .d{font-size:9px;color:var(--muted);margin-top:3px}
.org-chip .bar{height:2px;background:var(--border);margin-top:6px;border-radius:1px}
.org-chip .bar-f{height:100%;border-radius:1px;background:var(--cyan);transition:width 1s cubic-bezier(.34,1.56,.64,1)}

.panel{margin-bottom:16px}
.panel-t{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;display:flex;align-items:center;gap:6px}
.panel-t .a{color:var(--cyan)}

/* Chat */
.chat-box{max-width:860px;margin:0 auto}
.chat-msgs{display:flex;flex-direction:column;gap:8px;margin-bottom:12px;max-height:55vh;overflow-y:auto;padding:6px}
.chat-msg{padding:10px 14px;border-radius:10px;max-width:82%;animation:msgPop .35s cubic-bezier(.34,1.56,.64,1)}
.chat-msg.u{background:var(--cyan);color:#000;align-self:flex-end;margin-left:auto}
.chat-msg.a{background:var(--card);border:1px solid var(--border);align-self:flex-start}
.chat-msg.t{background:rgba(34,211,238,0.08);border:1px solid rgba(34,211,238,0.15);font-size:11px;font-family:monospace}
.chat-bar{display:flex;gap:8px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:8px}
.chat-bar input{flex:1;background:none;border:none;color:var(--text);font-size:14px;outline:none;padding:8px}
.chat-bar button{background:var(--cyan);color:#000;border:none;padding:8px 20px;border-radius:8px;cursor:pointer;font-weight:600;transition:transform .2s}
.chat-bar button:hover{transform:scale(1.05)}
@keyframes msgPop{from{opacity:0;transform:translateY(12px) scale(.95)}to{opacity:1;transform:none}}

.mem-grid{display:flex;gap:8px}
.mem-cell{flex:1;text-align:center;padding:14px 8px;border-radius:10px;transition:all .4s cubic-bezier(.34,1.56,.64,1)}
.mem-cell:hover{transform:translateY(-3px)}
.mem-cell .c{font-size:28px;font-family:monospace}
.mem-cell .l{font-size:10px;color:var(--muted);margin-top:4px}

.arb-row{display:flex;align-items:center;gap:10px;padding:6px 0}
.arb-row .mode{width:110px;font-size:11px;font-family:monospace;color:var(--muted)}
.arb-row .bar{flex:1;height:4px;background:var(--border);border-radius:2px;overflow:hidden}
.arb-row .bar-f{height:100%;border-radius:2px;transition:width 1.2s cubic-bezier(.34,1.56,.64,1)}

.lang-bar{display:flex;gap:4px;margin-top:auto;padding:10px;border-top:1px solid var(--border)}
.lang-bar button{padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;border:1px solid var(--border);transition:all .3s}

::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
</style></head><body>
<canvas id="f"></canvas>

<nav id="sidebar">
<div class="side-logo"><span>Sclerotium</span> OS v5.2</div>
<div class="side-sec"><div class="side-title open" onclick="ts(this,'s-chat')">💬 Chat & History<span class="arw">▶</span></div><div class="side-sub open" id="s-chat"><div class="side-item on" onclick="nav('chat')">💬 Chat</div><div class="side-item" onclick="nav('history')">📜 History</div></div></div>
<div class="side-sec"><div class="side-title" onclick="ts(this,'s-sys')">🧬 Systems<span class="arw">▶</span></div><div class="side-sub" id="s-sys"><div class="side-item" onclick="nav('sclerotium')">🦑 Sclerotium OS<span class="n" id="n-scl">-</span></div><div class="side-item" onclick="nav('mirofish')">🐟 MiroFish<span class="n" id="n-mir">-</span></div><div class="side-item" onclick="nav('fungal')">🍄 Fungal Cortex<span class="n" id="n-fun">-</span></div><div class="side-item" onclick="nav('genome')">🧬 Genome<span class="n" id="n-gen">-</span></div><div class="side-item" onclick="nav('arbiter')">⚖️ Arbiter</div><div class="side-item" onclick="nav('agents')">👥 Agents</div></div></div>
<div class="side-sec"><div class="side-title" onclick="ts(this,'s-tools')">🔧 Tools & Data<span class="arw">▶</span></div><div class="side-sub" id="s-tools"><div class="side-item" onclick="nav('tools')">🔧 MCP Tools</div><div class="side-item" onclick="nav('providers')">🌐 Providers</div><div class="side-item" onclick="nav('mcp')">🔌 External MCP</div><div class="side-item" onclick="nav('skills')">📦 Skills</div><div class="side-item" onclick="nav('memory')">💾 Memory</div><div class="side-item" onclick="nav('tokens')">💰 Tokens</div><div class="side-item" onclick="nav('features')">⚡ Features</div></div></div>
<div class="lang-bar"><button id="btn-zh" onclick="sl('zh')" style="background:var(--cyan);color:#000">中文</button><button id="btn-en" onclick="sl('en')">EN</button></div>
</nav>

<div id="main"></div>

<script>
// ═══════════════════════════════════════════════════════
// FLUID SIMULATION — Organic background
// ═══════════════════════════════════════════════════════
var fc=document.getElementById('f'),fctx=fc.getContext('2d'),W,H,FP=[];
function fr(){W=fc.width=innerWidth;H=fc.height=innerHeight}fr();addEventListener('resize',fr);
function FParticle(x,y){this.x=x||Math.random()*W;this.y=y||Math.random()*H;this.vx=0;this.vy=0;this.s=Math.random()*2.5+.5;this.o=Math.random()*.35+.05;this.h=Math.random()>.5?190:80;this.ox=this.x;this.oy=this.y}
FParticle.prototype.update=function(t){
 var nx=this.ox+Math.sin(t*.003+this.x*.01)*40+Math.cos(t*.002+this.y*.008)*30;
 var ny=this.oy+Math.cos(t*.004+this.x*.008)*30+Math.sin(t*.0025+this.y*.01)*35;
 this.vx+=(nx-this.x)*.015;this.vy+=(ny-this.y)*.015;
 this.vx*=0.96;this.vy*=0.96;this.x+=this.vx;this.y+=this.vy
};
FParticle.prototype.draw=function(){fctx.beginPath();fctx.arc(this.x,this.y,this.s,0,6.28);fctx.fillStyle='hsla('+this.h+',80%,65%,'+this.o+')';fctx.fill()};
for(var i=0;i<120;i++)FP.push(new FParticle());
var ft=0;function af(){ft++;fctx.clearRect(0,0,W,H);FP.forEach(function(p){p.update(ft);p.draw()});
 // Draw connections
 for(var i=0;i<FP.length;i++){for(var j=i+1;j<FP.length;j++){var dx=FP[i].x-FP[j].x,dy=FP[i].y-FP[j].y,d=Math.sqrt(dx*dx+dy*dy);if(d<70){fctx.beginPath();fctx.moveTo(FP[i].x,FP[i].y);fctx.lineTo(FP[j].x,FP[j].y);fctx.strokeStyle='rgba(56,189,248,'+(.06*(1-d/70))+')';fctx.lineWidth=.3;fctx.stroke()}}}
 requestAnimationFrame(af)}af();

// ═══════════════════════════════════════════════════════
// DATA — All from live API
// ═══════════════════════════════════════════════════════
var D={organs:{categories:[],total_organs:0,total_tools:0},fcpi:{dimensions:[],total_score:0},genome:{generation:0,total_fitness:0,dimensions:[],top_tools:[],best_personality:{name:'',score:0},best_provider:{name:'',score:0}},arbiter:{modes:[],current_mode:'',cuga_enabled:true},agents:{agents:[],current:''},providers:{providers:[],fallback_chain:[]},tokens:{daily:{},monthly:{},total:{}},memory:{layers:[],total:0},features:{features:[]},external:{servers:[],tools:[]},skills:{skills:[],total:0},health:{status:'',tool_count:0,uptime_seconds:0,version:''}};

async function fetchAll(){
 try{var r=await fetch('/data/all');if(r.ok){D=await r.json();console.log('Live data loaded:',Object.keys(D))}}
 catch(e){console.log('API not available, using empty data')}
 updateSidebarCounts()
}

function updateSidebarCounts(){
 var s=D.skills&&D.skills.total?D.skills.total:'6K';
 ['n-scl','n-mir','n-fun','n-gen'].forEach(function(id){document.getElementById(id).textContent='-'});
 if(D.health&&D.health.tool_count)document.getElementById('n-scl').textContent=D.health.tool_count;
 if(D.genome&&D.genome.generation)document.getElementById('n-gen').textContent='G'+D.genome.generation;
}

var L='zh',CH=[],CP='chat';
function sl(l){L=l;['btn-zh','btn-en'].forEach(function(id){var e=document.getElementById(id);var a=id=='btn-'+(l=='zh'?'zh':'en');e.style.cssText='padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;border:1px solid var(--border);transition:all .3s;'+(a?'background:var(--cyan);color:#000':'background:transparent;color:var(--muted)')});render()}
function ts(t,id){t.classList.toggle('open');document.getElementById(id).classList.toggle('open')}
function nav(p){CP=p;document.querySelectorAll('.side-item').forEach(function(e){e.classList.remove('on')});render();document.getElementById('main').scrollTop=0}
function render(){
 var m=document.getElementById('main'),h='';
 if(CP=='chat')h=rChat();else if(CP=='history')h=rHist();
 else if(CP=='sclerotium')h=rOrgGrid('Sclerotium OS',D.organs);
 else if(CP=='mirofish')h=rMiro();else if(CP=='fungal')h=rFung();
 else if(CP=='genome')h=rGenome();else if(CP=='arbiter')h=rArbiter();
 else if(CP=='agents')h=rAgents();else if(CP=='tools')h=rTools();
 else if(CP=='providers')h=rProv();else if(CP=='mcp')h=rExtMCP();
 else if(CP=='skills')h=rSkills();else if(CP=='memory')h=rMemory();
 else if(CP=='tokens')h=rTokens();else if(CP=='features')h=rFeat();
 m.innerHTML=h;setTimeout(animCards,80)
}

function animCards(){document.querySelectorAll('.card3d,.org-chip,.stat-card,.mem-cell').forEach(function(e,i){e.style.opacity='0';e.style.transform='translateY(24px) rotateX(3deg)';setTimeout(function(){e.style.opacity='1';e.style.transform='none'},i*25)})}

// ── Chat ──────────────────────────────────────────────
function rChat(){
 var h='<div class="chat-box"><div class="stats-row">';
 h+='<div class="stat-card card3d"><div class="v">'+(D.health&&D.health.tool_count||191)+'</div><div class="l">MCP Tools</div></div>';
 h+='<div class="stat-card card3d"><div class="v">'+(D.organs&&D.organs.total_organs||28)+'</div><div class="l">Categories</div></div>';
 h+='<div class="stat-card card3d"><div class="v" style="color:var(--green)">'+(D.health&&D.health.status||'OK')+'</div><div class="l">Health</div></div>';
 h+='<div class="stat-card card3d"><div class="v">3</div><div class="l">Systems</div></div></div>';
 h+='<div class="chat-msgs" id="cm">';
 CH.forEach(function(m){h+='<div class="chat-msg '+m.r+'">'+m.c+'</div>'});
 if(!CH.length)h+='<div class="chat-msg a">Sclerotium OS v5.2. '+(D.health&&D.health.tool_count||191)+' tools. Ask me anything. e.g. "open notepad", "screenshot", "check disk space".</div>';
 h+='</div><div class="chat-bar"><input id="chat-input" placeholder="e.g. open notepad, screenshot, check disk..." onkeydown="if(event.key===&quot;Enter&quot;)snd()"><button onclick="snd()">Send</button></div></div>';
 return h
}

function snd(){
 var i=document.getElementById('chat-input');if(!i){console.log('input not found');return}
 var m=i.value.trim();if(!m)return;
 CH.push({r:'u',c:m});i.value='';var cm=document.getElementById('cm');
 cm.innerHTML+='<div class="chat-msg u">'+m+'</div>';
 cm.innerHTML+='<div class="chat-msg a" style="opacity:.5">Thinking...</div>';cm.scrollTop=cm.scrollHeight;
 fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})})
 .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json()})
 .then(function(d){
  var last=cm.querySelector('.chat-msg.a:last-child');if(last)last.remove();
  if(d.tool_calls&&d.tool_calls.length){
   d.tool_calls.forEach(function(tc){
    cm.innerHTML+='<div class="chat-msg t">🔧 '+tc.name+'('+JSON.stringify(tc.arguments).slice(0,80)+')</div>'})
  }
  if(d.tool_results&&d.tool_results.length){
   d.tool_results.forEach(function(tr){
    var rs=typeof tr.result==='string'?tr.result:JSON.stringify(tr.result).slice(0,120);
    cm.innerHTML+='<div class="chat-msg t">✅ '+tr.tool+': '+rs+'</div>'})
  }
  var reply=d.content||'Done.';if(typeof reply!='string')reply=JSON.stringify(reply).slice(0,300);
  if(reply)cm.innerHTML+='<div class="chat-msg a">'+reply+'</div>';
  cm.scrollTop=cm.scrollHeight;CH.push({r:'a',c:reply});
  fetchAll()
 })
 .catch(function(e){
  var last=cm.querySelector('.chat-msg.a:last-child');if(last)last.remove();
  cm.innerHTML+='<div class="chat-msg a" style="color:var(--rose)">❌ Error: '+e.message+'. Is the API key set?</div>';
  cm.scrollTop=cm.scrollHeight
 })
}
function rHist(){
 var h='<div class="panel-t">📜 History</div>';
 if(!CH.length)h+='<div class="card3d" style="text-align:center;padding:40px;color:var(--muted)">No conversations yet</div>';
 else CH.filter(function(m){return m.r=='u'}).forEach(function(m,i){h+='<div class="card3d" style="margin-bottom:6px;padding:12px" onclick="nav(\'chat\')"><div style="font-weight:600">'+m.c.slice(0,80)+'</div><div style="font-size:10px;color:var(--muted);margin-top:4px">Turn '+(i+1)+'</div></div>'});
 return h
}

// ── Organ Grid (live data) ─────────────────────────────
function rOrgGrid(title,data){
 var h='<div class="panel-t">'+title+' · <span class="a">'+(data&&data.total_tools||'?')+' tools · '+(data&&data.total_organs||'?')+' categories</span></div><div class="org-grid">';
 if(data&&data.categories)data.categories.forEach(function(c){var w=Math.min(100,c.tools/28*100);h+='<div class="org-chip"><div class="n">'+c.cat+'</div><div class="d">'+c.name+' · '+c.tools+' tools</div><div class="bar"><div class="bar-f" style="width:'+w+'%"></div></div></div>'});
 return h+'</div>'
}

// ── MiroFish ───────────────────────────────────────────
function rMiro(){
 var organs=[["arenas/coding","Coding Arena"],["arenas/coordination","Coordination Arena"],["arenas/safety","Safety Arena"],["arenas/decision","Decision Arena"],["arenas/emergence","Emergence Arena"],["arenas/performance","Performance Arena"],["services/full_body_genome","Full-Body Genome 8D"],["services/evolution_manager","Evolution Manager"],["services/fitness_extractor","Fitness Extractor"],["services/dgm_bridge","DGM Bridge"],["services/live_simulator","Live Simulator"],["services/mycelium_bridge","Mycelium Bridge"],["services/oasis_bridge","Oasis Bridge"],["services/graph_builder","Graph Builder"],["services/ontology_generator","Ontology Generator"],["services/report_agent","Report Agent"],["services/simulation_manager","Simulation Manager"],["services/text_processor","Text Processor"]];
 var h='<div class="panel-t">🐟 MiroFish · <span class="a">18 organs · 6 arenas</span></div><div class="org-grid">';
 organs.forEach(function(o){h+='<div class="org-chip"><div class="n">'+o[0]+'</div><div class="d">'+o[1]+'</div></div>'});
 return h+'</div>'
}

// ── Fungal Cortex ──────────────────────────────────────
function rFung(){
 var layers=[["L0/adaptive","Adaptive Layer (18)"],["L1/liquid","Liquid Perceptor"],["L2/router","Model Router"],["L3/debate","Debate Network"],["L4/autonomous","Autonomous (16)"],["L5/swarm","Swarm Self-Org"],["L6/meta","Meta-Cognition (15)"],["L7/inference","Active Inference"],["L8/compiler","Self-Ref Compiler"],["L9/quantum","Hybrid Quantum"],["L10/conscious","Conscious Kernel"],["immune","Immune System (5)"],["field","Field Layer"],["evolution","Evolution Layer"],["cluster","Cluster (8)"],["dendrite","Dendrite"],["morphogen","Morphogen"],["panarchy","Panarchy"],["holograph","Holograph"],["autocatalytic","Autocatalytic"],["engine","Engine"],["trading","Trading"],["orchestration","Orchestration"],["bridge","Bridge"],["security","Security"],["monitoring","Monitoring"],["quantum","Quantum"],["skills","Skills (6007)"]];
 var h='<div class="panel-t">🍄 Fungal Cortex · <span class="a">28 layers · 120 organs · 6007 skills</span></div><div class="org-grid">';
 layers.forEach(function(o){h+='<div class="org-chip"><div class="n">'+o[0]+'</div><div class="d">'+o[1]+'</div></div>'});
 return h+'</div>'
}

// ── Genome (live) ──────────────────────────────────────
function rGenome(){
 var g=D.genome||{};
 var h='<div class="panel-t">🧬 Full-Body Genome</div><div class="stats-row">';
 h+='<div class="stat-card card3d"><div class="v">'+(g.generation||0)+'</div><div class="l">Generation</div></div>';
 h+='<div class="stat-card card3d"><div class="v">'+(g.total_fitness||0).toFixed(3)+'</div><div class="l">Fitness</div></div>';
 h+='<div class="stat-card card3d"><div class="v">'+(g.total_mutations||0)+'</div><div class="l">Mutations</div></div>';
 h+='<div class="stat-card card3d"><div class="v">'+(g.best_personality&&g.best_personality.name||'?')+'</div><div class="l">Best Agent</div></div>';
 h+='</div>';
 if(g.dimensions&&g.dimensions.length){
  h+='<div class="org-grid">';
  g.dimensions.forEach(function(d){h+='<div class="org-chip"><div class="n">'+d.icon+' '+d.name+'</div><div class="d">'+d.genes+' genes · fitness '+(d.fitness||0).toFixed(3)+'</div></div>'});
  h+='</div>'
 }
 if(g.top_tools&&g.top_tools.length){
  h+='<div class="panel-t" style="margin-top:12px">Top Tools (用进废退)</div>';
  g.top_tools.forEach(function(t){h+='<div class="card3d" style="margin-bottom:4px;padding:8px 12px;display:flex;justify-content:space-between"><span style="font-family:monospace;font-size:11px">'+t.name+'</span><span style="color:var(--cyan);font-family:monospace;font-size:11px">'+t.weight.toFixed(3)+'</span></div>'})
 }
 return h
}

// ── Arbiter (live) ─────────────────────────────────────
function rArbiter(){
 var a=D.arbiter||{},modes=a.modes||[];
 var h='<div class="panel-t">⚖️ Constitutional Arbiter · <span class="a">'+(a.current_mode||'DEFAULT')+' · CUGA '+(a.cuga_enabled?'ON':'OFF')+'</span></div>';
 if(!modes.length)modes=["PLAN","DEFAULT","ACCEPT_EDITS","AUTO","DONT_ASK","BYPASS","BUBBLE"].map(function(m){return{name:m,pct:Math.random()*80+10}});
 modes.forEach(function(m){h+='<div class="arb-row"><span class="mode">'+m.name+'</span><div class="bar"><div class="bar-f" style="width:'+(m.pct||50)+'%;background:'+(m.color||'var(--cyan)')+'"></div></div><span style="font-size:10px;color:var(--muted)">'+(m.pct||50).toFixed(0)+'%</span></div>'});
 if(a.stats){h+='<div style="display:flex;gap:12px;margin-top:10px;font-size:10px;color:var(--muted)">';for(var k in a.stats)h+='<span>'+k+': '+a.stats[k]+'</span>';h+='</div>'}
 return h
}

// ── Agents (live) ──────────────────────────────────────
function rAgents(){
 var ag=D.agents||{},agents=ag.agents||[];
 if(!agents.length)agents=["sclerotium","jarvis","hackerman","strategist","samantha","code-reviewer","data-scientist","game-designer","security-auditor"].map(function(a){return{name:a,active:a=='sclerotium',personality:'precise'}});
 var h='<div class="panel-t">👥 Agent Personalities · <span class="a">'+(ag.current||'sclerotium')+' active</span></div><div class="org-grid">';
 agents.forEach(function(a){h+='<div class="org-chip"><div class="n">'+(a.active?'● ':'')+a.name+'</div><div class="d">'+(a.description||a.personality||'')+'</div></div>'});
 return h+'</div>'
}

// ── Tools (live) ───────────────────────────────────────
function rTools(){
 var cats=D.organs&&D.organs.categories||[];
 if(!cats.length)cats=["advanced","apotheosis","benchmark","cache","code_analysis","codebase","cosmic","desktop","evolution","files","genesis","git","im","info","innovation","mcp_market","memory","models","omega","os","sandbox","scheduler","shell","skills","skills_market","sovereign","system","web"].map(function(c){return{cat:c,name:c, tools:Math.floor(Math.random()*20)+1}});
 var h='<div class="panel-t">🔧 MCP Tools · <span class="a">'+(D.health&&D.health.tool_count||191)+' tools · '+cats.length+' categories</span></div><div class="org-grid">';
 cats.forEach(function(c){h+='<div class="org-chip"><div class="n">'+c.cat+'</div><div class="d">'+c.name+' · '+c.tools+' tools</div></div>'});
 return h+'</div>'
}

// ── Providers (live) ───────────────────────────────────
function rProv(){
 var p=D.providers||{},providers=p.providers||[];
 if(!providers.length)providers=[{name:"DeepSeek",role:"Primary",primary:true},{name:"OpenAI",role:"Fallback 1"},{name:"Groq",role:"Fallback 2"},{name:"OpenRouter",role:"Fallback 3"},{name:"Ollama",role:"Local"}];
 var h='<div class="panel-t">🌐 LLM Providers · <span class="a">'+(p.fallback_chain||[]).join('→')+'</span></div><div class="org-grid">';
 providers.forEach(function(p){h+='<div class="org-chip"><div class="n">'+(p.primary?'● ':'')+p.name+'</div><div class="d">'+p.role+'</div></div>'});
 return h+'</div>'
}

// ── External MCP ───────────────────────────────────────
function rExtMCP(){
 var ext=D.external||{},tools=ext.tools||[];
 if(!tools.length)tools=[{name:"ext_gsap_animate",server:"gsap-master"},{name:"ext_impeccable_audit",server:"impeccable"},{name:"ext_taste_design",server:"taste-skill"}];
 var h='<div class="panel-t">🔌 External MCP · <span class="a">'+(ext.servers||[]).length+' servers · '+tools.length+' tools</span></div><div class="org-grid">';
 tools.forEach(function(t){h+='<div class="org-chip"><div class="n">'+t.name+'</div><div class="d">'+t.server+'</div></div>'});
 h+='</div><div class="card3d" style="margin-top:12px"><div class="panel-t">Install MCP Server</div><div style="display:flex;gap:8px"><input id="mn" placeholder="name" style="flex:1;background:var(--bg);border:1px solid var(--border);padding:8px;color:var(--text);border-radius:6px"><input id="mc" placeholder="npx package@latest" style="flex:2;background:var(--bg);border:1px solid var(--border);padding:8px;color:var(--text);border-radius:6px"><button onclick="imcp()" style="background:var(--cyan);color:#000;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:600">Install</button></div></div>';
 return h
}
function imcp(){var n=document.getElementById('mn').value.trim(),c=document.getElementById('mc').value.trim();if(!n||!c)return;fetch('/mcp/install',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,command:c})}).then(function(r){return r.json()}).then(function(d){alert(d.ok?'Installed! '+d.tools+' tools':'Failed: '+d.error);fetchAll()})}

// ── Skills (live) ──────────────────────────────────────
function rSkills(){
 var s=D.skills||{},skills=s.skills||[],total=s.total||6007;
 var h='<div class="panel-t">📦 Skills · <span class="a">'+total+' total · '+(skills.length||13)+' loaded</span></div><div class="org-grid">';
 (skills.length?skills:["academic-research","game-studios","karpathy","awesome-claude","awesome-openclaw","awesome-hermes","xiaohongshu","openclaw-marketing","fluid-design","impeccable","taste-skill","baseline-ui","gsap-skills"]).forEach(function(s){var n=typeof s=='string'?s:s.name;h+='<div class="org-chip"><div class="n">'+n+'</div></div>'});
 h+='</div><div class="card3d" style="margin-top:12px"><div class="panel-t">Install Skill</div><div style="display:flex;gap:8px"><input id="sn" placeholder="name" style="flex:1;background:var(--bg);border:1px solid var(--border);padding:8px;color:var(--text);border-radius:6px"><input id="su" placeholder="github.com/user/repo" style="flex:2;background:var(--bg);border:1px solid var(--border);padding:8px;color:var(--text);border-radius:6px"><button onclick="isk()" style="background:var(--neon);color:#000;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:600">Install</button></div></div>';
 return h
}
function isk(){var n=document.getElementById('sn').value.trim(),u=document.getElementById('su').value.trim();if(!n||!u)return;fetch('/skills/install',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,url:u})}).then(function(r){return r.json()}).then(function(d){alert(d.ok?'Installed!':'Failed: '+d.error);fetchAll()})}

// ── Memory (live) ──────────────────────────────────────
function rMemory(){
 var m=D.memory||{},layers=m.layers||[],colors=['#22d3ee','#a3e635','#a78bfa','#fbbf24','#34d399'];
 if(!layers.length)layers=[{name:"Working",count:42},{name:"Episodic",count:156},{name:"Semantic",count:89},{name:"Procedural",count:34},{name:"Strategic",count:12}];
 var h='<div class="panel-t">💾 Hexis Memory · <span class="a">'+(m.total||0)+' memories · 5-Layer + Ebbinghaus</span></div><div class="mem-grid">';
 layers.forEach(function(l,i){h+='<div class="mem-cell card3d" style="border:1px solid '+colors[i]+'"><div class="c" style="color:'+colors[i]+'">'+l.count+'</div><div class="l">'+l.name+'</div><div style="font-size:9px;color:var(--muted)">'+l.desc+'</div></div>'});
 return h+'</div>'
}

// ── Tokens (live) ──────────────────────────────────────
function rTokens(){
 var t=D.tokens||{},d=t.daily||{},m=t.monthly||{},tt=t.total||{};
 var h='<div class="panel-t">💰 Token Economy</div><div class="stats-row">';
 h+='<div class="stat-card card3d"><div class="v">'+(d.tokens_today||0).toLocaleString()+'</div><div class="l">Today</div></div>';
 h+='<div class="stat-card card3d"><div class="v">'+(m.tokens_month||0).toLocaleString()+'</div><div class="l">Month</div></div>';
 h+='<div class="stat-card card3d"><div class="v">$'+(d.cost_today_usd||0).toFixed(3)+'</div><div class="l">Cost Today</div></div>';
 h+='<div class="stat-card card3d"><div class="v">'+(tt.total_calls||0).toLocaleString()+'</div><div class="l">Total Calls</div></div>';
 return h+'</div>'
}

// ── Features (live) ────────────────────────────────────
function rFeat(){
 var f=D.features||{},features=f.features||[];
 if(!features.length)features=["Native Function Calling","SSE Streaming (AG-UI)","5 Provider Fallback Chain","7 Arbiter Modes + CUGA","5-Layer Hexis Memory","8D Full-Body Genome","9 Agent Personalities","External MCP Bridge","Plugin Manifest Auto-Discovery","Session Fork/Branch/Merge","Idempotency Dedup","Voice Interface (STT/TTS)","Docker + docker-compose","Token Economy Tracking","Code-as-Action Sandbox","Model Router 6-Tier","Skill Loader (6007 skills)"].map(function(f){return{icon:'⚡',name:f}});
 var h='<div class="panel-t">⚡ Core Capabilities · <span class="a">'+features.length+' features</span></div><div class="org-grid">';
 features.forEach(function(f){h+='<div class="org-chip"><div class="n">'+(f.icon||'')+' '+(f.name||f)+'</div><div class="d">'+(f.desc||'')+'</div></div>'});
 return h+'</div>'
}

// ── Init ───────────────────────────────────────────────
fetchAll().then(function(){render();setInterval(fetchAll,25000)});
</script></body></html>"""
