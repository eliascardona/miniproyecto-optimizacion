"""
Utilería: matplotlib no es seguro para hilos.

FastAPI ejecuta los endpoints síncronos en un pool de hilos, así que dos
optimizaciones que terminen casi a la vez dibujan su gráfica final al mismo
tiempo. El analizador de mathtext de matplotlib (que dibuja las marcas
10^n del eje logarítmico) comparte estado global entre hilos y falla con
ValueError("Unknown symbol: \\mathdefault ...") -- se comprobó con el código
anterior: 5 a 8 de 8 hilos concurrentes fallaban, y la petición terminaba en
un 500 después de minutos de optimización.

`serializado` ejecuta la función decorada de a una a la vez dentro del
proceso. Dibujar toma ~0.2 s, así que el costo es despreciable frente a una
optimización completa.
"""
import functools
import threading

_BLOQUEO_MATPLOTLIB = threading.RLock()


def serializado(funcion):
    @functools.wraps(funcion)
    def envoltura(*args, **kwargs):
        with _BLOQUEO_MATPLOTLIB:
            return funcion(*args, **kwargs)
    return envoltura