from pathlib import Path

# Cada filtro tiene su propia subcarpeta con su .cir/lm741.lib (topologías
# distintas), pero comparten el mismo ngspice instalado. Antes esto era fijo
# a un solo filtro (pasa_altas); ahora ConstantsRepository(filtro) arma las
# rutas dentro de esa subcarpeta, para que agregar un filtro nuevo solo
# implique agregar una carpeta más, sin tocar esta clase.
_DIRECTORIO_BASE = Path(__file__).resolve().parent

NGSPICE_EXE = r"C:\SPICE_ELECTRONICS\Spice64\bin\ngspice.exe"  # cambiar según el usuario que ejecuta el programa


class ConstantsRepository:

    def __init__(self, filtro: str):

        directorio_filtro = _DIRECTORIO_BASE / filtro

        if not directorio_filtro.is_dir():
            raise ValueError(
                f"No existe la carpeta de recursos para el filtro '{filtro}' "
                f"(se esperaba: {directorio_filtro})"
            )

        self.filtro = filtro
        self.ngspice_exe = NGSPICE_EXE
        self.archivo_cir = str(directorio_filtro / "filtro.cir")
        self.archivo_datos = str(directorio_filtro / "datos_filtro.txt")
        self.resultado_json = str(directorio_filtro / "resultado.json")
        self.grafica_archivo = str(directorio_filtro / "resultado_filtro.png")

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