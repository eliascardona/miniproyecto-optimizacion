"""
Controlador del filtro pasa-altas. Responsabilidades:
  - Recibir el request_data crudo desde la ruta FastAPI.
  - Delegar TODA la lógica al servicio.
  - Empaquetar el resultado del servicio en la respuesta Pydantic de salida.
"""
from app.preparation_service.pasa_altas_service import PasaAltasPreparationService
from app.pydantic_schema.api_response_schema.circuit_response import CircuitoOptimizadoResponse
from app.pydantic_schema.api_request_schema.circuit_optimization_request import CircuitOptimizationRequest


class GeneticController:

    # Doble switch como diccionario de servicios
    SERVICE_MAP = {
        ("pasa_altas", "algoritmo_genetico"): PasaAltasPreparationService,
        # ("pasa_bajas", "algoritmo_genetico"): PasaBajasPreparationService,
    }

    def optimize(self, request: CircuitOptimizationRequest) -> CircuitoOptimizadoResponse:
        key = (request.filtro, request.algoritmo)
        service_class = self.SERVICE_MAP.get(key)

        if service_class is None:
            raise ValueError(f"Sin servicio para: {key}")

        service = service_class()

        circuit_config = service.validate_json_config(request.entorno)
        componentes = service.extract_components()
        result = service.run_optimization(cfg=circuit_config, componentes_ag=componentes)

        return CircuitoOptimizadoResponse(**result)