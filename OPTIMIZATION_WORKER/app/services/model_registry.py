from app.models.filter_type import (
    FilterType
)


class ModelRegistry:

    compiled_models = {}

    @classmethod
    def register_model(
        cls,
        filter_type: FilterType,
        model
    ):

        cls.compiled_models[
            filter_type.value
        ] = model

    @classmethod
    def get_model(
        cls,
        filter_type: FilterType
    ):

        return cls.compiled_models.get(
            filter_type.value
        )

    @classmethod
    def get_all_models(cls):

        return cls.compiled_models