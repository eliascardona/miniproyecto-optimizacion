from fastapi import APIRouter, Request
from app.controller.genetic_controller import GeneticController
from app.pydantic_schema.api_response_schema.circuit_response import CircuitoOptimizadoResponse
from app.pydantic_schema.api_request_schema.circuit_optimization_request import CircuitOptimizationRequest


unique_entrypoint = APIRouter(
    prefix="/api/optimizar",
    tags=["Optimización de circuitos"],
)

controller = GeneticController()

@unique_entrypoint.post("", response_model=CircuitoOptimizadoResponse, status_code=201)
def optimize_circuit(request: CircuitOptimizationRequest):
    return controller.optimize(request)
