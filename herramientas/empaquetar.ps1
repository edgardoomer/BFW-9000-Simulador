# Arma un ZIP de BFW-9000 para compartir.
#
#   .venv         se excluye siempre: pesa 45 MB y es propia de cada maquina
#   db.sqlite3    se excluye por defecto: quien lo reciba arranca con los ejemplos
#   .env          SE INCLUYE por defecto, con la llave de oilpriceapi
#
# La llave es de plan gratuito y solo devuelve una cotizacion, asi que se
# comparte para que el analisis economico funcione sin configurar nada. Use
# -SinLlave si el paquete va a un sitio publico (GitHub, Drive abierto).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File herramientas\empaquetar.ps1
#   ... -ConDatos      incluye tambien sus proyectos
#   ... -SinLlave      no incluye .env; solo .env.example

param([switch]$ConDatos, [switch]$SinLlave)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$nombre  = "BFW-9000"
$escrit  = [Environment]::GetFolderPath('Desktop')
$destino = Join-Path $escrit "$nombre.zip"
$temp    = Join-Path $env:TEMP "$nombre-empaque"

Write-Host ""
Write-Host "  Empaquetando BFW-9000 para compartir..." -ForegroundColor Cyan
Write-Host ""

if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
$stage = Join-Path $temp $nombre
New-Item -ItemType Directory -Path $stage -Force | Out-Null

# --- carpetas y archivos que no viajan -------------------------------------
$dirsFuera = @('.venv', '__pycache__', '.git', '.claude', 'staticfiles', 'varios')
# Se excluye el .ico generado, pero NO la carpeta icono\ con el original.
$filesFuera = @('.env', '*.log', 'BFW-9000.ico', 'db.sqlite3', 'db.sqlite3-journal')

if (-not $ConDatos) { $dirsFuera += 'datos' }

# robocopy maneja exclusiones recursivas mejor que Copy-Item
$args = @('.', $stage, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP',
          '/XD') + $dirsFuera + @('/XF') + $filesFuera
$null = robocopy @args
if ($LASTEXITCODE -ge 8) { throw "robocopy fallo con codigo $LASTEXITCODE" }

# --- la llave de la API ------------------------------------------------------
# robocopy la excluyo arriba; aqui se agrega a proposito, para que quede a la
# vista en el codigo que compartirla es una decision y no un descuido.
$llaveIncluida = $false
if (-not $SinLlave -and (Test-Path ".env")) {
    Copy-Item ".env" (Join-Path $stage ".env")
    $llaveIncluida = $true
}

# --- comprimir --------------------------------------------------------------
# Si el ZIP anterior sigue abierto (el Explorador suele dejarlo tomado),
# se escribe con la fecha en el nombre en vez de fallar.
if (Test-Path $destino) {
    try {
        Remove-Item $destino -Force -ErrorAction Stop
    } catch {
        $destino = Join-Path $escrit ("{0}-{1}.zip" -f $nombre, (Get-Date -Format "yyyyMMdd-HHmm"))
        Write-Host "  El ZIP anterior estaba en uso; se guarda como $(Split-Path $destino -Leaf)" -ForegroundColor Yellow
    }
}
Compress-Archive -Path $stage -DestinationPath $destino -CompressionLevel Optimal -Force

$n = (Get-ChildItem $stage -Recurse -File -Force).Count
$mb = [math]::Round((Get-Item $destino).Length / 1MB, 2)
Remove-Item $temp -Recurse -Force

Write-Host "  Listo: $destino" -ForegroundColor Green
Write-Host "  $n archivos, $mb MB"
Write-Host ""
if ($llaveIncluida) {
    Write-Host "  INCLUYE su llave de oilpriceapi (.env)" -ForegroundColor Yellow
    Write-Host "  El analisis economico funcionara sin configurar nada." -ForegroundColor Yellow
    Write-Host "  Use -SinLlave si el paquete va a un sitio publico." -ForegroundColor Yellow
} else {
    Write-Host "  Sin llave: solo va .env.example. El analisis economico"
    Write-Host "  usara el precio de respaldo hasta que se configure una llave."
}
Write-Host ""
Write-Host "  No incluye:  .venv  db.sqlite3$(if(-not $ConDatos){'  datos\'})"
Write-Host "  Quien lo reciba solo descomprime y da doble clic a"
Write-Host "  'Iniciar BFW-9000.bat'  o  'Iniciar BFW-9000 (Docker).bat'."
Write-Host ""
