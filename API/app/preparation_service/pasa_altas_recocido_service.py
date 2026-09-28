"""
Conecta SimulatedAnnealingPreparationService con las piezas específicas
del filtro pasa-altas.

Reutiliza TAL CUAL utils.genetico.pasa_altas.fitness (pesos idénticos al
AG: 0.2/0.4/0.2/0.2 y 0.4/0.3/0.1/0.2, mismas calcular_f_plano/
calcular_metricas_fc/calcular_metricas_paso_aten) y graficar_resultado
(idéntica al AG).

_guardar_resultado_json es la única pieza donde NO se sigue el código
fuente de RS literalmente: esa versión no incluye grafica_png_base64 ni
tipo/conexion_tierra en cada componente, campos requeridos por
CircuitoOptimizadoResponse (ver la nota completa en la respuesta al
usuario). Se reutiliza el guardar_resultado_json completo, el mismo que
ya usan AG/PSO/BO para este filtro, para no romper el contrato de la API.
"""
from app.pydantic_schema.api_request_schema.algorithm_config.pasaaltas import PasaAltasConfiguration
from app.preparation_service.simulated_annealing_runner_preparation_service import SimulatedAnnealingPreparationService
from app.utils.genetico.pasa_altas.fitness import fitness_fc, fitness_paso_aten
from app.utils.genetico.pasa_altas.result_exporter import graficar_resultado, guardar_resultado_json


class PasaAltasRecocidoPreparationService(SimulatedAnnealingPreparationService):
    config_schema = PasaAltasConfiguration
    filtro_nombre = "pasa_altas"

    _fitness_fc = staticmethod(fitness_fc)
    _fitness_paso_aten = staticmethod(fitness_paso_aten)
    _graficar_resultado = staticmethod(graficar_resultado)
    _guardar_resultado_json = staticmethod(guardar_resultado_json)

    # _extraer_frecuencias: no se sobreescribe -- pasa_altas usa el
    # default de SimulatedAnnealingPreparationService (fc_objetivo /
    # f_paso + f_aten), igual que sus contrapartes de AG, PSO y BO.

    # ------------------------------------------------------------------
    # Logging por consola con más detalle que el genérico (opcional).
    # Mismas columnas que las versiones de AG/PSO/BO, porque fitness_fc/
    # fitness_paso_aten son las mismas funciones y devuelven exactamente
    # la misma forma de tupla. El código fuente original de RS no traía
    # un desglose así de detallado (solo imprimía Ciclo/Temp/Mejor Fit);
    # se enriquece aquí para que la consola dé la misma visibilidad que
    # ya tienen AG/PSO/BO.
    # ------------------------------------------------------------------

    def _log_encabezado(self, ctx: dict, componentes_ag: list[dict]) -> None:
        modo = ctx["modo"]
        print(
            f"Modo={modo} | Algoritmo=recocido_simulado | V_fuente={ctx['vs_valor']} V | "
            f"Rs={ctx['rs_valor']} Ω | Rl={ctx['rl_valor']} Ω"
        )
        print(
            f"RS: temp_inicial={ctx['temp_inicial']} | temp_final={ctx['temp_final']} | "
            f"factor_enfriamiento={ctx['factor_enfriamiento']} | "
            f"iteraciones_por_temp={ctx['iteraciones_por_temp']}"
        )
        fc = ctx["frecuencias_ctx"]
        if modo == "BASICO":
            print(f"Fc objetivo={fc['fc_objetivo']} Hz | Pendiente objetivo=80.0 dB/dec\n")
            print(
                f"{'Ciclo':<6} | {'Fit':<6} | {'Fc (Hz)':<10} | {'Amp (V)':<8} | "
                f"{'Pend (dB/dec)':<15} | {'f_fc':<6} | {'f_amp':<6} | "
                f"{'f_pend':<6} | {'f_plano':<7}"
            )
        else:
            print(
                f"F_ATEN={fc['f_aten']} Hz | F_PASO={fc['f_paso']} Hz | "
                f"Pendiente objetivo=80.0 dB/dec\n"
            )
            print(
                f"{'Ciclo':<6} | {'Fit':<6} | {'Amp Aten (V)':<13} | "
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