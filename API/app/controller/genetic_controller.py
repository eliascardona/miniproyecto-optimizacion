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
from app.pydantic_schema.api_response_schema.circuit_response import (
    CircuitoOptimizadoResponse,
    CircuitoOptimizadoConTiempoResponse,
)
from app.pydantic_schema.api_request_schema.circuit_optimization_request import CircuitOptimizationRequest


class GeneticController:

    # Doble switch como diccionario de servicios. El nombre de la clase
    # quedó de cuando solo existía el AG; ahora también enruta PSO
    # (enjambre_particulas) y BO (optimizacion_bayesiana). No la renombré
    # en este cambio para no tocar unique_entrypoint.py de más -- si
    # quieres, en un próximo paso la renombro a algo como
    # OptimizationController.
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
    }

    def optimize(self, request: CircuitOptimizationRequest) -> CircuitoOptimizadoResponse:
        key = (request.filtro, request.algoritmo)
        service_class = self.SERVICE_MAP.get(key)

        if service_class is None:
            raise HTTPException(
                status_code=422,
                detail=f"Sin servicio para: {key}",
            )

        service = service_class()

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

        # Algunos algoritmos (hoy: optimización bayesiana) agregan
        # tiempo_ejecucion_s al resultado; el resto no lo trae. Se decide
        # aquí, según lo que el resultado realmente contenga, en vez de
        # preguntarle al service_class qué tipo es -- así un futuro
        # algoritmo que también reporte tiempo no necesita ningún cambio
        # en este método.
        if "tiempo_ejecucion_s" in result:
            return CircuitoOptimizadoConTiempoResponse(**result)
        return CircuitoOptimizadoResponse(**result)