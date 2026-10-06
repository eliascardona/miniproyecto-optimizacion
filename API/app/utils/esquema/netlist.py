"""
Parser del subconjunto de netlist SPICE que usan los .cir del proyecto.

Elementos:  R/C/L (2 terminales) · V (fuentes) · X (op-amp, subcircuito de 5 pines)
Directivas: .title, y dentro de .control la línea que observa la salida (vm(<nodo>)).
El resto de directivas (.INCLUDE, .AC, .END...) se ignora.

Función pura: no toca archivos ni estado global.
"""
import re
from dataclasses import dataclass

from .errores import NetlistInvalido

GND = "0"


@dataclass(frozen=True)
class Pasivo:
    nombre: str
    tipo: str                      # "R" | "C" | "L"
    nodos: tuple[str, str]
    valor: float

    def otro_nodo(self, nodo: str) -> str:
        a, b = self.nodos
        return b if a == nodo else a


@dataclass(frozen=True)
class FuenteTension:
    nombre: str
    nodos: tuple[str, str]
    modo: str                      # "ac" | "dc"
    valor: float


@dataclass(frozen=True)
class OpAmp:
    """Pines en el orden del subcircuito LM741: In+, In-, V+, V-, Out."""
    nombre: str
    in_p: str
    in_n: str
    v_pos: str
    v_neg: str
    salida: str
    modelo: str


@dataclass(frozen=True)
class Netlist:
    titulo: str
    pasivos: tuple[Pasivo, ...]
    fuentes: tuple[FuenteTension, ...]
    opamps: tuple[OpAmp, ...]
    nodo_observado: str | None     # nodo de vm(...) en el bloque .control


_NUMERO = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)([A-Za-z]*)")
_MULTIPLICADOR = {"t": 1e12, "g": 1e9, "k": 1e3, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}


def valor_spice_a_float(token: str) -> float:
    """'1.5e-8' -> 1.5e-08 · '4.7u' -> 4.7e-06 · '1meg' -> 1e6 · '500ohms' -> 500 · '5.0V' -> 5.0"""
    m = _NUMERO.match(token)
    if not m:
        raise ValueError(f"no es un número SPICE: {token!r}")
    base, sufijo = float(m.group(1)), m.group(2).lower()
    if sufijo.startswith("meg"):
        return base * 1e6
    if sufijo.startswith("mil"):
        return base * 25.4e-6
    return base * _MULTIPLICADOR.get(sufijo[:1], 1.0)


_OBSERVACION = re.compile(r"\b(?:vm|vdb|vp|v)\(([^)\s,]+)", re.IGNORECASE)


def parse_netlist(texto: str) -> Netlist:
    titulo, nodo_observado = "", None
    pasivos: list[Pasivo] = []
    fuentes: list[FuenteTension] = []
    opamps: list[OpAmp] = []
    vistos: set[str] = set()
    en_control, primera = False, True

    for numero, cruda in enumerate(texto.splitlines(), start=1):
        linea = cruda.strip()
        if not linea:
            continue
        if primera:
            primera = False
            if not linea.startswith(("*", ".")):      # convención SPICE: la 1.ª línea es el título
                titulo = linea
                continue
        bajo = linea.lower()
        if linea.startswith("*"):
            continue
        if bajo.startswith(".title"):
            titulo = linea[6:].strip()
            continue
        if bajo.startswith(".control"):
            en_control = True
            continue
        if bajo.startswith(".endc"):
            en_control = False
            continue
        if en_control:
            if nodo_observado is None:
                m = _OBSERVACION.search(linea)
                if m:
                    nodo_observado = m.group(1)
            continue
        if linea.startswith("."):
            continue

        p = linea.split()
        nombre, letra = p[0], p[0][0].upper()
        if nombre.lower() in vistos:
            raise NetlistInvalido(f"línea {numero}: el componente '{nombre}' está repetido")
        vistos.add(nombre.lower())

        try:
            if letra in "RCL":
                if len(p) < 4:
                    raise ValueError("se esperaba: nombre nodo1 nodo2 valor")
                pasivos.append(Pasivo(nombre, letra, (p[1], p[2]), valor_spice_a_float(p[3])))
            elif letra == "V":
                if len(p) < 4:
                    raise ValueError("se esperaba: nombre nodo+ nodo- [AC|DC] valor")
                tokens = [t.lower() for t in p[3:]]
                modo = "ac" if "ac" in tokens else "dc"
                idx = tokens.index(modo) + 1 if modo in tokens else 0
                fuentes.append(FuenteTension(nombre, (p[1], p[2]), modo, valor_spice_a_float(p[3 + idx])))
            elif letra == "X":
                if len(p) < 7:
                    raise ValueError("se esperaba: nombre in+ in- v+ v- out modelo")
                opamps.append(OpAmp(nombre, p[1], p[2], p[3], p[4], p[5], p[6]))
            else:
                raise ValueError(f"tipo de elemento no soportado ('{letra}')")
        except (ValueError, IndexError) as e:
            raise NetlistInvalido(f"línea {numero} ({linea!r}): {e}") from e

    return Netlist(titulo, tuple(pasivos), tuple(fuentes), tuple(opamps), nodo_observado)