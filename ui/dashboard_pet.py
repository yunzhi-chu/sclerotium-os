r"""Sclerotium OS v5.2 — Desktop Pet · Arc Reactor Core.

Layout: History(TL) · Vitals(TR) · Core(Center) · Evolution(BR) · Chat(Bottom)
Design: impeccable anti-slop · baseline-ui precision · taste-skill variance · gsap motion
"""
PET_DASHBOARD = r"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Sclerotium OS v5.2</title>
<style>
/* ══════ TASTE: variance=8 motion=7 density=6 · IMPECCABLE: no Inter/Roboto · BASELINE: compositor-only ══════ */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;600&display=swap');

:root{--bg:#020617;--card:rgba(15,23,42,.92);--border:rgba(56,189,248,.12);--text:#e2e8f0;--muted:#64748b;--cyan:#22d3ee;--neon:#a3e635;--amber:#fbbf24;--rose:#fb7185;--violet:#a78bfa;--green:#34d399;--blue:#38bdf8;--font:'Space Grotesk',system-ui,sans-serif;--mono:'JetBrains Mono',monospace}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font:13px/1.5 var(--font);overflow:hidden;height:100vh;display:grid;grid-template-columns:300px 1fr 280px;grid-template-rows:1fr auto;gap:12px;padding:12px}

/* ══════ PANELS ══════ */
.panel{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px;backdrop-filter:blur(20px);transition:border-color .3s,box-shadow .3s;overflow:hidden;display:flex;flex-direction:column}
.panel:hover{border-color:rgba(34,211,238,.3);box-shadow:0 0 24px rgba(34,211,238,.06)}
.panel-h{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;cursor:pointer;user-select:none;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px}
.panel-h .dot{width:6px;height:6px;border-radius:50%;background:var(--cyan);margin-right:8px;animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:.4}50%{opacity:1}}
.panel-body{flex:1;overflow-y:auto}

/* ══════ GRID POSITIONING ══════ */
#history-panel{grid-column:1;grid-row:1;max-height:calc(100vh - 160px)}
#core-area{grid-column:2;grid-row:1;display:flex;align-items:center;justify-content:center}
#vitals-panel{grid-column:3;grid-row:1}
#evolve-panel{grid-column:3;grid-row:1;align-self:end;max-height:45%}
#chat-panel{grid-column:1 / -1;grid-row:2;max-height:140px;flex-shrink:0}

/* ══════ ARC REACTOR CORE ══════ */
.core{position:relative;width:200px;height:200px;cursor:pointer}
.core-glow{position:absolute;inset:-20px;border-radius:50%;background:radial-gradient(circle,rgba(34,211,238,.25) 0%,rgba(34,211,238,.04) 50%,transparent 70%);animation:glowPulse 2s ease-in-out infinite}
@keyframes glowPulse{0%,100%{transform:scale(1);opacity:.5}50%{transform:scale(1.2);opacity:1}}
.core-ring{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);border-radius:50%;border:1px solid rgba(56,189,248,.15)}
.core-ring:nth-child(1){width:100%;height:100%;animation:spin 10s linear infinite}
.core-ring:nth-child(2){width:82%;height:82%;animation:spin 7s linear infinite reverse}
.core-ring:nth-child(3){width:64%;height:64%;animation:spin 5s linear infinite}
.core-ring:nth-child(4){width:46%;height:46%;border-color:rgba(34,211,238,.25);animation:spin 3.5s linear infinite reverse}
@keyframes spin{to{transform:translate(-50%,-50%) rotate(360deg)}}
.core-tri{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:90px;height:90px}
.core-tri svg{width:100%;height:100%;filter:drop-shadow(0 0 16px rgba(34,211,238,.5)) drop-shadow(0 0 32px rgba(34,211,238,.2))}

/* ══════ CHAT ══════ */
#chat-panel .chat-body{display:flex;flex-direction:column;flex:1;min-height:0}
.chat-msgs{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin-bottom:8px;max-height:60px}
.chat-msg{padding:6px 10px;border-radius:6px;max-width:70%;font-size:12px;animation:msgIn .25s ease}
.chat-msg.u{background:var(--cyan);color:#000;align-self:flex-end}
.chat-msg.a{background:var(--card);border:1px solid var(--border);align-self:flex-start}
.chat-msg.t{background:rgba(34,211,238,.06);border:1px solid rgba(34,211,238,.12);font-size:10px;font-family:var(--mono)}
.chat-bar{display:flex;gap:8px}
.chat-bar input{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 14px;color:var(--text);font-size:14px;outline:none;font-family:var(--font);transition:border-color .3s}
.chat-bar input:focus{border-color:var(--cyan)}
.chat-bar button{background:var(--cyan);color:#000;border:none;padding:10px 20px;border-radius:8px;cursor:pointer;font-weight:600;font-size:13px;font-family:var(--font);transition:transform .2s,box-shadow .2s}
.chat-bar button:hover{transform:scale(1.03);box-shadow:0 0 16px rgba(34,211,238,.3)}
@keyframes msgIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}

/* ══════ HISTORY ══════ */
.hist-item{padding:8px 10px;border:1px solid var(--border);border-radius:8px;cursor:pointer;margin-bottom:5px;font-size:11px;transition:all .2s}
.hist-item:hover{border-color:var(--cyan);transform:translateX(3px)}
.hist-empty{color:var(--muted);text-align:center;padding:24px;font-size:12px}

/* ══════ VITALS ══════ */
.v-row{display:flex;justify-content:space-between;padding:6px 0;font-size:11px;border-bottom:1px solid rgba(148,163,184,.05)}
.v-row:last-child{border-bottom:none}
.v-k{color:var(--muted)}.v-v{font-family:var(--mono);font-weight:500}
.v-bar{height:2px;background:var(--border);border-radius:1px;margin:2px 0;overflow:hidden}
.v-bar-f{height:100%;border-radius:1px;transition:width 1s ease}

/* ══════ EVOLUTION ══════ */
.evo-stat{text-align:center;padding:6px;margin-bottom:6px}
.evo-stat .evo-n{font-size:22px;font-family:var(--mono);font-weight:700;color:var(--cyan)}
.evo-stat .evo-l{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px}

/* ══════ RESPONSIVE ══════ */
@media(max-width:1000px){body{grid-template-columns:1fr;grid-template-rows:auto;overflow-y:auto}#core-area{display:none}}
::-webkit-scrollbar{width:3px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
</style></head><body>

<!-- HISTORY (Top Left) -->
<div class="panel" id="history-panel">
<div class="panel-h" onclick="this.parentElement.classList.toggle('folded')"><span><span class="dot"></span>History</span><span style="font-size:10px">_</span></div>
<div class="panel-body" id="history"><div class="hist-empty">No conversations yet</div></div>
</div>

<!-- ARC REACTOR CORE (Center) -->
<div id="core-area">
<div class="core"><div class="core-glow"></div><div class="core-ring"></div><div class="core-ring"></div><div class="core-ring"></div><div class="core-ring"></div>
<div class="core-tri"><svg viewBox="0 0 120 120"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#22d3ee"/><stop offset="100%" stop-color="#a78bfa"/></linearGradient></defs><polygon points="60,8 112,108 8,108" fill="none" stroke="url(#g)" stroke-width="1.5"><animate attributeName="stroke-dasharray" values="0,400;400,0" dur="3s" repeatCount="indefinite"/></polygon><polygon points="60,28 96,92 24,92" fill="none" stroke="url(#g)" stroke-width="0.7" opacity="0.5"><animate attributeName="stroke-dasharray" values="0,300;300,0" dur="3s" begin="1s" repeatCount="indefinite"/></polygon><circle cx="60" cy="60" r="6" fill="none" stroke="#22d3ee" stroke-width="1"><animate attributeName="r" values="6;10;6" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values="1;.3;1" dur="2s" repeatCount="indefinite"/></circle><circle cx="60" cy="60" r="2" fill="#22d3ee"/></svg></div></div>
</div>

<!-- VITALS (Top Right) -->
<div class="panel" id="vitals-panel">
<div class="panel-h"><span><span class="dot"></span>Vitals</span><span style="font-size:10px">auto</span></div>
<div class="panel-body" id="vitals"></div>
</div>

<!-- EVOLUTION (Bottom Right, inside vitals area) -->
<div class="panel" id="evolve-panel">
<div class="panel-h"><span><span class="dot"></span>Evolution</span></div>
<div class="panel-body" id="evolution"></div>
</div>

<!-- CHAT (Bottom Full Width) -->
<div class="panel" id="chat-panel">
<div class="panel-h"><span><span class="dot"></span>Neural Link</span></div>
<div class="chat-body"><div class="chat-msgs" id="cm"></div>
<div class="chat-bar"><input id="ci" placeholder="Say something..." onkeydown="if(event.key==='Enter')send()"><button onclick="send()">Send</button></div></div>
</div>

<script>
var CH=[],D={};

function send(){
 var i=document.getElementById('ci'),m=i.value.trim();if(!m)return;
 CH.push({r:'u',c:m});i.value='';var cm=document.getElementById('cm');
 cm.innerHTML+='<div class="chat-msg u">'+m+'</div>';
 cm.innerHTML+='<div class="chat-msg a" style="opacity:.5">...</div>';cm.scrollTop=cm.scrollHeight;
 fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})})
 .then(r=>r.json()).then(function(d){
  var last=cm.querySelector('.chat-msg.a:last-child');if(last)last.remove();
  if(d.tool_calls)d.tool_calls.forEach(function(tc){cm.innerHTML+='<div class="chat-msg t">'+tc.name+'</div>'});
  if(d.tool_results)d.tool_results.forEach(function(tr){cm.innerHTML+='<div class="chat-msg t">OK:'+tr.tool+'</div>'});
  var reply=d.content||'Done.';if(reply)cm.innerHTML+='<div class="chat-msg a">'+reply+'</div>';
  cm.scrollTop=cm.scrollHeight;CH.push({r:'a',c:reply});updateHistory();fetchData()
 }).catch(function(e){
  var last=cm.querySelector('.chat-msg.a:last-child');if(last)last.remove();
  cm.innerHTML+='<div class="chat-msg a" style="color:var(--rose)">Error</div>'
 })
}

function updateHistory(){
 var h=document.getElementById('history');
 h.innerHTML=CH.filter(function(m){return m.r=='u'}).map(function(m,i){
  return'<div class="hist-item" onclick="navigator.clipboard.writeText(\''+m.c.replace(/'/g,"\\'")+'\')">'+m.c.slice(0,50)+(m.c.length>50?'...':'')+'<div style="font-size:9px;color:var(--muted);margin-top:2px">Turn '+(i+1)+'</div></div>'
 }).join('')||'<div class="hist-empty">No conversations yet</div>'
}

function updateVitals(){
 if(!D.health&&!D.organs&&!D.genome){return}
 var v=document.getElementById('vitals'),h='';
 var items=[
  ['Tools',D.health?D.health.tool_count:(D.organs?D.organs.total_tools:'..'),'var(--cyan)'],
  ['Health',(D.health&&D.health.status)||'..','var(--green)'],
  ['Organs',(D.organs&&D.organs.total_organs)||'..','var(--cyan)'],
  ['Systems',(D.organs&&D.organs.breakdown)?(D.organs.breakdown.sclerotium_organs||'?')+'+'+(D.organs.breakdown.fungal_organs||'?')+'+'+(D.organs.breakdown.mirofish_organs||'?'):'..','var(--green)'],
  ['Genome',D.genome&&D.genome.generation?'Gen '+D.genome.generation:'..','var(--violet)'],
  ['Fitness',D.genome&&D.genome.total_fitness!=null?Number(D.genome.total_fitness).toFixed(3):'..','var(--neon)'],
  ['Memory',D.memory&&D.memory.total!=null?D.memory.total:'..','var(--amber)'],
  ['Personality',(D.genome&&D.genome.best_personality||{}).name||'..','var(--blue)'],
  ['Provider',(D.genome&&D.genome.best_provider||{}).name||'..','var(--rose)'],
 ];
 items.forEach(function(item){h+='<div class="v-row"><span class="v-k">'+item[0]+'</span><span class="v-v" style="color:'+item[2]+'">'+item[1]+'</span></div>'});
 v.innerHTML=h
}

function updateEvo(){
 var e=document.getElementById('evolution');
 if(!D.genome||!D.genome.dimensions||!D.genome.dimensions.length){e.innerHTML='<div class="evo-stat"><div class="evo-n">..</div><div class="evo-l">Waiting for data</div></div>';return}
 var dims=D.genome.dimensions,h='';
 h+='<div class="evo-stat"><div class="evo-n">'+(D.genome.generation||'..')+'</div><div class="evo-l">Generation</div></div>';
 dims.forEach(function(d){
  var pct=Number(d.fitness||d.value||0);
  if(isNaN(pct))pct=0;
  h+='<div style=\"margin:4px 0\"><div style=\"display:flex;justify-content:space-between;font-size:9px\"><span>'+(d.name||d.icon+' '||'?')+'</span><span style=\"color:'+(d.color||'var(--cyan)')+'\">'+(pct*100).toFixed(0)+'%</span></div><div class=\"v-bar\"><div class=\"v-bar-f\" style=\"width:'+(pct*100)+'%;background:'+(d.color||'var(--cyan)')+'\"></div></div></div>'
 });
 e.innerHTML=h
}

async function fetchData(){
 try{var r=await fetch('/data/all');if(r.ok){D=await r.json();updateVitals();updateEvo()}}catch(e){}
}
fetchData();setInterval(fetchData,15000);updateHistory();
</script></body></html>"""
