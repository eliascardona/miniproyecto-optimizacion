"""
Estado global compartido del worker.

ApplicationState es una clase estatica que mantiene:
  - lock: asyncio.Lock para exclusion mutua entre compilacion y ejecucion.
  - worker_ready: flag que indica si el worker completo su inicializacion.
  - startup_summary: resumen del estado de arranque.

El lock garantiza que solo un subprocess de ngspice se ejecute a la vez,
ya que ngspice no es thread-safe.
"""

from typing import Optional


class ApplicationState:
    lock = None
    worker_ready: bool = False
    startup_summary: Optional[dict] = None


def init_lock():
    """Inicializa el asyncio.Lock. Debe llamarse dentro del event loop."""
    import asyncio
    ApplicationState.lock = asyncio.Lock()
