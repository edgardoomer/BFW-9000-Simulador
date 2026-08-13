@echo off
cd /d "%~dp0"
title BFW-9000 - Detener (Docker)
echo.
echo   Apagando el contenedor...
echo.
docker compose down
echo.
echo   Listo. Su base de datos sigue en la carpeta  datos\
echo.
ping -n 4 127.0.0.1 >nul
