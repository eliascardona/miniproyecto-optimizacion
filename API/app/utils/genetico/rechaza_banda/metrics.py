"""
Utilería: cálculo de métricas sobre la curva de respuesta en frecuencia
leída del archivo de datos producido por ngspice, para el filtro
RECHAZA-BANDA (notch).

Adaptado del código fuente del equipo de algoritmos (ALGORITMO_GENETICO/
FILTRO_RECHAZABANDA/algoritmo.py). Aquí la forma de la curva es la
contraria a un pasa-banda: pasa en los dos extremos y se hunde en el
centro (una "muesca"), producida por una red Twin-T pasiva entre dos
buffers Op-Amp — no hay una etapa que decaiga monótonamente hacia 0 en
ningún extremo del barrido, así que a diferencia de pasa_banda:
  - No existe mecanismo de "rebote" que vigilar (no hay compuerta dura
    aquí; ambos extremos son banda de PASO, no de atenuación permanente).
  - En MODO BASICO se divide el espectro por el VALLE (mínimo), no por
    el pico.
  - En MODO AVANZADO, la atenuación en F_ATEN_1/F_ATEN_2 se lee por
    interpolación en el punto exacto (no "peor caso" de una región,
    porque aquí no hay banda de rechazo abierta hacia el infinito que
    pueda "esconder" una resonancia).

No depende de ninguna otra capa ni de estado global; recibe todo lo que
necesita como argumentos.
"""
import numpy as np
import traceback


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _db(x) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(x, 1e-12))


def _cruce_interpolado(frecuencias: np.ndarray, amplitudes: np.ndarray, nivel: float) -> float:
    """
    Busca el cruce (interpolado linealmente) de `amplitudes` por `nivel`,
    recorriendo los arreglos en el orden en que se pasen — por eso quien
    llama debe pasar ya el tramo de la curva que le interesa (antes o
    después del valle). Si no hay cruce exacto, cae al punto más cercano a
    `nivel` dentro del tramo dado.
    """
    for i in range(len(amplitudes) - 1):
        a1, a2 = amplitudes[i], amplitudes[i + 1]
        if (a1 <= nivel <= a2) or (a1 >= nivel >= a2):
            f1, f2 = frecuencias[i], frecuencias[i + 1]
            if a2 != a1:
                return float(f1 + (nivel - a1) * (f2 - f1) / (a2 - a1))
            return float(f1)
    return float(frecuencias[np.argmin(np.abs(amplitudes - nivel))])


def _safe_div(valle: float, fc: float) -> float:
    """Evita división por cero cuando el valle coincide con el propio Fc
    (caso límite: una muesca casi inexistente)."""
    den = abs(np.log10(valle / fc))
    return den if den > 1e-12 else 1e-12


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def calcular_metricas_fc(
    archivo_datos: str,
) -> tuple[float | None, float | None, float, float, float]:
    """
    MODO BASICO: se busca el VALLE (mínimo) de la muesca para dividir el
    espectro en dos mitades. Los cruces a -3dB se calculan respecto al
    amp_max (nivel de la banda de paso), uno antes del valle (borde
    inferior) y otro después (borde superior). Las pendientes se miden
    entre cada cruce y el propio valle (no "una década más allá", como en
    pasa_banda), con protección ante división por cero si el valle
    coincide con el cruce.

    Retorna: (fc_inferior, fc_superior, amp_max, pend_subida, pend_bajada)
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = float(np.max(amplitudes))
        idx_valle = int(np.argmin(amplitudes))
        nivel_fc = amp_max / np.sqrt(2)

        fc_inferior = _cruce_interpolado(frecuencias[: idx_valle + 1], amplitudes[: idx_valle + 1], nivel_fc)
        fc_superior = _cruce_interpolado(frecuencias[idx_valle:], amplitudes[idx_valle:], nivel_fc)

        f_valle = frecuencias[idx_valle]
        amp_valle = amplitudes[idx_valle]

        idx_inf = np.argmin(np.abs(frecuencias - fc_inferior))
        pend_subida = abs(_db(amplitudes[idx_inf]) - _db(amp_valle)) / _safe_div(f_valle, fc_inferior)

        idx_sup = np.argmin(np.abs(frecuencias - fc_superior))
        pend_bajada = abs(_db(amplitudes[idx_sup]) - _db(amp_valle)) / _safe_div(f_valle, fc_superior)

        return float(fc_inferior), float(fc_superior), amp_max, float(pend_subida), float(pend_bajada)
    except Exception:
        print("[AVISO] calcular_metricas_fc (rechaza_banda) falló; se usará (None, None, 0.0, 0.0, 0.0):")
        traceback.print_exc()
        return None, None, 0.0, 0.0, 0.0


def calcular_metricas_paso_aten(
    archivo_datos: str,
    f_paso_1: float,
    f_paso_2: float,
    f_aten_1: float,
    f_aten_2: float,
) -> tuple[float | None, float, float, float, float, float, float]:
    """
    MODO AVANZADO. Orden esperado (de menor a mayor frecuencia):
        F_PASO_1 < F_ATEN_1 < F_ATEN_2 < F_PASO_2
    (es el orden invertido respecto a un pasa-banda: aquí la atenuación
    queda en el CENTRO y el paso en los extremos).

    A diferencia de pasa_banda, aquí amp_aten_1/amp_aten_2 se leen por
    interpolación en el punto exacto (no "peor caso" de toda una región):
    no existe una banda de rechazo abierta hacia el infinito donde una
    resonancia pueda esconderse fuera de los puntos medidos.

    Retorna: (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
              pend_subida, pend_bajada)
    pend_bajada -> entre F_PASO_1 y F_ATEN_1 (entrando a la muesca)
    pend_subida -> entre F_ATEN_2 y F_PASO_2 (saliendo de la muesca)
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = float(np.max(amplitudes))
        log_f = np.log10(frecuencias)

        amp_paso_1 = float(np.interp(np.log10(f_paso_1), log_f, amplitudes))
        amp_paso_2 = float(np.interp(np.log10(f_paso_2), log_f, amplitudes))
        amp_aten_1 = float(np.interp(np.log10(f_aten_1), log_f, amplitudes))
        amp_aten_2 = float(np.interp(np.log10(f_aten_2), log_f, amplitudes))

        # abs() en ambos lados: así no importa el orden relativo de las
        # frecuencias en el JSON.
        pend_bajada = abs(_db(amp_paso_1) - _db(amp_aten_1)) / abs(np.log10(f_aten_1 / f_paso_1))
        pend_subida = abs(_db(amp_paso_2) - _db(amp_aten_2)) / abs(np.log10(f_aten_2 / f_paso_2))

        return amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2, float(pend_subida), float(pend_bajada)
    except Exception:
        print("[AVISO] calcular_metricas_paso_aten (rechaza_banda) falló; se usará ceros:")
        traceback.print_exc()
        return None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0