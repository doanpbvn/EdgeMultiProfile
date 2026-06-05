@echo off
REM ============================================================
REM  Build Edge Multi Profile into a .exe file (PyInstaller)
REM ============================================================
setlocal

echo [1/4] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [2/4] Generating version info...
python tools\make_version.py
if errorlevel 1 goto :error

echo [3/4] Packaging with PyInstaller...
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name "EdgeMultiProfile" ^
  --icon "assets\icon.ico" ^
  --version-file "version_info.txt" ^
  --paths src ^
  --collect-submodules edge_multi ^
  --collect-all customtkinter ^
  main.py
if errorlevel 1 goto :error

echo [4/4] Done!
echo The exe is located at: dist\EdgeMultiProfile.exe
goto :eof

:error
echo.
echo *** Build failed. See the error message above. ***
exit /b 1
