"""
Utilería: fitness_fc (modo BASICO) para PSO + filtro PASA-BAJAS.

ÚNICA función de fitness que se separa de utils.genetico.pasa_bajas.fitness:
el equipo de algoritmos entregó pesos distintos para esta combinación
específica (PSO + pasa_bajas + BASICO) frente a la versión de AG para el
mismo filtro -- 0.65/0.15 aquí vs. 0.5/0.3 en el AG, confirmado explícitamente
con el usuario como una diferencia intencional, no un error de copia.

fitness_paso_aten (modo AVANZADO) SÍ es idéntica entre AG y PSO para este
filtro (mismos pesos 0.4/0.3/0.2/0.1) y calcular_metricas_fc/
calcular_metricas_paso_aten también lo son, así que esas se siguen
importando de utils.genetico.pasa_bajas.* sin duplicar nada -- ver
PasaBajasEnjambrePreparationService, que mezcla ambos orígenes.
"""
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.genetico.pasa_bajas.metrics import calcular_metricas_fc

# Mismo valor teórico que el AG (80 dB/dec para un pasa-bajas Sallen-Key
# de 4.º orden); lo único que cambia aquí son los PESOS del fitness, no
# el objetivo de pendiente en sí.
PENDIENTE_OBJETIVO_FC: float = 80.0


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
    Fitness BASICO (PSO): evalúa Fc y pendiente objetivo, más
    anti-resonancia -- misma estructura que la versión de AG, pero con
    f_fc pesando 0.65 (vs 0.5 en AG) y f_pend pesando 0.15 (vs 0.3 en AG).
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

        fit = (f_plano * 0.2) + (f_fc * 0.65) + (f_pend * 0.15)
        return float(fit), fc, amp_dc, amp_max, pend, f_fc, f_pend, f_plano

    except Exception:
        return 1e-6, None, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0