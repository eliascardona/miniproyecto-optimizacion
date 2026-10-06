"""
ngspice SIMULADO para las pruebas (no es ngspice: solo imita lo justo).

Uso:  python _ngspice_falso.py -b <archivo.cir>

Imita lo que importa para el aislamiento de archivos:
  * lee el barrido `.AC DEC n f1 f2` y la línea `wrdata <archivo> vm(<nodo>)`;
  * escribe <archivo> con RUTA RELATIVA, o sea relativa al directorio de
    trabajo (cwd) del proceso -- igual que ngspice real;
  * la curva depende de los valores de los componentes del .cir, de modo que
    dos circuitos distintos producen datos distintos (así se distingue un
    resultado fresco de uno viejo).
"""
import math
import re
import sys
from pathlib import Path


def main() -> int:
    cir = Path(sys.argv[sys.argv.index("-b") + 1])
    texto = cir.read_text()

    m_ac = re.search(r"^\s*\.AC\s+DEC\s+(\d+)\s+(\S+)\s+(\S+)", texto, re.I | re.M)
    m_wr = re.search(r"^\s*wrdata\s+(\S+)", texto, re.I | re.M)
    m_vs = re.search(r"^Vs\s+\S+\s+\S+\s+AC\s+(\S+)", texto, re.I | re.M)
    if not (m_ac and m_wr and m_vs):
        return 1

    puntos_por_decada, f1, f2 = int(m_ac.group(1)), float(m_ac.group(2)), float(m_ac.group(3))
    vs = float(m_vs.group(1))

    valores = [float(v) for v in re.findall(r"^[RC]\w*\s+\S+\s+\S+\s+(\S+)\s*$", texto, re.M)]
    huella = sum(math.log10(v) * (i + 1) for i, v in enumerate(valores))
    fc = 10 ** (1.5 + (huella * 0.37) % 2.5)

    n = max(2, int(round(math.log10(f2 / f1) * puntos_por_decada)) + 1)
    with open(m_wr.group(1), "w") as salida:          # ruta relativa -> cwd del proceso
        for i in range(n):
            f = f1 * 10 ** (i / puntos_por_decada)
            salida.write(f"{f:.8e} {vs / math.sqrt(1 + (f / fc) ** 4):.8e}\n")
    Path("simulacion.raw").write_bytes(b"RAW")
    return 0


if __name__ == "__main__":
    sys.exit(main())