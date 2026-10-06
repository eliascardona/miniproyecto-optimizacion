"""
Herramienta de DESARROLLO: dibuja el esquema de uno o más filtros en un PNG.

    python -m tools.dibujar_esquema                       # los 4 filtros -> esquemas.png
    python -m tools.dibujar_esquema pasa_altas -o x.png   # uno solo

Dibuja usando ÚNICAMENTE el JSON de obtener_esquema() (nada del netlist): es lo
mismo que tendrá que hacer cualquier cliente, así que sirve para comprobar a
simple vista que el contrato es suficiente. Usa la API de Figure (sin pyplot).
"""
import argparse
import math

from matplotlib.figure import Figure
from matplotlib.patches import Circle, Polygon, Rectangle

from app.utils.esquema import obtener_esquema

FILTROS = ["pasa_altas", "pasa_bajas", "pasa_banda", "rechaza_banda"]
PREFIJOS = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"), (1e-12, "p")]
UNIDAD = {"R": "Ω", "C": "F", "L": "H", "V": "V"}


def en_ingenieria(valor: float, tipo: str) -> str:
    for factor, prefijo in PREFIJOS:
        if abs(valor) >= factor * 0.9999:
            return f"{valor / factor:.3g} {prefijo}{UNIDAD[tipo]}"
    return f"{valor:g} {UNIDAD[tipo]}"


def _cable(ax, ruta):
    ax.plot([p[0] for p in ruta], [p[1] for p in ruta], color="k", lw=1.4, solid_capstyle="round", zorder=1)


def _tierra(ax, x, y):
    for i, mitad in enumerate((0.45, 0.30, 0.15)):
        ax.plot([x - mitad, x + mitad], [y + 0.12 + i * 0.12] * 2, color="k", lw=1.4)


def _simbolo(ax, e):
    ruta, k = e["ruta"], e["seg"]
    (xa, ya), (xb, yb) = ruta[k], ruta[k + 1]
    largo = math.hypot(xb - xa, yb - ya)
    ux, uy = (xb - xa) / largo, (yb - ya) / largo
    nx, ny = -uy, ux
    mx, my = (xa + xb) / 2, (ya + yb) / 2
    t = e["tipo"]
    mitad = {"R": 0.5, "C": 0.12, "L": 0.6, "V": 0.45}[t]
    _cable(ax, ruta[:k + 1] + [[mx - ux * mitad, my - uy * mitad]])
    _cable(ax, [[mx + ux * mitad, my + uy * mitad]] + ruta[k + 1:])
    if t == "R":
        ax.add_patch(Rectangle((mx - ux * 0.5 - nx * 0.17, my - uy * 0.5 - ny * 0.17), 1.0, 0.34,
                               angle=math.degrees(math.atan2(uy, ux)), fc="w", ec="k", lw=1.4, zorder=2))
    elif t == "C":
        for s in (-1, 1):
            cx, cy = mx + ux * 0.12 * s, my + uy * 0.12 * s
            ax.plot([cx - nx * 0.45, cx + nx * 0.45], [cy - ny * 0.45, cy + ny * 0.45], color="k", lw=2.2, zorder=2)
    elif t == "L":
        for i in range(4):
            a0 = -0.6 + i * 0.3
            ang = [math.pi * j / 20 for j in range(21)]
            ax.plot([mx + ux * (a0 + 0.15 - 0.15 * math.cos(q)) + nx * 0.18 * math.sin(q) for q in ang],
                    [my + uy * (a0 + 0.15 - 0.15 * math.cos(q)) + ny * 0.18 * math.sin(q) for q in ang],
                    color="k", lw=1.4, zorder=2)
    else:
        ax.add_patch(Circle((mx, my), 0.45, fc="w", ec="k", lw=1.4, zorder=2))
        q = [i / 20 for i in range(21)]
        ax.plot([mx - 0.28 + 0.56 * s for s in q], [my + 0.14 * math.sin(2 * math.pi * s) for s in q],
                color="k", lw=1.1, zorder=3)

    texto = f"{e['nombre']}\n{en_ingenieria(e['valor'], t)}"
    if abs(uy) < 0.5:                                   # horizontal; y crece hacia abajo en pantalla
        if e["rol"] == "realimentacion":
            ax.text(mx, my - 0.5, texto, ha="center", va="bottom", fontsize=6.6)
        elif my < -0.1:
            ax.text(mx, my + 0.5, texto, ha="center", va="top", fontsize=6.6)
        elif my > 0.1:
            ax.text(mx, my - 0.5, texto, ha="center", va="bottom", fontsize=6.6)
        else:
            ax.text(mx, my - 0.5, texto, ha="center", va="bottom", fontsize=6.6)
    elif e["rol"] == "carga":
        ax.text(mx + 0.55, my, texto, ha="left", va="center", fontsize=6.6)
    else:
        ax.text(mx - 0.55, my, texto, ha="right", va="center", fontsize=6.6)


def dibujar(ax, esquema: dict) -> None:
    for e in esquema["elementos"]:
        _simbolo(ax, e)
    for c in esquema["cables"]:
        _cable(ax, c)
    for x, y in esquema["tierras"]:
        _tierra(ax, x, y)
    for x, y in esquema["uniones"]:
        ax.add_patch(Circle((x, y), 0.085, fc="k", zorder=4))

    tension = {a["nodo"]: a["valor"] for a in esquema["alimentacion"]}
    for o in esquema["opamps"]:
        ax.add_patch(Polygon(o["triangulo"], closed=True, fc="#f4f4f4", ec="k", lw=1.5, zorder=2))
        (xp, yp), (xn, yn) = o["pines"]["in_p"], o["pines"]["in_n"]
        ax.text(xp + 0.12, yp, "+", fontsize=8, va="center")
        ax.text(xn + 0.12, yn, "−", fontsize=9, va="center")
        vp, vn = tension.get(o["alimentacion"]["v_pos"]), tension.get(o["alimentacion"]["v_neg"])
        etiqueta = o["nombre"] + (f"\n{vp:+g} V / {vn:+g} V" if vp is not None and vn is not None else "")
        ax.text(xp + 0.9, -1.15, etiqueta, fontsize=6.2, ha="center", va="bottom")

    ruta = esquema["salida"]["ruta"]
    _cable(ax, ruta)
    ax.add_patch(Circle(ruta[1], 0.09, fc="w", ec="k", zorder=3))
    ax.text(ruta[1][0] + 0.15, ruta[1][1], "Vout", va="center", fontsize=7)
    for nodo, p in esquema["nodos"].items():
        if nodo != esquema["nodo_fuente"]:
            ax.text(p["x"] - 0.05, p["y"] - 0.2, nodo, fontsize=5.5, color="#777", ha="right", va="bottom")

    lim = esquema["limites"]
    ax.set_title(esquema["titulo"], fontsize=9, loc="left")
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(lim["x_min"] - 1.5, lim["x_max"] + 2.5)
    ax.set_ylim(lim["y_max"] + 1.5, lim["y_min"] - 1.8)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("filtros", nargs="*", default=FILTROS)
    ap.add_argument("-o", "--salida", default="esquemas.png")
    args = ap.parse_args()

    n = len(args.filtros)
    columnas = 2 if n > 1 else 1
    filas = math.ceil(n / columnas)
    fig = Figure(figsize=(8.6 * columnas, 4.8 * filas))
    for i, filtro in enumerate(args.filtros, start=1):
        dibujar(fig.add_subplot(filas, columnas, i), obtener_esquema(filtro))
    fig.tight_layout()
    fig.savefig(args.salida, dpi=110)
    print(f"Esquemas guardados en: {args.salida}")


if __name__ == "__main__":
    main()