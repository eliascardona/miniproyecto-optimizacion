from app.algorithms.base_adapter import (
    BaseAdapter
)


class PasaBandaAdapter(
    BaseAdapter
):

    def compile(self):

        print(
            "Compilando adaptador PASA_BANDA"
        )

        return {
            "compiled": True
        }

    def optimize(
        self,
        payload: dict
    ):

        return {
            "tipo_filtro": "PASA_BANDA",
            "payload_recibido": payload,
            "fitness": 0.95
        }