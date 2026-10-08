from fastapi import FastAPI

from app.routes.circuit_schema_router import circuit_schema_router
from app.routes.individual_optimization_router import individual_optimization_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="API CON ALGORITMOS DE OPTIMIZACIÓN EN EL DISEÑO DE FILTROS ANALÓGICOS",
        description="UNIVERSIDAD AUTÓNOMA DE AGUASCALIENTES Mini proyecto MP-26-154",
        version="1.0.0",
    )

    app.include_router(individual_optimization_router)
    app.include_router(circuit_schema_router)

    return app

app = create_app()