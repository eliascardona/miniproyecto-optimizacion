from app.algorithms.base_adapter import (
    BaseAdapter
)


class PasaAltaAdapter(
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
            "tipo_filtro": "PASA_ALTA",
            "fitness": 0.91
        }