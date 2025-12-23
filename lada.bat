@echo off
chcp 65001 > nul

:: 激活虚拟环境
if exist "%~dp0.venv312\Scripts\activate.bat" (
    call "%~dp0.venv312\Scripts\activate.bat"
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0lada.ps1"
pause