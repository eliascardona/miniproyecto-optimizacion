"""
Punto de entrada del FastAPI Worker.

El worker es un proceso persistente que:
  1. Verifica su entorno al iniciar (scripts, ngspice, workspace).
  2. Mantiene un asyncio.Lock para garantizar ejecucion secuencial
     (ngspice no es thread-safe, solo un subprocess a la vez).
  3. Expone endpoints internos para validacion y ejecucion de optimizacion.
  4. Recibe solicitudes exclusivamente del Express BFF (no del frontend directamente).

Arquitectura:
  Express (port 3000) -> FastAPI (port 8001) -> subprocess (Python script) -> ngspice
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.optimization import router
from app.state import ApplicationState, init_lock
from app.lifecycle import startup_sequence, shutdown_sequence


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager de FastAPI (lifespan).
    - Inicializa el asyncio.Lock para exclusion mutua.
    - Ejecuta la secuencia de verificacion de startup dentro del lock.
    - Si las verificaciones fallan, el worker no se marca como listo.
    - Al cerrarse, ejecuta shutdown_sequence.
    """
    init_lock()
    async with ApplicationState.lock:
        summary = await startup_sequence()
        ApplicationState.startup_summary = summary
        general = summary.get("general", {})
        ApplicationState.worker_ready = general.get("ready", False)
    yield
    await shutdown_sequence()


app = FastAPI(
    title="Optimization Worker",
    description="Worker persistente para optimizacion de filtros analogicos activos",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="")
