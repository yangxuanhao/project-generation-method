@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo [初始化] 正在创建虚拟环境...
    python -m venv venv
    echo [安装] 正在安装依赖包...
    venv\Scripts\pip install -r requirements.txt -q
)
echo [启动] AILab 低代码AI模型构建平台...
start "" venv\Scripts\pythonw.exe main.py
