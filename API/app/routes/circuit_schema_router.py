from fastapi import APIRouter

from app.controller.circuit_schema_controller import CircuitSchemaController
from app.pydantic_schema.api_response_schema.esquema_schema import EsquemaCircuito


circuit_schema_router = APIRouter(
    prefix="/api/circuitos",
    tags=["Esquemas de circuito"],
)

controller = CircuitSchemaController()


@circuit_schema_router.get("/{filtro}", response_model=EsquemaCircuito)
def get_circuit_schema(filtro: str):
    """Esquema (dibujo) del filtro con los valores base de su plantilla."""
    return controller.get_schema(filtro)