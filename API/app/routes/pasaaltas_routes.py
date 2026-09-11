from fastapi import APIRouter, Request
from pydantic import Any
from app.controller.pasaaltas_controller import PasaAltasController
from app.pydantic_schema.api_response_schema.pasaaltas import PasaAltasResponse


pasaaltas_routes = APIRouter(
    prefix="/api/customers",
    tags=["Customers"],
)

controller = PasaAltasController()

@pasaaltas_routes.post(
    "",
    response_model=PasaAltasResponse,
    status_code=201,
)
async def create_customer(request: Request):
    raw_json_data = await request.json()
    return controller.optimize_pasaaltas(raw_json_data)
