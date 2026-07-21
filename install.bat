@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Omni-Writer AI 一键安装
echo ==========================================
echo    Omni-Writer AI 一键安装向导
echo ==========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python！
    echo.
    echo 请先安装 Python 3.10 或更高版本：
    echo   1. 打开 https://www.python.org/downloads/
    echo   2. 下载并运行安装包
    echo   3. 安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [1/3] Python 已检测到：
python --version
echo.

REM 安装依赖
echo [2/3] 正在安装依赖（约 1-2 分钟）...
python -m pip install --upgrade pip -q
if errorlevel 1 goto pip_fail
pip install -r requirements.txt -q
if errorlevel 1 goto pip_fail
echo 依赖安装完成！
echo.
goto config

:pip_fail
echo [错误] 依赖安装失败，请检查网络后重试
pause
exit /b 1

:config
REM 配置向导
if exist config.yaml (
    echo [3/3] 检测到已有配置文件，跳过配置向导
) else (
    echo [3/3] 配置向导
    echo ------------------------------------------
    echo 你需要一个 DeepSeek API Key 才能开始创作。
    echo.
    echo 获取方式（免费注册，送 500 万 tokens）：
    echo   https://platform.deepseek.com/api_keys
    echo.
    set /p API_KEY="请粘贴你的 API Key（sk-开头，可留空稍后配置）: "
    if "!API_KEY!"=="" (
        echo 未输入 Key，已生成模板配置，请稍后手动编辑 config.yaml
        copy config.example.yaml config.yaml >nul
    ) else (
        python setup_config.py "!API_KEY!"
    )
)
echo.
echo ==========================================
echo    安装完成！双击 start.bat 启动
echo ==========================================
pause
