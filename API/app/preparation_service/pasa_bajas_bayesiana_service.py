"""
Conecta BayesianPreparationService con las piezas específicas del filtro
pasa-bajas.

A diferencia de PasaBajasEnjambrePreparationService (donde fitness_fc SÍ
tenía pesos propios para PSO, 0.65/0.15), aquí comparé línea por línea
contra el código fuente de BO: fitness_fc trae los MISMOS pesos que el AG
(0.2/0.5/0.3), fitness_paso_aten también coincide (0.4/0.3/0.2/0.1), y
las métricas (calcular_f_plano, calcular_metricas_fc,
calcular_metricas_paso_aten) son idénticas. Así que aquí SÍ se reutiliza
TODO de utils.genetico.pasa_bajas sin ninguna pieza aparte -- la
divergencia de PSO fue específica de esa combinación, no una regla
general "BO/PSO siempre traen pesos distintos al AG".
"""
from app.pydantic_schema.api_request_schema.algorithm_config.pasabajas import PasaBajasConfiguration
from app.preparation_service.bayesian_preparation_service import BayesianPreparationService
from app.utils.genetico.pasa_bajas.fitness import fitness_fc, fitness_paso_aten
from app.utils.genetico.pasa_bajas.result_exporter import graficar_resultado, guardar_resultado_json


class PasaBajasBayesianaPreparationService(BayesianPreparationService):
    config_schema = PasaBajasConfiguration
    filtro_nombre = "pasa_bajas"

    _fitness_fc = staticmethod(fitness_fc)
    _fitness_paso_aten = staticmethod(fitness_paso_aten)
    _graficar_resultado = staticmethod(graficar_resultado)
    _guardar_resultado_json = staticmethod(guardar_resultado_json)

    # _extraer_frecuencias: no se sobreescribe -- pasa_bajas usa el
    # default de BayesianPreparationService (fc_objetivo / f_paso +
    # f_aten), igual que sus contrapartes de AG y PSO.

    # ------------------------------------------------------------------
    # Logging por consola con más detalle que el genérico (opcional).
    # Columnas adaptadas del código fuente original (fitness_fc de
    # pasa_bajas no trae f_amp, igual que en AG/PSO).
    # ------------------------------------------------------------------

    def _log_encabezado(self, ctx: dict, componentes_ag: list[dict]) -> None:
        modo = ctx["modo"]
        print(
            f"Modo={modo} | Algoritmo=optimizacion_bayesiana | V_fuente={ctx['vs_valor']} V | "
            f"Rs={ctx['rs_valor']} Ω | Rl={ctx['rl_valor']} Ω"
        )
        print(
            f"BO: puntos_iniciales={ctx['n_iniciales']} | iteraciones={ctx['n_iteraciones']} | "
            f"xi={ctx['xi']} | n_candidatos={ctx['n_candidatos']} | n_restarts={ctx['n_restarts']}"
        )
        fc = ctx["frecuencias_ctx"]
        if modo == "BASICO":
            print(f"Fc objetivo={fc['fc_objetivo']} Hz | Pendiente objetivo=80.0 dB/dec\n")
            print(
                f"{'Gen':<6} | {'Fit':<6} | {'Fc (Hz)':<10} | {'Amp (V)':<8} | "
                f"{'Pend (dB/dec)':<15} | {'f_fc':<8} | {'f_pend':<8} | {'f_plano':<8}"
            )
        else:
            print(
                f"F_PASO={fc['f_paso']} Hz | F_ATEN={fc['f_aten']} Hz | "
                f"Pendiente objetivo=80.0 dB/dec\n"
            )
            print(
                f"{'Gen':<6} | {'Fit':<6} | {'Amp Paso (V)':<13} | "
                f"{'Amp Aten (V)':<13} | {'Pend (dB/dec)':<13} | "
                f"{'f_paso':<8} | {'f_aten':<8} | {'f_pend':<8} | {'f_plano':<8}"
            )
        print("-" * 110)

    def _log_generacion(self, gen: int, fit: float, res: tuple, modo: str) -> None:
        if modo == "BASICO":
            # fitness_fc (pasa_bajas) -> (fit, fc, amp_dc, amp_max, pend, f_fc, f_pend, f_plano)
            fc, amp_max, pend = res[1], res[3], res[4]
            f_fc, f_pend, f_plano = res[5], res[6], res[7]
            print(
                f"{gen+1:<6} | {fit:.4f} | {fc:10.1f} | {amp_max:8.2f} | {pend:15.2f} | "
                f"{f_fc:<8.4f} | {f_pend:<8.4f} | {f_plano:<8.4f}"
            )
        else:
            # fitness_paso_aten (pasa_bajas) -> (fit, amp_dc, amp_paso, amp_aten, pendiente, f_paso, f_aten, f_pend, f_plano)
            amp_paso, amp_aten, pend = res[2], res[3], res[4]
            f_paso_s, f_aten_s, f_pend, f_plano = res[5], res[6], res[7], res[8]
            print(
                f"{gen+1:<6} | {fit:.4f} | {amp_paso:13.3f} | {amp_aten:13.4f} | "
                f"{pend:13.2f} | {f_paso_s:<8.4f} | {f_aten_s:<8.4f} | "
                f"{f_pend:<8.4f} | {f_plano:<8.4f}"
            )