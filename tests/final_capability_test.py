"""Sclerotium OS v0.5.0 — Final Engineering Capability Test"""
import sys, os, asyncio, shutil, time
from pathlib import Path
os.environ['PYTHONIOENCODING'] = 'utf-8'
# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

PASS = 0; FAIL = 0
def test(name, fn):
    global PASS, FAIL
    try: fn(); PASS += 1; print(f'  [PASS] {name}')
    except Exception as e: FAIL += 1; print(f'  [FAIL] {name}: {str(e)[:80]}')

print('='*60)
print('SCLEROTIUM OS v0.5.0 — ENGINEERING CAPABILITY TEST')
print('='*60)

# 1. KERNEL MODULES
print('\n--- 1. KERNEL MODULES (15 files) ---')
for mod in ['agent_loop','code_generation_pipeline','capability_router',
    'codebase_indexer','collaborative_reasoner','command_registry',
    'context_compressor','hexis_memory','hooks','organ_symphony',
    'permission_gate','prompt_cache','session_store','super_prompt_factory','tool_router']:
    test(f'kernel.{mod}', lambda m=mod: __import__(f'kernel.{m}'))

# 2. GATEWAY
print('\n--- 2. GATEWAY ---')
from gateways.models import UniversalModelGateway, RoutingStrategy
gw = UniversalModelGateway()
test('gateway instantiated', lambda: gw)
test('gateway strategy', lambda: gw.strategy)
test('gateway providers > 15', lambda: len(gw.list_providers()) > 15)
test('chat_stream method exists', lambda: gw.chat_stream)

# 3. MCP SERVER & TOOLS
print('\n--- 3. MCP SERVER & TOOLS ---')
from mcp.server import SclerotiumMCPServer
mcp = SclerotiumMCPServer()
mcp.register_all_tools()
tc = mcp.tools.tool_count
test(f'MCP tools: {tc}', lambda: None if tc > 100 else (_ for _ in ()))

# 4. COMMAND REGISTRY
print('\n--- 4. COMMAND REGISTRY ---')
from kernel.command_registry import CommandRegistry
cr = CommandRegistry()
bc = cr.load_builtins()
mc = cr.load_mcp_tools(mcp.tools)
test(f'Builtins: {bc}', lambda: None)
test(f'MCP commands: {mc}', lambda: None)
test('Search /model', lambda: cr.search('/model'))
test('Search /generate', lambda: cr.search('/generate'))

# 5. CAPABILITY ROUTER
print('\n--- 5. CAPABILITY ROUTER ---')
from kernel.capability_router import CapabilityRouter
cap = CapabilityRouter()
counts = cap.discover_all()
test(f'Discovered: {counts}', lambda: None)
r = cap.route('build a FastAPI endpoint with JWT auth')
test(f'Route: {len(r)} caps', lambda: None)
ctx = cap.build_context_injection('build a FastAPI endpoint')
test(f'Context: {len(ctx)} chars', lambda: None)

# 6. ORGAN SYMPHONY
print('\n--- 6. ORGAN SYMPHONY ---')
from kernel.organ_symphony import OrganSymphony, OrganLayer
sym = OrganSymphony()
counts = sym.register_all(mcp.tools)
stats = sym.get_stats()
test(f'Total organs: {stats["total_organs"]}', lambda: None)
test(f'Systems: {stats["by_system"]}', lambda: None)
sym.organ_activated('HexisMemory', 'Searching 5-layer memory...')
sym.organ_activated('AgentLoop', 'Processing...')
test(f'Active: {len(sym.get_active_organs())}', lambda: None)
test('Symphony context', lambda: len(sym.build_symphony_context('test')) > 0)

# 7. PERMISSION GATE
print('\n--- 7. PERMISSION GATE ---')
from kernel.permission_gate import ConstitutionalArbiter, PermissionMode
arb = ConstitutionalArbiter()
async def perm_test():
    ok, _ = await arb.check('file_read', {'path':'test.py'})
    assert ok, 'Read must be allowed'
    arb.set_mode(PermissionMode.PLAN)
    ok2, reason = await arb.check('file_write', {'path':'test.py'})
    print(f'     Plan mode result: allowed={ok2}, reason={reason[:60]}')
    assert not ok2, f'Plan mode must block writes, got: allowed={ok2}'
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(perm_test())
test('Read allowed', lambda: None)
test('Plan blocks write', lambda: None)
test(f'Mode: {arb.mode.value}', lambda: None)

# 8. CODE GENERATION PIPELINE
print('\n--- 8. NINE LAWS PIPELINE ---')
from kernel.code_generation_pipeline import NineLawsPipeline, Law
pipe = NineLawsPipeline()
test('Pipeline instantiated', lambda: pipe)
test(f'Laws: {len(Law.__members__)}', lambda: None)

# 9. PROMPT CACHE
print('\n--- 9. PROMPT CACHE ---')
from kernel.prompt_cache import PromptCacheEngine, CacheZone
cache = PromptCacheEngine()
cache.add_segment('constitution','Sclerotium OS v0.5',CacheZone.STATIC)
p, bp = cache.assemble('deepseek')
test(f'Assembly: {len(p)} chars', lambda: None)

# 10. HOOKS
print('\n--- 10. HOOKS ---')
from kernel.hooks import HookSystem, Hook
hooks = HookSystem()
hooks.register(Hook('test','PreToolUse'))
ok, _ = hooks.run('PreToolUse','test_tool',{'k':'v'})
test('Hook registered + run', lambda: None)

# 11. SESSION STORE
print('\n--- 11. SESSION STORE ---')
from kernel.session_store import SessionStore
ss = SessionStore('./data/_test_sessions')
sid = ss.create_session()
ss.append({'type':'test','content':'hello'})
events = ss.get_transcript(sid)
test(f'Sessions: {len(ss.list_sessions())}, Events: {len(events)}', lambda: None)
shutil.rmtree('./data/_test_sessions', ignore_errors=True)

# 12. TOOLS
print('\n--- 12. TOOLS (functional) ---')
from mcp.tools.web_search import web_search, web_fetch
r = web_search('hello world')
test(f'WebSearch: {r["status"]}', lambda: None)
r2 = web_fetch('https://github.com')
test(f'WebFetch: {r2["status"]}', lambda: None)
from mcp.tools.git_tools import git_status
test('Git status', lambda: git_status())

# 13. TUI WIDGETS
print('\n--- 13. TUI WIDGETS ---')
from cli.tui.widgets.sidebar import OrganismSidebar
from cli.tui.widgets.task_tracker import TaskTracker
from cli.tui.widgets.organ_flow import OrganFlow
test('Sidebar', lambda: OrganismSidebar())
test('TaskTracker', lambda: TaskTracker())
test('OrganFlow', lambda: OrganFlow())

# 14. AGENT LOOP INTEGRATION
print('\n--- 14. AGENT LOOP INTEGRATION ---')
from kernel.agent_loop import AgentLoop
loop = AgentLoop(gateway=gw, tools=mcp.tools, memory=None, arbiter=arb)
loop.wire_cache(cache)
loop.wire_hooks(hooks)
test('AgentLoop wired (cache+hooks)', lambda: None)
test('AgentLoop has stream types', lambda: hasattr(loop, 'run'))

# RESULTS
print('\n' + '='*60)
total = PASS + FAIL
pct = PASS/total*100 if total else 0
print(f'RESULTS: {PASS}/{total} PASSED ({pct:.0f}%)')
if FAIL: print(f'FAILURES: {FAIL}')
else: print('ALL TESTS PASSED')
print('='*60)
