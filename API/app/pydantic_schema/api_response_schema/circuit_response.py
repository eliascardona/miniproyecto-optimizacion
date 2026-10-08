from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from app.pydantic_schema.api_response_schema.esquema_schema import EsquemaCircuito, RespuestaFrecuencia
 
 
class FrecuenciaObtenida(BaseModel):
    clave: str = Field(..., description="Nombre del parámetro de frecuencia")
    valor: float = Field(..., description="Valor numérico del parámetro")
 
 
class ComponenteOptimizado(BaseModel):
    nombre: str = Field(..., description="Identificador del componente (ej. C1_1, R2_2)")
    tipo: Literal["R", "C"] = Field(..., description="Tipo de componente")
    valor: float = Field(..., description="Valor numérico optimizado")
    conexion_tierra: bool = Field(
        ..., description="True si el componente conecta directamente a tierra (nodo 0)"
    )

 
class CircuitoOptimizadoResponse(BaseModel):
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
    # --- Campos agregados (todos opcionales: los clientes anteriores los ignoran) ---
    esquema: Optional[EsquemaCircuito] = Field(
        None,
        description="Esquema del circuito OPTIMIZADO (con los valores finales de cada componente), "
                    "listo para dibujarlo. Es null si no se pudo construir (ver esquema_error).",
    )
    esquema_error: Optional[str] = Field(
        None,
        description="Por qué no hay esquema. El resto de la respuesta sigue siendo válida: "
                    "un problema de dibujo nunca descarta una optimización terminada.",
    )
    respuesta_frecuencia: Optional[RespuestaFrecuencia] = Field(
        None,
        description="Curva de respuesta (frecuencia, Vout) del circuito optimizado.",
    )


class CircuitoOptimizadoConTiempoResponse(CircuitoOptimizadoResponse):
    """
    Igual que CircuitoOptimizadoResponse, con un campo adicional para
    algoritmos que reportan cuánto tardó la optimización (p.ej.
    optimización bayesiana, donde cada iteración ajusta un proceso
    gaussiano + una optimización L-BFGS-B, mucho más costosa que una
    generación de AG o una iteración de PSO). GeneticController decide
    cuál de las dos clases construir según si el resultado trae o no
    'tiempo_ejecucion_s'.
    """
    tiempo_ejecucion_s: float = Field(
        ..., description="Tiempo total de la optimización, en segundos"
    )