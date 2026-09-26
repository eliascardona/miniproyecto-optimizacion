"""
Utilería: cálculo de fitness para cada individuo del AG, filtro PASA-BAJAS.

Adaptado del código fuente del equipo de algoritmos (ALGORITMO_GENETICO/
FILTRO_PASABAJAS/algoritmo.py): las fórmulas de fitness aquí son
DELIBERADAMENTE distintas a las de pasa_altas (no es una copia con nombres
cambiados) — fitness_fc no tiene término de amplitud máxima (en
pasa_altas sí, porque ahí interesa que el pico se acerque a V_fuente; en
un pasa-bajas la ganancia relevante ya se evalúa vía amp_dc dentro de las
métricas) y los pesos de cada término son distintos.

Recibe todo el contexto como argumentos; no mantiene estado propio (el
script original usaba variables globales VS_VALOR/FC_OBJETIVO/etc.
cargadas una sola vez al importar el módulo).
"""
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.genetico.pasa_bajas.metrics import calcular_metricas_fc, calcular_metricas_paso_aten

# Pendiente teórica máxima de un pasa-bajas Sallen-Key de 4.º orden (dos
# etapas de 2.º orden en cascada): 80 dB/dec. Se mantienen dos constantes
# separadas (aunque hoy valen lo mismo) porque así las trae el código
# fuente original, por si en el futuro se quieren afinar por separado.
PENDIENTE_OBJETIVO_FC: float = 80.0
PENDIENTE_OBJETIVO_PASO_ATEN: float = 80.0


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
    Fitness BASICO: evalúa Fc y pendiente objetivo, más anti-resonancia.
    A diferencia del pasa-altas, NO pondera amplitud máxima como término
    aparte (ver docstring del módulo).
    Retorna: (fit, fc_real, amp_dc, amp_max, pendiente, f_fc, f_pend, f_plano)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        fc, amp_dc, amp_max, pend, f_plano = calcular_metricas_fc(archivo_datos)

        if fc is None:
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        if amp_max > vs_valor * 1.01:  # Op-Amp saturado
            return 1e-6, fc, amp_dc, amp_max, pend, 0.0, 0.0, f_plano

        f_fc = 1.0 / (1.0 + abs(fc - fc_objetivo) / fc_objetivo)
        f_pend = 1.0 / (1.0 + abs(pend - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)

        fit = (f_plano * 0.2) + (f_fc * 0.5) + (f_pend * 0.3)
        return float(fit), fc, amp_dc, amp_max, pend, f_fc, f_pend, f_plano

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
) -> tuple[float, float | None, float, float, float, float, float, float, float]:
    """
    Fitness AVANZADO: evalúa voltaje en F_PASO (baja frecuencia) y F_ATEN
    (alta frecuencia), pendiente y anti-resonancia.
    Retorna: (fit, amp_dc, amp_paso, amp_aten, pendiente, f_paso_score, f_aten_score, f_pend, f_plano)
    """
    try:
        actualizar_circuito(
            individuo, componentes_ag, archivo_cir,
            vs_valor, vpp_valor, vnn_valor, rs_valor, rl_valor,
            f_inicial, f_final,
        )
        if not ejecutar_spice(ngspice_exe, archivo_cir):
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        amp_dc, amp_max, amp_paso, amp_aten, pendiente, f_plano = calcular_metricas_paso_aten(
            archivo_datos, f_paso, f_aten
        )

        if amp_dc is None:
            return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        if amp_max > vs_valor * 1.01:  # Op-Amp saturado
            return 1e-6, amp_dc, amp_paso, amp_aten, pendiente, 0.0, 0.0, 0.0, 0.0

        error_rel_paso = abs(amp_paso_objetivo - amp_paso) / amp_paso_objetivo
        f_paso_score = 1.0 / (1.0 + (error_rel_paso ** 4) * 100.0)
        f_aten_score = 1.0 / (1.0 + abs(amp_aten - amp_aten_objetivo) / vs_valor)
        f_pend = 1.0 / (1.0 + abs(pendiente - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)

        fit = (f_paso_score * 0.4) + (f_aten_score * 0.3) + (f_pend * 0.2) + (f_plano * 0.1)
        return float(fit), amp_dc, amp_paso, amp_aten, pendiente, f_paso_score, f_aten_score, f_pend, f_plano

    except Exception:
        return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0