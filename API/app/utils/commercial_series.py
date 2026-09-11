"""
Utilería: Series comerciales E6 (capacitores) y E12 (resistencias).
No depende de ninguna otra capa.
"""


def generar_serie(base: list[float], decadas: range) -> list[float]:
    serie = []
    for d in decadas:
        for b in base:
            serie.append(round(b * (10 ** d), 12))
    return sorted(serie)


SERIE_E6: list[float] = generar_serie(
    [1.0, 1.5, 2.2, 3.3, 4.7, 6.8],
    range(-9, -5),
)

SERIE_E12: list[float] = generar_serie(
    [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2],
    range(1, 6),
)