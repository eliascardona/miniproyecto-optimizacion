"""
Controlador del filtro pasa-altas. Responsabilidades:
  - Recibir el request_data crudo desde la ruta FastAPI.
  - Delegar TODA la lógica al servicio.
  - Empaquetar el resultado del servicio en la respuesta Pydantic de salida.
"""
from fastapi import HTTPException

from app.preparation_service.pasa_altas_service import PasaAltasPreparationService
from app.preparation_service.pasa_bajas_service import PasaBajasPreparationService
from app.preparation_service.pasa_banda_service import PasaBandaPreparationService
from app.preparation_service.rechaza_banda_service import RechazaBandaPreparationService
from app.preparation_service.pasa_altas_enjambre_service import PasaAltasEnjambrePreparationService
from app.preparation_service.pasa_bajas_enjambre_service import PasaBajasEnjambrePreparationService
from app.preparation_service.pasa_banda_enjambre_service import PasaBandaEnjambrePreparationService
from app.preparation_service.rechaza_banda_enjambre_service import RechazaBandaEnjambrePreparationService
from app.preparation_service.pasa_altas_bayesiana_service import PasaAltasBayesianaPreparationService
from app.preparation_service.pasa_altas_recocido_service import PasaAltasRecocidoPreparationService
from app.preparation_service.pasa_bajas_recocido_service import PasaBajasRecocidoPreparationService
from app.preparation_service.pasa_banda_recocido_service import PasaBandaRecocidoPreparationService
from app.preparation_service.rechaza_banda_recocido_service import RechazaBandaRecocidoPreparationService
from app.preparation_service.pasa_bajas_bayesiana_service import PasaBajasBayesianaPreparationService
from app.preparation_service.pasa_banda_bayesiana_service import PasaBandaBayesianaPreparationService
from app.preparation_service.rechaza_banda_bayesiana_service import RechazaBandaBayesianaPreparationService
from app.pydantic_schema.api_response_schema.circuit_response import (
    CircuitoOptimizadoResponse,
    CircuitoOptimizadoConTiempoResponse,
)
from app.pydantic_schema.api_request_schema.circuit_optimization_request import CircuitOptimizationRequest
from app.utils.esquema.respuesta import extras_de_respuesta


class IndividualOptimizationController:

    # Doble switch como diccionario de servicios. El nombre de la clase
    # quedó de cuando solo existía el AG; ahora también enruta PSO
    # (enjambre_particulas). No la renombré en este cambio para no tocar
    # unique_entrypoint.py de más -- si quieres, en un próximo paso la
    # renombro a algo como OptimizationController.
    SERVICE_MAP = {
        ("pasa_altas", "algoritmo_genetico"): PasaAltasPreparationService,
        ("pasa_bajas", "algoritmo_genetico"): PasaBajasPreparationService,
        ("pasa_banda", "algoritmo_genetico"): PasaBandaPreparationService,
        ("rechaza_banda", "algoritmo_genetico"): RechazaBandaPreparationService,
        ("pasa_altas", "enjambre_particulas"): PasaAltasEnjambrePreparationService,
        ("pasa_bajas", "enjambre_particulas"): PasaBajasEnjambrePreparationService,
        ("pasa_banda", "enjambre_particulas"): PasaBandaEnjambrePreparationService,
        ("rechaza_banda", "enjambre_particulas"): RechazaBandaEnjambrePreparationService,
        ("pasa_altas", "optimizacion_bayesiana"): PasaAltasBayesianaPreparationService,
        ("pasa_altas", "recocido_simulado"): PasaAltasRecocidoPreparationService,
        ("pasa_bajas", "recocido_simulado"): PasaBajasRecocidoPreparationService,
        ("pasa_banda", "recocido_simulado"): PasaBandaRecocidoPreparationService,
        ("rechaza_banda", "recocido_simulado"): RechazaBandaRecocidoPreparationService,
        ("pasa_bajas", "optimizacion_bayesiana"): PasaBajasBayesianaPreparationService,
        ("pasa_banda", "optimizacion_bayesiana"): PasaBandaBayesianaPreparationService,
        ("rechaza_banda", "optimizacion_bayesiana"): RechazaBandaBayesianaPreparationService,
    }

    @staticmethod
    def _extras(service, filtro: str, circuit_config: dict, result: dict) -> dict:
        # El entorno (Vs, Rs, Rl, Vpp, Vnn) sale del MISMO _build_run_context que usó la
        # optimización: así el esquema nunca contradice a la simulación (p. ej. Vpp = Vs + 10).
        try:
            entorno = service._build_run_context(circuit_config)
        except Exception:                                    # noqa: BLE001
            entorno = {}
        return extras_de_respuesta(filtro, result, entorno, service.constants_repository.get_archivo_datos())

    def optimize(self, request: CircuitOptimizationRequest) -> CircuitoOptimizadoResponse:
        key = (request.filtro, request.algoritmo)
        service_class = self.SERVICE_MAP.get(key)

        if service_class is None:
            raise HTTPException(
                status_code=422,
                detail=f"Sin servicio para: {key}",
            )

        service = service_class()

        # Cada servicio trabaja en su propio directorio temporal (ver
        # ConstantsRepository). Se borra SIEMPRE al terminar la petición,
        # salga bien o mal: el resultado ya trae la gráfica codificada en
        # base64 y no depende de ningún archivo del directorio.
        try:
            circuit_config = service.validate_json_config(request.entorno)
            componentes = service.extract_components()

            try:
                result = service.run_optimization(cfg=circuit_config, componentes_ag=componentes)
            except ValueError as e:
                # Típicamente: parametros_optimizador o frecuencias traen las
                # claves de otro filtro/algoritmo (ver GeneticPreparationService._buscar
                # y sus equivalentes en ParticleSwarmPreparationService/
                # BayesianPreparationService). Es un problema del request, no
                # del servidor -> 422, no 500.
                raise HTTPException(status_code=422, detail=str(e))
            except RuntimeError as e:
                raise HTTPException(status_code=500, detail=str(e))

            # Datos extra para el cliente: esquema del circuito optimizado y curva de
            # respuesta. Se calculan AQUÍ porque el directorio de trabajo (con el
            # datos_filtro.txt del mejor individuo) existe hasta el `finally`.
            result.update(self._extras(service, request.filtro, circuit_config, result))

            # Algunos algoritmos (hoy: optimización bayesiana) agregan
            # tiempo_ejecucion_s al resultado; el resto no lo trae. Se decide
            # aquí, según lo que el resultado realmente contenga, en vez de
            # preguntarle al service_class qué tipo es -- así un futuro
            # algoritmo que también reporte tiempo no necesita ningún cambio
            # en este método.
            if "tiempo_ejecucion_s" in result:
                return CircuitoOptimizadoConTiempoResponse(**result)
            return CircuitoOptimizadoResponse(**result)
        finally:
            service.constants_repository.cleanup()