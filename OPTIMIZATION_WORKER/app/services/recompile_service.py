from app.services.adapter_factory import (
    AdapterFactory
)

from app.services.model_registry import (
    ModelRegistry
)

from app.services.lock_service import (
    LockService
)


class RecompileService:

    @staticmethod
    async def recompile(filter_type):

        lock = (
            LockService.get_lock(
                filter_type
            )
        )

        async with lock:

            adapter = (
                AdapterFactory.create(
                    filter_type
                )
            )

            adapter.compile()

            ModelRegistry.register_model(
                filter_type,
                adapter
            )

            return {
                "status": "RECOMPILED",
                "filter": filter_type
            }