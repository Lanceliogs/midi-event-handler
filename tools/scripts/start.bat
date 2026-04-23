@echo off
setlocal
cd /d "%~dp0"
python\python.exe -m midi_event_handler.launcher %*
