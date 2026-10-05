"""
Utilería: métricas sobre la curva de respuesta en frecuencia, filtro
RECHAZA-BANDA, versión del algoritmo de RECOCIDO SIMULADO.

Port literal de obtener_metricas_fc / obtener_metricas_paso_aten del
código fuente de RS (decisión confirmada con el usuario: "portar el RS tal
cual"). NO es la misma métrica que utils.genetico.rechaza_banda.metrics
(la del AG/PSO/BO), en dos puntos:

  1. Ancla del -3 dB (BASICO): aquí es VS/sqrt(2), con VS la amplitud de la
     fuente (por eso calcular_metricas_fc recibe vs_valor); en el AG es
     amp_max/sqrt(2), con amp_max el máximo medido en la curva. Para un
     filtro de ganancia unitaria en la banda de paso coinciden; si la
     ganancia no es 1 (o hay un pico de resonancia) dan Fc distintas.

  2. Pendiente (BASICO): aquí se mide una década HACIA AFUERA de cada Fc
     (fc_inf/10 y fc_sup*10); en el AG se mide entre cada Fc y el valle
     de la muesca. En una muesca "hacia afuera" ya es la banda de paso
     plana, así que esta pendiente sale ~3 dB/dec (la diferencia de los
     -3 dB) sin importar qué tan aguda sea la muesca, contra un objetivo
     de 40 dB/dec -- ver la nota en fitness.py sobre su consecuencia.

Los helpers _db y _cruce_interpolado son idénticos a los del código fuente
de RS (comparados línea por línea) y a los del AG, por eso se importan de
ahí en vez de duplicarlos.

No depende de ninguna otra capa ni de estado global.
"""
import traceback

import numpy as np

from app.utils.genetico.rechaza_banda.metrics import _db, _cruce_interpolado


def calcular_metricas_fc(
    archivo_datos: str,
    vs_valor: float,
) -> tuple[float | None, float | None, float, float, float]:
    """
    MODO BASICO. Divide el espectro en el valle (mínimo); busca el cruce
    interpolado por VS/sqrt(2) antes del valle (borde inferior) y después
    (borde superior); y mide las pendientes a una década hacia afuera de
    cada cruce.

    Retorna: (fc_inferior, fc_superior, amp_max, pend_bajada, pend_subida)
    pend_bajada -> flanco inferior (fc_inferior vs fc_inferior/10)
    pend_subida -> flanco superior (fc_superior vs fc_superior*10)
    (Nótese el orden bajada/subida: es el del código fuente de RS, el
    inverso del que devuelve la métrica del AG.)
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias, amplitudes = datos[:, 0], datos[:, 1]

        amp_max = float(np.max(amplitudes))
        idx_valle = int(np.argmin(amplitudes))
        nivel_fc = vs_valor / np.sqrt(2)

        fc_inf = _cruce_interpolado(frecuencias[: idx_valle + 1], amplitudes[: idx_valle + 1], nivel_fc)
        fc_sup = _cruce_interpolado(frecuencias[idx_valle:], amplitudes[idx_valle:], nivel_fc)

        idx_inf = np.argmin(np.abs(frecuencias - fc_inf))
        idx_ref_inf = np.argmin(np.abs(frecuencias - (fc_inf / 10.0)))
        pend_bajada = abs(_db(amplitudes[idx_inf]) - _db(amplitudes[idx_ref_inf]))

        idx_sup = np.argmin(np.abs(frecuencias - fc_sup))
        idx_ref_sup = np.argmin(np.abs(frecuencias - (fc_sup * 10.0)))
        pend_subida = abs(_db(amplitudes[idx_sup]) - _db(amplitudes[idx_ref_sup]))

        return float(fc_inf), float(fc_sup), amp_max, float(pend_bajada), float(pend_subida)
    except Exception:
        print("[AVISO] calcular_metricas_fc (rechaza_banda, RS) falló; se usará (None, None, 0.0, 0.0, 0.0):")
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
    Todas las amplitudes se leen por interpolación en el punto exacto
    (en escala logarítmica de frecuencia).

    Retorna: (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
              pend_bajada, pend_subida)
    pend_bajada -> entre F_PASO_1 y F_ATEN_1 (entrando a la muesca)
    pend_subida -> entre F_ATEN_2 y F_PASO_2 (saliendo de la muesca)
    (El fitness de RS no usa las pendientes en este modo; se calculan
    igual porque el código fuente las devuelve.)
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias, amplitudes = datos[:, 0], datos[:, 1]

        amp_max = float(np.max(amplitudes))
        log_f = np.log10(frecuencias)

        amp_paso_1 = float(np.interp(np.log10(f_paso_1), log_f, amplitudes))
        amp_paso_2 = float(np.interp(np.log10(f_paso_2), log_f, amplitudes))
        amp_aten_1 = float(np.interp(np.log10(f_aten_1), log_f, amplitudes))
        amp_aten_2 = float(np.interp(np.log10(f_aten_2), log_f, amplitudes))

        pend_bajada = abs(_db(amp_paso_1) - _db(amp_aten_1)) / abs(np.log10(f_aten_1 / f_paso_1))
        pend_subida = abs(_db(amp_paso_2) - _db(amp_aten_2)) / abs(np.log10(f_paso_2 / f_aten_2))

        return amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2, float(pend_bajada), float(pend_subida)
    except Exception:
        print("[AVISO] calcular_metricas_paso_aten (rechaza_banda, RS) falló; se usará ceros:")
        traceback.print_exc()
        return None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0