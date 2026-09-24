from pydantic import BaseModel
from typing import Union, Literal
from enum import Enum

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

class PasaBajasConfiguration(BaseModel):
    modo: str
    entorno: Entorno
    barrido_ac: BarridoAC
    parametros_optimizador: list[Par]
    frecuencias: list[Par]

class PasaBajasRequest(BaseModel):
    filtro: Literal['pasa_bajas']
    algoritmo: Literal['algoritmo_genetico']
    entorno: PasaBajasConfiguration