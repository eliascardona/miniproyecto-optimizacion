"""
Servicio de orquestación del algoritmo genético para el filtro pasa-altas.

Responsabilidades:
  - Validar y transformar la configuración recibida del controlador.
  - Extraer los componentes del archivo .cir.
  - Ejecutar el bucle del AG delegando cada operación a sus utilidades.
  - Exportar los resultados (gráfica + JSON) al final.

Sólo interactúa hacia abajo con: utilidades (utils/).
"""
import numpy as np
from fastapi import HTTPException
from pathlib import Path
import re

from app.pydantic_schema.global_validator import safe_parse
from app.pydantic_schema.api_request_schema.pasaaltas import PasaAltasConfiguration
from app.constants_repository import ConstantsRepository

from app.utils.commercial_series import SERIE_E6, SERIE_E12
from app.utils.genetic_operators import (
    crear_individuo,
    seleccion_torneo,
    cruzar,
    mutar,
)
from app.utils.fitness import fitness_fc, fitness_paso_aten
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.result_exporter import graficar_resultado, guardar_resultado_json


class PasaAltasPreparationService:

    def __init__(self):
        self.constants_repository = ConstantsRepository()

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def validate_json_config(self, request_data: dict) -> dict:
        parsed, errors = safe_parse(PasaAltasConfiguration, request_data)
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        return parsed.model_dump()

    # ------------------------------------------------------------------
    # Extracción de componentes del .cir
    # ------------------------------------------------------------------

    def extract_components(self) -> list[dict]:
        archivo_cir = self.constants_repository.get_archivo_cir()
        texto = Path(archivo_cir).read_text()
        detectados = []
        fijos = {"RS", "RL", "VS", "VPP", "VNN"}
        patron = r"^([CR][a-zA-Z0-9_]*)\s+"

        for linea in texto.splitlines():
            linea = linea.strip()
            m = re.match(patron, linea)
            if m:
                nombre = m.group(1)
                if nombre.upper() not in fijos:
                    partes = linea.split()
                    tipo = "R" if nombre.upper().startswith("R") else "C"
                    nodos = partes[1:3]
                    detectados.append({"nombre": nombre, "tipo": tipo, "nodos": nodos})
        return detectados

    # ------------------------------------------------------------------
    # Construcción del contexto de ejecución
    # ------------------------------------------------------------------

    def _build_run_context(self, cfg: dict) -> dict:
        """
        Transforma la configuración validada (dict plano del schema Pydantic)
        en el contexto completo que necesita el AG, incluyendo las variables
        derivadas (VPP, VNN, amp_paso_objetivo, amp_aten_objetivo).
        """
        modo = str(cfg["modo"]).upper()
        entorno = cfg["entorno"]
        barrido = cfg["barrido_ac"]

        def _buscar(lista, clave):
            return next((p["valor"] for p in lista if p["clave"] == clave), None)

        params = cfg["parametros_optimizador"]
        frecuencias = cfg["frecuencias"]

        vs_valor = float(entorno["v_fuente"])
        vpp = vs_valor + 10.0
        vnn = -(vs_valor + 10.0)

        ctx = {
            "modo": modo,
            "vs_valor": vs_valor,
            "vpp_valor": vpp,
            "vnn_valor": vnn,
            "rs_valor": float(entorno["r_fuente"]),
            "rl_valor": float(entorno["r_carga"]),
            "f_inicial": float(barrido["f_inicial"]),
            "f_final": float(barrido["f_final"]),
            # AG
            "tam_poblacion": int(_buscar(params, "tam_poblacion")),
            "num_generaciones": int(_buscar(params, "num_generaciones")),
            "prob_cruce": float(_buscar(params, "prob_cruce")),
            "prob_mutacion": float(_buscar(params, "prob_mutacion")),
            "elitismo": int(_buscar(params, "elitismo")),
            "torneo_k": int(_buscar(params, "torneo_k")),
        }

        if modo == "BASICO":
            ctx["fc_objetivo"] = float(_buscar(frecuencias, "fc_objetivo"))
        else:
            ctx["f_paso"] = float(_buscar(frecuencias, "f_paso"))
            ctx["f_aten"] = float(_buscar(frecuencias, "f_aten"))
            ctx["amp_paso_objetivo"] = vs_valor
            ctx["amp_aten_objetivo"] = 0.0

        return ctx

    # ------------------------------------------------------------------
    # Función de fitness unificada (despacha según modo)
    # ------------------------------------------------------------------

    def _evaluar(self, individuo: list[int], ctx: dict, componentes_ag: list[dict]) -> tuple:
        repo = self.constants_repository
        shared = dict(
            individuo=individuo,
            componentes_ag=componentes_ag,
            archivo_cir=repo.get_archivo_cir(),
            archivo_datos=repo.get_archivo_datos(),
            ngspice_exe=repo.get_ngspice_exe(),
            vs_valor=ctx["vs_valor"],
            vpp_valor=ctx["vpp_valor"],
            vnn_valor=ctx["vnn_valor"],
            rs_valor=ctx["rs_valor"],
            rl_valor=ctx["rl_valor"],
            f_inicial=ctx["f_inicial"],
            f_final=ctx["f_final"],
        )

        if ctx["modo"] == "BASICO":
            return fitness_fc(**shared, fc_objetivo=ctx["fc_objetivo"])
        else:
            return fitness_paso_aten(
                **shared,
                f_paso=ctx["f_paso"],
                f_aten=ctx["f_aten"],
                amp_paso_objetivo=ctx["amp_paso_objetivo"],
                amp_aten_objetivo=ctx["amp_aten_objetivo"],
            )

    # ------------------------------------------------------------------
    # Logging por consola
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
        if modo == "BASICO":
            print(
                f"Fc objetivo={ctx['fc_objetivo']} Hz | "
                f"Pendiente objetivo=80.0 dB/dec\n"
            )
            print(
                f"{'Gen':<6} | {'Fit':<6} | {'Fc (Hz)':<10} | {'Amp (V)':<8} | "
                f"{'Pend (dB/dec)':<15} | {'f_fc':<6} | {'f_amp':<6} | "
                f"{'f_pend':<6} | {'f_plano':<7}"
            )
        else:
            print(
                f"F_ATEN={ctx['f_aten']} Hz | F_PASO={ctx['f_paso']} Hz | "
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

    # ------------------------------------------------------------------
    # Bucle principal del AG
    # ------------------------------------------------------------------

    def run_optimization(self, cfg: dict, componentes_ag: list[dict]) -> dict:
        """
        Ejecuta el algoritmo genético completo con la configuración dada.
        Devuelve el diccionario de resultado generado por result_exporter.
        """
        ctx = self._build_run_context(cfg)
        repo = self.constants_repository
        num_parametros = len(componentes_ag)

        poblacion = [crear_individuo(componentes_ag) for _ in range(ctx["tam_poblacion"])]
        mejor_global: list[int] | None = None
        mejor_fit = -1.0
        cache_fitness: dict[tuple, tuple] = {}

        def evaluar_con_cache(individuo: list[int]) -> tuple:
            clave = tuple(individuo)
            if clave not in cache_fitness:
                cache_fitness[clave] = self._evaluar(individuo, ctx, componentes_ag)
            return cache_fitness[clave]

        self._log_encabezado(ctx, componentes_ag)

        for gen in range(ctx["num_generaciones"]):
            resultados = [evaluar_con_cache(ind) for ind in poblacion]
            fitnesses = [r[0] for r in resultados]

            idx_best = int(np.argmax(fitnesses))
            if fitnesses[idx_best] > mejor_fit:
                mejor_fit = fitnesses[idx_best]
                mejor_global = poblacion[idx_best][:]

            self._log_generacion(gen, fitnesses[idx_best], resultados[idx_best], ctx["modo"])

            # Elitismo + nueva generación
            indices_ordenados = np.argsort(fitnesses)[::-1]
            nueva_pob = [poblacion[i][:] for i in indices_ordenados[: ctx["elitismo"]]]

            while len(nueva_pob) < ctx["tam_poblacion"]:
                p1 = seleccion_torneo(poblacion, fitnesses, ctx["torneo_k"])
                p2 = seleccion_torneo(poblacion, fitnesses, ctx["torneo_k"])
                h1, h2 = cruzar(p1, p2, ctx["prob_cruce"], num_parametros)
                mutar(h1, componentes_ag, ctx["prob_mutacion"])
                nueva_pob.append(h1)
                if len(nueva_pob) < ctx["tam_poblacion"]:
                    mutar(h2, componentes_ag, ctx["prob_mutacion"])
                    nueva_pob.append(h2)

            poblacion = nueva_pob

        # Simulación final con el mejor individuo
        actualizar_circuito(
            mejor_global, componentes_ag, repo.get_archivo_cir(),
            ctx["vs_valor"], ctx["vpp_valor"], ctx["vnn_valor"],
            ctx["rs_valor"], ctx["rl_valor"], ctx["f_inicial"], ctx["f_final"],
        )
        ejecutar_spice(repo.get_ngspice_exe(), repo.get_archivo_cir())

        print("\n" + "=" * 50)
        print("OPTIMIZACIÓN FINALIZADA")
        print("Componentes Optimizados:")
        for i, comp in enumerate(componentes_ag):
            lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
            from app.utils.spice_formatter import valor_spice
            print(f"  {comp['nombre']}: {valor_spice(lista[mejor_global[i]])}")
        print("=" * 50)

        # Exportar gráfica
        graficar_resultado(
            archivo_datos=repo.get_archivo_datos(),
            archivo_salida=repo.get_grafica_archivo(),
            modo=ctx["modo"],
            vs_valor=ctx["vs_valor"],
            fc_objetivo=ctx.get("fc_objetivo"),
            f_paso=ctx.get("f_paso"),
            f_aten=ctx.get("f_aten"),
            amp_paso_objetivo=ctx.get("amp_paso_objetivo"),
            amp_aten_objetivo=ctx.get("amp_aten_objetivo"),
        )

        # Exportar JSON y devolver resultado
        return guardar_resultado_json(
            mejor_global=mejor_global,
            mejor_fit=mejor_fit,
            componentes_ag=componentes_ag,
            modo=ctx["modo"],
            archivo_datos=repo.get_archivo_datos(),
            archivo_grafica=repo.get_grafica_archivo(),
            archivo_salida=repo.get_resultado_json(),
            f_paso=ctx.get("f_paso"),
            f_aten=ctx.get("f_aten"),
        )