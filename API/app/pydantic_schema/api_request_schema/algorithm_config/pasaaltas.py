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

class PasaAltasConfiguration(BaseModel):
    modo: str
    entorno: Entorno
    barrido_ac: BarridoAC
    parametros_optimizador: list[Par]
    frecuencias: list[Par]

class PasaAltasRequest(BaseModel):
    filtro: Literal['pasa_altas']
    algoritmo: Literal['algoritmo_genetico']
    entorno: PasaAltasConfiguration

# Mismo shape de configuración que el AG (entorno/barrido_ac/frecuencias
# no cambian; solo difieren las claves dentro de parametros_optimizador,
# y eso Pydantic no lo valida aquí -- parametros_optimizador es
# list[Par] genérico en ambos casos). Por eso PasaAltasConfiguration se
# reutiliza tal cual; solo hace falta esta variante de Request con el
# Literal del algoritmo distinto.
class PasaAltasEnjambreRequest(BaseModel):
    filtro: Literal['pasa_altas']
    algoritmo: Literal['enjambre_particulas']
    entorno: PasaAltasConfiguration

# Mismo shape de configuración que el AG/PSO; solo cambia el Literal
# del algoritmo.
class PasaAltasBayesianaRequest(BaseModel):
    filtro: Literal['pasa_altas']
    algoritmo: Literal['optimizacion_bayesiana']
    entorno: PasaAltasConfiguration