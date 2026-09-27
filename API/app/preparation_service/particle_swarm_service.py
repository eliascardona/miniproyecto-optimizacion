"""
Preparación genérica del algoritmo de Enjambre de Partículas (PSO) para
CUALQUIER filtro.

Estructuralmente es el equivalente de GeneticPreparationService, pero
para PSO en vez de AG: valida la configuración, extrae los componentes
del .cir, arma el contexto de ejecución, y orquesta la corrida delegando
el ciclo de PSO al motor genérico (utils.enjambre_particulas.
particle_swarm_runner) y llamando a los mismos "hooks" de fitness/gráfica/
JSON que ya usan los servicios de AG para ese mismo filtro (fitness y
métricas son propiedad del FILTRO, no del algoritmo de búsqueda — por
eso PasaAltasEnjambrePreparationService reutiliza sin cambios
utils.genetico.pasa_altas.fitness/metrics/result_exporter).

Es una clase INDEPENDIENTE de GeneticPreparationService (no hereda de
ella ni comparte una base común), a propósito: extraer una base común
implicaría tocar GeneticPreparationService, que ya está verificado para
4 filtros con AG, y el objetivo aquí es agregar PSO sin arriesgar eso.
Duplica una porción moderada de código (validate_json_config,
extract_components, _evaluar, la cola de run_optimization) a cambio de
mantener el AG completamente aislado de este cambio.

Cada filtro concreto (p.ej. PasaAltasEnjambrePreparationService) debe
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
from app.utils.enjambre_particulas.particule_swarm_runner import ejecutar_pso
from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice
from app.utils.spice_formatter import valor_spice


class ParticleSwarmPreparationService:

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
    # Validación (idéntica a GeneticPreparationService)
    # ------------------------------------------------------------------

    def validate_json_config(self, request_data: dict) -> dict:
        parsed, errors = safe_parse(self.config_schema, request_data)
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        return parsed.model_dump()

    # ------------------------------------------------------------------
    # Extracción de componentes del .cir (idéntica a GeneticPreparationService)
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
    # Construcción del contexto de ejecución. Igual que en
    # GeneticPreparationService para entorno/barrido/frecuencias; la
    # única diferencia real es qué hiperparámetros de
    # parametros_optimizador se leen (PSO: num_particulas, num_iteraciones,
    # w, c1, c2 -- en vez de tam_poblacion, num_generaciones, etc.).
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
            # PSO
            "num_particulas": int(self._buscar(params, "num_particulas")),
            "num_iteraciones": int(self._buscar(params, "num_iteraciones")),
            "w": float(self._buscar(params, "w")),
            "c1": float(self._buscar(params, "c1")),
            "c2": float(self._buscar(params, "c2")),
        }

        ctx["frecuencias_ctx"] = self._extraer_frecuencias(modo, frecuencias, vs_valor)

        return ctx

    @staticmethod
    def _buscar(lista: list[dict], clave: str):
        """Busca un {clave, valor} por su 'clave' dentro de una lista (sirve
        tanto para parametros_optimizador como para frecuencias).

        Antes devolvía None en silencio si la clave no estaba, y quien
        llamaba hacía int(None)/float(None), que revienta con un
        TypeError críptico varios niveles más abajo (sin decir CUÁL
        clave faltaba). Ahora falla aquí mismo, con un mensaje claro que
        GeneticController convierte en un 422 útil en vez de un 500 con
        traceback -- típicamente indica que el request trae las claves
        de otro filtro o de otro algoritmo (parametros_optimizador y
        frecuencias no son intercambiables entre combinaciones).
        """
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
        Mismo default que GeneticPreparationService (1 frecuencia objetivo
        en BASICO; f_paso/f_aten en AVANZADO). Un filtro con un shape
        distinto (pasa_banda, rechaza_banda) debe sobreescribir este
        método -- igual que ya hacen sus contrapartes de AG.
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
    # Fitness unificado (idéntico a GeneticPreparationService: no
    # depende de qué algoritmo de búsqueda esté llamando)
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
    # staticmethod(...) apuntando a utils.genetico.<filtro>.* (SÍ, la
    # misma ruta "genetico" que usa el AG -- el fitness es del filtro,
    # no del algoritmo; ver el docstring del módulo) ---

    def _fitness_fc(self, **kwargs) -> tuple:
        raise NotImplementedError(f"{type(self).__name__} no definió '_fitness_fc'.")

    def _fitness_paso_aten(self, **kwargs) -> tuple:
        raise NotImplementedError(f"{type(self).__name__} no definió '_fitness_paso_aten'.")

    def _graficar_resultado(self, **kwargs) -> None:
        raise NotImplementedError(f"{type(self).__name__} no definió '_graficar_resultado'.")

    def _guardar_resultado_json(self, **kwargs) -> dict:
        raise NotImplementedError(f"{type(self).__name__} no definió '_guardar_resultado_json'.")

    # ------------------------------------------------------------------
    # Logging por consola (genérico por defecto; igual que en
    # GeneticPreparationService, no afecta la respuesta de la API)
    # ------------------------------------------------------------------

    def _log_encabezado(self, ctx: dict, componentes_ag: list[dict]) -> None:
        print(
            f"Filtro={self.filtro_nombre} | Algoritmo=enjambre_particulas | "
            f"Modo={ctx['modo']} | V_fuente={ctx['vs_valor']} V | "
            f"Rs={ctx['rs_valor']} Ω | Rl={ctx['rl_valor']} Ω"
        )
        print(
            f"PSO: partículas={ctx['num_particulas']} | iteraciones={ctx['num_iteraciones']} | "
            f"w={ctx['w']} | c1={ctx['c1']} | c2={ctx['c2']}"
        )
        print("-" * 80)

    def _log_generacion(self, gen: int, fit: float, res: tuple, modo: str) -> None:
        print(f"Iter {gen + 1:<4} | fitness={fit:.4f}")

    # ------------------------------------------------------------------
    # Orquestación: arma ctx, corre el PSO genérico, simula el mejor
    # individuo, exporta gráfica + JSON con los hooks del filtro. Misma
    # estructura que GeneticPreparationService.run_optimization, solo
    # que delega a ejecutar_pso en vez de ejecutar_algoritmo_genetico.
    # ------------------------------------------------------------------

    def run_optimization(self, cfg: dict, componentes_ag: list[dict]) -> dict:
        ctx = self._build_run_context(cfg)
        repo = self.constants_repository

        mejor_global, mejor_fit = ejecutar_pso(
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
        print("OPTIMIZACIÓN FINALIZADA (PSO)")
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