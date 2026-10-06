"""
Análisis de topología: de un Netlist a una cadena de ETAPAS.

Modelo (el de los 4 filtros del proyecto y el de las escaleras LC clásicas):

    Vs ─ Rs ─ [etapa 1] ─ [etapa 2] ─ ... ─ Rl            (Rl a tierra en la salida)

Cada op-amp CIERRA una etapa. Dentro de una etapa:
  · serie        elementos entre dos nodos que no son tierra y que forman el
                 camino (o 2 caminos paralelos) desde la entrada de la etapa
                 hasta la entrada no inversora (+) del op-amp;
  · derivación   elemento entre un nodo de la etapa y tierra;
  · realimentación  elemento entre un nodo de la etapa y la SALIDA de su op-amp.
Una etapa sin op-amp (escalera pasiva) termina directamente en el nodo de salida.

Todo lo que no encaje se rechaza con TopologiaNoSoportada y un mensaje que
dice QUÉ no encajó; nunca se dibuja "a medias".
"""
from dataclasses import dataclass

from .errores import TopologiaNoSoportada
from .netlist import GND, FuenteTension, Netlist, OpAmp, Pasivo

MAX_RAMAS_PARALELAS = 2


@dataclass(frozen=True)
class Camino:
    nodos: tuple[str, ...]          # n0, n1, ..., nk
    pasivos: tuple[Pasivo, ...]     # k elementos; pasivos[i] une nodos[i] con nodos[i+1]


@dataclass(frozen=True)
class Etapa:
    indice: int                     # 1, 2, ...
    nodo_entrada: str
    nodo_objetivo: str              # entrada (+) del op-amp, o la salida del circuito si no hay op-amp
    opamp: OpAmp | None
    caminos: tuple[Camino, ...]
    derivaciones: tuple[Pasivo, ...]
    realimentacion: tuple[Pasivo, ...]


@dataclass(frozen=True)
class Topologia:
    fuente: FuenteTension
    alimentaciones: tuple[FuenteTension, ...]
    resistencia_fuente: Pasivo
    carga: Pasivo
    nodo_fuente: str
    nodo_entrada: str
    nodo_salida: str
    etapas: tuple[Etapa, ...]


def _unico(candidatos: list, que: str, preferencias=()):
    """Devuelve el único candidato; si hay varios, intenta desempatar con `preferencias` (en orden)."""
    actuales = list(candidatos)
    if len(actuales) == 1:
        return actuales[0]
    if actuales:
        for preferida in preferencias:
            filtrados = [c for c in actuales if preferida(c)]
            if len(filtrados) == 1:
                return filtrados[0]
            if filtrados:
                actuales = filtrados
    nombres = [c.nombre for c in candidatos]
    if not candidatos:
        raise TopologiaNoSoportada(f"No se encontró {que}.")
    raise TopologiaNoSoportada(f"No se pudo identificar {que} sin ambigüedad (candidatos: {nombres}).")


def _alcanzables(nodo_inicial: str, core: list[Pasivo], asignados: set[str], salidas_opamp: set[str]):
    """Nodos alcanzables desde la entrada de la etapa por elementos aún sin asignar, sin cruzar
    tierra ni la salida de ningún op-amp (esas salidas quedan como 'borde')."""
    alcanzados, borde, pendientes = {nodo_inicial}, set(), [nodo_inicial]
    while pendientes:
        n = pendientes.pop()
        for e in core:
            if e.nombre in asignados or n not in e.nodos:
                continue
            otro = e.otro_nodo(n)
            if otro == GND:
                continue
            if otro in salidas_opamp and otro != nodo_inicial:
                borde.add(otro)
                continue
            if otro not in alcanzados:
                alcanzados.add(otro)
                pendientes.append(otro)
    return alcanzados, borde


def _caminos_serie(origen: str, destino: str, series: list[Pasivo]) -> list[Camino]:
    resultado: list[Camino] = []

    def dfs(nodo, nodos, pasivos):
        if nodo == destino:
            resultado.append(Camino(tuple(nodos), tuple(pasivos)))
            return
        for e in series:
            if e in pasivos or nodo not in e.nodos:
                continue
            siguiente = e.otro_nodo(nodo)
            if siguiente not in nodos:
                dfs(siguiente, nodos + [siguiente], pasivos + [e])

    dfs(origen, [origen], [])
    return resultado


def analizar_topologia(net: Netlist) -> Topologia:
    # ---- fuente, resistencia de fuente, entrada ----
    fuentes_ac = [f for f in net.fuentes if f.modo == "ac"]
    if len(fuentes_ac) != 1:
        raise TopologiaNoSoportada(
            f"Se esperaba exactamente una fuente de señal AC y hay {len(fuentes_ac)}.")
    fuente = fuentes_ac[0]
    no_tierra = [n for n in fuente.nodos if n != GND]
    if len(no_tierra) != 1:
        raise TopologiaNoSoportada(f"La fuente {fuente.nombre} debe tener un terminal a tierra.")
    nodo_fuente = no_tierra[0]
    alimentaciones = tuple(f for f in net.fuentes if f is not fuente)

    rs = _unico([p for p in net.pasivos if nodo_fuente in p.nodos],
                f"la resistencia de la fuente (conectada al nodo {nodo_fuente})",
                [lambda p: p.nombre.lower() == "rs"])
    nodo_entrada = rs.otro_nodo(nodo_fuente)
    if nodo_entrada == GND:
        raise TopologiaNoSoportada(f"{rs.nombre} conecta la fuente directamente a tierra.")

    # ---- salida y carga ----
    nodos_existentes = {n for p in net.pasivos for n in p.nodos} | {o.salida for o in net.opamps}
    if net.nodo_observado in nodos_existentes:
        nodo_salida = net.nodo_observado
    else:
        rl = next((p for p in net.pasivos if p.nombre.lower() == "rl"), None)
        if rl is None:
            raise TopologiaNoSoportada("No se pudo determinar el nodo de salida (sin vm(...) en .control ni 'Rl').")
        nodo_salida = rl.otro_nodo(GND) if GND in rl.nodos else rl.nodos[0]

    carga = _unico([p for p in net.pasivos if p is not rs and set(p.nodos) == {nodo_salida, GND}],
                   f"la carga (entre el nodo {nodo_salida} y tierra)",
                   [lambda p: p.nombre.lower() == "rl", lambda p: p.tipo == "R"])

    # ---- op-amps ----
    salidas_opamp = {o.salida for o in net.opamps}
    if len(salidas_opamp) != len(net.opamps):
        raise TopologiaNoSoportada("Dos op-amps comparten el mismo nodo de salida.")
    for o in net.opamps:
        if o.in_n != o.salida:
            raise TopologiaNoSoportada(
                f"El op-amp {o.nombre} no es un seguidor de ganancia unitaria (in- = {o.in_n}, "
                f"salida = {o.salida}); solo se dibujan op-amps con la entrada inversora unida a la salida.")

    # ---- descomposición en etapas ----
    core = [p for p in net.pasivos if p is not rs and p is not carga]
    asignados: set[str] = set()
    usados: set[str] = set()
    etapas: list[Etapa] = []
    nodo_actual = nodo_entrada

    for _ in range(len(net.opamps) + 1):
        k = len(etapas) + 1
        alcanzados, _borde = _alcanzables(nodo_actual, core, asignados, salidas_opamp)

        candidatos = [o for o in net.opamps if o.nombre not in usados and o.in_p in alcanzados]
        if len(candidatos) > 1:
            raise TopologiaNoSoportada(
                f"Etapa {k}: más de un op-amp ({[o.nombre for o in candidatos]}) parte del mismo punto.")
        opamp = candidatos[0] if candidatos else None
        objetivo = opamp.in_p if opamp else nodo_salida
        if opamp is None and nodo_salida not in alcanzados:
            raise TopologiaNoSoportada(
                f"Etapa {k}: la señal no llega desde el nodo {nodo_actual} hasta la salida ({nodo_salida}).")

        series, derivaciones, realim = [], [], []
        for e in core:
            if e.nombre in asignados:
                continue
            a, b = e.nodos
            if a == b:
                raise TopologiaNoSoportada(f"{e.nombre} tiene sus dos terminales en el nodo {a}.")
            if GND in e.nodos:
                if e.otro_nodo(GND) in alcanzados:
                    derivaciones.append(e)
                continue
            dentro = [n for n in e.nodos if n in alcanzados]
            if len(dentro) == 2:
                series.append(e)
            elif len(dentro) == 1 and opamp is not None and e.otro_nodo(dentro[0]) == opamp.salida:
                realim.append(e)

        caminos = _caminos_serie(nodo_actual, objetivo, series)
        if not caminos:
            raise TopologiaNoSoportada(
                f"Etapa {k}: no hay una cadena de elementos en serie entre {nodo_actual} y {objetivo}.")
        if len(caminos) > MAX_RAMAS_PARALELAS:
            raise TopologiaNoSoportada(
                f"Etapa {k}: hay {len(caminos)} ramas en paralelo y solo se soportan {MAX_RAMAS_PARALELAS}.")
        if len({len(c.nodos) for c in caminos}) > 1:
            raise TopologiaNoSoportada(f"Etapa {k}: las ramas en paralelo tienen distinto número de elementos.")
        en_caminos = {p.nombre for c in caminos for p in c.pasivos}
        sueltos = [e.nombre for e in series if e.nombre not in en_caminos]
        if sueltos:
            raise TopologiaNoSoportada(f"Etapa {k}: elementos en serie fuera de las ramas: {sueltos}.")
        if len(caminos) > 1:
            extremos = {nodo_actual, objetivo}
            en_extremo = [e.nombre for e in derivaciones if e.otro_nodo(GND) in extremos]
            if en_extremo:
                raise TopologiaNoSoportada(
                    f"Etapa {k}: derivaciones a tierra en el punto donde se unen las ramas: {en_extremo}.")

        asignados.update(e.nombre for e in (*series, *derivaciones, *realim))
        etapas.append(Etapa(k, nodo_actual, objetivo, opamp, tuple(caminos),
                            tuple(derivaciones), tuple(realim)))

        if opamp is None:
            break
        usados.add(opamp.nombre)
        nodo_actual = opamp.salida
        if nodo_actual == nodo_salida and all(e.nombre in asignados for e in core):
            break
    else:
        raise TopologiaNoSoportada("No se pudo cerrar la cadena de etapas.")

    sin_etapa = [e.nombre for e in core if e.nombre not in asignados]
    if sin_etapa:
        raise TopologiaNoSoportada(f"Elementos que no pertenecen a ninguna etapa reconocible: {sin_etapa}.")
    sin_usar = [o.nombre for o in net.opamps if o.nombre not in usados]
    if sin_usar:
        raise TopologiaNoSoportada(f"Op-amps que no están en la cadena de señal: {sin_usar}.")
    if etapas[-1].opamp is not None and etapas[-1].opamp.salida != nodo_salida:
        raise TopologiaNoSoportada(
            f"La cadena termina en {etapas[-1].opamp.salida} pero la salida observada es {nodo_salida}.")

    return Topologia(fuente, alimentaciones, rs, carga, nodo_fuente, nodo_entrada, nodo_salida, tuple(etapas))