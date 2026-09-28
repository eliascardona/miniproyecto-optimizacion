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

# Mismo shape de configuración que el AG (ver la nota equivalente en
# pasaaltas.py); solo cambia el Literal del algoritmo.
class PasaBajasEnjambreRequest(BaseModel):
    filtro: Literal['pasa_bajas']
    algoritmo: Literal['enjambre_particulas']
    entorno: PasaBajasConfiguration

# Mismo shape de configuración que el AG/PSO; solo cambia el Literal
# del algoritmo.
class PasaBajasBayesianaRequest(BaseModel):
    filtro: Literal['pasa_bajas']
    algoritmo: Literal['optimizacion_bayesiana']
    entorno: PasaBajasConfiguration