"""
Rutas del FastAPI Worker.

Endpoints:
  GET  /health    - Estado del worker.
  POST /validate  - Valida configuracion (Nivel 2) sin ejecutar.
  POST /optimize  - Valida + ejecuta el algoritmo de optimizacion.

Todos los endpoints reciben tipo_filtro y algoritmo para seleccionar
el script correcto, pero estos campos NO se incluyen en el config.json
que se escribe en disco para el script Python.
"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import ExecutionRequest, ValidationRequest
from app.services.validation import validar_config_nivel2
from app.services.config_builder import build_config_json
from app.services.script_runner import ejecutar_script

from app.state import ApplicationState

router = APIRouter()


@router.get("/health")
async def health():
    """Verifica que el worker este inicializado y listo."""
    return {
        "status": "UP" if ApplicationState.worker_ready else "DOWN",
        "worker_ready": ApplicationState.worker_ready,
    }


@router.post("/validate")
async def validate(req: ValidationRequest):
    """
    Valida la configuracion usando las reglas Nivel 2:
      - Orden de frecuencias por tipo de filtro y modo.
      - Margen de una decade respecto al barrido AC.
      - Hiperparametros del algoritmo (AG o PSO).
    No ejecuta nada, solo valida.
    """
    config = req.configuracion.model_dump()
    config_json = build_config_json(config)
    valido, errores = validar_config_nivel2(req.tipo_filtro, req.algoritmo, config_json)

    if not valido:
        raise HTTPException(status_code=400, detail={
            "error": "Error de validacion Nivel 2",
            "detalles": errores,
        })

    return {"valido": True, "mensaje": "Configuracion valida"}


@router.post("/optimize")
async def optimize(req: ExecutionRequest):
    """
    Flujo completo de optimizacion:
      1. Valida Nivel 2 (ordenes, decadas, hiperparametros).
      2. Genera config.json limpio (sin tipo_filtro ni algoritmo).
      3. Ejecuta el script Python via subprocess dentro del asyncio.Lock.
      4. Retorna el resultado (fitness, componentes, grafica base64).

    El asyncio.Lock garantiza que solo un subprocess de ngspice
    se ejecute a la vez (exclusion mutua).
    """
    config = req.configuracion.model_dump()
    config_json = build_config_json(config)

    valido, errores = validar_config_nivel2(req.tipo_filtro, req.algoritmo, config_json)
    if not valido:
        raise HTTPException(status_code=400, detail={
            "error": "Error de validacion Nivel 2",
            "detalles": errores,
        })

    # Ejecucion protegida por lock (solo un subprocess a la vez)
    async with ApplicationState.lock:
        resultado = await ejecutar_script(config_json, req.tipo_filtro, req.algoritmo)

    if resultado.get("estado") == "ERROR":
        raise HTTPException(status_code=500, detail={
            "error": "Error durante la ejecucion del algoritmo",
            "detalles": resultado.get("error", "Error desconocido"),
        })

    return resultado
