"""
Ejecutor de scripts Python de optimizacion.

Crea un workspace temporal, escribe config.json, ejecuta el script
correspondiente (via subprocess o import directo si tiene GeneticWorker).

Flujo:
  1. Copia el script Python al workspace temporal.
  2. Copia filtro.cir y lm741.lib.
  3. Ejecuta el script (directo o subprocess).
  4. Obtiene resultado.json (o el dict directamente si es import directo).
  5. Elimina el workspace temporal (limpieza).
"""

import asyncio
import importlib.util
import subprocess
import os
import sys
import json
import tempfile
import traceback
import shutil
from typing import Dict, Any

from ..config import SCRIPT_MAP, NGSPICE_PATH, WORKSPACE_DIR


async def ejecutar_script(
    config_json: Dict[str, Any],
    tipo_filtro: str,
    algoritmo: str,
) -> Dict[str, Any]:
    """
    Ejecuta el script de optimizacion en un workspace temporal.

    Si el script exporta una clase GeneticWorker, la importa directamente
    y ejecuta compile+fit+predict en el mismo proceso (mas eficiente).
    En caso contrario, ejecuta el script via subprocess como antes.
    """
    script_path = SCRIPT_MAP.get(tipo_filtro, {}).get(algoritmo)
    if not script_path or not os.path.exists(script_path):
        return {
            "estado": "ERROR",
            "error": f"Script no encontrado para {tipo_filtro}/{algoritmo}: {script_path}",
        }

    # Intenta import directo si el script tiene GeneticWorker
    WorkerClass = _cargar_clase_worker(script_path)
    if WorkerClass is not None:
        return await _ejecutar_worker_directo(config_json, script_path, WorkerClass)

    # Fallback a subprocess
    return await _ejecutar_subprocess(config_json, script_path)


def _cargar_clase_worker(script_path: str):
    """Importa dinamicamente GeneticWorker desde un archivo script."""
    try:
        nombre_modulo = "worker_" + os.path.basename(script_path).replace(".", "_")
        spec = importlib.util.spec_from_file_location(nombre_modulo, script_path)
        if spec is None:
            return None
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return getattr(modulo, "GeneticWorker", None)
    except BaseException:
        return None


async def _ejecutar_worker_directo(
    config_json: Dict[str, Any],
    script_path: str,
    WorkerClass,
) -> Dict[str, Any]:
    """
    Ejecuta GeneticWorker por import directo (sin subprocess).
    Corre en un hilo separado para no bloquear el event loop.
    """
    dir_origen = os.path.dirname(script_path)
    workspace = tempfile.mkdtemp(prefix="opt_")

    try:
        for extra in ["filtro.cir", "lm741.lib"]:
            src = os.path.join(dir_origen, extra)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(workspace, extra))

        def _run():
            worker = WorkerClass(workspace_dir=workspace)
            worker.compile(config=config_json, ngspice_path=NGSPICE_PATH)
            worker.fit()
            resultado = worker.predict()
            resultado["estado"] = "TERMINADO"
            return resultado

        return await asyncio.to_thread(_run)

    except Exception:
        return {"estado": "ERROR", "error": traceback.format_exc()}

    finally:
        try:
            shutil.rmtree(workspace, ignore_errors=True)
        except Exception:
            pass


async def _ejecutar_subprocess(
    config_json: Dict[str, Any],
    script_path: str,
) -> Dict[str, Any]:
    """
    Ejecuta un script Python como subprocess (flujo original).
    Copia el script al workspace, escribe config.json, ejecuta y lee resultado.json.
    """
    workspace = tempfile.mkdtemp(prefix="opt_")

    try:
        script_dest = os.path.join(workspace, os.path.basename(script_path))
        dir_origen = os.path.dirname(script_path)
        shutil.copy2(script_path, script_dest)

        for extra in ["filtro.cir", "lm741.lib"]:
            src = os.path.join(dir_origen, extra)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(workspace, extra))

        with open(script_dest, "r", encoding="utf-8") as f:
            contenido = f.read()
        contenido = contenido.replace(
            r"C:\Users\luis_\Desktop\Spice64\bin\ngspice.exe",
            NGSPICE_PATH
        )
        with open(script_dest, "w", encoding="utf-8") as f:
            f.write(contenido)

        config_path = os.path.join(workspace, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_json, f, ensure_ascii=False, indent=2)

        env = os.environ.copy()
        env["PATH"] = os.path.dirname(NGSPICE_PATH) + os.pathsep + env.get("PATH", "")
        env["PYTHONIOENCODING"] = "utf-8"

        result = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-u", os.path.basename(script_path)],
            cwd=workspace,
            env=env,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            return {
                "estado": "ERROR",
                "error": f"Script finalizo con codigo {result.returncode}: {error_msg}",
            }

        resultado_path = os.path.join(workspace, "resultado.json")
        if not os.path.exists(resultado_path):
            return {
                "estado": "ERROR",
                "error": "El script no genero resultado.json",
            }

        with open(resultado_path, "r", encoding="utf-8") as f:
            resultado = json.load(f)

        resultado["estado"] = "TERMINADO"
        return resultado

    except Exception:
        return {"estado": "ERROR", "error": traceback.format_exc()}

    finally:
        try:
            shutil.rmtree(workspace, ignore_errors=True)
        except Exception:
            pass
