from typing import Union
from fastapi import HTTPException, status

from app.pydantic_schema.global_validator import safe_parse
from app.pydantic_schema.api_request_schema.pasaaltas import PasaAltasConfiguration
from API.app.preparation_service.pasa_altas import PasaAltasPreparationService



class PasaAltasController:

    def __init__(self):
        self.algorithm_preparation_service = PasaAltasPreparationService()

    def execute_algorithm(self, request_data):

        customer = self.algorithm_preparation_service.validate_json_config(
            request_data,
        )

        return CustomerResponse(**customer)