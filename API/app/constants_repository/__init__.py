from app.pydantic_schema.global_validator import safe_parse

NGSPICE_EXE = r"C:\SPICE_ELECTRONICS\Spice64\bin\ngspice.exe"
ARCHIVO_CIR = r"C:\Users\elias\Documents\ESCUELA\servicio-social\miniproyecto-optimizacion\API\app\constants_repository\filtro.cir"
ARCHIVO_DATOS = r"C:\Users\elias\Documents\ESCUELA\servicio-social\miniproyecto-optimizacion\API\app\constants_repository\datos_filtro.txt"
ARCHIVO_CONFIG_JSON = "config.json"
ARCHIVO_RESULTADO_JSON = "resultado.json"

# Gráfica de la respuesta final del filtro optimizado
GRAFICA_ARCHIVO = r"C:\Users\elias\Documents\ESCUELA\servicio-social\miniproyecto-optimizacion\API\app\constants_repository\resultado_filtro.png"

# JSON con el resumen del resultado de la optimización
ARCHIVO_RESULTADO_JSON = "resultado.json"


class ConstantsRepository:

    def __init__(self):
        self.ngspice_exe = NGSPICE_EXE
        self.archivo_datos = ARCHIVO_DATOS
        self.archivo_cir = ARCHIVO_CIR
        self.resultado_json = ARCHIVO_RESULTADO_JSON
        self.grafica_archivo = GRAFICA_ARCHIVO

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