@echo off
cd /d "%~dp0"
title BFW-9000 - Empaquetar para compartir
powershell -NoProfile -ExecutionPolicy Bypass -File "herramientas\empaquetar.ps1"
pause
