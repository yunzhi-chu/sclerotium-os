@echo off
set "DIR=%~dp0"
set "DIR=%DIR:~0,-1%"
python -c "import sys; sys.path.insert(0, r'%DIR%'); from sclerotium_cli import main; main()" %*
