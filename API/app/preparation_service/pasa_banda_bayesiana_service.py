"""
Conecta BayesianPreparationService con las piezas específicas del filtro
pasa-banda.

Comparé línea por línea el fitness (pesos 0.25/0.25/0.125/0.125/0.25 y
0.25/0.25/0.15/0.15/0.1/0.1, misma compuerta dura de rebote:
REBOTE_TOLERADO_REL=0.03, PENALIZACION_ATEN_FALLO=0.1) y las métricas
(_cruce_interpolado, _peor_rebote, calcular_metricas_fc,
calcular_metricas_paso_aten) contra el código fuente de BO: son
IDÉNTICOS a los de utils.genetico.pasa_banda -- igual que pasó con
PasaAltasBayesianaPreparationService, todo se reutiliza tal cual.

Único punto genuino de este servicio: sobreescribir _extraer_frecuencias,
porque pasa_banda necesita 2 frecuencias en BASICO y 4 en AVANZADO
(mismo patrón que sus contrapartes de AG y PSO para este filtro).
"""
from app.pydantic_schema.api_request_schema.algorithm_config.pasabanda import PasaBandaConfiguration
from app.preparation_service.bayesian_preparation_service import BayesianPreparationService
from app.utils.genetico.pasa_banda.fitness import fitness_fc, fitness_paso_aten
from app.utils.genetico.pasa_banda.result_exporter import graficar_resultado, guardar_resultado_json


class PasaBandaBayesianaPreparationService(BayesianPreparationService):
    config_schema = PasaBandaConfiguration
    filtro_nombre = "pasa_banda"

    _fitness_fc = staticmethod(fitness_fc)
    _fitness_paso_aten = staticmethod(fitness_paso_aten)
    _graficar_resultado = staticmethod(graficar_resultado)
    _guardar_resultado_json = staticmethod(guardar_resultado_json)

    # ------------------------------------------------------------------
    # Mismo override que PasaBandaPreparationService (AG) y
    # PasaBandaEnjambrePreparationService (PSO): dos bordes, no uno.
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
    # Logging por consola con más detalle que el genérico (opcional).
    # Mismas columnas que PasaBandaPreparationService (AG): mismas
    # funciones de fitness, misma forma de tupla (12 y 15 elementos).
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