@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Course Reader - Local Search
set "MODE=serve"
set "SEMANTIC=true"
:args
if "%~1"=="" goto args_done
if /I "%~1"=="--build-only" set "MODE=build"
if /I "%~1"=="--semantic" set "SEMANTIC=true"
shift
goto args
:args_done
set "BASEPY="
where py >nul 2>nul && set "BASEPY=py -3"
if not defined BASEPY where python >nul 2>nul && set "BASEPY=python"
if not defined BASEPY (
  echo Python was not found. Downloading a local runtime...
  set "LOCALPY=%CD%\.python"
  mkdir "%LOCALPY%" 2>nul
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile '$env:TEMP\course-python.zip'; Expand-Archive -Force '$env:TEMP\course-python.zip' '%CD%\.python'; Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%CD%\.python\get-pip.py'; (Get-Content '%CD%\.python\python312._pth') -replace '#import site','import site' | Set-Content '%CD%\.python\python312._pth'"
  set "BASEPY=\"%LOCALPY%\python.exe\""
)
if "%MODE%"=="build" (
  call %BASEPY% course_viewer.py --force-index
  exit /b %ERRORLEVEL%
)
REM Full startup creates a local venv, installs all requirements, builds, and serves.
if not exist ".venv\Scripts\python.exe" call %BASEPY% -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo Failed to create local Python environment.
  pause
  exit /b 1
)
set "PY=%CD%\.venv\Scripts\python.exe"
if "%SEMANTIC%"=="true" (
  "%PY%" -m pip install --upgrade pip --no-cache-dir
  "%PY%" -m pip install --no-cache-dir -r requirements.txt
  if errorlevel 1 echo Semantic model unavailable; SQLite FTS fallback remains active.
)
"%PY%" course_viewer.py --force-index --serve --port 8765
set "EXITCODE=%ERRORLEVEL%"
echo.
echo The Course Reader backend stopped with code %EXITCODE%.
pause
exit /b %EXITCODE%
