from pydantic import BaseModel
from typing import Union, Literal

class Entorno(BaseModel):
    v_fuente: float
    r_fuente: float
    r_carga: float

class BarridoAC(BaseModel):
    f_inicial: float
    f_final: float

class Par(BaseModel):
    clave: str
    valor: Union[int, float]

class RechazaBandaConfiguration(BaseModel):
    modo: str
    entorno: Entorno
    barrido_ac: BarridoAC
    parametros_optimizador: list[Par]
    frecuencias: list[Par]

class RechazaBandaRequest(BaseModel):
    filtro: Literal['rechaza_banda']
    algoritmo: Literal['algoritmo_genetico']
    entorno: RechazaBandaConfiguration