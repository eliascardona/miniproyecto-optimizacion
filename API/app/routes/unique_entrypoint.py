from fastapi import APIRouter, Request
from app.controller.genetic_controller import GeneticController
from app.pydantic_schema.api_request_schema.circuit_optimization_request import CircuitOptimizationRequest


unique_entrypoint = APIRouter(
    prefix="/api/optimizar",
    tags=["Optimización de circuitos"],
)

controller = GeneticController()

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
@unique_entrypoint.post("", response_model=None, status_code=201)
def optimize_circuit(request: CircuitOptimizationRequest):
    return controller.optimize(request)