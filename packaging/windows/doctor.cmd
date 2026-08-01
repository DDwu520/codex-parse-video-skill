@echo off
setlocal
chcp 65001 >nul
"%~dp0skill\parse-video\run.cmd" doctor %*
exit /b %ERRORLEVEL%
