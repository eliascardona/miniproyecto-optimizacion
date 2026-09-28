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

# Mismo shape de configuración que el AG (ver la nota equivalente en
# pasaaltas.py); solo cambia el Literal del algoritmo.
class PasaBandaEnjambreRequest(BaseModel):
    filtro: Literal['pasa_banda']
    algoritmo: Literal['enjambre_particulas']
    entorno: PasaBandaConfiguration

# Mismo shape de configuración que el AG/PSO; solo cambia el Literal
# del algoritmo.
class PasaBandaBayesianaRequest(BaseModel):
    filtro: Literal['pasa_banda']
    algoritmo: Literal['optimizacion_bayesiana']
    entorno: PasaBandaConfiguration