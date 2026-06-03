from pydantic import BaseModel

from app.models.filter_type import (
    FilterType
)


class OptimizationRequest(
    BaseModel
):

    tipo_filtro: FilterType

    configuracion_recibida: dict

