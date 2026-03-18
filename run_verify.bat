@echo off
set "PYTHON_PATH=C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe"
if exist "%PYTHON_PATH%" (
    echo [INFO] Found Python at %PYTHON_PATH%
    "%PYTHON_PATH%" verify_fix.py
) else (
    echo [ERROR] Python not found at %PYTHON_PATH%
    echo [INFO] Trying 'python' directly...
    python verify_fix.py
)
pause
