@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions
title ComfyUI - RDNA1 (RX 5700 XT)

REM ============================================================
REM  ComfyUI launcher for AMD RDNA1 (gfx1010) on Windows + ROCm
REM  改这三行即可适配你自己的目录
REM ============================================================
set "AI_HOME=E:\AI"
set "COMFY_DIR=%AI_HOME%\ComfyUI"
set "PYTHON=%AI_HOME%\python_embeded\python.exe"

REM 有多张卡 / 有核显时指定用哪张：0 = 第一张，1 = 第二张
REM 选错会跑在核显上，速度差十倍
set "HIP_VISIBLE_DEVICES=0"

REM 可选：某些节点需要现场编译算子，指到 MSVC 工具链（没有就注释掉）
REM set "PATH=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231;%PATH%"

REM ============================================================

if not exist "%PYTHON%" (
    echo [ERROR] 找不到 Python: %PYTHON%
    echo         请修改脚本顶部的 AI_HOME / PYTHON
    pause
    exit /b 1
)
if not exist "%COMFY_DIR%\main.py" (
    echo [ERROR] 找不到 ComfyUI: %COMFY_DIR%
    pause
    exit /b 1
)

cd /d "%COMFY_DIR%"

echo ============================================================
echo   ComfyUI - RDNA1 / ROCm
echo   GPU device   : %HIP_VISIBLE_DEVICES%
echo   Python       : %PYTHON%
echo   ComfyUI      : %COMFY_DIR%
echo ============================================================
echo.

"%PYTHON%" main.py --enable-dynamic-vram --auto-launch --port 8188 %*

echo.
echo ComfyUI 已退出。
pause
