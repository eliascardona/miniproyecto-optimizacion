"""
Configuracion centralizada del worker.

Carga variables de entorno desde .env y define las rutas a los scripts
de optimizacion. El SCRIPT_MAP mapea (tipo_filtro, algoritmo) -> path
del script Python correspondiente dentro de ALGORITMOS_DE_OPTIMIZACION/.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Path al ejecutable ngspice (se inyecta al PATH del subprocess)
NGSPICE_PATH = os.getenv("NGSPICE_PATH", r"C:\PROGRAMAS_UNI\Spice64\bin\ngspice.exe")

# Directorio de trabajo temporal para cada ejecucion de script
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "tempwork")

# Raiz del proyecto (un nivel arriba de fastapi-worker/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALGOS_DIR = os.path.join(PROJECT_ROOT, "ALGORITMOS_DE_OPTIMIZACION")

# Enums validos
VALID_FILTER_TYPES = ["PASA_BAJA", "PASA_ALTA", "PASA_BANDA", "RECHAZO_BANDA"]
VALID_ALGORITHMS = ["AG", "PSO"]
VALID_MODES = ["BASICO", "AVANZADO"]

# Mapa de rutas: cada combinacion (tipo_filtro, algoritmo) apunta a un script Python.
# Los scripts son "cajas negras" del equipo de Computacion Inteligente.
SCRIPT_MAP = {
    "PASA_BAJA": {
        "AG": os.path.join(ALGOS_DIR, "ALGORITMO_GENETICO", "FILTRO_PASABAJAS", "algoritmo.py"),
        "PSO": os.path.join(ALGOS_DIR, "ENJAMBRE_DE_PARTICULAS", "FILTRO_PASABAJAS", "algoritmo.py"),
    },
    "PASA_ALTA": {
        "AG": os.path.join(ALGOS_DIR, "ALGORITMO_GENETICO", "FILTRO_PASAALTAS", "ejemplo_worker.py"),
        "PSO": os.path.join(ALGOS_DIR, "ENJAMBRE_DE_PARTICULAS", "FILTRO_PASAALTAS", "algoritmo.py"),
    },
    "PASA_BANDA": {
        "AG": os.path.join(ALGOS_DIR, "ALGORITMO_GENETICO", "FILTRO_PASABANDA", "algoritmo.py"),
        "PSO": os.path.join(ALGOS_DIR, "ENJAMBRE_DE_PARTICULAS", "FILTRO_PASABANDA", "algoritmo.py"),
    },
    "RECHAZO_BANDA": {
        "AG": os.path.join(ALGOS_DIR, "ALGORITMO_GENETICO", "FILTRO_RECHAZABANDA", "algoritmo.py"),
        "PSO": os.path.join(ALGOS_DIR, "ENJAMBRE_DE_PARTICULAS", "FILTRO_RECHAZABANDA", "algoritmo.py"),
    },
}
