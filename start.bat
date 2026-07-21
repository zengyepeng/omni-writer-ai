@echo off
chcp 65001 >nul
title Omni-Writer AI
echo ==========================================
echo    启动 Omni-Writer AI
echo ==========================================
echo.
echo 选择启动模式：
echo   1. Web 控制台（推荐，浏览器操作）
echo   2. CLI 命令行（终端操作）
echo   3. Demo 体验模式（无需 API Key，仅看界面）
echo.
set /p MODE="请选择 (1/2/3，默认 1): "

if "%MODE%"=="2" (
    echo.
    echo 启动 CLI 模式...
    python main.py
) else if "%MODE%"=="3" (
    echo.
    echo 启动 Demo 体验模式（无需 API Key）...
    python demo_mode.py
) else (
    echo.
    echo 启动 Web 控制台...
    echo 浏览器将自动打开 http://127.0.0.1:7860
    start "" "http://127.0.0.1:7860"
    python web_ui.py
)
pause
