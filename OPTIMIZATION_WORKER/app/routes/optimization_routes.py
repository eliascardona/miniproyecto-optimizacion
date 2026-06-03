from fastapi import APIRouter

from app.models.optimization_models import (
    OptimizationRequest
)

from app.services.optimization_service import (
    OptimizationService
)

from app.models.filter_type import (
    FilterType
)

from app.services.recompile_service import (
    RecompileService
)

router = APIRouter()


@router.post("/optimize")
async def optimize(
    request: OptimizationRequest
):

    result = (
        await OptimizationService.optimize(
            request.tipo_filtro,
            request.configuracion_recibida
        )
    )

    return result

@router.post(
    "/recompile/{filter_type}"
)
async def recompile(
    filter_type: FilterType
):

    result = (
        await RecompileService
        .recompile(
            filter_type
        )
    )

    return result

