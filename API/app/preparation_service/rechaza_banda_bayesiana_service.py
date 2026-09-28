"""
Conecta BayesianPreparationService con las piezas específicas del filtro
rechaza-banda.

Comparé línea por línea el fitness (pesos 0.4/0.4/0.1/0.1 y
0.15/0.15/0.25/0.25/0.1/0.1, sin compuerta dura de rebote -- misma razón
física que en AG/PSO: la topología Twin-T pasa en ambos extremos) y las
métricas (_cruce_interpolado, _safe_div, calcular_metricas_fc con
división por el valle, calcular_metricas_paso_aten con interpolación
puntual) contra el código fuente de BO: son IDÉNTICOS a los de
utils.genetico.rechaza_banda -- así que, igual que con pasa_altas,
pasa_bajas y pasa_banda, todo se reutiliza tal cual.

Único punto genuino de este servicio: sobreescribir _extraer_frecuencias,
porque rechaza_banda necesita 2 frecuencias en BASICO y 4 en AVANZADO
(mismas claves que sus contrapartes de AG y PSO para este filtro).
"""
from app.pydantic_schema.api_request_schema.algorithm_config.rechazabanda import RechazaBandaConfiguration
from app.preparation_service.bayesian_preparation_service import BayesianPreparationService
from app.utils.genetico.rechaza_banda.fitness import fitness_fc, fitness_paso_aten
from app.utils.genetico.rechaza_banda.result_exporter import graficar_resultado, guardar_resultado_json


class RechazaBandaBayesianaPreparationService(BayesianPreparationService):
    config_schema = RechazaBandaConfiguration
    filtro_nombre = "rechaza_banda"

    _fitness_fc = staticmethod(fitness_fc)
    _fitness_paso_aten = staticmethod(fitness_paso_aten)
    _graficar_resultado = staticmethod(graficar_resultado)
    _guardar_resultado_json = staticmethod(guardar_resultado_json)

    # ------------------------------------------------------------------
    # Mismo override que RechazaBandaPreparationService (AG) y
    # RechazaBandaEnjambrePreparationService (PSO): dos bordes, no uno.
    # ------------------------------------------------------------------

    def _extraer_frecuencias(self, modo: str, frecuencias: list[dict], vs_valor: float) -> dict:
        if modo == "BASICO":
            return {
                "fc_inferior_objetivo": float(self._buscar(frecuencias, "fc_inferior")),
                "fc_superior_objetivo": float(self._buscar(frecuencias, "fc_superior")),
            }
        else:
            return {
                "f_paso_1": float(self._buscar(frecuencias, "f_paso_1")),
                "f_aten_1": float(self._buscar(frecuencias, "f_aten_1")),
                "f_aten_2": float(self._buscar(frecuencias, "f_aten_2")),
                "f_paso_2": float(self._buscar(frecuencias, "f_paso_2")),
                "amp_paso_objetivo": vs_valor,
                "amp_aten_objetivo": 0.0,
            }

    # ------------------------------------------------------------------
    # Logging por consola con más detalle que el genérico (opcional).
    # Mismas columnas que RechazaBandaPreparationService (AG): mismas
    # funciones de fitness, misma forma de tupla (9 y 13 elementos, sin
    # columna de rebote -- ver la nota del módulo).
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
                f"Pendiente objetivo=40.0 dB/dec (cada flanco)\n"
            )
            print(
                f"{'Gen':<6} | {'Fit':<6} | {'FcInf (Hz)':<11} | {'FcSup (Hz)':<11} | "
                f"{'PendSub':<8} | {'PendBaj':<8} | {'f_fcInf':<8} | {'f_fcSup':<8} | "
                f"{'f_pSub':<7} | {'f_pBaj':<7}"
            )
        else:
            print(
                f"F_PASO_1={fc['f_paso_1']} Hz | F_ATEN_1={fc['f_aten_1']} Hz | "
                f"F_ATEN_2={fc['f_aten_2']} Hz | F_PASO_2={fc['f_paso_2']} Hz | "
                f"Pendiente objetivo=40.0 dB/dec (cada flanco)\n"
            )
            print(
                f"{'Gen':<6} | {'Fit':<6} | {'AmpPaso1 (V)':<12} | {'AmpAten1 (V)':<12} | "
                f"{'AmpAten2 (V)':<12} | {'AmpPaso2 (V)':<12} | {'PendBaj':<8} | {'PendSub':<8} | "
                f"{'f_paso1':<7} | {'f_paso2':<7} | {'f_aten1':<7} | {'f_aten2':<7} | "
                f"{'f_pBaj':<7} | {'f_pSub':<7}"
            )
        print("-" * 140)

    def _log_generacion(self, gen: int, fit: float, res: tuple, modo: str) -> None:
        if modo == "BASICO":
            # fitness_fc (rechaza_banda) -> (fit, fc_inf, fc_sup, pend_sub, pend_baj,
            #                                 f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj)  [9 elementos]
            fc_inf, fc_sup, pend_sub, pend_baj = res[1], res[2], res[3], res[4]
            f_fc_inf, f_fc_sup, f_pSub, f_pBaj = res[5], res[6], res[7], res[8]
            print(
                f"{gen+1:<6} | {fit:.4f} | {fc_inf:11.1f} | {fc_sup:11.1f} | "
                f"{pend_sub:8.2f} | {pend_baj:8.2f} | {f_fc_inf:<8.3f} | {f_fc_sup:<8.3f} | "
                f"{f_pSub:<7.3f} | {f_pBaj:<7.3f}"
            )
        else:
            # fitness_paso_aten (rechaza_banda) -> (fit, amp_aten_1, amp_paso_1, amp_paso_2,
            #   amp_aten_2, pend_subida, pend_bajada, f_paso1, f_paso2, f_aten1, f_aten2,
            #   f_pend_subida, f_pend_bajada)  [13 elementos]
            amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2 = res[1], res[2], res[3], res[4]
            pend_sub, pend_baj = res[5], res[6]
            f_paso1, f_paso2, f_aten1, f_aten2, f_pSub, f_pBaj = res[7], res[8], res[9], res[10], res[11], res[12]
            print(
                f"{gen+1:<6} | {fit:.4f} | {amp_paso_1:12.4f} | {amp_aten_1:12.4f} | "
                f"{amp_aten_2:12.4f} | {amp_paso_2:12.4f} | {pend_baj:8.2f} | {pend_sub:8.2f} | "
                f"{f_paso1:<7.3f} | {f_paso2:<7.3f} | {f_aten1:<7.3f} | {f_aten2:<7.3f} | "
                f"{f_pBaj:<7.3f} | {f_pSub:<7.3f}"
            )