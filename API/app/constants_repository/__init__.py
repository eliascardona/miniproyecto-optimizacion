import shutil
import tempfile
import weakref
from pathlib import Path

# Cada filtro tiene su propia subcarpeta con su .cir/lm741.lib (topologías
# distintas), pero comparten el mismo ngspice instalado. ConstantsRepository
# (filtro) resuelve esa subcarpeta.
#
# IMPORTANTE -- la subcarpeta del repositorio es una PLANTILLA DE SOLO LECTURA.
# Antes, las rutas de trabajo (filtro.cir, datos_filtro.txt, la gráfica...)
# apuntaban directamente ahí, y eso causaba tres problemas:
#   1. actualizar_circuito() reescribía el filtro.cir de la plantilla en
#      cada evaluación, dejándolo con los valores del último individuo y el
#      entorno de la última petición.
#   2. ngspice escribe `wrdata datos_filtro.txt` y `write simulacion.raw`
#      relativos al directorio de trabajo del PROCESO (no al del .cir): los
#      archivos nuevos caían en la carpeta desde la que se lanzó uvicorn
#      mientras el fitness leía el datos_filtro.txt viejo de la plantilla.
#   3. Dos peticiones simultáneas sobre el mismo filtro se pisaban el .cir.
# Ahora cada ConstantsRepository crea un directorio de trabajo propio
# (temporal), copia ahí la plantilla y expone SUS rutas; ejecutar_spice()
# lanza ngspice con ese directorio como cwd. El controlador lo borra al
# terminar la petición (cleanup()); weakref.finalize es la red de seguridad si
# algo se interrumpe antes.
_DIRECTORIO_BASE = Path(__file__).resolve().parent

NGSPICE_EXE = r"C:\SPICE_ELECTRONICS\Spice64\bin\ngspice.exe"  # cambiar según el usuario que ejecuta el programa

# Qué archivos de la plantilla se copian al directorio de trabajo de cada corrida.
_EXTENSIONES_PLANTILLA = (".cir", ".lib")


class ConstantsRepository:

    @staticmethod
    def directorio_plantilla_de(filtro: str) -> Path:
        """Carpeta (de solo lectura) con la plantilla del filtro."""
        if not filtro or Path(filtro).name != filtro or filtro in (".", ".."):
            raise ValueError(f"Nombre de filtro inválido: {filtro!r}")

        directorio_filtro = _DIRECTORIO_BASE / filtro
        if not directorio_filtro.is_dir():
            raise ValueError(
                f"No existe la carpeta de recursos para el filtro '{filtro}' "
                f"(se esperaba: {directorio_filtro})"
            )
        return directorio_filtro

    @classmethod
    def plantilla_cir(cls, filtro: str) -> str:
        """Ruta del filtro.cir de la PLANTILLA. Solo para leer (p. ej. para
        dibujar el esquema): nunca se escribe ni se simula sobre él."""
        return str(cls.directorio_plantilla_de(filtro) / "filtro.cir")

    def __init__(self, filtro: str):
        # Se valida ANTES de crear el directorio temporal, para no dejar uno
        # huérfano si el filtro no existe.
        self.directorio_plantilla = self.directorio_plantilla_de(filtro)

        self.filtro = filtro
        self.ngspice_exe = NGSPICE_EXE

        self.directorio_trabajo = Path(tempfile.mkdtemp(prefix=f"opt_{filtro}_"))
        # Red de seguridad: si cleanup() nunca se llama, el directorio se
        # borra cuando este objeto se recoge o al cerrar el intérprete.
        self._finalizador = weakref.finalize(
            self, shutil.rmtree, str(self.directorio_trabajo), True
        )

        for archivo in self.directorio_plantilla.iterdir():
            if archivo.is_file() and archivo.suffix.lower() in _EXTENSIONES_PLANTILLA:
                shutil.copy2(archivo, self.directorio_trabajo / archivo.name)

        self.archivo_cir = str(self.directorio_trabajo / "filtro.cir")
        self.archivo_datos = str(self.directorio_trabajo / "datos_filtro.txt")
        self.resultado_json = str(self.directorio_trabajo / "resultado.json")
        self.grafica_archivo = str(self.directorio_trabajo / "resultado_filtro.png")

    # --- ciclo de vida del directorio de trabajo ---

    def cleanup(self) -> None:
        """Borra el directorio de trabajo. Es idempotente."""
        self._finalizador()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cleanup()

    # --- accesores (misma API de siempre) ---

    def get_archivo_cir(self):
        return self.archivo_cir

    def get_archivo_datos(self):
        return self.archivo_datos

    def get_ngspice_exe(self):
        return self.ngspice_exe

    def get_resultado_json(self):
        return self.resultado_json

    def get_grafica_archivo(self):
        return self.grafica_archivo

    def get_directorio_trabajo(self):
        return str(self.directorio_trabajo)

    def get_plantilla_cir(self):
        return str(self.directorio_plantilla / "filtro.cir")