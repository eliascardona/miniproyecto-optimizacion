"""
Utilería: exportación de resultados (gráfica PNG + JSON de resumen),
filtro RECHAZA-BANDA.

Mismo contrato que pasa_banda (BASICO reporta 2 Fc, AVANZADO reporta 4
amplitudes), con las métricas propias de rechaza_banda (metrics.py).

No mantiene estado; recibe todo como argumentos.
"""
import base64
import traceback
from pathlib import Path

import numpy as np

from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12
from app.utils.genetico.rechaza_banda.metrics import calcular_metricas_fc, calcular_metricas_paso_aten


# ---------------------------------------------------------------------------
# Gráfica
# ---------------------------------------------------------------------------

def graficar_resultado(
    archivo_datos: str,
    archivo_salida: str,
    modo: str,
    vs_valor: float,
    fc_inferior_objetivo: float | None = None,
    fc_superior_objetivo: float | None = None,
    f_paso_1: float | None = None,
    f_paso_2: float | None = None,
    f_aten_1: float | None = None,
    f_aten_2: float | None = None,
    amp_paso_objetivo: float | None = None,
    amp_aten_objetivo: float | None = None,
) -> None:
    """Genera la gráfica de respuesta en frecuencia y la guarda en archivo_salida."""
    try:
        import matplotlib.pyplot as plt
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

    fig, ax = plt.subplots(figsize=(8, 5))

    if modo == "BASICO":
        fc_inf, fc_sup, amp_max, _, _ = calcular_metricas_fc(archivo_datos)
        nivel_fc = (amp_max / np.sqrt(2)) if amp_max else None

        ax.semilogx(frecuencias, amplitudes, color="#2563eb", linewidth=2, label="Respuesta simulada")
        if nivel_fc is not None:
            ax.axhline(nivel_fc, color="gray", linestyle="--", linewidth=1,
                       label=f"Nivel de corte (-3 dB) ({nivel_fc:.2f} V)")
        if fc_inferior_objetivo is not None:
            ax.axvline(fc_inferior_objetivo, color="#16a34a", linestyle="--", linewidth=1,
                       label=f"Fc inferior objetivo ({fc_inferior_objetivo:.0f} Hz)")
        if fc_superior_objetivo is not None:
            ax.axvline(fc_superior_objetivo, color="#16a34a", linestyle="--", linewidth=1,
                       label=f"Fc superior objetivo ({fc_superior_objetivo:.0f} Hz)")
        if fc_inf:
            ax.axvline(fc_inf, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"Fc inferior obtenida ({fc_inf:.0f} Hz)")
        if fc_sup:
            ax.axvline(fc_sup, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"Fc superior obtenida ({fc_sup:.0f} Hz)")

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
        if f_paso_1 is not None:
            ax.axvline(f_paso_1, color="#16a34a", linestyle=":", linewidth=1.5,
                       label=f"F_PASO_1 ({f_paso_1:.0f} Hz)")
        if f_aten_1 is not None:
            ax.axvline(f_aten_1, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"F_ATEN_1 ({f_aten_1:.0f} Hz)")
        if f_aten_2 is not None:
            ax.axvline(f_aten_2, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"F_ATEN_2 ({f_aten_2:.0f} Hz)")
        if f_paso_2 is not None:
            ax.axvline(f_paso_2, color="#16a34a", linestyle=":", linewidth=1.5,
                       label=f"F_PASO_2 ({f_paso_2:.0f} Hz)")

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
    fc_inferior_objetivo: float | None = None,
    fc_superior_objetivo: float | None = None,
    f_paso_1: float | None = None,
    f_paso_2: float | None = None,
    f_aten_1: float | None = None,
    f_aten_2: float | None = None,
    amp_paso_objetivo: float | None = None,
    amp_aten_objetivo: float | None = None,
) -> dict:
    # fc_inferior_objetivo/fc_superior_objetivo/amp_paso_objetivo/
    # amp_aten_objetivo se aceptan sin usarse (igual que en pasa_banda):
    # graficar_resultado() sí los necesita y ambas reciben el mismo
    # ctx["frecuencias_ctx"].
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
        fc_inf, fc_sup, _, _, _ = calcular_metricas_fc(archivo_datos)
        if fc_inf is None or fc_sup is None:
            raise RuntimeError(
                "No se pudieron calcular fc_inferior/fc_superior a partir de "
                f"'{archivo_datos}'. Revisa calcular_metricas_fc() (rechaza_banda)."
            )
        frecuencias_obtenidas = [
            {"clave": "fc_inferior_obtenida", "valor": float(fc_inf)},
            {"clave": "fc_superior_obtenida", "valor": float(fc_sup)},
        ]
    else:
        (_, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2, _, _) = calcular_metricas_paso_aten(
            archivo_datos, f_paso_1, f_paso_2, f_aten_1, f_aten_2
        )
        frecuencias_obtenidas = [
            {"clave": "amp_paso_1_obtenida", "valor": float(amp_paso_1)},
            {"clave": "amp_paso_2_obtenida", "valor": float(amp_paso_2)},
            {"clave": "amp_aten_1_obtenida", "valor": float(amp_aten_1)},
            {"clave": "amp_aten_2_obtenida", "valor": float(amp_aten_2)},
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