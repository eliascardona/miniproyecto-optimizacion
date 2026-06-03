from enum import Enum


class FilterType(str, Enum):

    PASA_BAJA = "PASA_BAJA"

    PASA_ALTA = "PASA_ALTA"

    PASA_BANDA = "PASA_BANDA"

    BANDA_RECHAZO = "BANDA_RECHAZO"
