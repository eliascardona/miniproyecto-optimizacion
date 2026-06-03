from app.algorithms.base_adapter import (
    BaseAdapter
)


class BandaRechazoAdapter(
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
            "tipo_filtro": "BANDA_RECHAZO",
            "fitness": 0.93
        }