package model;

/**
 * Tablas de valores/décadas comerciales usadas para codificar/decodificar
 * componentes en el modelo Element (value/decade son ÍNDICES dentro de estas
 * tablas, no el valor físico real).
 *
 * Estas mismas tablas ya estaban duplicadas en dos lugares del código
 * original (view.CircuitPanel#drawCircuit y controller.InputCircuitController),
 * cada una como arreglos locales dentro del método. Se centralizan aquí para
 * que format_converter.FormatConverter (que traduce la respuesta de la API a
 * Element) no tenga que mantener una TERCERA copia desincronizable.
 *
 * Índice 0 = capacitancia, 1 = resistencia, 2 = inductancia
 * (igual que Element.type).
 */
public final class ComponentTables {
    private ComponentTables() {}

    public static final int[][] VALUES = {
            {10, 15, 22, 33, 47, 68},
            {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82},
            {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82}
    };

    public static final int[][] DECADES = {
            {-5, -6, -7, -8, -9},
            {1, 2, 3, 4, 5, 6},
            {-1, -2, -3, -4, -5, -6}
    };
}
