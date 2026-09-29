@echo off
call "%~dp0start.bat" --build-only
set "EXITCODE=%ERRORLEVEL%"
echo.
echo Index build finished with code %EXITCODE%.
pause
exit /b %EXITCODE%
