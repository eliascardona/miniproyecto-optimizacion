from pydantic import BaseModel, Field
from typing import List
 
 
class FrecuenciaObtenida(BaseModel):
    clave: str = Field(..., description="Nombre del parámetro de frecuencia")
    valor: float = Field(..., description="Valor numérico del parámetro")
 
 
class ComponenteOptimizado(BaseModel):
    nombre: str = Field(..., description="Identificador del componente (ej. C1_1, R2_2)")
    valor: float = Field(..., description="Valor numérico del componente")
 
 
class PasaAltasResponse(BaseModel):
    fitness: float = Field(..., description="Valor de aptitud del resultado (0.0 - 1.0)")
    frecuencias_obtenidas: List[FrecuenciaObtenida] = Field(
        ..., description="Lista de frecuencias obtenidas tras la optimización"
    )
    componentes_optimizados: List[ComponenteOptimizado] = Field(
        ..., description="Lista de componentes con sus valores optimizados"
    )
    grafica_png_base64: str = Field(
        ..., description="Imagen de la gráfica en formato PNG codificada en Base64"
    )
