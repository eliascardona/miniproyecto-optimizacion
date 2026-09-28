from pydantic import BaseModel, Field, model_validator
from typing import Union, Any
from enum import Enum
from app.pydantic_schema.api_request_schema.algorithm_config.pasaaltas import PasaAltasRequest, PasaAltasEnjambreRequest, PasaAltasBayesianaRequest
from app.pydantic_schema.api_request_schema.algorithm_config.pasabajas import PasaBajasRequest, PasaBajasEnjambreRequest, PasaBajasBayesianaRequest
from app.pydantic_schema.api_request_schema.algorithm_config.pasabanda import PasaBandaRequest, PasaBandaEnjambreRequest, PasaBandaBayesianaRequest
from app.pydantic_schema.api_request_schema.algorithm_config.rechazabanda import RechazaBandaRequest, RechazaBandaEnjambreRequest, RechazaBandaBayesianaRequest


# Only enums for the reference
class FiltroEnum(str, Enum):
    pasa_altas = "pasa_altas"
    pasa_bajas = "pasa_bajas"
    pasa_banda = "pasa_banda"
    rechaza_banda = "rechaza_banda"

class AlgoritmoEnum(str, Enum):
    algoritmo_genetico = "algoritmo_genetico"
    optimizacion_bayesiana = "optimizacion_bayesiana"
    enjambre_particulas = "enjambre_particulas"
    recocido_simulado = "recocido_simulado"

FILTRO_ALGORITMO_MAP = {
    ("pasa_altas", "algoritmo_genetico"): PasaAltasRequest,
    ("pasa_altas", "enjambre_particulas"): PasaAltasEnjambreRequest,
    ("pasa_altas", "optimizacion_bayesiana"): PasaAltasBayesianaRequest,
    ("pasa_bajas", "algoritmo_genetico"): PasaBajasRequest,
    ("pasa_bajas", "enjambre_particulas"): PasaBajasEnjambreRequest,
    ("pasa_bajas", "optimizacion_bayesiana"): PasaBajasBayesianaRequest,
    ("pasa_banda", "algoritmo_genetico"): PasaBandaRequest,
    ("pasa_banda", "enjambre_particulas"): PasaBandaEnjambreRequest,
    ("pasa_banda", "optimizacion_bayesiana"): PasaBandaBayesianaRequest,
    ("rechaza_banda", "algoritmo_genetico"): RechazaBandaRequest,
    ("rechaza_banda", "enjambre_particulas"): RechazaBandaEnjambreRequest,
    ("rechaza_banda", "optimizacion_bayesiana"): RechazaBandaBayesianaRequest,
}

class CircuitOptimizationRequest(BaseModel):
    filtro: str
    algoritmo: str
    entorno: dict

    @model_validator(mode='before')
    @classmethod
    def validate_and_parse(cls, data: Any):
        filtro = data.get("filtro")
        algoritmo = data.get("algoritmo")
        key = (filtro, algoritmo)

        schema = FILTRO_ALGORITMO_MAP.get(key)
        if schema is None:
            raise ValueError(
                f"Combinación no soportada: filtro='{filtro}', algoritmo='{algoritmo}'. "
                f"Opciones válidas: {list(FILTRO_ALGORITMO_MAP.keys())}"
            )

        # Valida el request completo con el schema correcto
        parsed = schema(**data)
        # Devuelve como dict para que Pydantic termine de construir
        return parsed.model_dump()