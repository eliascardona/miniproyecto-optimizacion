from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.lifecycle import (
    startup_sequence
)

from app.state.application_state import (
    ApplicationState
)

from app.services.model_registry import (
    ModelRegistry
)
from app.routes.optimization_routes import (
    router as optimization_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    await startup_sequence()

    yield

    print()

    print("Cerrando worker...")


app = FastAPI(
    title="Optimization Worker",
    version="1.0.0",
    lifespan=lifespan
)



@app.get("/health")
async def health():

    models = (
        len(
            ModelRegistry
            .get_all_models()
        )
    )

    return {

        "status": "UP",

        "model_ready":
            ApplicationState.model_ready,

        "registered_models":
            models,

        "startup_summary":
            ApplicationState.startup_summary
    }



@app.get("/models")
async def models():

    return ModelRegistry.get_all_models()

app.include_router(
    optimization_router
)
