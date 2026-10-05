"""
Utilería: fitness_fc (BASICO) y fitness_paso_aten (AVANZADO) para el filtro
RECHAZA-BANDA, versión del algoritmo de RECOCIDO SIMULADO.

Port literal de fitness_fc / fitness_paso_aten del código fuente de RS
(decisión confirmada con el usuario: "portar el RS tal cual"). NO es el
mismo fitness que utils.genetico.rechaza_banda.fitness (el del AG/PSO/BO).
Diferencias, tal como vienen en el código fuente de RS:

  BASICO
    - Pesos 0.25 f_fc_inf + 0.25 f_fc_sup + 0.125 f_pend_baj
      + 0.125 f_pend_sub + 0.25 f_amp (el AG: 0.4/0.4/0.1/0.1, sin f_amp).
    - Usa las métricas de este paquete (ancla VS/sqrt(2); pendiente a una
      década hacia afuera de cada Fc). Sobre una muesca esa pendiente da
      ~3 dB/dec sin importar su agudeza, así que f_pend_baj y f_pend_sub
      quedan casi constantes (~0.52 contra el objetivo de 40 dB/dec) y
      ese 25% del fitness no distingue buenos de malos circuitos.

  AVANZADO
    - Pesos 0.25 x f_paso1, f_paso2, f_aten1, f_aten2; sin ningún término
      de pendiente (el AG: 0.25/0.25 paso, 0.15/0.15 aten, 0.1/0.1 pend.).

  Ambos
    - SIN penalización por saturación del Op-Amp (amp_max > 1.01 * VS), que
      el AG sí aplica.
    - Devuelven una tupla de 2 elementos (fit, amp_max), no las tuplas
      largas del AG; por eso el servicio de RS para este filtro trae su
      propio _log_generacion.

Recibe todo el contexto como argumentos; no mantiene estado propio.
"""
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.recocido_simulado.rechaza_banda.metrics import calcular_metricas_fc, calcular_metricas_paso_aten

# Pendiente objetivo por flanco de la muesca (solo la usa BASICO).
PENDIENTE_OBJETIVO_FC: float = 40.0


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
) -> tuple[float, float]:
    """
    Fitness BASICO: Fc inferior y superior de la muesca (25% cada una),
    pendientes de ambos flancos (12.5% cada una) y qué tan cerca está
    amp_max de VS (25%).
    Retorna: (fit, amp_max)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, 0.0

        fc_inf, fc_sup, amp_max, pend_baj, pend_sub = calcular_metricas_fc(archivo_datos, vs_valor)
        if fc_inf is None or fc_sup is None:
            return 1e-6, 0.0

        f_fc_inf = 1.0 / (1.0 + abs(fc_inf - fc_inferior_objetivo) / fc_inferior_objetivo)
        f_fc_sup = 1.0 / (1.0 + abs(fc_sup - fc_superior_objetivo) / fc_superior_objetivo)
        f_pend_baj = 1.0 / (1.0 + abs(pend_baj - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_pend_sub = 1.0 / (1.0 + abs(pend_sub - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_amp = 1.0 / (1.0 + abs(amp_max - vs_valor) / vs_valor)

        fit = (f_fc_inf * 0.25) + (f_fc_sup * 0.25) + (f_pend_baj * 0.125) + \
              (f_pend_sub * 0.125) + (f_amp * 0.25)
        return float(fit), amp_max

    except Exception:
        return 1e-6, 0.0


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
) -> tuple[float, float]:
    """
    Fitness AVANZADO: cercanía a amp_paso_objetivo en F_PASO_1/F_PASO_2 y
    a amp_aten_objetivo en F_ATEN_1/F_ATEN_2, 25% cada una; sin términos
    de pendiente.
    Retorna: (fit, amp_max)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, 0.0

        amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2, _, _ = calcular_metricas_paso_aten(
            archivo_datos, f_paso_1, f_paso_2, f_aten_1, f_aten_2
        )
        if amp_max is None:
            return 1e-6, 0.0

        f_paso1 = 1.0 / (1.0 + abs(amp_paso_1 - amp_paso_objetivo) / vs_valor)
        f_paso2 = 1.0 / (1.0 + abs(amp_paso_2 - amp_paso_objetivo) / vs_valor)
        f_aten1 = 1.0 / (1.0 + abs(amp_aten_1 - amp_aten_objetivo) / vs_valor)
        f_aten2 = 1.0 / (1.0 + abs(amp_aten_2 - amp_aten_objetivo) / vs_valor)

        fit = (f_paso1 * 0.25) + (f_paso2 * 0.25) + (f_aten1 * 0.25) + (f_aten2 * 0.25)
        return float(fit), amp_max

    except Exception:
        return 1e-6, 0.0