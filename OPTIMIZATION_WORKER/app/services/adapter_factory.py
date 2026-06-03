from app.models.filter_type import (
    FilterType
)

from app.algorithms.pasa_baja_adapter import (
    PasaBajaAdapter
)

from app.algorithms.pasa_alta_adapter import (
    PasaAltaAdapter
)

from app.algorithms.pasa_banda_adapter import (
    PasaBandaAdapter
)

from app.algorithms.banda_rechazo_adapter import (
    BandaRechazoAdapter
)


class AdapterFactory:

    @staticmethod
    def create(
        filter_type: FilterType
    ):

        if (
            filter_type
            == FilterType.PASA_BAJA
        ):
            return PasaBajaAdapter()

        if (
            filter_type
            == FilterType.PASA_ALTA
        ):
            return PasaAltaAdapter()

        if (
            filter_type
            == FilterType.PASA_BANDA
        ):
            return PasaBandaAdapter()

        if (
            filter_type
            == FilterType.BANDA_RECHAZO
        ):
            return BandaRechazoAdapter()

        raise Exception(
            f"Filtro no soportado: {filter_type}"
        )