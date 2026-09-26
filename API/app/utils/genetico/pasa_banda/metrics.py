"""
Utilería: cálculo de métricas sobre la curva de respuesta en frecuencia
leída del archivo de datos producido por ngspice, para el filtro PASA-BANDA.

Adaptado del código fuente del equipo de algoritmos (ALGORITMO_GENETICO/
FILTRO_PASABANDA/algoritmo.py). A diferencia de pasa_altas/pasa_bajas (un
solo borde), un pasa-banda tiene DOS bordes (inferior y superior) y DOS
mecanismos de anti-resonancia distintos por lado:
  - Lado inferior: lo gobierna la etapa pasa-altas del netlist (dos
    capacitores en serie). Por debajo de F_ATEN_1 la impedancia de esos
    capacitores solo crece al bajar la frecuencia, así que la curva tiende
    a 0 monótonamente — no hay mecanismo físico de rebote ahí.
  - Lado superior: lo gobierna la etapa pasa-bajas del netlist, más la
    caída de ganancia en lazo abierto del Op-Amp en alta frecuencia. Ahí SÍ
    puede haber una resonancia que impida que la curva se quede atenuada
    (ver `_peor_rebote`), así que solo se mide ese lado.

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
    después del pico). Si no hay cruce exacto, cae al punto más cercano a
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


def _peor_rebote(amplitudes_desde_borde: np.ndarray) -> float:
    """
    Recorre `amplitudes_desde_borde` (empezando justo en el borde de
    atenuación superior y alejándose hacia la banda de rechazo) y mide
    cuánto sube la curva DESPUÉS de su mínimo más profundo hasta ese
    punto.
      - Si la curva solo baja o se mantiene plana: rebote = 0 (válido
        aunque nunca llegue a 0V, p.ej. porque F_ATEN está físicamente
        cerca de F_PASO y no hay décadas suficientes para que la
        pendiente termine de caer — eso NO se castiga).
      - Si después de bajar la curva vuelve a subir (resonancia que no
        decae, el problema real): el rebote crece con esa subida.
    """
    minimo = amplitudes_desde_borde[0]
    peor = 0.0
    for a in amplitudes_desde_borde[1:]:
        if a < minimo:
            minimo = a
        else:
            peor = max(peor, a - minimo)
    return float(peor)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def calcular_metricas_fc(
    archivo_datos: str,
) -> tuple[float | None, float | None, float, float, float, float]:
    """
    MODO BASICO: cada borde se define por el cruce a -3dB respecto del
    PICO de amplitud (no respecto a DC ni al extremo del barrido, porque
    aquí ambos extremos están atenuados). El borde inferior (sube) se
    busca ANTES del pico; el superior (baja), DESPUÉS. Las pendientes se
    miden una década por fuera de cada Fc: por DEBAJO para el inferior
    (estilo pasa-altas) y por ENCIMA para el superior (estilo pasa-bajas).

    Retorna: (fc_inferior, fc_superior, amp_max, pend_subida, pend_bajada, rebote)
    (rebote solo del lado superior; ver docstring del módulo).
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = float(np.max(amplitudes))
        idx_pico = int(np.argmax(amplitudes))
        nivel_fc = amp_max / np.sqrt(2)

        fc_inferior = _cruce_interpolado(frecuencias[: idx_pico + 1], amplitudes[: idx_pico + 1], nivel_fc)
        fc_superior = _cruce_interpolado(frecuencias[idx_pico:], amplitudes[idx_pico:], nivel_fc)

        idx_inf = np.argmin(np.abs(frecuencias - fc_inferior))
        f_ref_inf = fc_inferior / 10.0  # una década POR DEBAJO (atenuación inferior)
        idx_ref_inf = np.argmin(np.abs(frecuencias - f_ref_inf))
        pend_subida = abs(_db(amplitudes[idx_inf]) - _db(amplitudes[idx_ref_inf]))

        idx_sup = np.argmin(np.abs(frecuencias - fc_superior))
        f_ref_sup = fc_superior * 10.0  # una década POR ENCIMA (atenuación superior)
        idx_ref_sup = np.argmin(np.abs(frecuencias - f_ref_sup))
        pend_bajada = abs(_db(amplitudes[idx_sup]) - _db(amplitudes[idx_ref_sup]))

        rebote = _peor_rebote(amplitudes[idx_sup:])

        return (float(fc_inferior), float(fc_superior), amp_max,
                float(pend_subida), float(pend_bajada), rebote)
    except Exception:
        print("[AVISO] calcular_metricas_fc (pasa_banda) falló; se usará (None, None, 0.0, 0.0, 0.0, 0.0):")
        traceback.print_exc()
        return None, None, 0.0, 0.0, 0.0, 0.0


def calcular_metricas_paso_aten(
    archivo_datos: str,
    f_paso_1: float,
    f_paso_2: float,
    f_aten_1: float,
    f_aten_2: float,
) -> tuple[float | None, float, float, float, float, float, float, float]:
    """
    MODO AVANZADO: evalúa la amplitud real en las dos frecuencias de paso
    (F_PASO_1, F_PASO_2) y el PEOR CASO (máximo) de amplitud en toda la
    región del barrido por fuera de cada extremo de atenuación — no solo
    el punto exacto F_ATEN_X, para que ninguna resonancia se "esconda"
    entre dos muestras sin ser detectada.

    Retorna: (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
              pend_subida, pend_bajada, rebote)
    (rebote solo del lado superior; ver docstring del módulo).
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = float(np.max(amplitudes))
        log_f = np.log10(frecuencias)
        amp_paso_1 = float(np.interp(np.log10(f_paso_1), log_f, amplitudes))
        amp_paso_2 = float(np.interp(np.log10(f_paso_2), log_f, amplitudes))

        idx_aten1 = int(np.argmin(np.abs(frecuencias - f_aten_1)))
        idx_aten2 = int(np.argmin(np.abs(frecuencias - f_aten_2)))
        amp_aten_1 = float(np.max(amplitudes[: idx_aten1 + 1]))
        amp_aten_2 = float(np.max(amplitudes[idx_aten2:]))

        # abs() en ambos lados: así no importa el orden relativo de las
        # frecuencias en el JSON.
        pend_subida = abs(_db(amp_paso_1) - _db(amp_aten_1)) / abs(np.log10(f_aten_1 / f_paso_1))
        pend_bajada = abs(_db(amp_paso_2) - _db(amp_aten_2)) / abs(np.log10(f_aten_2 / f_paso_2))

        rebote = _peor_rebote(amplitudes[idx_aten2:])

        return (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
                float(pend_subida), float(pend_bajada), rebote)
    except Exception:
        print("[AVISO] calcular_metricas_paso_aten (pasa_banda) falló; se usará ceros:")
        traceback.print_exc()
        return None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0