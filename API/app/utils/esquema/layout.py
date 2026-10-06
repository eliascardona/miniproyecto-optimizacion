"""
Layout: Topologia -> ESQUEMA (diccionario listo para serializar a JSON).

Coordenadas en UNIDADES DE REJILLA (x crece a la derecha, y hacia ABAJO); el
cliente decide cuántos píxeles vale una unidad. Cada elemento trae su RUTA
(polilínea) y el índice del segmento donde va su símbolo, de modo que quien
dibuje solo tiene que pintar: no necesita conocer la topología.

Convenciones:
  · fila principal y = 0 (la línea de señal); derivaciones hacia abajo, salvo en
    ramas paralelas, donde la rama superior deriva hacia arriba y la inferior hacia abajo;
  · cada derivación termina en su propio símbolo de tierra (no hay riel común);
  · la realimentación se dibuja como un lazo por encima de la fila principal.
"""
from collections import defaultdict

from .errores import TopologiaNoSoportada
from .etapas import Etapa, analizar_topologia
from .netlist import GND, Netlist

# --- geometría (unidades de rejilla) ---
PASO_SERIE = 2.0                  # distancia entre nodos consecutivos de un camino
LARGO_DERIVACION = 1.6            # largo de un elemento a tierra
SEPARACION_DERIVACIONES = 1.2     # entre derivaciones en un mismo nodo
SEPARACION_RAMAS = 4.4            # entre las dos filas de ramas paralelas
ALTO_CARRIL = 2.0                 # del punto más alto de la etapa al lazo de realimentación
HOLGURA_OPAMP = 1.5               # del nodo + al borde izquierdo del triángulo
ANCHO_OPAMP = 1.8
SALIDA_OPAMP = 0.9                # del vértice de salida al nodo de salida
LAZO_SEGUIDOR = 2.0               # profundidad del cable que une la salida con la entrada (-)
TERMINAL_SALIDA = 1.2
VERSION_ESQUEMA = 1

ROLES_OPTIMIZABLES = ("serie", "derivacion", "realimentacion")


def _r(v: float) -> float:
    return round(v, 3) + 0.0       # "+ 0.0" evita -0.0


def _punto(p) -> list:
    return [_r(p[0]), _r(p[1])]


def _filas(n_ramas: int) -> list[float]:
    if n_ramas == 1:
        return [0.0]
    if n_ramas == 2:
        return [-SEPARACION_RAMAS / 2, SEPARACION_RAMAS / 2]
    raise TopologiaNoSoportada(f"{n_ramas} ramas en paralelo")   # no debería ocurrir: lo filtra etapas.py


class _Lienzo:
    def __init__(self):
        self.pos: dict[str, tuple[float, float]] = {}
        self.elementos: list[dict] = []
        self.opamps: list[dict] = []
        self.cables: list[list] = []
        self.tierras: list[tuple] = []

    def elemento(self, comp, rol, etapa, ruta, seg, tipo=None):
        self.elementos.append({
            "nombre": comp.nombre,
            "tipo": tipo or comp.tipo,
            "valor": comp.valor,
            "nodos": list(comp.nodos),
            "rol": rol,
            "etapa": etapa,
            "optimizable": rol in ROLES_OPTIMIZABLES,
            "ruta": [_punto(p) for p in ruta],
            "seg": seg,
        })


def _colocar_etapa(L: _Lienzo, etapa: Etapa) -> None:
    caminos = etapa.caminos
    largo = len(caminos[0].nodos)
    filas = _filas(len(caminos))

    deriv_por_nodo: dict[str, list] = defaultdict(list)
    for e in etapa.derivaciones:
        deriv_por_nodo[e.otro_nodo(GND)].append(e)

    # columnas: cada nodo extra de derivaciones ensancha el paso hacia el siguiente
    xs = [L.pos[etapa.nodo_entrada][0]]
    for i in range(largo - 1):
        extra = max(max(len(deriv_por_nodo.get(c.nodos[i], [])) - 1, 0) for c in caminos)
        xs.append(xs[-1] + PASO_SERIE + SEPARACION_DERIVACIONES * extra)

    for camino, fila in zip(caminos, filas):
        for i, nodo in enumerate(camino.nodos):
            punto = (xs[i], 0.0 if i in (0, largo - 1) else fila)
            if L.pos.get(nodo, punto) != punto:
                raise TopologiaNoSoportada(f"Etapa {etapa.indice}: el nodo {nodo} pertenece a dos ramas.")
            L.pos[nodo] = punto

    # elementos en serie (los extremos de una rama se unen a la fila principal con tramos verticales)
    for camino, fila in zip(caminos, filas):
        for i, e in enumerate(camino.pasivos):
            (xa, ya), (xb, yb) = L.pos[camino.nodos[i]], L.pos[camino.nodos[i + 1]]
            ruta = [(xa, ya)]
            if ya != fila:
                ruta.append((xa, fila))
            ruta.append((xb, fila))
            if yb != fila:
                ruta.append((xb, yb))
            L.elemento(e, "serie", etapa.indice, ruta, 1 if ya != fila else 0)

    # derivaciones a tierra
    y_alto = min(0.0, *filas)
    for nodo, lista in deriv_por_nodo.items():
        x, y = L.pos[nodo]
        sentido = -1.0 if y < 0 else 1.0
        for j, e in enumerate(lista):
            xj = x + SEPARACION_DERIVACIONES * j
            if j:
                L.cables.append([(xj - SEPARACION_DERIVACIONES, y), (xj, y)])
            punta = y + sentido * LARGO_DERIVACION
            y_alto = min(y_alto, punta)
            L.elemento(e, "derivacion", etapa.indice, [(xj, y), (xj, punta)], 0)
            L.tierras.append((xj, punta))

    o = etapa.opamp
    if o is None:
        return

    # op-amp (seguidor): el nodo + queda en la fila principal; la salida es el nodo de entrada de la etapa siguiente
    xp, yp = L.pos[o.in_p]
    xu = xp + SEPARACION_DERIVACIONES * max(len(deriv_por_nodo.get(o.in_p, [])) - 1, 0)
    x0 = xu + HOLGURA_OPAMP
    x1 = x0 + ANCHO_OPAMP
    x_sal = x1 + SALIDA_OPAMP
    xj = x1 + SALIDA_OPAMP / 2
    L.pos[o.salida] = (x_sal, 0.0)

    L.cables.append([(xu, yp), (xu + 0.6, yp), (xu + 0.6, -0.5), (x0, -0.5)])      # nodo -> entrada (+)
    L.cables.append([(x1, 0.0), (xj, 0.0)])                                        # salida del op-amp
    L.cables.append([(xj, 0.0), (x_sal, 0.0)])                                     #   (partida en xj: ahí nace el lazo)
    L.cables.append([(xj, 0.0), (xj, LAZO_SEGUIDOR), (x0 - 0.7, LAZO_SEGUIDOR),    # salida -> entrada (-)
                     (x0 - 0.7, 0.5), (x0, 0.5)])
    L.opamps.append({
        "nombre": o.nombre,
        "modelo": o.modelo,
        "etapa": etapa.indice,
        "nodos": {"in_p": o.in_p, "in_n": o.in_n, "out": o.salida},
        "pines": {"in_p": _punto((x0, -0.5)), "in_n": _punto((x0, 0.5)), "out": _punto((x1, 0.0))},
        "triangulo": [_punto((x0, -1.0)), _punto((x0, 1.0)), _punto((x1, 0.0))],
        "alimentacion": {"v_pos": o.v_pos, "v_neg": o.v_neg},
    })

    # realimentación: lazo por encima de todo lo que ocupa la etapa
    carril = y_alto - ALTO_CARRIL
    for e in etapa.realimentacion:
        interno = next(n for n in e.nodos if n != o.salida)
        xi, yi = L.pos[interno]
        L.elemento(e, "realimentacion", etapa.indice,
                   [(xi, yi), (xi, carril), (x_sal, carril), (x_sal, 0.0)], 1)


def construir_esquema(net: Netlist) -> dict:
    top = analizar_topologia(net)
    L = _Lienzo()

    # fuente y su resistencia
    L.pos[top.nodo_fuente] = (0.0, 0.0)
    L.pos[top.nodo_entrada] = (PASO_SERIE, 0.0)
    L.elemento(top.fuente, "fuente", 0, [(0.0, 0.0), (0.0, LARGO_DERIVACION)], 0, tipo="V")
    L.tierras.append((0.0, LARGO_DERIVACION))
    L.elemento(top.resistencia_fuente, "resistencia_fuente", 0, [(0.0, 0.0), (PASO_SERIE, 0.0)], 0)

    for etapa in top.etapas:
        _colocar_etapa(L, etapa)

    # carga y terminal de salida (RL va a la derecha de otras derivaciones del mismo nodo)
    x_sal, _ = L.pos[top.nodo_salida]
    otras = sum(1 for e in L.elementos if e["rol"] == "derivacion" and top.nodo_salida in e["nodos"])
    x_rl = x_sal + SEPARACION_DERIVACIONES * otras
    if otras:
        L.cables.append([(x_rl - SEPARACION_DERIVACIONES, 0.0), (x_rl, 0.0)])
    L.elemento(top.carga, "carga", 0, [(x_rl, 0.0), (x_rl, LARGO_DERIVACION)], 0)
    L.tierras.append((x_rl, LARGO_DERIVACION))
    salida = {"nodo": top.nodo_salida, "ruta": [_punto((x_rl, 0.0)), _punto((x_rl + TERMINAL_SALIDA, 0.0))]}

    # uniones: puntos donde confluyen 3 o más extremos (se dibuja un punto)
    conteo: dict[tuple, int] = defaultdict(int)
    for e in L.elementos:
        for p in (e["ruta"][0], e["ruta"][-1]):
            conteo[tuple(p)] += 1
    for c in L.cables:
        for p in (c[0], c[-1]):
            conteo[(_r(p[0]), _r(p[1]))] += 1
    conteo[tuple(salida["ruta"][0])] += 1
    uniones = sorted([list(p) for p, n in conteo.items() if n >= 3])

    cables = [[_punto(p) for p in c] for c in L.cables]
    tierras = [_punto(p) for p in L.tierras]

    puntos = [p for e in L.elementos for p in e["ruta"]] + [p for c in cables for p in c] + \
             [p for o in L.opamps for p in o["triangulo"]] + salida["ruta"] + \
             [[x + dx, y + dy] for x, y in tierras for dx, dy in ((-0.5, 0.0), (0.5, 0.5))]
    limites = {"x_min": min(p[0] for p in puntos), "x_max": max(p[0] for p in puntos),
               "y_min": min(p[1] for p in puntos), "y_max": max(p[1] for p in puntos)}

    return {
        "version_esquema": VERSION_ESQUEMA,
        "titulo": net.titulo,
        "nodo_fuente": top.nodo_fuente,
        "nodo_entrada": top.nodo_entrada,
        "nodo_salida": top.nodo_salida,
        "num_etapas": len(top.etapas),
        "alimentacion": [{"nombre": f.nombre, "nodo": next(n for n in f.nodos if n != GND), "valor": f.valor}
                         for f in top.alimentaciones],
        "nodos": {n: {"x": _r(x), "y": _r(y)} for n, (x, y) in L.pos.items()},
        "elementos": L.elementos,
        "opamps": L.opamps,
        "cables": cables,
        "tierras": tierras,
        "uniones": uniones,
        "salida": salida,
        "limites": limites,
    }