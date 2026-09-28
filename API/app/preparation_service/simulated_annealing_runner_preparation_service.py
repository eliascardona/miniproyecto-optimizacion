"""
Preparación genérica de Recocido Simulado (RS) para CUALQUIER filtro.

Estructuralmente es el equivalente de GeneticPreparationService/
ParticleSwarmPreparationService/BayesianPreparationService, pero para RS:
valida la configuración, extrae los componentes del .cir, arma el
contexto de ejecución, y orquesta la corrida delegando el ciclo de
enfriamiento al motor genérico (utils.recocido_simulado.
simulated_annealing_runner) y llamando a los mismos "hooks" de
fitness/gráfica/JSON que ya usan los servicios de AG/PSO/BO para ese
mismo filtro (fitness y métricas son propiedad del FILTRO, no del
algoritmo de búsqueda).

Es una clase INDEPENDIENTE de las otras tres bases, por la misma razón de
siempre: no arriesgar AG/PSO/BO ya verificados.

A diferencia de BayesianPreparationService, run_optimization aquí NO
agrega "tiempo_ejecucion_s" al resultado -- el código fuente de RS no
mide ni reporta tiempo de ejecución (a diferencia de BO), así que esta
combinación siempre construye CircuitoOptimizadoResponse (sin tiempo),
nunca CircuitoOptimizadoConTiempoResponse.

Cada filtro concreto (p.ej. PasaAltasRecocidoPreparationService) debe
fijar estos 6 atributos de clase (los "hooks"):

    config_schema           (type)      -> el schema Pydantic de PasaXConfiguration
    filtro_nombre           (str)       -> nombre de subcarpeta en constants_repository/
    _fitness_fc             (staticmethod) -> fitness del modo BASICO
    _fitness_paso_aten      (staticmethod) -> fitness del modo AVANZADO
    _graficar_resultado     (staticmethod) -> genera y guarda la gráfica PNG
    _guardar_resultado_json (staticmethod) -> arma el dict de resultado final
"""
from pathlib import Path
import re

from fastapi import HTTPException

from app.pydantic_schema.global_validator import safe_parse
from app.constants_repository import ConstantsRepository
from app.utils.recocido_simulado.simulated_annealing_runner import ejecutar_recocido_simulado
from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.spice_formatter import valor_spice


class SimulatedAnnealingPreparationService:

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
    # Validación (idéntica a las otras tres bases)
    # ------------------------------------------------------------------

    def validate_json_config(self, request_data: dict) -> dict:
        parsed, errors = safe_parse(self.config_schema, request_data)
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        return parsed.model_dump()

    # ------------------------------------------------------------------
    # Extracción de componentes del .cir (idéntica a las otras tres bases)
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
                        "es_shunt": "0" in nodos,
                    })
        return detectados

    # ------------------------------------------------------------------
    # Construcción del contexto de ejecución. Igual que en las otras tres
    # bases para entorno/barrido/frecuencias; la única diferencia real es
    # qué hiperparámetros de parametros_optimizador se leen (RS:
    # temp_inicial, temp_final, factor_enfriamiento, iteraciones_por_temp).
    # ------------------------------------------------------------------

    def _build_run_context(self, cfg: dict) -> dict:
        modo = str(cfg["modo"]).upper()
        entorno = cfg["entorno"]
        barrido = cfg["barrido_ac"]
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
            # RS
            "temp_inicial": float(self._buscar(params, "temp_inicial")),
            "temp_final": float(self._buscar(params, "temp_final")),
            "factor_enfriamiento": float(self._buscar(params, "factor_enfriamiento")),
            "iteraciones_por_temp": int(self._buscar(params, "iteraciones_por_temp")),
        }

        ctx["frecuencias_ctx"] = self._extraer_frecuencias(modo, frecuencias, vs_valor)

        return ctx

    @staticmethod
    def _buscar(lista: list[dict], clave: str):
        """Ver la misma nota en GeneticPreparationService._buscar: falla
        con un mensaje claro (GeneticController lo convierte en 422) en
        vez de devolver None en silencio."""
        for p in lista:
            if p.get("clave") == clave:
                return p["valor"]
        claves_recibidas = [p.get("clave") for p in lista]
        raise ValueError(
            f"Falta el parámetro requerido '{clave}'. "
            f"Claves recibidas: {claves_recibidas}. "
            "¿El request trae las claves de otro filtro o de otro algoritmo?"
        )

    def _extraer_frecuencias(self, modo: str, frecuencias: list[dict], vs_valor: float) -> dict:
        """
        Mismo default que las otras tres bases (1 frecuencia objetivo en
        BASICO; f_paso/f_aten en AVANZADO). Un filtro con un shape
        distinto (pasa_banda, rechaza_banda) debe sobreescribir este
        método -- igual que ya hacen sus contrapartes de AG/PSO/BO.
        """
        if modo == "BASICO":
            return {"fc_objetivo": float(self._buscar(frecuencias, "fc_objetivo"))}
        else:
            return {
                "f_paso": float(self._buscar(frecuencias, "f_paso")),
                "f_aten": float(self._buscar(frecuencias, "f_aten")),
                "amp_paso_objetivo": vs_valor,
                "amp_aten_objetivo": 0.0,
            }

    # ------------------------------------------------------------------
    # Fitness unificado (idéntico a las otras tres bases: no depende de
    # qué algoritmo de búsqueda esté llamando)
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
            return self._fitness_fc(**shared, **ctx["frecuencias_ctx"])
        else:
            return self._fitness_paso_aten(**shared, **ctx["frecuencias_ctx"])

    # --- Hooks de fitness/exportación: cada subclase los reemplaza con
    # staticmethod(...) apuntando a utils.genetico.<filtro>.* ---

    def _fitness_fc(self, **kwargs) -> tuple:
        raise NotImplementedError(f"{type(self).__name__} no definió '_fitness_fc'.")

    def _fitness_paso_aten(self, **kwargs) -> tuple:
        raise NotImplementedError(f"{type(self).__name__} no definió '_fitness_paso_aten'.")

    def _graficar_resultado(self, **kwargs) -> None:
        raise NotImplementedError(f"{type(self).__name__} no definió '_graficar_resultado'.")

    def _guardar_resultado_json(self, **kwargs) -> dict:
        raise NotImplementedError(f"{type(self).__name__} no definió '_guardar_resultado_json'.")

    # ------------------------------------------------------------------
    # Logging por consola (genérico por defecto; igual que las otras
    # bases, no afecta la respuesta de la API)
    # ------------------------------------------------------------------

    def _log_encabezado(self, ctx: dict, componentes_ag: list[dict]) -> None:
        print(
            f"Filtro={self.filtro_nombre} | Algoritmo=recocido_simulado | "
            f"Modo={ctx['modo']} | V_fuente={ctx['vs_valor']} V | "
            f"Rs={ctx['rs_valor']} Ω | Rl={ctx['rl_valor']} Ω"
        )
        print(
            f"RS: temp_inicial={ctx['temp_inicial']} | temp_final={ctx['temp_final']} | "
            f"factor_enfriamiento={ctx['factor_enfriamiento']} | "
            f"iteraciones_por_temp={ctx['iteraciones_por_temp']}"
        )
        print("-" * 80)

    def _log_generacion(self, gen: int, fit: float, res: tuple, modo: str) -> None:
        print(f"Ciclo {gen + 1:<4} | fitness={fit:.4f}")

    # ------------------------------------------------------------------
    # Orquestación: arma ctx, corre el recocido genérico, simula el
    # mejor individuo, exporta gráfica + JSON con los hooks del filtro.
    # A diferencia de BayesianPreparationService, NO agrega
    # tiempo_ejecucion_s (RS no lo mide en el código fuente original).
    # ------------------------------------------------------------------

    def run_optimization(self, cfg: dict, componentes_ag: list[dict]) -> dict:
        ctx = self._build_run_context(cfg)
        repo = self.constants_repository

        mejor_global, mejor_fit = ejecutar_recocido_simulado(
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
        print("OPTIMIZACIÓN FINALIZADA (RS)")
        print("Componentes Optimizados:")
        for i, comp in enumerate(componentes_ag):
            lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
            print(f"  {comp['nombre']}: {valor_spice(lista[mejor_global[i]])}")
        print("=" * 50)

        self._graficar_resultado(
            archivo_datos=repo.get_archivo_datos(),
            archivo_salida=repo.get_grafica_archivo(),
            modo=ctx["modo"],
            vs_valor=ctx["vs_valor"],
            **ctx["frecuencias_ctx"],
        )

        return self._guardar_resultado_json(
            mejor_global=mejor_global,
            mejor_fit=mejor_fit,
            componentes_ag=componentes_ag,
            modo=ctx["modo"],
            archivo_datos=repo.get_archivo_datos(),
            archivo_grafica=repo.get_grafica_archivo(),
            **ctx["frecuencias_ctx"],
        )