@echo off
set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run_selector.ps1" -Mode copy -Preset fast -DevicePreset cpu
