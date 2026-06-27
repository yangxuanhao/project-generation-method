@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0
if not exist venv (
    echo 正在创建虚拟环境...
    python -m venv venv
)
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
pause
