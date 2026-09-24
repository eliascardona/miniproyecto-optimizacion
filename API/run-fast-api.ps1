$ErrorActionPreference = "Stop"

Write-Host "Instalando dependencias desde requirements.txt..." -ForegroundColor Cyan
pip install --no-cache-dir -r requirements.txt

Write-Host "Iniciando servidor Uvicorn en el puerto 8082..." -ForegroundColor Green
uvicorn app.main:app --port 8082