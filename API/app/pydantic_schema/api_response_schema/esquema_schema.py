"""
Contrato con los clientes: ESQUEMA de un circuito (cómo dibujarlo) y su respuesta en frecuencia.

Coordenadas en UNIDADES DE REJILLA: x crece hacia la derecha, y hacia ABAJO. El cliente decide
cuántos píxeles vale una unidad. Cada elemento trae su RUTA (polilínea) y `seg`, el índice del
segmento de la ruta donde va su símbolo; quien dibuje solo tiene que pintar.

`tipo` y `rol` se declaran como str (no Literal) a propósito: si se agrega un tipo de elemento o
un rol nuevo, los clientes viejos siguen recibiendo la respuesta y deciden qué hacer con él.
  tipo: "R" | "C" | "L" | "V"
  rol:  "fuente" | "resistencia_fuente" | "serie" | "derivacion" | "realimentacion" | "carga"
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class NodoPosicion(BaseModel):
    x: float = Field(..., description="Posición horizontal del nodo (rejilla)")
    y: float = Field(..., description="Posición vertical del nodo (rejilla, crece hacia abajo)")


class ElementoEsquema(BaseModel):
    nombre: str = Field(..., description="Nombre en el .cir (ej. C1_1, R2_2, Vs, Rl)")
    tipo: str = Field(..., description="R, C, L o V")
    valor: float = Field(..., description="Valor en unidades SI (ohm, faradio, henrio, volt)")
    nodos: List[str] = Field(..., description="Nodos a los que conecta (\"0\" es tierra)")
    rol: str = Field(..., description="Función del elemento dentro del circuito")
    etapa: int = Field(..., description="Etapa a la que pertenece (0 = fuente/carga)")
    optimizable: bool = Field(..., description="True si lo ajusta el optimizador; False si es fijo")
    ruta: List[List[float]] = Field(..., description="Polilínea [[x, y], ...] que recorre el elemento")
    seg: int = Field(..., description="Índice del segmento de `ruta` donde va el símbolo")


class OpAmpNodos(BaseModel):
    in_p: str = Field(..., description="Nodo de la entrada no inversora (+)")
    in_n: str = Field(..., description="Nodo de la entrada inversora (-)")
    out: str = Field(..., description="Nodo de salida")


class OpAmpPines(BaseModel):
    in_p: List[float] = Field(..., description="Posición [x, y] del pin +")
    in_n: List[float] = Field(..., description="Posición [x, y] del pin -")
    out: List[float] = Field(..., description="Posición [x, y] del pin de salida")


class OpAmpAlimentacion(BaseModel):
    v_pos: str = Field(..., description="Nodo de alimentación positiva (ver `alimentacion` del esquema)")
    v_neg: str = Field(..., description="Nodo de alimentación negativa")


class OpAmpEsquema(BaseModel):
    nombre: str = Field(..., description="Nombre en el .cir (ej. XOP1)")
    modelo: str = Field(..., description="Subcircuito SPICE (ej. LM741)")
    etapa: int = Field(..., description="Etapa que cierra este op-amp")
    nodos: OpAmpNodos
    pines: OpAmpPines
    triangulo: List[List[float]] = Field(..., description="Vértices [[x, y], ...] del símbolo")
    alimentacion: OpAmpAlimentacion


class AlimentacionEsquema(BaseModel):
    nombre: str = Field(..., description="Fuente de alimentación (ej. Vpp)")
    nodo: str = Field(..., description="Nodo que alimenta (ej. Vp)")
    valor: float = Field(..., description="Tensión en volts (negativa para Vnn)")


class SalidaEsquema(BaseModel):
    nodo: str = Field(..., description="Nodo de salida del circuito")
    ruta: List[List[float]] = Field(..., description="Cable hacia el terminal de salida [[x, y], ...]")


class LimitesEsquema(BaseModel):
    x_min: float
    x_max: float
    y_min: float
    y_max: float


class EsquemaCircuito(BaseModel):
    version_esquema: int = Field(..., description="Versión del formato (hoy 1)")
    filtro: Optional[str] = Field(None, description="Filtro al que corresponde")
    titulo: str = Field(..., description="Título del circuito (.title del .cir)")
    nodo_fuente: str
    nodo_entrada: str
    nodo_salida: str
    num_etapas: int
    alimentacion: List[AlimentacionEsquema]
    nodos: Dict[str, NodoPosicion] = Field(..., description="Posición de cada nodo (excepto tierra)")
    elementos: List[ElementoEsquema]
    opamps: List[OpAmpEsquema]
    cables: List[List[List[float]]] = Field(..., description="Cables sueltos: lista de polilíneas")
    tierras: List[List[float]] = Field(..., description="Posiciones [x, y] de los símbolos de tierra")
    uniones: List[List[float]] = Field(..., description="Puntos de unión (>= 3 conductores): se pinta un punto")
    salida: SalidaEsquema
    limites: LimitesEsquema = Field(..., description="Caja que contiene toda la geometría (sin márgenes)")


class RespuestaFrecuencia(BaseModel):
    frecuencia_hz: List[float] = Field(..., description="Frecuencias del barrido AC, en Hz (ascendentes)")
    vout: List[float] = Field(..., description="Amplitud de la salida (V) en cada frecuencia")