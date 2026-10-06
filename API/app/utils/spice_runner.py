"""
Utilería: escritura del archivo .cir con los valores del individuo actual
y ejecución de ngspice en modo batch.

No guarda estado; recibe todo lo que necesita como argumentos.
"""
import subprocess
from pathlib import Path
from typing import Sequence

from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12
from app.utils.spice_formatter import valor_spice, valor_frecuencia


def actualizar_circuito(
    individuo: list[int],
    componentes_ag: list[dict],
    archivo_cir: str,
    vs_valor: float,
    vpp_valor: float,
    vnn_valor: float,
    rs_valor: float,
    rl_valor: float,
    f_inicial: float,
    f_final: float,
) -> None:
    """
    Reescribe el archivo .cir con:
        - los valores R/C del individuo (según series E12 / E6), y
        - los parámetros fijos de entorno (VS, VPP, VNN, RS, RL, barrido .AC).
    """
    texto = Path(archivo_cir).read_text()
    lineas = texto.splitlines()

    # 1. Actualizar componentes R y C
    for i, comp in enumerate(componentes_ag):
        lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
        nuevo_valor = valor_spice(lista[individuo[i]])

        for idx, linea in enumerate(lineas):
            if linea.strip().startswith(comp["nombre"] + " "):
                partes = linea.split()
                partes[-1] = nuevo_valor
                lineas[idx] = " ".join(partes)
                break

    # 2. Parámetros fijos de entorno
    for i, linea in enumerate(lineas):
        partes = linea.split()
        if not partes:
            continue
        nombre = partes[0].upper()

        if nombre == "VS":
            partes[-1] = str(vs_valor)
        elif nombre == "VPP":
            partes[-1] = str(vpp_valor)
        elif nombre == "VNN":
            partes[-1] = str(vnn_valor)
        elif nombre == "RS":
            partes[-1] = str(rs_valor)
        elif nombre == "RL":
            partes[-1] = str(rl_valor)
        elif nombre == ".AC":
            partes[-2] = valor_frecuencia(f_inicial)
            partes[-1] = valor_frecuencia(f_final)
        else:
            continue

        lineas[i] = " ".join(partes)

    Path(archivo_cir).write_text("\n".join(lineas))


def ejecutar_spice(ngspice_exe: "str | Sequence[str]", archivo_cir: str) -> bool:
    """
    Lanza ngspice en modo batch y devuelve True si el código de retorno es 0.

    ngspice se ejecuta con el DIRECTORIO DEL .cir como directorio de trabajo
    (cwd). Es necesario porque el .cir pide `wrdata datos_filtro.txt` y
    `write simulacion.raw` con rutas RELATIVAS, y ngspice las resuelve contra
    el cwd del proceso, no contra la carpeta del netlist. Sin el cwd explícito,
    esos archivos caían en el directorio desde el que se arrancó uvicorn,
    mientras el fitness leía el datos_filtro.txt de otra carpeta (desfasado).

    `ngspice_exe` puede ser una ruta (str) o una lista de argumentos (p. ej.
    [sys.executable, "ngspice_falso.py"]); lo segundo permite probar este
    flujo sin tener ngspice instalado.
    """
    ruta_cir = Path(archivo_cir).resolve()
    prefijo = [ngspice_exe] if isinstance(ngspice_exe, str) else list(ngspice_exe)
    resultado = subprocess.run(
        [*prefijo, "-b", str(ruta_cir)],
        cwd=str(ruta_cir.parent),
        capture_output=True,
        text=True,
    )
    return resultado.returncode == 0