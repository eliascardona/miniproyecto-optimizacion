"""
Comprobaciones de consistencia de un esquema ya construido. Se ejecutan al
construir el esquema de cada filtro (si algo falla, falla fuerte y temprano)
y en las pruebas.
"""
from .errores import EsquemaError
from .netlist import GND, Netlist

# Caja (largo del símbolo a lo largo de la ruta, ancho transversal) por tipo de elemento.
_CAJA = {"R": (1.1, 0.5), "L": (1.3, 0.5), "C": (0.5, 1.0), "V": (1.0, 1.0)}


def _cajas(esquema: dict) -> list[tuple]:
    cajas = []
    for e in esquema["elementos"]:
        (xa, ya), (xb, yb) = e["ruta"][e["seg"]], e["ruta"][e["seg"] + 1]
        mx, my = (xa + xb) / 2, (ya + yb) / 2
        largo, ancho = _CAJA[e["tipo"]]
        w, h = (largo, ancho) if abs(yb - ya) < abs(xb - xa) else (ancho, largo)
        cajas.append((e["nombre"], mx - w / 2, my - h / 2, mx + w / 2, my + h / 2))
    for o in esquema["opamps"]:
        xs, ys = [p[0] for p in o["triangulo"]], [p[1] for p in o["triangulo"]]
        cajas.append((o["nombre"], min(xs), min(ys), max(xs), max(ys)))
    return cajas


def validar_esquema(esquema: dict, net: Netlist) -> list[str]:
    """Devuelve la lista de problemas encontrados (vacía = esquema consistente)."""
    problemas: list[str] = []
    nodos = esquema["nodos"]

    # 1) cobertura exacta: cada componente del netlist aparece UNA vez
    esperados = {p.nombre for p in net.pasivos} | {f.nombre for f in net.fuentes if f.modo == "ac"}
    dibujados = [e["nombre"] for e in esquema["elementos"]]
    for n in sorted({n for n in dibujados if dibujados.count(n) > 1}):
        problemas.append(f"{n} aparece más de una vez")
    for n in sorted(esperados - set(dibujados)):
        problemas.append(f"{n} está en el netlist y no en el esquema")
    for n in sorted(set(dibujados) - esperados):
        problemas.append(f"{n} está en el esquema y no en el netlist")
    faltan = {o.nombre for o in net.opamps} - {o["nombre"] for o in esquema["opamps"]}
    if faltan:
        problemas.append(f"op-amps sin dibujar: {sorted(faltan)}")

    # 2) rutas: sin segmentos de largo cero; símbolo sobre un segmento válido; extremos sobre sus nodos
    tierras = {tuple(t) for t in esquema["tierras"]}
    # Un elemento a tierra puede arrancar desplazado de su nodo (varias derivaciones en el mismo nodo):
    # vale si arranca en el extremo de un cable, que es el que lo une al nodo.
    extremos_de_cable = {tuple(p) for c in esquema["cables"] for p in (c[0], c[-1])}
    for e in esquema["elementos"]:
        ruta = e["ruta"]
        if any(a == b for a, b in zip(ruta, ruta[1:])):
            problemas.append(f"{e['nombre']}: ruta con un segmento de largo cero")
        if not 0 <= e["seg"] < len(ruta) - 1:
            problemas.append(f"{e['nombre']}: índice de segmento fuera de rango")
            continue
        no_tierra = [n for n in e["nodos"] if n != GND]
        posiciones = [[nodos[n]["x"], nodos[n]["y"]] for n in no_tierra if n in nodos]
        if len(posiciones) != len(no_tierra):
            problemas.append(f"{e['nombre']}: algún nodo no tiene posición")
        elif len(no_tierra) == 2:
            if sorted([ruta[0], ruta[-1]]) != sorted(posiciones):
                problemas.append(f"{e['nombre']}: los extremos de la ruta no coinciden con sus nodos {no_tierra}")
        elif ruta[0] != posiciones[0] and tuple(ruta[0]) not in extremos_de_cable:
            problemas.append(f"{e['nombre']}: la ruta no arranca en su nodo {no_tierra[0]}")
        if len(no_tierra) == 1 and tuple(ruta[-1]) not in tierras:
            problemas.append(f"{e['nombre']}: su extremo a tierra no tiene símbolo de tierra")

    # 3) choques entre símbolos (elementos y op-amps)
    cajas = _cajas(esquema)
    for i, a in enumerate(cajas):
        for b in cajas[i + 1:]:
            if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]:
                problemas.append(f"los símbolos de {a[0]} y {b[0]} se encimen")

    # 4) todo cae dentro de los límites declarados
    lim = esquema["limites"]
    puntos = [p for e in esquema["elementos"] for p in e["ruta"]] + [p for c in esquema["cables"] for p in c]
    if any(not (lim["x_min"] <= x <= lim["x_max"] and lim["y_min"] <= y <= lim["y_max"]) for x, y in puntos):
        problemas.append("hay geometría fuera de 'limites'")
    return problemas


def exigir_esquema_valido(esquema: dict, net: Netlist) -> None:
    problemas = validar_esquema(esquema, net)
    if problemas:
        raise EsquemaError("El esquema generado es inconsistente: " + "; ".join(problemas))