from fastapi import FastAPI

from app.routes.unique_entrypoint import unique_entrypoint


def create_app() -> FastAPI:
    app = FastAPI(
        title="API CON ALGORITMOS DE OPTIMIZACIÓN EN EL DISEÑO DE FILTROS ANALÓGICOS",
        description="UNIVERSIDAD AUTÓNOMA DE AGUASCALIENTES Mini proyecto MP-26-154",
        version="1.0.0",
    )

    app.include_router(unique_entrypoint)

    return app

app = create_app()