"""
Conecta GeneticPreparationService con las piezas específicas del filtro
pasa-altas: su schema Pydantic, su subcarpeta de recursos (.cir/lm741.lib),
sus funciones de fitness/métricas y su exportador de resultado.

No repite ninguna de las responsabilidades genéricas (esas ya están en
GeneticPreparationService); esta clase solo "conecta cables".
"""
from app.pydantic_schema.api_request_schema.algorithm_config.pasaaltas import PasaAltasConfiguration
from app.preparation_service.genetic_preparation_service import GeneticPreparationService
from app.utils.genetico.pasa_altas.fitness import fitness_fc, fitness_paso_aten
from app.utils.genetico.pasa_altas.result_exporter import graficar_resultado, guardar_resultado_json


class PasaAltasPreparationService(GeneticPreparationService):
    config_schema = PasaAltasConfiguration
    filtro_nombre = "pasa_altas"

    _fitness_fc = staticmethod(fitness_fc)
    _fitness_paso_aten = staticmethod(fitness_paso_aten)
    _graficar_resultado = staticmethod(graficar_resultado)
    _guardar_resultado_json = staticmethod(guardar_resultado_json)

    # ------------------------------------------------------------------
    # Logging por consola con más detalle que el genérico (opcional; no
    # afecta la respuesta de la API). Se conserva tal cual estaba antes
    # del refactor.
    # ------------------------------------------------------------------

    def _log_encabezado(self, ctx: dict, componentes_ag: list[dict]) -> None:
        modo = ctx["modo"]
        print(
            f"Modo={modo} | V_fuente={ctx['vs_valor']} V | "
            f"Rs={ctx['rs_valor']} Ω | Rl={ctx['rl_valor']} Ω"
        )
        print(
            f"AG: población={ctx['tam_poblacion']} | generaciones={ctx['num_generaciones']} | "
            f"elitismo={ctx['elitismo']} | torneo_k={ctx['torneo_k']} | "
            f"prob_cruce={ctx['prob_cruce']} | prob_mutacion={ctx['prob_mutacion']}"
        )
        fc = ctx["frecuencias_ctx"]
        if modo == "BASICO":
            print(
                f"Fc objetivo={fc['fc_objetivo']} Hz | "
                f"Pendiente objetivo=80.0 dB/dec\n"
            )
            print(
                f"{'Gen':<6} | {'Fit':<6} | {'Fc (Hz)':<10} | {'Amp (V)':<8} | "
                f"{'Pend (dB/dec)':<15} | {'f_fc':<6} | {'f_amp':<6} | "
                f"{'f_pend':<6} | {'f_plano':<7}"
            )
        else:
            print(
                f"F_ATEN={fc['f_aten']} Hz | F_PASO={fc['f_paso']} Hz | "
                f"Pendiente objetivo=80.0 dB/dec\n"
            )
            print(
                f"{'Gen':<6} | {'Fit':<6} | {'Amp Aten (V)':<13} | "
                f"{'Amp Paso (V)':<13} | {'Pend (dB/dec)':<13} | "
                f"{'f_aten':<6} | {'f_paso':<6} | {'f_pend':<6} | {'f_plano':<7}"
            )
        print("-" * 110)

    def _log_generacion(self, gen: int, fit: float, res: tuple, modo: str) -> None:
        if modo == "BASICO":
            fc, amp, pend, f_fc, f_pend, f_plano, f_amp = (
                res[1], res[2], res[3], res[4], res[5], res[6], res[7]
            )
            print(
                f"{gen+1:<6} | {fit:.4f} | {fc:10.1f} | {amp:8.2f} | {pend:15.2f} | "
                f"{f_fc:<6.3f} | {f_amp:<6.3f} | {f_pend:<6.3f} | {f_plano:<7.3f}"
            )
        else:
            amp_paso, amp_aten, pend = res[1], res[2], res[3]
            f_paso_s, f_aten_s, f_pend, f_plano = res[4], res[5], res[6], res[7]
            print(
                f"{gen+1:<6} | {fit:.4f} | {amp_aten:13.4f} | {amp_paso:13.3f} | "
                f"{pend:13.2f} | {f_aten_s:<6.3f} | {f_paso_s:<6.3f} | "
                f"{f_pend:<6.3f} | {f_plano:<7.3f}"
            )