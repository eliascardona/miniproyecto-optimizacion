"""
Conecta ParticleSwarmPreparationService con las piezas específicas del
filtro pasa-bajas.

A diferencia de PasaAltasEnjambrePreparationService (donde TODO se
reutiliza del AG sin cambios), aquí los imports se mezclan a propósito:

  - _fitness_fc          -> utils.enjambre_particulas.pasa_bajas.fitness
                             (pesos propios de PSO, confirmados con el
                             usuario como una diferencia intencional del
                             equipo de algoritmos, no un error)
  - _fitness_paso_aten    -> utils.genetico.pasa_bajas.fitness
                             (idéntica a la del AG: mismos pesos)
  - _graficar_resultado /
    _guardar_resultado_json -> utils.genetico.pasa_bajas.result_exporter
                             (no dependen de los pesos del fitness, solo
                             de las métricas -- que sí son idénticas)
"""
from app.pydantic_schema.api_request_schema.algorithm_config.pasabajas import PasaBajasConfiguration
from app.preparation_service.particle_swarm_service import ParticleSwarmPreparationService
from app.utils.enjambre_particulas.pasa_bajas.fitness import fitness_fc
from app.utils.genetico.pasa_bajas.fitness import fitness_paso_aten
from app.utils.genetico.pasa_bajas.result_exporter import graficar_resultado, guardar_resultado_json


class PasaBajasEnjambrePreparationService(ParticleSwarmPreparationService):
    config_schema = PasaBajasConfiguration
    filtro_nombre = "pasa_bajas"

    _fitness_fc = staticmethod(fitness_fc)
    _fitness_paso_aten = staticmethod(fitness_paso_aten)
    _graficar_resultado = staticmethod(graficar_resultado)
    _guardar_resultado_json = staticmethod(guardar_resultado_json)

    # _extraer_frecuencias: no se sobreescribe -- pasa_bajas usa el
    # default de ParticleSwarmPreparationService (fc_objetivo / f_paso +
    # f_aten), igual que su contraparte de AG.

    # ------------------------------------------------------------------
    # Logging por consola con más detalle que el genérico (opcional).
    # Columnas adaptadas del código fuente original (fitness_fc de PSO
    # para pasa_bajas no trae f_amp, igual que la versión de AG).
    # ------------------------------------------------------------------

    def _log_encabezado(self, ctx: dict, componentes_ag: list[dict]) -> None:
        modo = ctx["modo"]
        print(
            f"Modo={modo} | Algoritmo=enjambre_particulas | V_fuente={ctx['vs_valor']} V | "
            f"Rs={ctx['rs_valor']} Ω | Rl={ctx['rl_valor']} Ω"
        )
        print(
            f"PSO: partículas={ctx['num_particulas']} | iteraciones={ctx['num_iteraciones']} | "
            f"w={ctx['w']} | c1={ctx['c1']} | c2={ctx['c2']}"
        )
        fc = ctx["frecuencias_ctx"]
        if modo == "BASICO":
            print(f"Fc objetivo={fc['fc_objetivo']} Hz | Pendiente objetivo=80.0 dB/dec\n")
            print(
                f"{'Iter':<6} | {'Fit':<6} | {'Fc (Hz)':<10} | {'Amp (V)':<8} | "
                f"{'Pend (dB/dec)':<15} | {'f_fc':<8} | {'f_pend':<8} | {'f_plano':<8}"
            )
        else:
            print(
                f"F_PASO={fc['f_paso']} Hz | F_ATEN={fc['f_aten']} Hz | "
                f"Pendiente objetivo=80.0 dB/dec\n"
            )
            print(
                f"{'Iter':<6} | {'Fit':<6} | {'Amp Paso (V)':<13} | "
                f"{'Amp Aten (V)':<13} | {'Pend (dB/dec)':<13} | "
                f"{'f_paso':<8} | {'f_aten':<8} | {'f_pend':<8} | {'f_plano':<8}"
            )
        print("-" * 110)

    def _log_generacion(self, gen: int, fit: float, res: tuple, modo: str) -> None:
        if modo == "BASICO":
            # fitness_fc (PSO, pasa_bajas) -> (fit, fc, amp_dc, amp_max, pend, f_fc, f_pend, f_plano)
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