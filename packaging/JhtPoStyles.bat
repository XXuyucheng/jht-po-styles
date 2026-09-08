@echo off
REM Double-click helper: keep the console open after errors.
cd /d "%~dp0"
echo Starting JhtPoStyles...
echo If startup fails, see %%LOCALAPPDATA%%\jht-po-styles\crash.log
echo.
JhtPoStyles.exe
echo.
echo Exit code: %ERRORLEVEL%
pause
