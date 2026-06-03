from app.services.model_registry import ModelRegistry
from app.services.lock_service import (
    LockService
)


class OptimizationService:

    @staticmethod
    async def optimize(
        filter_type,
        payload
    ):

        adapter = (
            ModelRegistry.get_model(
                filter_type
            )
        )

        if adapter is None:

            raise Exception(
                f"No existe adaptador para {filter_type}"
            )

        lock = (
            LockService.get_lock(
                filter_type
            )
        )

        async with lock:

            return adapter.optimize(
                payload
            )