"""
Utilería: cálculo de fitness para cada individuo del AG, filtro PASA-BANDA.

Adaptado del código fuente del equipo de algoritmos (ALGORITMO_GENETICO/
FILTRO_PASABANDA/algoritmo.py). Dos diferencias importantes frente a
pasa_altas/pasa_bajas (no es una copia con nombres cambiados):

  1. Hay DOS bordes que optimizar a la vez (inferior y superior), cada
     uno con su propia Fc/pendiente objetivo — por eso fitness_fc y
     fitness_paso_aten reciben el doble de objetivos y devuelven tuplas
     bastante más largas (12 y 15 elementos).
  2. Hay una "compuerta dura": si la curva REBOTA (vuelve a subir después
     de tocar un mínimo) más allá de un margen tolerado del lado superior
     de la banda, el fitness completo se multiplica por
     PENALIZACION_ATEN_FALLO en vez de solo restar puntos — una resonancia
     que no decae ahí es un defecto grave, no un simple desvío del
     objetivo. Este mecanismo no existe en pasa_altas/pasa_bajas.

Recibe todo el contexto como argumentos; no mantiene estado propio.
"""
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.genetico.pasa_banda.metrics import calcular_metricas_fc, calcular_metricas_paso_aten

# Pendiente teórica máxima POR BORDE en un pasa-banda hecho de una etapa
# pasa-altas + una etapa pasa-bajas (cada una de 2.º orden): 40 dB/dec. A
# diferencia del pasa-bajas/pasa-altas puros (donde las dos etapas
# cascadean sobre el MISMO borde: 80 dB/dec), aquí cada etapa gobierna un
# borde distinto.
PENDIENTE_OBJETIVO_FC: float = 40.0
PENDIENTE_OBJETIVO_PASO_ATEN: float = 40.0

# Compuerta dura para el borde SUPERIOR de la banda (lo gobierna la etapa
# pasa-bajas, en ambos modos): castiga el fitness COMPLETO si la curva
# sube de nuevo más de este margen DESPUÉS de haber tocado un mínimo. No
# se aplica al borde inferior (sin mecanismo físico de rebote; ver
# metrics.py).
REBOTE_TOLERADO_REL: float = 0.03      # margen tolerado, como fracción de VS (3%)
PENALIZACION_ATEN_FALLO: float = 0.1   # multiplicador aplicado al fitness si rebota


# ---------------------------------------------------------------------------
# MODO BASICO
# ---------------------------------------------------------------------------

def fitness_fc(
    individuo: list[int],
    componentes_ag: list[dict],
    archivo_cir: str,
    archivo_datos: str,
    ngspice_exe: str,
    vs_valor: float,
    vpp_valor: float,
    vnn_valor: float,
    rs_valor: float,
    rl_valor: float,
    f_inicial: float,
    f_final: float,
    fc_inferior_objetivo: float,
    fc_superior_objetivo: float,
) -> tuple[float, float, float | None, float | None, float, float, float, float, float, float, float, float]:
    """
    Fitness BASICO: Fc inferior + Fc superior + pendiente de subida y de
    bajada objetivo + amplitud máxima respecto a VS (mientras más cerca
    esté el pico de VS, mejor).
    Retorna: (fit, amp_max, fc_inf, fc_sup, pend_sub, pend_baj,
              f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj, f_amp, pen_rebote)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, 0.0, None, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0

        fc_inf, fc_sup, amp_max, pend_sub, pend_baj, rebote = calcular_metricas_fc(archivo_datos)

        if fc_inf is None or fc_sup is None:
            return 1e-6, 0.0, None, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0

        if amp_max > vs_valor * 1.01:  # Op-Amp saturado
            return 1e-6, amp_max, fc_inf, fc_sup, pend_sub, pend_baj, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0

        f_fc_inf = 1.0 / (1.0 + abs(fc_inf - fc_inferior_objetivo) / fc_inferior_objetivo)
        f_fc_sup = 1.0 / (1.0 + abs(fc_sup - fc_superior_objetivo) / fc_superior_objetivo)
        f_pend_sub = 1.0 / (1.0 + abs(pend_sub - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_pend_baj = 1.0 / (1.0 + abs(pend_baj - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        # Amplitud máxima vs VS: 1.0 cuando amp_max == VS exacto, decae
        # mientras más se aleje (por arriba o por abajo).
        f_amp = 1.0 / (1.0 + abs(amp_max - vs_valor) / vs_valor)

        fit = (f_fc_inf * 0.25) + (f_fc_sup * 0.25) + (f_pend_sub * 0.125) + \
              (f_pend_baj * 0.125) + (f_amp * 0.25)

        # Compuerta dura: solo lado superior (ver docstring del módulo).
        pen_rebote = PENALIZACION_ATEN_FALLO if rebote > vs_valor * REBOTE_TOLERADO_REL else 1.0
        fit *= pen_rebote

        return (float(fit), amp_max, fc_inf, fc_sup, pend_sub, pend_baj,
                f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj, f_amp, pen_rebote)

    except Exception:
        return 1e-6, 0.0, None, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0


# ---------------------------------------------------------------------------
# MODO AVANZADO
# ---------------------------------------------------------------------------

def fitness_paso_aten(
    individuo: list[int],
    componentes_ag: list[dict],
    archivo_cir: str,
    archivo_datos: str,
    ngspice_exe: str,
    vs_valor: float,
    vpp_valor: float,
    vnn_valor: float,
    rs_valor: float,
    rl_valor: float,
    f_inicial: float,
    f_final: float,
    f_paso_1: float,
    f_paso_2: float,
    f_aten_1: float,
    f_aten_2: float,
    amp_paso_objetivo: float,
    amp_aten_objetivo: float,
) -> tuple[float, float | None, float, float, float, float, float, float, float, float, float, float, float, float, float]:
    """
    Fitness AVANZADO: cercanía de la amplitud real en F_PASO_1/F_PASO_2 a
    la amplitud de paso deseada, atenuación en los dos extremos (peor
    caso, no solo el punto exacto) y pendientes de subida/bajada objetivo.
    Retorna: (fit, amp_max, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
              pend_subida, pend_bajada, f_paso1, f_paso2, f_aten1, f_aten2,
              f_pSub, f_pBaj, pen_aten)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0

        (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
         pend_subida, pend_bajada, rebote) = calcular_metricas_paso_aten(
            archivo_datos, f_paso_1, f_paso_2, f_aten_1, f_aten_2
        )

        if amp_max is None:
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0

        if amp_max > vs_valor * 1.01:  # Op-Amp saturado
            return (1e-6, amp_max, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
                    pend_subida, pend_bajada, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)

        # Banda de paso: mientras más cerca de amp_paso_objetivo (Vs), mejor.
        f_paso1 = 1.0 / (1.0 + abs(amp_paso_1 - amp_paso_objetivo) / vs_valor)
        f_paso2 = 1.0 / (1.0 + abs(amp_paso_2 - amp_paso_objetivo) / vs_valor)

        # Atenuación: mientras más cerca de amp_aten_objetivo (0V), mejor.
        f_aten1 = 1.0 / (1.0 + abs(amp_aten_1 - amp_aten_objetivo) / vs_valor)
        f_aten2 = 1.0 / (1.0 + abs(amp_aten_2 - amp_aten_objetivo) / vs_valor)

        # Pendientes de subida (borde inferior) y bajada (borde superior).
        f_pSub = 1.0 / (1.0 + abs(pend_subida - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)
        f_pBaj = 1.0 / (1.0 + abs(pend_bajada - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)

        fit = (f_paso1 * 0.25) + (f_paso2 * 0.25) + (f_aten1 * 0.15) + (f_aten2 * 0.15) + \
              (f_pSub * 0.1) + (f_pBaj * 0.1)

        # Compuerta dura: solo lado superior (ver docstring del módulo).
        pen_aten = PENALIZACION_ATEN_FALLO if rebote > vs_valor * REBOTE_TOLERADO_REL else 1.0
        fit *= pen_aten

        return (float(fit), amp_max, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
                pend_subida, pend_bajada, f_paso1, f_paso2, f_aten1, f_aten2, f_pSub, f_pBaj, pen_aten)

    except Exception:
        return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0