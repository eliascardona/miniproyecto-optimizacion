"""
Utilería: cálculo de fitness para cada individuo del AG.

Recibe todo el contexto como argumentos; no mantiene estado propio.
"""
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.metrics import calcular_metricas_fc, calcular_metricas_paso_aten

# Pendiente teórica máxima de un pasa-altas Sallen-Key de 4.º orden
# (dos etapas de 2.º orden en cascada): 80 dB/dec.
PENDIENTE_OBJETIVO: float = 80.0


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
    fc_objetivo: float,
) -> tuple[float, float | None, float, float, float, float, float, float]:
    """
    Fitness BASICO: evalúa Fc, pendiente de -80 dB/dec y amplitud máxima.
    Retorna: (fit, fc_real, amp_max, pendiente, f_fc, f_pend, f_plano, f_amp)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        fc, amp_max, pend, f_plano = calcular_metricas_fc(archivo_datos)

        if fc is None:
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        if amp_max > vs_valor * 1.01:  # Op-Amp saturado
            return 1e-6, fc, amp_max, pend, 0.0, 0.0, f_plano, 0.0

        f_fc = 1.0 / (1.0 + abs(fc - fc_objetivo) / fc_objetivo)
        f_pend = 1.0 / (1.0 + abs(pend - PENDIENTE_OBJETIVO) / PENDIENTE_OBJETIVO)
        f_amp = 1.0 / (1.0 + abs(vs_valor - amp_max) / vs_valor)

        fit = (f_plano * 0.2) + (f_fc * 0.4) + (f_pend * 0.2) + (f_amp * 0.2)
        return float(fit), fc, amp_max, pend, f_fc, f_pend, f_plano, f_amp

    except Exception:
        return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


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
    f_paso: float,
    f_aten: float,
    amp_paso_objetivo: float,
    amp_aten_objetivo: float,
) -> tuple[float, float, float, float, float, float, float, float]:
    """
    Fitness AVANZADO: evalúa voltaje en F_PASO y F_ATEN, pendiente y anti-resonancia.
    Retorna: (fit, amp_paso, amp_aten, pendiente, f_paso, f_aten_score, f_pend, f_plano)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        amp_max, amp_paso, amp_aten, pendiente, f_plano = calcular_metricas_paso_aten(
            archivo_datos, f_paso, f_aten
        )

        if amp_max is None:
            return 1e-6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        if amp_max > vs_valor * 1.01:  # Op-Amp saturado
            return 1e-6, amp_paso, amp_aten, pendiente, 0.0, 0.0, 0.0, 0.0

        error_rel_paso = abs(amp_paso_objetivo - amp_paso) / amp_paso_objetivo
        f_paso_score = 1.0 / (1.0 + (error_rel_paso ** 4) * 100.0)
        f_aten_score = 1.0 / (1.0 + abs(amp_aten - amp_aten_objetivo) / vs_valor)
        f_pend = 1.0 / (1.0 + abs(pendiente - PENDIENTE_OBJETIVO) / PENDIENTE_OBJETIVO)

        fit = (f_paso_score * 0.4) + (f_aten_score * 0.3) + (f_pend * 0.1) + (f_plano * 0.2)
        return float(fit), amp_paso, amp_aten, pendiente, f_paso_score, f_aten_score, f_pend, f_plano

    except Exception:
        return 1e-6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0