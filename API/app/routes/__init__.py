from fastapi import APIRouter, Request
from pydantic import Any
from app.controller.pasaaltas_controller import PasaAltasController
from app.pydantic_schema.api_request_schema.pasaaltas import Configuracion


customer_routes = APIRouter(
    prefix="/api/customers",
    tags=["Customers"],
)

controller = PasaAltasController()

@customer_routes.post(
    "",
    response_model=Any,
    status_code=201,
)
def create_customer(request: Request):
    raw_json_data = await request.json()
    return controller.execute_algorithm(raw_json_data)
