from fastapi import APIRouter, Request
from app.controller.individual_optimization_controller import IndividualOptimizationController
from app.pydantic_schema.api_request_schema.circuit_optimization_request import CircuitOptimizationRequest


individual_optimization_router = APIRouter(
    prefix="/api/optimizar",
    tags=["Optimización de circuitos"],
)

controller = IndividualOptimizationController()

"""
  response_model=None a propósito: el controller puede devolver
  CircuitoOptimizadoResponse (AG/PSO) o CircuitoOptimizadoConTiempoResponse
  (BO, con tiempo_ejecucion_s) según el algoritmo. Con un response_model
  fijo, FastAPI filtraría la salida a ESE schema exacto -- y con un
  Union[...], como CircuitoOptimizadoConTiempoResponse hereda de
  CircuitoOptimizadoResponse, ambas clases pasan isinstance() contra la
  base, así que no hay garantía de que Pydantic elija la subclase más
  específica: el campo extra podría descartarse en silencio igual.
  response_model=None desactiva ese filtrado: FastAPI serializa el
  objeto Pydantic devuelto tal cual, con todos sus campos reales.
"""
@individual_optimization_router.post("", response_model=None, status_code=201)
def optimize_circuit(request: CircuitOptimizationRequest):
    return controller.optimize(request)