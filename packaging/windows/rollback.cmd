@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "PYTHON_EXE=%~dp0skill\parse-video\runtime\windows-x64\python\python.exe"
"%PYTHON_EXE%" "%~dp0tools\installer.py" rollback %*
exit /b %ERRORLEVEL%
