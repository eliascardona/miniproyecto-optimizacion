from fastapi import FastAPI

from API.app.routes.individual_optimization_router import individual_optimization_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="API CON ALGORITMOS DE OPTIMIZACIÓN EN EL DISEÑO DE FILTROS ANALÓGICOS",
        description="UNIVERSIDAD AUTÓNOMA DE AGUASCALIENTES Mini proyecto MP-26-154",
        version="1.0.0",
    )

    app.include_router(individual_optimization_router)

    return app

app = create_app()