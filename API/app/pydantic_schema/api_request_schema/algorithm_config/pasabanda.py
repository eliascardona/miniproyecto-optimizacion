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

class PasaBandaConfiguration(BaseModel):
    modo: str
    entorno: Entorno
    barrido_ac: BarridoAC
    parametros_optimizador: list[Par]
    frecuencias: list[Par]

class PasaBandaRequest(BaseModel):
    filtro: Literal['pasa_banda']
    algoritmo: Literal['algoritmo_genetico']
    entorno: PasaBandaConfiguration