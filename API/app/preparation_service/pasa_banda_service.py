"""
Conecta GeneticPreparationService con las piezas específicas del filtro
pasa-banda: su schema Pydantic, su subcarpeta de recursos (.cir/lm741.lib),
sus funciones de fitness/métricas, su exportador de resultado, y su propio
mapeo de frecuencias (a diferencia de pasa_altas/pasa_bajas, necesita 2
frecuencias en BASICO y 4 en AVANZADO, con otros nombres de clave).
"""
from app.pydantic_schema.api_request_schema.algorithm_config.pasabanda import PasaBandaConfiguration
from app.preparation_service.genetic_preparation_service import GeneticPreparationService
from app.utils.genetico.pasa_banda.fitness import fitness_fc, fitness_paso_aten
from app.utils.genetico.pasa_banda.result_exporter import graficar_resultado, guardar_resultado_json


class PasaBandaPreparationService(GeneticPreparationService):
    config_schema = PasaBandaConfiguration
    filtro_nombre = "pasa_banda"

    _fitness_fc = staticmethod(fitness_fc)
    _fitness_paso_aten = staticmethod(fitness_paso_aten)
    _graficar_resultado = staticmethod(graficar_resultado)
    _guardar_resultado_json = staticmethod(guardar_resultado_json)

    # ------------------------------------------------------------------
    # Único hook "de contexto" que este filtro necesita sobreescribir: el
    # pasa-banda tiene DOS bordes (no uno), así que su JSON de frecuencias
    # trae otras claves (fc_inferior/fc_superior en BASICO;
    # f_aten_1/f_paso_1/f_paso_2/f_aten_2 en AVANZADO) en vez de
    # fc_objetivo / f_paso+f_aten.
    # ------------------------------------------------------------------

    def _extraer_frecuencias(self, modo: str, frecuencias: list[dict], vs_valor: float) -> dict:
        if modo == "BASICO":
            return {
                "fc_inferior_objetivo": float(self._buscar(frecuencias, "fc_inferior")),
                "fc_superior_objetivo": float(self._buscar(frecuencias, "fc_superior")),
            }
        else:
            return {
                "f_aten_1": float(self._buscar(frecuencias, "f_aten_1")),
                "f_paso_1": float(self._buscar(frecuencias, "f_paso_1")),
                "f_paso_2": float(self._buscar(frecuencias, "f_paso_2")),
                "f_aten_2": float(self._buscar(frecuencias, "f_aten_2")),
                "amp_paso_objetivo": vs_valor,
                "amp_aten_objetivo": 0.0,
            }

    # ------------------------------------------------------------------
    # Logging por consola con más detalle que el genérico (opcional; no
    # afecta la respuesta de la API). Columnas adaptadas del código
    # fuente original (tuplas de 12 y 15 elementos, respectivamente).
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
                f"Fc inferior objetivo={fc['fc_inferior_objetivo']} Hz | "
                f"Fc superior objetivo={fc['fc_superior_objetivo']} Hz | "
                f"Pendiente objetivo=40.0 dB/dec (cada borde)\n"
            )
            print(
                f"{'Gen':<6} | {'Fit':<6} | {'AmpMax (V)':<10} | {'FcInf (Hz)':<11} | {'FcSup (Hz)':<11} | "
                f"{'PendSub':<8} | {'PendBaj':<8} | {'f_amp':<7} | {'f_fcInf':<8} | {'f_fcSup':<8} | "
                f"{'f_pSub':<7} | {'f_pBaj':<7} | {'pen_reb':<7}"
            )
        else:
            print(
                f"F_ATEN_1={fc['f_aten_1']} Hz | F_PASO_1={fc['f_paso_1']} Hz | "
                f"F_PASO_2={fc['f_paso_2']} Hz | F_ATEN_2={fc['f_aten_2']} Hz | "
                f"Pendiente objetivo=40.0 dB/dec (cada borde)\n"
            )
            print(
                f"{'Gen':<6} | {'Fit':<6} | {'AmpAten1 (V)':<12} | {'AmpPaso1 (V)':<12} | "
                f"{'AmpPaso2 (V)':<12} | {'AmpAten2 (V)':<12} | {'PendSub':<8} | {'PendBaj':<8} | "
                f"{'f_paso1':<7} | {'f_paso2':<7} | {'f_aten1':<7} | {'f_aten2':<7} | "
                f"{'f_pSub':<7} | {'f_pBaj':<7} | {'pen_aten':<8}"
            )
        print("-" * 150)

    def _log_generacion(self, gen: int, fit: float, res: tuple, modo: str) -> None:
        if modo == "BASICO":
            # fitness_fc (pasa_banda) -> (fit, amp_max, fc_inf, fc_sup, pend_sub, pend_baj,
            #                             f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj, f_amp, pen_rebote)
            amp_max, fc_inf, fc_sup, pend_sub, pend_baj = res[1], res[2], res[3], res[4], res[5]
            f_fc_inf, f_fc_sup, f_pSub, f_pBaj, f_amp, pen_rebote = res[6], res[7], res[8], res[9], res[10], res[11]
            print(
                f"{gen+1:<6} | {fit:.4f} | {amp_max:10.3f} | {fc_inf:11.1f} | {fc_sup:11.1f} | "
                f"{pend_sub:8.2f} | {pend_baj:8.2f} | {f_amp:<7.3f} | {f_fc_inf:<8.3f} | {f_fc_sup:<8.3f} | "
                f"{f_pSub:<7.3f} | {f_pBaj:<7.3f} | {pen_rebote:<7.2f}"
            )
        else:
            # fitness_paso_aten (pasa_banda) -> (fit, amp_max, amp_aten_1, amp_paso_1, amp_paso_2,
            #   amp_aten_2, pend_subida, pend_bajada, f_paso1, f_paso2, f_aten1, f_aten2, f_pSub, f_pBaj, pen_aten)
            amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2 = res[2], res[3], res[4], res[5]
            pend_sub, pend_baj = res[6], res[7]
            f_paso1, f_paso2, f_aten1, f_aten2, f_pSub, f_pBaj, pen_aten = res[8], res[9], res[10], res[11], res[12], res[13], res[14]
            print(
                f"{gen+1:<6} | {fit:.4f} | {amp_aten_1:12.4f} | {amp_paso_1:12.3f} | "
                f"{amp_paso_2:12.3f} | {amp_aten_2:12.4f} | {pend_sub:8.2f} | {pend_baj:8.2f} | "
                f"{f_paso1:<7.3f} | {f_paso2:<7.3f} | {f_aten1:<7.3f} | {f_aten2:<7.3f} | "
                f"{f_pSub:<7.3f} | {f_pBaj:<7.3f} | {pen_aten:<8.2f}"
            )