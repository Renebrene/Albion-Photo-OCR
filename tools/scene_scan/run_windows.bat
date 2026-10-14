@echo off
setlocal
set "REPO_ROOT=%~dp0..\.."
set "PYTHONPATH=%REPO_ROOT%;%PYTHONPATH%"

if exist "%REPO_ROOT%\.venv-scene-scan\Scripts\python.exe" (
  "%REPO_ROOT%\.venv-scene-scan\Scripts\python.exe" -m tools.scene_scan %*
  exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.12 launcher not found. Install Python 3.12, then follow tools\scene_scan\README.md.
  exit /b 2
)

py -3.12 -m tools.scene_scan %*
exit /b %ERRORLEVEL%
