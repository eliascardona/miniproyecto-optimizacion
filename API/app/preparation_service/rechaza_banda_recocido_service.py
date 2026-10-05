"""
Conecta SimulatedAnnealingPreparationService con las piezas específicas
del filtro rechaza-banda.

A diferencia de los otros tres servicios de RS ya integrados (pasa_altas,
pasa_bajas, pasa_banda), aquí NO se reutiliza el fitness del AG: el código
fuente de RS para este filtro trae fórmulas distintas (otros pesos, otra
ancla del -3 dB, otra métrica de pendiente, sin penalización por
saturación y con fitness que devuelven tuplas de 2 elementos). Decisión
confirmada con el usuario: "portar el RS tal cual". Por eso fitness,
métricas y exportador salen de utils.recocido_simulado.rechaza_banda.* y
no de utils.genetico.rechaza_banda.* (ver el docstring de cada módulo para
el detalle de las diferencias).

Piezas propias de este servicio:
  - _extraer_frecuencias: rechaza_banda necesita 2 frecuencias en BASICO y
    4 en AVANZADO (mismo override que sus contrapartes de AG, PSO y BO).
  - _log_encabezado / _log_generacion: el fitness devuelve (fit, amp_max).
  - vs_valor para el exportador: en BASICO el exportador necesita VS para
    recalcular las Fc con la métrica de RS (ancla VS/sqrt(2)), pero
    SimulatedAnnealingPreparationService.run_optimization no lo pasa a
    _guardar_resultado_json (ctx["frecuencias_ctx"] de BASICO solo trae las
    dos Fc objetivo). Se recuerda aquí al armar el contexto. Es seguro: el
    controlador crea una instancia nueva del servicio por request, así que
    no hay estado compartido entre corridas.

Igual que en los demás servicios de RS, la corrida usa el actualizar_circuito
de la API (que inyecta VS, VPP, VNN, RS, RL y .AC), no el compactado del
script de RS, que solo inyectaba VS y .AC.
"""
from app.pydantic_schema.api_request_schema.algorithm_config.rechazabanda import RechazaBandaConfiguration
from app.preparation_service.simulated_annealing_runner_preparation_service import SimulatedAnnealingPreparationService
from app.utils.recocido_simulado.rechaza_banda.fitness import fitness_fc, fitness_paso_aten
from app.utils.recocido_simulado.rechaza_banda.result_exporter import graficar_resultado, guardar_resultado_json


class RechazaBandaRecocidoPreparationService(SimulatedAnnealingPreparationService):
    config_schema = RechazaBandaConfiguration
    filtro_nombre = "rechaza_banda"

    _fitness_fc = staticmethod(fitness_fc)
    _fitness_paso_aten = staticmethod(fitness_paso_aten)
    _graficar_resultado = staticmethod(graficar_resultado)

    # Se llena en _build_run_context (ver docstring del módulo).
    _vs_valor: float | None = None

    def _build_run_context(self, cfg: dict) -> dict:
        ctx = super()._build_run_context(cfg)
        self._vs_valor = ctx["vs_valor"]
        return ctx

    def _guardar_resultado_json(self, **kwargs) -> dict:
        return guardar_resultado_json(vs_valor=self._vs_valor, **kwargs)

    # ------------------------------------------------------------------
    # Mismo override que RechazaBandaPreparationService (AG),
    # RechazaBandaEnjambrePreparationService (PSO) y
    # RechazaBandaBayesianaPreparationService (BO): dos bordes, no uno.
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
    # Logging por consola (opcional; no afecta la respuesta de la API).
    # El fitness de RS para este filtro devuelve (fit, amp_max) en ambos
    # modos, así que solo hay dos columnas que mostrar.
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
            print(
                f"Fc inferior objetivo={fc['fc_inferior_objetivo']} Hz | "
                f"Fc superior objetivo={fc['fc_superior_objetivo']} Hz | "
                f"Pendiente objetivo=40.0 dB/dec (cada flanco)\n"
            )
        else:
            print(
                f"F_PASO_1={fc['f_paso_1']} Hz | F_ATEN_1={fc['f_aten_1']} Hz | "
                f"F_ATEN_2={fc['f_aten_2']} Hz | F_PASO_2={fc['f_paso_2']} Hz\n"
            )
        print(f"{'Ciclo':<6} | {'Fit':<6} | {'AmpMax (V)':<10}")
        print("-" * 32)

    def _log_generacion(self, gen: int, fit: float, res: tuple, modo: str) -> None:
        # fitness_fc / fitness_paso_aten (RS, rechaza_banda) -> (fit, amp_max)  [2 elementos]
        amp_max = res[1]
        print(f"{gen+1:<6} | {fit:.4f} | {amp_max:10.3f}")