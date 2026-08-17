"""
Verificaciones de startup del FastAPI Worker.

Se ejecutan una sola vez al arrancar el worker, antes de aceptar
solicitudes. Verifican que el entorno este listo:

  1. Directorio ALGORITMOS_DE_OPTIMIZACION existe.
  2. Los 8 scripts Python (4 filtros x 2 algoritmos) existen en disco.
  3. Los archivos auxiliares (filtro.cir, lm741.lib) existen.
  4. ngspice es accesible en NGSPICE_PATH.
  5. El directorio temporal (WORKSPACE_DIR) se puede crear.

Cada verificacion produce un resultado individual para que el health
endpoint pueda reportar el estado detallado.
"""

import os
import sys
import shutil
from pathlib import Path

from .config import NGSPICE_PATH, WORKSPACE_DIR, ALGOS_DIR, SCRIPT_MAP


def _check_path(label: str, path: str, must_be_file: bool = False) -> dict:
    """Verifica si un path existe (archivo o directorio)."""
    p = Path(path)
    exists = p.exists()
    if exists and must_be_file and not p.is_file():
        return {label: {"ok": False, "error": f"Existe pero no es un archivo: {path}"}}
    if not exists:
        return {label: {"ok": False, "error": f"No encontrado: {path}"}}
    return {label: {"ok": True}}


def _check_ngspice() -> dict:
    """Verifica que el ejecutable ngspice sea accesible."""
    result = _check_path("ngspice", NGSPICE_PATH, must_be_file=True)
    if not result["ngspice"]["ok"]:
        return result
    # Verifica que sea ejecutable (opcional en Windows, pero lo intentamos)
    try:
        if not os.access(NGSPICE_PATH, os.X_OK):
            result["ngspice"]["advertencia"] = (
                f"El archivo existe pero podria no tener permisos de ejecucion: {NGSPICE_PATH}"
            )
    except Exception:
        pass  # En Windows os.access no siempre funciona como en Unix
    return result


def _check_scripts() -> dict:
    """Verifica que los 8 scripts Python del SCRIPT_MAP existan."""
    resultados = {}
    todos_ok = True
    for tipo_filtro, alg_map in SCRIPT_MAP.items():
        for algoritmo, script_path in alg_map.items():
            key = f"script_{tipo_filtro}_{algoritmo}"
            r = _check_path(key, script_path, must_be_file=True)
            resultados[key] = r[key]
            if not r[key]["ok"]:
                todos_ok = False
    resultados["scripts_todos_presentes"] = {"ok": todos_ok}
    return resultados


def _check_aux_files(tipo_filtro: str, base_dir: str) -> dict:
    """Verifica que filtro.cir y lm741.lib existan en un directorio de filtro."""
    results = {}
    for fname in ("filtro.cir", "lm741.lib"):
        path = os.path.join(base_dir, fname)
        r = _check_path(f"{fname} ({tipo_filtro})", path, must_be_file=True)
        results.update(r)
    return results


def _check_all_aux_files() -> dict:
    """Verifica filtro.cir y lm741.lib para los 8 directorios de filtro."""
    todos_ok = True
    for tipo_filtro, alg_map in SCRIPT_MAP.items():
        # Ambos algoritmos (AG y PSO) usan los mismos directorios de filtro
        for algoritmo, script_path in alg_map.items():
            base_dir = os.path.dirname(script_path)
            r = _check_aux_files(f"{tipo_filtro}/{algoritmo}", base_dir)
            for k, v in r.items():
                if not v.get("ok"):
                    todos_ok = False
    return {
        "archivos_auxiliares_presentes": {"ok": todos_ok}
    }


def _check_workspace() -> dict:
    """Verifica que WORKSPACE_DIR se pueda crear."""
    try:
        Path(WORKSPACE_DIR).mkdir(parents=True, exist_ok=True)
        test_file = Path(WORKSPACE_DIR) / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        return {"workspace": {"ok": True, "path": str(Path(WORKSPACE_DIR).resolve())}}
    except Exception as e:
        return {"workspace": {"ok": False, "error": str(e)}}


async def startup_sequence() -> dict:
    """
    Ejecuta todas las verificaciones de startup.

    Returns:
        dict: Resumen completo con el resultado de cada verificacion.
              Incluye la clave "general" con "ready" (bool) y "mensaje".
    """
    print("=" * 60)
    print("  Inicializando FastAPI Optimization Worker...")
    print("=" * 60)

    resultados = {}
    resultados["entorno"] = _check_path("ALGORITMOS_DE_OPTIMIZACION", ALGOS_DIR)
    resultados.update(_check_scripts())
    resultados.update(_check_all_aux_files())
    resultados.update(_check_ngspice())
    resultados.update(_check_workspace())

    # Determina estado general
    componentes_ok = [
        v.get("ok", False)
        for v in resultados.values()
        if isinstance(v, dict) and "ok" in v
    ]
    worker_ready = all(componentes_ok) if componentes_ok else False

    print(f"  Worker listo: {worker_ready}")
    for key, val in resultados.items():
        if isinstance(val, dict) and "ok" in val:
            estado = "OK" if val["ok"] else "FALL"
            print(f"    {estado}  {key}")
            if not val["ok"] and "error" in val:
                print(f"         Error: {val['error']}")

    return {
        "general": {
            "ready": worker_ready,
            "mensaje": (
                "Worker listo para recibir solicitudes"
                if worker_ready
                else "Worker en estado incompleto - revisar logs"
            ),
        },
        "componentes": resultados,
    }


async def shutdown_sequence():
    """Operaciones de cierre controlado del worker."""
    print("=" * 60)
    print("  Finalizando FastAPI Optimization Worker...")
    print("=" * 60)
