@echo off
setlocal
cd /d "%~dp0"
title BFW-9000 - Docker
color 0B

set "PUERTO=8017"
set "URL=http://localhost:%PUERTO%/"

echo.
echo   ============================================================
echo      BFW-9000  .  Simulador de Waterflooding   [Docker]
echo   ============================================================
echo.

REM ------------------------------------------------------ 1. hay Docker?
docker version >nul 2>nul
if errorlevel 1 (
    echo   ERROR: Docker no responde.
    echo.
    echo   Abra Docker Desktop y espere a que el icono de la ballena
    echo   deje de animarse; luego vuelva a ejecutar este archivo.
    echo.
    echo   Si no lo tiene instalado:
    echo     https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------------- 2. ya corre?
curl -s -o nul --max-time 2 "%URL%proyectos/" >nul 2>nul
if not errorlevel 1 (
    echo   El contenedor ya estaba encendido. Abriendo el navegador...
    start "" "%URL%"
    ping -n 3 127.0.0.1 >nul
    exit /b 0
)

REM ---------------------------------------------- 3. construir y levantar
if not exist "datos" mkdir datos
echo   Construyendo la imagen y levantando el contenedor.
echo   La primera vez tarda varios minutos; despues es inmediato.
echo.
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo   ERROR al levantar el contenedor. Detalle arriba.
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------------- 4. esperar
echo.
echo   Esperando a que el simulador responda...
set /a intentos=0
:esperar
set /a intentos+=1
curl -s -o nul --max-time 2 "%URL%proyectos/" >nul 2>nul
if not errorlevel 1 goto :abrir
if %intentos% geq 60 goto :fallo
ping -n 2 127.0.0.1 >nul
goto :esperar

:abrir
start "" "%URL%"
echo.
echo   ------------------------------------------------------------
echo     BFW-9000 corriendo en  %URL%
echo.
echo     Su base de datos esta en la carpeta  datos\
echo     Para apagarlo use  "Detener BFW-9000 (Docker).bat"
echo   ------------------------------------------------------------
echo.
ping -n 6 127.0.0.1 >nul
exit /b 0

:fallo
echo.
echo   El contenedor no respondio. Registro de los ultimos errores:
echo.
docker compose logs --tail 30
echo.
pause
exit /b 1
