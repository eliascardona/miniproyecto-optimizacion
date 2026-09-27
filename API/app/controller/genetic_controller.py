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
from app.pydantic_schema.api_response_schema.circuit_response import CircuitoOptimizadoResponse
from app.pydantic_schema.api_request_schema.circuit_optimization_request import CircuitOptimizationRequest


class GeneticController:

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
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

        return CircuitoOptimizadoResponse(**result)