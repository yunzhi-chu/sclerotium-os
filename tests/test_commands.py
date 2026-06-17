import sys, io, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
PASS=0; FAIL=0
def t(name, fn, *args):
    global PASS, FAIL
    try: r=fn(*args); PASS+=1; print(f'  [PASS] {name}')
    except Exception as e: FAIL+=1; print(f'  [FAIL] {name}: {e}')

from mcp.tools.file_ops import file_write, file_read, file_edit, file_list
t('file_write', file_write, '_t.txt','ok')
t('file_read', file_read, '_t.txt')
t('file_edit', file_edit, '_t.txt','ok','OK')
t('file_list', file_list, '.')

from mcp.tools.os_commands import cmd_ls,cmd_pwd,cmd_cat,cmd_find,cmd_wc,cmd_uname,cmd_df,cmd_du
t('ls', cmd_ls, '.')
t('pwd', cmd_pwd)
t('cat', cmd_cat, '_t.txt')
t('find', cmd_find, '.', '*.txt')
t('wc', cmd_wc, '_t.txt')
t('uname', cmd_uname)
t('df', cmd_df, '.')
t('du', cmd_du, '.')

from mcp.tools.bash_tool import bash_execute, bash_smart
t('bash_execute', bash_execute, 'echo ok')
t('bash_smart', bash_smart, 'check')

from mcp.tools.git_tools import git_status, git_log
t('git_status', git_status)
t('git_log', git_log, 3)

from mcp.tools.web_search import web_fetch
t('web_fetch', web_fetch, 'https://httpbin.org/get')

os.remove('_t.txt')
print(f'{PASS}/{PASS+FAIL} passed')
