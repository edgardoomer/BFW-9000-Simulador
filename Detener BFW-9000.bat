@echo off
cd /d "%~dp0"
title BFW-9000 - Detener
echo.
echo   Apagando BFW-9000...
echo.

REM Cierra solo el proceso que escucha en el puerto 8017, no todo Python.
set "ENCONTRADO="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"TCP.*:8017 .*LISTENING"') do (
    taskkill /F /PID %%P >nul 2>nul
    if not errorlevel 1 (
        echo   Servidor detenido ^(PID %%P^).
        set "ENCONTRADO=1"
    )
)

if not defined ENCONTRADO (
    echo   No habia ningun servidor escuchando en el puerto 8017.
)

echo.
ping -n 3 127.0.0.1 >nul
