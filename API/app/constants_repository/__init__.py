from app.pydantic_schema.global_validator import safe_parse

NGSPICE_EXE = r"C:\Users\luis_\Desktop\Spice64\bin\ngspice.exe"
ARCHIVO_CIR = "filtro.cir"
ARCHIVO_DATOS = "datos_filtro.txt"
ARCHIVO_CONFIG_JSON = "config.json"

# Gráfica de la respuesta final del filtro optimizado
GRAFICA_ARCHIVO = "resultado_filtro.png"   # ruta donde se guarda la imagen

# JSON con el resumen del resultado de la optimización
ARCHIVO_RESULTADO_JSON = "resultado.json"


class ConstantsRepository:

    def __init__(self):
        self.archivo_cir = ARCHIVO_CIR

    def get_archivo_cir(self):
        return self.archivo_cir