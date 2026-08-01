@echo off
setlocal
chcp 65001 >nul
set "PYTHON_EXE=%~dp0skill\parse-video\runtime\windows-x64\python\python.exe"
if not exist "%PYTHON_EXE%" (
  echo [parse-video] 分享包不完整，缺少内置 Python。
  exit /b 2
)
"%PYTHON_EXE%" "%~dp0tools\installer.py" install --source "%~dp0skill\parse-video" %*
exit /b %ERRORLEVEL%
