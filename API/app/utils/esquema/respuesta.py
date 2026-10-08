"""
Datos extra que se agregan a la respuesta de /api/optimizar, para que el cliente pueda DIBUJAR el
resultado sin adivinar la topología:

  · esquema               el circuito optimizado, con los valores finales de cada componente y los
                          del entorno de la petición (Vs, Rs, Rl, Vpp, Vnn);
  · respuesta_frecuencia  la curva (frecuencia, Vout) del circuito optimizado.

Regla de oro: NADA de esto puede descartar una optimización terminada. Cada parte se construye por
separado y, si falla, queda en None (el esquema además explica por qué en `esquema_error`).
"""
import traceback

import numpy as np

from .servicio import obtener_esquema

MAX_PUNTOS_RESPUESTA = 2000

# Nombre del elemento en el .cir  ->  clave del contexto de ejecución (_build_run_context)
_ENTORNO = {"Vs": "vs_valor", "Rs": "rs_valor", "Rl": "rl_valor", "Vpp": "vpp_valor", "Vnn": "vnn_valor"}


def _cifras(x: float) -> float:
    """7 cifras significativas: sobra para dibujar y recorta el JSON."""
    return float(f"{x:.7g}")


def leer_respuesta_frecuencia(archivo_datos: str, max_puntos: int = MAX_PUNTOS_RESPUESTA) -> dict:
    """Lee el datos_filtro.txt de ngspice (frecuencia, |Vout|) y lo devuelve como dos listas."""
    # ndmin=2: un archivo de UNA columna con varias filas no debe confundirse con UNA fila de varias columnas
    datos = np.loadtxt(archivo_datos, ndmin=2)
    if datos.shape[1] < 2:
        raise ValueError(f"'{archivo_datos}' no tiene al menos dos columnas (frecuencia, amplitud).")

    f, v = datos[:, 0], datos[:, 1]
    validos = np.isfinite(f) & np.isfinite(v)
    f, v = f[validos], v[validos]
    if f.size == 0:
        raise ValueError(f"'{archivo_datos}' no tiene puntos válidos.")

    if f.size > max_puntos:                       # submuestreo uniforme que conserva los extremos
        indices = np.unique(np.round(np.linspace(0, f.size - 1, max_puntos)).astype(int))
        f, v = f[indices], v[indices]

    return {"frecuencia_hz": [_cifras(x) for x in f], "vout": [_cifras(x) for x in v]}


def valores_de_componentes(resultado: dict) -> dict:
    return {c["nombre"]: c["valor"] for c in resultado["componentes_optimizados"]}


def valores_de_entorno(entorno: dict) -> dict:
    return {nombre: entorno[clave] for nombre, clave in _ENTORNO.items() if clave in entorno}


def extras_de_respuesta(filtro: str, resultado: dict, entorno: dict, archivo_datos: str) -> dict:
    """Devuelve {"esquema", "esquema_error", "respuesta_frecuencia"}; nunca lanza."""
    extras = {"esquema": None, "esquema_error": None, "respuesta_frecuencia": None}

    try:
        extras["esquema"] = obtener_esquema(
            filtro,
            valores=valores_de_componentes(resultado),
            valores_opcionales=valores_de_entorno(entorno),
        )
    except Exception as e:                                   # noqa: BLE001 -- ver "regla de oro"
        extras["esquema_error"] = f"{type(e).__name__}: {e}"
        print(f"[AVISO] No se pudo construir el esquema de '{filtro}':")
        traceback.print_exc()

    try:
        extras["respuesta_frecuencia"] = leer_respuesta_frecuencia(archivo_datos)
    except Exception as e:                                   # noqa: BLE001
        print(f"[AVISO] No se pudo leer la respuesta en frecuencia de '{archivo_datos}': {e}")

    return extras