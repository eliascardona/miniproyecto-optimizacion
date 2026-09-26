"""
Utilería: cálculo de fitness para cada individuo del AG, filtro
RECHAZA-BANDA.

Adaptado del código fuente del equipo de algoritmos (ALGORITMO_GENETICO/
FILTRO_RECHAZABANDA/algoritmo.py). Dos diferencias importantes frente a
pasa_banda (no es una copia con nombres cambiados):

  1. NO existe la "compuerta dura" de rebote: la topología (Twin-T pasivo
     entre dos buffers Op-Amp) pasa en ambos extremos del barrido, así
     que no hay un lado que deba decaer monótonamente a 0 para siempre
     — el mecanismo de rebote de pasa_banda no aplica aquí.
  2. fitness_fc no pondera amplitud máxima como término aparte (a
     diferencia de pasa_banda, que sí premia que el pico se acerque a
     V_fuente): aquí los dos términos de Fc pesan 0.4 cada uno.

Recibe todo el contexto como argumentos; no mantiene estado propio.
"""
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.genetico.rechaza_banda.metrics import calcular_metricas_fc, calcular_metricas_paso_aten

# Pendiente objetivo POR FLANCO de la muesca (mismo valor que pasa_banda:
# cada flanco lo gobierna una sola etapa de 2.º orden -> 40 dB/dec).
PENDIENTE_OBJETIVO_FC: float = 40.0
PENDIENTE_OBJETIVO_PASO_ATEN: float = 40.0


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
) -> tuple[float, float | None, float | None, float, float, float, float, float, float]:
    """
    Fitness BASICO: Fc inferior + Fc superior de la muesca (40% cada una)
    + pendiente de subida y de bajada objetivo (10% cada una).
    Retorna: (fit, fc_inf, fc_sup, pend_sub, pend_baj,
              f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, None, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        fc_inf, fc_sup, amp_max, pend_sub, pend_baj = calcular_metricas_fc(archivo_datos)

        if fc_inf is None or fc_sup is None:
            return 1e-6, None, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        if amp_max > vs_valor * 1.01:  # Op-Amp saturado
            return 1e-6, fc_inf, fc_sup, pend_sub, pend_baj, 0.0, 0.0, 0.0, 0.0

        f_fc_inf = 1.0 / (1.0 + abs(fc_inf - fc_inferior_objetivo) / fc_inferior_objetivo)
        f_fc_sup = 1.0 / (1.0 + abs(fc_sup - fc_superior_objetivo) / fc_superior_objetivo)
        f_pend_sub = 1.0 / (1.0 + abs(pend_sub - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_pend_baj = 1.0 / (1.0 + abs(pend_baj - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)

        fit = (f_fc_inf * 0.4) + (f_fc_sup * 0.4) + (f_pend_sub * 0.1) + (f_pend_baj * 0.1)

        return (float(fit), fc_inf, fc_sup, pend_sub, pend_baj,
                f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj)

    except Exception:
        return 1e-6, None, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


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
) -> tuple[float, float | None, float, float, float, float, float, float, float, float, float, float, float]:
    """
    Fitness AVANZADO: cercanía a AMP_PASO_OBJETIVO en F_PASO_1/F_PASO_2
    (25% cada una) + cercanía a AMP_ATEN_OBJETIVO en F_ATEN_1/F_ATEN_2
    (15% cada una) + pendientes de entrada/salida de la muesca objetivo
    (10% cada una). Sin compuerta dura de rebote (ver docstring del
    módulo).
    Retorna: (fit, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
              pend_subida, pend_bajada, f_paso1, f_paso2, f_aten1, f_aten2,
              f_pend_subida, f_pend_bajada)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
         pend_subida, pend_bajada) = calcular_metricas_paso_aten(
            archivo_datos, f_paso_1, f_paso_2, f_aten_1, f_aten_2
        )

        if amp_max is None:
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        if amp_max > vs_valor * 1.01:  # Op-Amp saturado
            return (1e-6, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
                    pend_subida, pend_bajada, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Qué tan baja (cerca de 0V) es la amplitud real en F_ATEN_1/F_ATEN_2.
        f_aten1 = 1.0 / (1.0 + abs(amp_aten_1 - amp_aten_objetivo) / vs_valor)
        f_aten2 = 1.0 / (1.0 + abs(amp_aten_2 - amp_aten_objetivo) / vs_valor)

        # Qué tan cerca de amp_paso_objetivo (Vs) está cada extremo de paso.
        f_paso1 = 1.0 / (1.0 + abs(amp_paso_1 - amp_paso_objetivo) / vs_valor)
        f_paso2 = 1.0 / (1.0 + abs(amp_paso_2 - amp_paso_objetivo) / vs_valor)

        # Pendientes de bajada (hacia la muesca, lado inferior) y subida
        # (saliendo de la muesca, lado superior).
        f_pend_subida = 1.0 / (1.0 + abs(pend_subida - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)
        f_pend_bajada = 1.0 / (1.0 + abs(pend_bajada - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)

        fit = (f_aten1 * 0.15) + (f_aten2 * 0.15) + (f_paso1 * 0.25) + (f_paso2 * 0.25) + \
              (f_pend_subida * 0.1) + (f_pend_bajada * 0.1)

        return (float(fit), amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
                pend_subida, pend_bajada,
                f_paso1, f_paso2, f_aten1, f_aten2, f_pend_subida, f_pend_bajada)

    except Exception:
        return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0