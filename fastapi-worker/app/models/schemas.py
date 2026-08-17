"""
Modelos Pydantic para validacion de entrada y salida del worker.

Estos modelos definen el contrato HTTP del FastAPI Worker:
  - OptimizationInput: los 5 bloques del config.json (modo, entorno, barrido_ac, etc.)
  - ExecutionRequest: wrapper que agrega tipo_filtro y algoritmo para enrutar.
  - OptimizationResult: forma de la respuesta con fitness, componentes y grafica.
"""

from pydantic import BaseModel, Field


class OptimizationInput(BaseModel):
    """Configuracion de optimizacion (los 5 bloques raiz del config.json)."""
    modo: str = Field(..., min_length=1)
    entorno: dict = Field(...)
    barrido_ac: dict = Field(...)
    parametros_optimizador: list = Field(...)
    frecuencias: list = Field(...)


class OptimizationResult(BaseModel):
    """Resultado de una ejecucion de optimizacion."""
    estado: str
    fitness: float
    frecuencias_obtenidas: dict = {}
    componentes_optimizados: dict = {}
    grafica_png_base64: str = ""


class ExecutionRequest(BaseModel):
    """
    Solicitud de ejecucion recibida del Express BFF.
    tipo_filtro y algoritmo se usan para seleccionar el script correcto.
    NO se pasan dentro del config.json que lee el script.
    """
    tipo_filtro: str
    algoritmo: str
    configuracion: OptimizationInput


class ValidationRequest(BaseModel):
    """
    Solicitud de validacion sin ejecucion (util para debugging).
    Mismo esquema que ExecutionRequest.
    """
    tipo_filtro: str
    algoritmo: str
    configuracion: OptimizationInput
