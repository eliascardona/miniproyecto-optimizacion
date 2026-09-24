from fastapi import FastAPI

from app.routes.unique_entrypoint import unique_entrypoint


def create_app() -> FastAPI:
    app = FastAPI(
        title="Optimización de circuitos",
        description="Mini proyecto de investigación UAA 2026",
        version="1.0.0",
    )

    app.include_router(unique_entrypoint)

    return app

app = create_app()