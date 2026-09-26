"""
Utilería: Series comerciales E6 (capacitores) y E12 (resistencias).
No depende de ninguna otra capa.

IMPORTANTE — las decadas aquí deben coincidir con lo que el frontend Java
puede reconstruir (view.CircuitPanel / model.ComponentTables), porque el
valor real (float) es lo único que viaja por la API: Java hace una búsqueda
inversa valor -> (índice de valor, índice de década) contra sus propias
tablas fijas, y lanza una excepción si el valor no encaja en ninguna
combinación. Las tablas de Java usan mantisas x10 respecto a estas (10-82 en
vez de 1.0-8.2), así que la década de Java equivale a "década aquí + 1".
Con eso, el rango que Java SÍ puede reconstruir es:
    capacitor:  decadas -8..-4   (Java: -9..-5)
    resistor:   decadas  2..7    (Java:  1..6)
Antes este archivo usaba range(-9,-5) y range(1,6), que incluían una década
fuera de ese rango (-9 y 1 respectivamente) y no llegaban a las decadas más
altas que sí son válidas (-4 y 6..7) — un ~20-25% del espacio de búsqueda
del AG caía en valores que Java no podía dibujar y terminaba lanzando
IllegalArgumentException en el frontend.
"""


def generar_serie(base: list[float], decadas: range) -> list[float]:
    serie = []
    for d in decadas:
        for b in base:
            serie.append(round(b * (10 ** d), 12))
    return sorted(serie)


SERIE_E6: list[float] = generar_serie(
    [1.0, 1.5, 2.2, 3.3, 4.7, 6.8],
    range(-8, -3),
)

SERIE_E12: list[float] = generar_serie(
    [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2],
    range(2, 8),
)