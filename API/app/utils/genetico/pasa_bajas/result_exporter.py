"""
Utilería: exportación de resultados (gráfica PNG + JSON de resumen),
filtro PASA-BAJAS.

Mismo contrato de entrada/salida que utils.genetico.pasa_altas.result_exporter
(mismos nombres de función, misma forma del dict de resultado), pero
internamente usa las métricas de pasa_bajas (calcular_metricas_fc aquí
devuelve una tupla de 5 elementos, no 4 — trae amp_dc además de amp_max).

No mantiene estado; recibe todo como argumentos.
"""
import base64
import traceback
from pathlib import Path

import numpy as np

from app.utils.matplotlib_seguro import serializado

from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12
from app.utils.genetico.pasa_bajas.metrics import calcular_metricas_fc, calcular_metricas_paso_aten


# ---------------------------------------------------------------------------
# Gráfica
# ---------------------------------------------------------------------------

@serializado
def graficar_resultado(
    archivo_datos: str,
    archivo_salida: str,
    modo: str,
    vs_valor: float,
    fc_objetivo: float | None = None,
    f_paso: float | None = None,
    f_aten: float | None = None,
    amp_paso_objetivo: float | None = None,
    amp_aten_objetivo: float | None = None,
) -> None:
    """Genera la gráfica de respuesta en frecuencia y la guarda en archivo_salida."""
    try:
        from matplotlib.figure import Figure
    except ImportError:
        print("[AVISO] No se pudo graficar: falta instalar matplotlib.")
        return

    try:
        datos = np.loadtxt(archivo_datos)
    except Exception as e:
        print(f"[AVISO] No se pudo leer '{archivo_datos}' para graficar: {e}")
        return

    frecuencias = datos[:, 0]
    amplitudes = datos[:, 1]

    # Figure directa (no pyplot): sin registro global de figuras ni backend
    # interactivo, seguro para los hilos de FastAPI y sin fugas de memoria.
    fig = Figure(figsize=(8, 5))
    ax = fig.subplots()

    if modo == "BASICO":
        fc_real, amp_dc, _, _, _ = calcular_metricas_fc(archivo_datos)
        nivel_fc = (amp_dc / np.sqrt(2)) if amp_dc else None

        ax.semilogx(frecuencias, amplitudes, color="#2563eb", linewidth=2, label="Respuesta simulada")
        if nivel_fc is not None:
            ax.axhline(nivel_fc, color="gray", linestyle="--", linewidth=1,
                       label=f"Nivel de corte (-3 dB) ({nivel_fc:.2f} V)")
        if fc_objetivo is not None:
            ax.axvline(fc_objetivo, color="#16a34a", linestyle="--", linewidth=1,
                       label=f"Fc objetivo ({fc_objetivo:.0f} Hz)")
        if fc_real:
            ax.axvline(fc_real, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"Fc obtenida ({fc_real:.0f} Hz)")

        ax.set_ylabel("Amplitud (V)")
        ax.set_title("Respuesta en frecuencia del filtro optimizado (MODO BASICO)")

    else:  # AVANZADO
        ax.semilogx(frecuencias, amplitudes, color="#2563eb", linewidth=2, label="Respuesta simulada")
        if amp_paso_objetivo is not None:
            ax.axhline(amp_paso_objetivo, color="#16a34a", linestyle="--", linewidth=1,
                       label=f"Objetivo banda de paso ({amp_paso_objetivo:.2f} V)")
        if amp_aten_objetivo is not None:
            ax.axhline(amp_aten_objetivo, color="#dc2626", linestyle="--", linewidth=1,
                       label=f"Objetivo banda de atenuación ({amp_aten_objetivo:.2f} V)")
        if f_paso is not None:
            ax.axvline(f_paso, color="#16a34a", linestyle=":", linewidth=1.5,
                       label=f"F_PASO ({f_paso:.0f} Hz)")
        if f_aten is not None:
            ax.axvline(f_aten, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"F_ATEN ({f_aten:.0f} Hz)")

        ax.set_ylabel("Amplitud (V)")
        ax.set_title("Respuesta en frecuencia del filtro optimizado (MODO AVANZADO)")

    ax.set_xlabel("Frecuencia (Hz)")
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(archivo_salida, dpi=150)
    print(f"\nGráfica guardada en: {archivo_salida}")


# ---------------------------------------------------------------------------
# JSON de resultado
# ---------------------------------------------------------------------------

def _codificar_imagen_base64(ruta_imagen: str) -> str | None:
    try:
        return base64.b64encode(Path(ruta_imagen).read_bytes()).decode("ascii")
    except Exception:
        print(f"[AVISO] No se pudo codificar la imagen '{ruta_imagen}' en base64:")
        traceback.print_exc()
        return None


def guardar_resultado_json(
    mejor_global: list[int],
    mejor_fit: float,
    componentes_ag: list[dict],
    modo: str,
    archivo_datos: str,
    archivo_grafica: str,
    f_paso: float | None = None,
    f_aten: float | None = None,
    fc_objetivo: float | None = None,
    amp_paso_objetivo: float | None = None,
    amp_aten_objetivo: float | None = None,
) -> dict:
    # fc_objetivo/amp_paso_objetivo/amp_aten_objetivo se aceptan sin usarse:
    # GeneticPreparationService.run_optimization() reenvía el mismo
    # ctx["frecuencias_ctx"] a graficar_resultado() (que sí los necesita
    # para dibujar las líneas objetivo) y a esta función, así que ambas
    # deben aceptar el mismo conjunto de claves aunque esta no las use.
    componentes_optimizados = [
        {
            "nombre": comp["nombre"],
            "tipo": comp["tipo"],
            "valor": float((SERIE_E12 if comp["tipo"] == "R" else SERIE_E6)[mejor_global[i]]),
            "conexion_tierra": comp["es_shunt"],
        }
        for i, comp in enumerate(componentes_ag)
    ]

    if modo == "BASICO":
        fc_real, _, _, _, _ = calcular_metricas_fc(archivo_datos)
        if fc_real is None:
            raise RuntimeError(
                "No se pudo calcular fc_real a partir de "
                f"'{archivo_datos}'. Revisa calcular_metricas_fc() (pasa_bajas)."
            )
        frecuencias_obtenidas = [{"clave": "fc_obtenida", "valor": float(fc_real)}]
    else:
        _, _, amp_paso, amp_aten, _, _ = calcular_metricas_paso_aten(
            archivo_datos, f_paso, f_aten
        )
        frecuencias_obtenidas = [
            {"clave": "amp_paso_obtenida", "valor": float(amp_paso)},
            {"clave": "amp_aten_obtenida", "valor": float(amp_aten)},
        ]

    grafica_b64 = _codificar_imagen_base64(archivo_grafica)
    if grafica_b64 is None:
        raise RuntimeError(
            f"No se pudo generar/leer la gráfica en '{archivo_grafica}'. "
            "Revisa que graficar_resultado() la haya guardado correctamente."
        )

    resultado = {
        "fitness": float(mejor_fit),
        "frecuencias_obtenidas": frecuencias_obtenidas,
        "componentes_optimizados": componentes_optimizados,
        "grafica_png_base64": grafica_b64,
    }

    return resultado