from app.algorithms.base_adapter import (
    BaseAdapter
)


class PasaBajaAdapter(
    BaseAdapter
):

    def compile(self):

        return {
            "compiled": True
        }

    def optimize(
        self,
        payload: dict
    ):

        return {
            "tipo_filtro": "PASA_BAJA",
            "fitness": 0.92
        }