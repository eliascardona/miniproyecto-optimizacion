# ====================================================================
# run.ps1 — Script de arranque del sistema completo
# ====================================================================
#
# Inicia los 3 componentes del sistema en orden:
#   1. Verifica que PostgreSQL este corriendo (puerto 5432).
#   2. Inicia el FastAPI Worker en una ventana separada (puerto 8000).
#   3. Inicia el Express API en una ventana separada (puerto 3000).
#
# Ejecutar desde la raiz del proyecto:
#   .\run.ps1
# ====================================================================

Write-Host ""
Write-Host "============================================"
Write-Host "  Sistema de Optimizacion de Filtros"
Write-Host "============================================"
Write-Host ""

$root = $PSScriptRoot

# 1. Verificar que PostgreSQL este corriendo
Write-Host "[1/4] Verificando PostgreSQL..."
$pgReady = & pg_isready -h localhost -p 5432 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: PostgreSQL no esta corriendo. Inicia el servicio PostgreSQL primero." -ForegroundColor Red
    exit 1
}
Write-Host "  PostgreSQL OK" -ForegroundColor Green

# 2. Iniciar FastAPI Worker en ventana separada
# El worker corre sobre uvicorn con --reload para desarrollo.
# Se espera hasta 15 segundos a que responda el endpoint /health.
Write-Host "[2/4] Iniciando FastAPI Worker (puerto 8001)..."
$workerDir = Join-Path $root "fastapi-worker"
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$workerDir'; & '.\.venv\Scripts\Activate.ps1'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
) -WindowStyle Minimized

Write-Host "  Esperando a que el worker este listo..."
$maxWait = 15
$waited = 0
while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    $waited++
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method GET -ErrorAction Stop
        if ($health.status -eq "UP") {
            Write-Host "  FastAPI Worker OK" -ForegroundColor Green
            break
        }
    } catch {
        # worker not ready yet
    }
}
if ($waited -ge $maxWait) {
    Write-Host "  WARNING: El worker no respondio en $maxWait segundos. Continuando de todas formas..." -ForegroundColor Yellow
}

# 3. Iniciar Express API en ventana separada
# Express corre sobre node directly (sin --reload).
Write-Host "[3/4] Iniciando Express API (puerto 3000)..."
$apiDir = Join-Path $root "API"
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$apiDir'; node src/index.js"
) -WindowStyle Minimized

Start-Sleep -Seconds 2
Write-Host "  Express API OK" -ForegroundColor Green

# 4. Resumen de endpoints disponibles
Write-Host "[4/4] Sistema iniciado" -ForegroundColor Green
Write-Host ""
Write-Host "============================================"
Write-Host "  Express API:   http://localhost:3000"
Write-Host "  FastAPI Worker: http://localhost:8001"
Write-Host "  Docs FastAPI:  http://localhost:8001/docs"
Write-Host "============================================"
Write-Host ""
Write-Host "Endpoints principales:"
Write-Host "  GET  /api/health"
Write-Host "  GET  /api/plantillas"
Write-Host "  POST /api/ejecuciones"
Write-Host "  POST /api/ejecuciones/:id/ejecutar"
Write-Host ""
Write-Host "Presiona Ctrl+C para detener. Las ventanas del worker y API siguen abiertas."
