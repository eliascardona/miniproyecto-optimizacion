"""
Respuesta de GET /api/catalogo: qué filtros, algoritmos y modos existen, qué parámetros pide cada uno
(claves, tipos, límites, relaciones y valores iniciales) y qué combinaciones corren de verdad.
Ver app/utils/catalogo/definiciones.py para el significado de cada límite.
"""
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

Numero = Union[int, float]


class CampoCatalogo(BaseModel):
    clave: str = Field(..., description="Nombre EXACTO de la clave en la petición a /api/optimizar")
    etiqueta: str
    tipo: Literal["entero", "decimal"]
    unidad: Optional[str] = None
    minimo: Optional[float] = Field(None, description="Límite duro inferior (null = sin límite)")
    minimo_exclusivo: bool = False
    maximo: Optional[float] = Field(None, description="Límite duro superior (null = sin límite)")
    maximo_exclusivo: bool = False
    ideal_min: Optional[float] = Field(None, description="Límite inferior RECOMENDADO (solo aviso)")
    ideal_max: Optional[float] = Field(None, description="Límite superior RECOMENDADO (solo aviso)")
    serie: Optional[Literal["E12"]] = Field(None, description="Serie comercial que se pide (solo aviso)")
    paso: float = Field(..., description="Incremento sugerido para controles de tipo spinner")
    descripcion: str = ""


class RelacionCatalogo(BaseModel):
    izquierda: str
    operador: Literal["<", "<="]
    derecha: str
    severidad: Literal["error", "aviso"]
    mensaje: str


class ModoCatalogo(BaseModel):
    id: Literal["BASICO", "AVANZADO"]
    etiqueta: str
    descripcion: str


class ExtremosFrecuencia(BaseModel):
    minima: str = Field(..., description="Clave de la frecuencia de interés más baja")
    maxima: str = Field(..., description="Clave de la frecuencia de interés más alta")


class FrecuenciasDeModo(BaseModel):
    modo: Literal["BASICO", "AVANZADO"]
    campos: List[CampoCatalogo] = Field(..., description="En orden ascendente de frecuencia")
    relaciones: List[RelacionCatalogo]
    extremos: ExtremosFrecuencia
    valores_iniciales: Dict[str, Numero]


class FiltroCatalogo(BaseModel):
    id: str
    etiqueta: str
    familia: Literal["corte_simple", "banda"]
    descripcion: str
    frecuencias: List[FrecuenciasDeModo]


class AlgoritmoCatalogo(BaseModel):
    id: str
    etiqueta: str
    descripcion: str
    parametros: List[CampoCatalogo]
    relaciones: List[RelacionCatalogo]


class CombinacionCatalogo(BaseModel):
    filtro: str
    algoritmo: str
    disponible: bool = Field(..., description="True si el servidor sabe ejecutar esta combinación")
    valores_iniciales: Dict[str, Numero] = Field(..., description="Hiperparámetros iniciales sugeridos")


class BarridoCatalogo(BaseModel):
    campos: List[CampoCatalogo]
    relaciones: List[RelacionCatalogo]


class MargenDecada(BaseModel):
    factor: Numero
    severidad: Literal["error", "aviso"]
    descripcion: str


class ReglasCatalogo(BaseModel):
    margen_decada: MargenDecada


class CatalogoResponse(BaseModel):
    version_catalogo: int
    modos: List[ModoCatalogo]
    entorno: List[CampoCatalogo]
    barrido_ac: BarridoCatalogo
    reglas: ReglasCatalogo
    filtros: List[FiltroCatalogo]
    algoritmos: List[AlgoritmoCatalogo]
    combinaciones: List[CombinacionCatalogo]