from app.models.filter_type import (
    FilterType
)

from app.services.adapter_factory import (
    AdapterFactory
)

from app.services.model_registry import (
    ModelRegistry
)


class CompilerService:

    @staticmethod
    def compile_all_models():

        summary = {}

        for filter_type in FilterType:

            print()

            print(
                f"Compilando {filter_type.value}..."
            )

            adapter = AdapterFactory.create(
                filter_type
            )

            adapter.compile()

            ModelRegistry.register_model(
                filter_type,
                adapter
            )

            summary[
                filter_type.value
            ] = "OK"

        return {
            "success": True,
            "compiled_models": summary
        }