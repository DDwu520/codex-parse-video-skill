@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "PYTHON_EXE=%~dp0runtime\windows-x64\python\python.exe"
if not exist "%PYTHON_EXE%" (
  echo [parse-video] 内置 Python 不存在：%PYTHON_EXE%
  exit /b 2
)
"%PYTHON_EXE%" "%~dp0scripts\parse_video.py" %*
exit /b %ERRORLEVEL%
