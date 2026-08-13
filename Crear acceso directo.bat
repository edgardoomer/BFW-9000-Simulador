@echo off
cd /d "%~dp0"
title BFW-9000 - Crear acceso directo
echo.
echo   Creando el acceso directo en el Escritorio...
echo.

REM Regenera el icono a partir de logo.png si hay entorno virtual
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe herramientas\crear_icono.py
    echo.
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$carpeta = (Get-Location).Path;" ^
  "$escritorio = [Environment]::GetFolderPath('Desktop');" ^
  "$destino = Join-Path $escritorio 'BFW-9000.lnk';" ^
  "$w = New-Object -ComObject WScript.Shell;" ^
  "$s = $w.CreateShortcut($destino);" ^
  "$s.TargetPath = Join-Path $carpeta 'Iniciar BFW-9000.bat';" ^
  "$s.WorkingDirectory = $carpeta;" ^
  "$s.Description = 'BFW-9000 - Simulador de Waterflooding (Buckley y Leverett)';" ^
  "$ico = Join-Path $carpeta 'BFW-9000.ico';" ^
  "if (Test-Path $ico) { $s.IconLocation = $ico }" ^
  "$s.WindowStyle = 7;" ^
  "$s.Save();" ^
  "Write-Host ('   Acceso directo creado: ' + $destino)"

echo.
echo   Puede arrastrarlo a la barra de tareas o al menu Inicio.
echo.
pause
