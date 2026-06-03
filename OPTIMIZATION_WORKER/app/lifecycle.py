from app.state.application_state import (
    ApplicationState
)

from app.services.compiler_service import (
    CompilerService
)


async def startup_sequence():

    print()

    print("Iniciando worker...")

    summary = (
        CompilerService
        .compile_all_models()
    )

    ApplicationState.startup_summary = (
        summary
    )

    ApplicationState.model_ready = True

    print()

    print("Worker listo")