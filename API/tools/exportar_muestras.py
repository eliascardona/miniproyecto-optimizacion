"""
Herramienta de DESARROLLO: exporta muestras JSON REALES para probar clientes (p. ej. el frontend Java).

    python -m tools.exportar_muestras DESTINO               # esquema de los 4 filtros
    python -m tools.exportar_muestras DESTINO --respuesta   # ademas, una respuesta de /api/optimizar por filtro

Escribe DESTINO/esquema_<filtro>.json (exactamente lo que devuelve GET /api/circuitos/<filtro>) y, con
--respuesta, DESTINO/respuesta_<filtro>.json (el cuerpo de POST /api/optimizar). La respuesta se obtiene con
el controlador real pero con un ngspice SIMULADO (tests/_ngspice_falso.py): las curvas NO son fisicas, sirven
solo para probar el contrato; no hace falta tener ngspice instalado.
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import app.constants_repository as repositorio
from app.controller.individual_optimization_controller import IndividualOptimizationController
from app.utils.esquema import obtener_esquema

FILTROS = ["pasa_altas", "pasa_bajas", "pasa_banda", "rechaza_banda"]
NGSPICE_FALSO = [sys.executable, str(Path(__file__).resolve().parent.parent / "tests" / "_ngspice_falso.py")]

PARAMETROS_AG = [("tam_poblacion", 6), ("num_generaciones", 3), ("prob_cruce", 0.8),
                 ("prob_mutacion", 0.3), ("elitismo", 1), ("torneo_k", 2)]
FRECUENCIAS = {
    "pasa_altas": [("f_aten", 1000), ("f_paso", 10000)],
    "pasa_bajas": [("f_paso", 100), ("f_aten", 1000)],
    "pasa_banda": [("f_aten_1", 10), ("f_paso_1", 100), ("f_paso_2", 1000), ("f_aten_2", 10000)],
    "rechaza_banda": [("f_paso_1", 10), ("f_aten_1", 100), ("f_aten_2", 500), ("f_paso_2", 10000)],
}


def _kv(pares):
    return [{"clave": k, "valor": v} for k, v in pares]


def _guardar(ruta: Path, datos) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {ruta}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("destino")
    ap.add_argument("--respuesta", action="store_true")
    args = ap.parse_args()

    destino = Path(args.destino)
    destino.mkdir(parents=True, exist_ok=True)

    print("Esquemas:")
    for filtro in FILTROS:
        _guardar(destino / f"esquema_{filtro}.json", obtener_esquema(filtro))

    if args.respuesta:
        print("Respuestas de /api/optimizar (ngspice simulado):")
        original = repositorio.NGSPICE_EXE
        repositorio.NGSPICE_EXE = NGSPICE_FALSO
        try:
            controlador = IndividualOptimizationController()
            for filtro in FILTROS:
                peticion = SimpleNamespace(filtro=filtro, algoritmo="algoritmo_genetico", entorno={
                    "modo": "AVANZADO",
                    "entorno": {"v_fuente": 5, "r_fuente": 500, "r_carga": 500},
                    "barrido_ac": {"f_inicial": 1, "f_final": 100000},
                    "parametros_optimizador": _kv(PARAMETROS_AG),
                    "frecuencias": _kv(FRECUENCIAS[filtro]),
                })
                _guardar(destino / f"respuesta_{filtro}.json", controlador.optimize(peticion).model_dump())
        finally:
            repositorio.NGSPICE_EXE = original


if __name__ == "__main__":
    main()