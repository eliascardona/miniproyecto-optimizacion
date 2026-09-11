"""
Controlador del filtro pasa-altas. Responsabilidades:
  - Recibir el request_data crudo desde la ruta FastAPI.
  - Delegar TODA la lógica al servicio.
  - Empaquetar el resultado del servicio en la respuesta Pydantic de salida.
"""
from app.preparation_service.pasa_altas_service import PasaAltasPreparationService
from app.pydantic_schema.api_response_schema.pasaaltas import PasaAltasResponse


class PasaAltasController:

    def __init__(self):
        self.algorithm_preparation_service = PasaAltasPreparationService()

    def optimize_pasaaltas(self, request_data: dict) -> PasaAltasResponse:
        # 1. Validar y obtener la configuración normalizada
        circuit_config = self.algorithm_preparation_service.validate_json_config(
            request_data,
        )

        # 2. Extraer los componentes del archivo .cir
        componentes_ag = self.algorithm_preparation_service.extract_components()

        # 3. Ejecutar el algoritmo genético completo
        optimization_result = self.algorithm_preparation_service.run_optimization(
            cfg=circuit_config,
            componentes_ag=componentes_ag,
        )

        # 4. Mapear el resultado al schema de respuesta
        return PasaAltasResponse(**optimization_result)