@echo off
REM ============================================
REM  37AC front-end stop (Nginx + PHP-CGI)
REM  Kills the LISTENING process on port 8000 by
REM  PID, then cleans up leftover nginx/php-cgi.
REM  Usage: stop-nginx.bat [-q]   (-q: no pause)
REM  ASCII-only file (cmd uses OEM codepage)
REM ============================================
setlocal enabledelayedexpansion

set PORT=8000
set KILLED=0

echo Stopping 37AC front-end...
echo.

REM --- 1. Kill the process LISTENING on port 8000 (by PID) ---
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%PORT% "') do (
    if not "%%p"=="0" (
        taskkill /PID %%p /F >nul 2>&1
        if !errorlevel!==0 (
            set KILLED=1
            echo   [OK] Killed PID %%p (port %PORT%)
        ) else (
            echo   [FAIL] Cannot kill PID %%p (access denied? run as administrator)
        )
    )
)

REM --- 2. Cleanup leftover Nginx / PHP-CGI instances ---
taskkill /IM nginx.exe /F >nul 2>&1
taskkill /IM php-cgi.exe /F >nul 2>&1

echo.
if "%KILLED%"=="1" (
    echo Port %PORT% released.
) else (
    echo Port %PORT% was not occupied.
)
echo Done.
if /i not "%~1"=="-q" pause
