"""
Preparación genérica del algoritmo genético para CUALQUIER filtro.

Responsabilidades (lo que antes vivía todo junto en PasaAltasPreparationService):
  - Validar la configuración recibida del controlador.
  - Extraer los componentes del archivo .cir correspondiente al filtro.
  - Construir el contexto de ejecución (ctx) a partir de esa configuración.
  - Orquestar la corrida: arma el ctx, delega el BUCLE del AG al motor
    genérico (utils.genetico.genetic_algorithm_runner), y llama a los
    "hooks" específicos del filtro para fitness/gráfica/JSON de salida.

Lo que este archivo NO sabe: qué significa un buen filtro pasa-altas vs
pasa-bajas, cómo se calculan sus métricas, ni cómo se arma su gráfica o su
JSON de resultado — eso es exclusivo de cada subclase concreta
(PasaAltasPreparationService, PasaBajasPreparationService, ...), que debe
fijar estos 6 atributos de clase (los "hooks"):

    config_schema           (type)      -> el schema Pydantic de PasaXConfiguration
    filtro_nombre           (str)       -> nombre de subcarpeta en constants_repository/
    _fitness_fc             (staticmethod) -> fitness del modo BASICO
    _fitness_paso_aten      (staticmethod) -> fitness del modo AVANZADO
    _graficar_resultado     (staticmethod) -> genera y guarda la gráfica PNG
    _guardar_resultado_json (staticmethod) -> arma el dict de resultado final

`_log_encabezado`/`_log_generacion` son opcionales de sobreescribir (traen
un valor genérico por defecto); no afectan la respuesta de la API, solo el
detalle que se imprime en consola mientras corre el AG.
"""
from pathlib import Path
import re

from fastapi import HTTPException

from app.pydantic_schema.global_validator import safe_parse
from app.constants_repository import ConstantsRepository
from app.utils.genetico.genetic_algorithm_runner import ejecutar_algoritmo_genetico
from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.spice_formatter import valor_spice


class GeneticPreparationService:

    # --- Deben fijarse en cada subclase concreta ---
    config_schema: type = None
    filtro_nombre: str = None

    def __init__(self):
        if self.config_schema is None or self.filtro_nombre is None:
            raise NotImplementedError(
                f"{type(self).__name__} debe definir 'config_schema' y 'filtro_nombre'."
            )
        self.constants_repository = ConstantsRepository(self.filtro_nombre)

    # ------------------------------------------------------------------
    # Validación (genérico: usa el schema que fije la subclase)
    # ------------------------------------------------------------------

    def validate_json_config(self, request_data: dict) -> dict:
        parsed, errors = safe_parse(self.config_schema, request_data)
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        return parsed.model_dump()

    # ------------------------------------------------------------------
    # Extracción de componentes del .cir (genérico: mismo formato de
    # netlist para todos los filtros — solo cambia la topología interna,
    # no la convención de nombres Rn_m / Cn_m)
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
                    detectados.append({
                        "nombre": nombre,
                        "tipo": tipo,
                        "nodos": nodos,
                        "es_shunt": "0" in nodos,  # derivado de la topología real, no del nombre
                    })
        return detectados

    # ------------------------------------------------------------------
    # Construcción del contexto de ejecución (genérico: mismo shape de
    # JSON para todos los filtros)
    # ------------------------------------------------------------------

    def _build_run_context(self, cfg: dict) -> dict:
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
    # Fitness unificado (genérico: dispatcha a los hooks de la subclase)
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
            return self._fitness_fc(**shared, fc_objetivo=ctx["fc_objetivo"])
        else:
            return self._fitness_paso_aten(
                **shared,
                f_paso=ctx["f_paso"],
                f_aten=ctx["f_aten"],
                amp_paso_objetivo=ctx["amp_paso_objetivo"],
                amp_aten_objetivo=ctx["amp_aten_objetivo"],
            )

    # --- Hooks de fitness/exportación: cada subclase los reemplaza con
    # staticmethod(...) apuntando a sus propias utils.genetico.<filtro>.* ---

    def _fitness_fc(self, **kwargs) -> tuple:
        raise NotImplementedError(f"{type(self).__name__} no definió '_fitness_fc'.")

    def _fitness_paso_aten(self, **kwargs) -> tuple:
        raise NotImplementedError(f"{type(self).__name__} no definió '_fitness_paso_aten'.")

    def _graficar_resultado(self, **kwargs) -> None:
        raise NotImplementedError(f"{type(self).__name__} no definió '_graficar_resultado'.")

    def _guardar_resultado_json(self, **kwargs) -> dict:
        raise NotImplementedError(f"{type(self).__name__} no definió '_guardar_resultado_json'.")

    # ------------------------------------------------------------------
    # Logging por consola (genérico por defecto; las subclases pueden dar
    # más detalle sobreescribiendo estos dos métodos — no afecta la
    # respuesta de la API, solo lo que se ve en consola)
    # ------------------------------------------------------------------

    def _log_encabezado(self, ctx: dict, componentes_ag: list[dict]) -> None:
        print(
            f"Filtro={self.filtro_nombre} | Modo={ctx['modo']} | V_fuente={ctx['vs_valor']} V | "
            f"Rs={ctx['rs_valor']} Ω | Rl={ctx['rl_valor']} Ω"
        )
        print(
            f"AG: población={ctx['tam_poblacion']} | generaciones={ctx['num_generaciones']} | "
            f"elitismo={ctx['elitismo']} | torneo_k={ctx['torneo_k']} | "
            f"prob_cruce={ctx['prob_cruce']} | prob_mutacion={ctx['prob_mutacion']}"
        )
        print("-" * 80)

    def _log_generacion(self, gen: int, fit: float, res: tuple, modo: str) -> None:
        print(f"Gen {gen + 1:<4} | fitness={fit:.4f}")

    # ------------------------------------------------------------------
    # Orquestación (genérico: arma ctx, corre el AG genérico, simula el
    # mejor individuo, exporta gráfica + JSON con los hooks del filtro)
    # ------------------------------------------------------------------

    def run_optimization(self, cfg: dict, componentes_ag: list[dict]) -> dict:
        """
        Ejecuta el algoritmo genético completo con la configuración dada.
        Devuelve el diccionario de resultado generado por el hook
        _guardar_resultado_json del filtro concreto.
        """
        ctx = self._build_run_context(cfg)
        repo = self.constants_repository

        mejor_global, mejor_fit = ejecutar_algoritmo_genetico(
            componentes_ag,
            ctx,
            evaluar_individuo=lambda individuo: self._evaluar(individuo, ctx, componentes_ag),
            log_encabezado=self._log_encabezado,
            log_generacion=self._log_generacion,
        )

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
            print(f"  {comp['nombre']}: {valor_spice(lista[mejor_global[i]])}")
        print("=" * 50)

        # Exportar gráfica (hook del filtro)
        self._graficar_resultado(
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

        # Exportar JSON y devolver resultado (hook del filtro)
        return self._guardar_resultado_json(
            mejor_global=mejor_global,
            mejor_fit=mejor_fit,
            componentes_ag=componentes_ag,
            modo=ctx["modo"],
            archivo_datos=repo.get_archivo_datos(),
            archivo_grafica=repo.get_grafica_archivo(),
            f_paso=ctx.get("f_paso"),
            f_aten=ctx.get("f_aten"),
        )