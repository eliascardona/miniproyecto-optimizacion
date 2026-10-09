from fastapi import APIRouter

from app.controller.catalog_controller import CatalogController
from app.pydantic_schema.api_response_schema.catalogo_esquema import CatalogoResponse


catalog_router = APIRouter(
    prefix="/api/catalogo",
    tags=["Catálogo de filtros y algoritmos"],
)

controller = CatalogController()


@catalog_router.get("", response_model=CatalogoResponse)
def get_catalog():
    """Qué filtros, algoritmos y modos existen, qué parámetros pide cada uno y qué combinaciones corren."""
    return controller.get_catalog()