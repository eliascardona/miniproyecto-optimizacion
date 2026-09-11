from fastapi import HTTPException

from app.pydantic_schema.global_validator import safe_parse
from app.pydantic_schema.api_request_schema.pasaaltas import PasaAltasConfiguration


class PasaAltasPreparationService:

    def validate_json_config(
        self,
        request_data,
    ):
        parsed, errors = safe_parse(PasaAltasConfiguration, request_data)

        if errors:
            raise HTTPException(status_code=422, detail=errors)

        return parsed.model_dump()