@echo off
rem 双击或在 cmd/PowerShell 里直接运行：
rem   scripts\run_today.cmd -Apply -Skip 七度雪乃,安守实里
rem   scripts\run_today.cmd -ListOnly
rem 作用：绕过 PowerShell 执行策略（Restricted）去调用 run_today.ps1
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_today.ps1" %*
endlocal
