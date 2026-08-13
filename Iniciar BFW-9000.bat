@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title BFW-9000 - Simulador de Waterflooding
color 0B

set "PUERTO=8017"
set "URL=http://localhost:%PUERTO%/"
set "PY=.venv\Scripts\python.exe"

echo.
echo   ============================================================
echo      BFW-9000  .  Simulador de Waterflooding
echo      Metodo Buckley ^& Leverett
echo   ============================================================
echo.

REM ---------------------------------------------------------------- 1. venv
if not exist "%PY%" (
    echo   [1/4] Primera vez: creando el entorno virtual...
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv .venv
    ) else (
        py -3 -m venv .venv
    )
    if not exist "%PY%" (
        echo.
        echo   ERROR: no se pudo crear el entorno virtual.
        echo   Instale Python 3.11 o superior desde https://www.python.org/downloads/
        echo   y marque "Add Python to PATH" durante la instalacion.
        echo.
        pause
        exit /b 1
    )
    echo   [1/4] Instalando dependencias, esto tarda un minuto...
    "%PY%" -m pip install --quiet --upgrade pip
    "%PY%" -m pip install --quiet -r requirements.txt
) else (
    echo   [1/4] Entorno virtual listo.
)

REM ------------------------------------------------------------ 2. ya corre?
curl -s -o nul --max-time 2 "%URL%proyectos/" >nul 2>nul
if not errorlevel 1 (
    echo   [2/4] El servidor ya estaba encendido.
    echo   [4/4] Abriendo el navegador...
    start "" "%URL%"
    echo.
    echo   Listo. Puede cerrar esta ventana.
    ping -n 4 127.0.0.1 >nul
    exit /b 0
)

REM ------------------------------------------------------- 3. base de datos
echo   [2/4] Preparando la base de datos...
"%PY%" manage.py migrate --noinput >nul 2>nul
if errorlevel 1 (
    echo.
    echo   ERROR al preparar la base de datos. Detalle:
    "%PY%" manage.py migrate --noinput
    echo.
    pause
    exit /b 1
)

if not exist "db.sqlite3" goto :sembrar
for /f %%N in ('"%PY%" -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','blsim.settings');django.setup();from core.models import Proyecto;print(Proyecto.objects.count())" 2^>nul') do set "NPROY=%%N"
if "%NPROY%"=="0" goto :sembrar
goto :servidor

:sembrar
echo         Cargando los proyectos de ejemplo...
"%PY%" manage.py cargar_ejemplos >nul 2>nul

REM ------------------------------------------------------------ 4. servidor
:servidor
echo   [3/4] Encendiendo el servidor en el puerto %PUERTO%...
start "BFW-9000 servidor" /min "%PY%" manage.py runserver %PUERTO% --noreload

set /a intentos=0
:esperar
set /a intentos+=1
curl -s -o nul --max-time 1 "%URL%proyectos/" >nul 2>nul
if not errorlevel 1 goto :abrir
if %intentos% geq 40 goto :fallo
ping -n 2 127.0.0.1 >nul
goto :esperar

:abrir
echo   [4/4] Abriendo el navegador...
start "" "%URL%"
echo.
echo   ------------------------------------------------------------
echo     BFW-9000 corriendo en  %URL%
echo.
echo     El servidor quedo en una ventana aparte, minimizada.
echo     Para apagarlo use  "Detener BFW-9000.bat"
echo   ------------------------------------------------------------
echo.
ping -n 6 127.0.0.1 >nul
exit /b 0

:fallo
echo.
echo   ERROR: el servidor no respondio despues de 40 segundos.
echo   Revise la ventana "BFW-9000 servidor" para ver el detalle.
echo.
pause
exit /b 1
