# ====================================================================
# run.ps1 — Script de arranque del FastAPI Worker
# ====================================================================
#
# Inicia el worker de optimizacion de forma independiente.
# Util para desarrollo o debugging del worker sin levantar Express.
#
# Ejecutar desde fastapi-worker/:
#   .\run.ps1
# ====================================================================

Write-Host "=== Iniciando FastAPI Optimization Worker ==="
$ErrorActionPreference = "Stop"

Set-Location "$PSScriptRoot"

# Crear entorno virtual si no existe
if (-not (Test-Path ".venv")) {
    Write-Host "Creando entorno virtual..."
    python -m venv .venv
}

# Activar entorno virtual e instalar dependencias
Write-Host "Activando entorno virtual..."
& ".\.venv\Scripts\Activate.ps1"

Write-Host "Instalando dependencias..."
pip install -r requirements.txt -q

# Iniciar uvicorn con auto-reload para desarrollo
Write-Host "Iniciando worker en puerto 8001..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
