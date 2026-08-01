@echo off
setlocal
chcp 65001 >nul
set "PYTHON_EXE=%~dp0skill\parse-video\runtime\windows-x64\python\python.exe"
"%PYTHON_EXE%" "%~dp0tools\verify_manifest.py" "%~dp0" --json
exit /b %ERRORLEVEL%
