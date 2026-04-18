@echo off
setlocal
REM author: jf

set "BACKEND_DIR=%~dp0python-ai-backend"
cd /d "%BACKEND_DIR%" || (
  echo [ERROR] python-ai-backend directory not found.
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python is not installed or not in PATH.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
  )
)

set "VENV_PY=.venv\Scripts\python.exe"
set "PIP_INDEX_ARGS="

echo [2/5] Upgrading pip...
"%VENV_PY%" -m pip install --upgrade pip >nul 2>&1

echo [3/5] Installing core dependencies...
"%VENV_PY%" -m pip install -r requirements.txt && goto :core_deps_ok

echo [INFO] Default index failed, retrying with Tsinghua mirror...
set "PIP_INDEX_ARGS=-i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn"
"%VENV_PY%" -m pip install -r requirements.txt %PIP_INDEX_ARGS% && goto :core_deps_ok

echo [INFO] Tsinghua mirror failed, retrying with official PyPI...
set "PIP_INDEX_ARGS=-i https://pypi.org/simple --trusted-host pypi.org --trusted-host files.pythonhosted.org"
"%VENV_PY%" -m pip install -r requirements.txt %PIP_INDEX_ARGS% && goto :core_deps_ok

echo [ERROR] Failed to install core dependencies.
echo [ERROR] Please check proxy/firewall policy for Python outbound HTTPS.
pause
exit /b 1

:core_deps_ok
if exist "requirements-optional.txt" (
  echo [4/5] Installing optional AI dependencies...
  "%VENV_PY%" -m pip install -r requirements-optional.txt %PIP_INDEX_ARGS%
  if errorlevel 1 (
    echo [WARN] Optional AI dependencies installation failed.
    echo [WARN] Core backend will still run with placeholder capabilities.
  )
)

if not exist ".env" (
  echo [5/5] Creating .env from .env.example...
  copy /Y ".env.example" ".env" >nul
)

echo [6/6] Cleaning old listener on port 8999 if present...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-python-backend.ps1" -Port 8999
if errorlevel 1 (
  echo [ERROR] Failed to free port 8999.
  echo [HINT] If the script says the listener is stale, reboot Windows once and rerun this bat.
  pause
  exit /b 1
)

echo Starting python-ai-backend on http://127.0.0.1:8999
echo Runtime check: http://127.0.0.1:8999/health/runtime
"%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8999 --app-dir "%BACKEND_DIR%"

echo.
echo Backend process exited.
pause
exit /b %errorlevel%
