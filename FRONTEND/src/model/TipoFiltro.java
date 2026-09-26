package model;

/**
 * Tipos de filtro seleccionables. `idealFilterType` es el mismo entero que
 * ya usa IdealFilter.type (0=Low Passes, 1=High Passes) y que
 * GenerateCircuitController sigue recalculando automáticamente a partir de
 * las frecuencias de paso/atenuación una vez que se abre GenerateCircuitPanel
 * — esta pantalla solo fija el punto de partida.
 *
 * Las etiquetas ("Low Passes"/"High Passes") coinciden a propósito con las
 * que ya usa GenerateCircuitPanel.filterProperties(), para no tener dos
 * nombres distintos para lo mismo en la misma app.
 */
public enum TipoFiltro {
    PASA_BAJAS(0, "pasa_bajas", "Low Passes", false),
    PASA_ALTAS(1, "pasa_altas", "High Passes", true);

    public final int idealFilterType;
    public final String valorApi;
    public final String etiqueta;
    public final boolean implementadoEnBackend;

    TipoFiltro(int idealFilterType, String valorApi, String etiqueta, boolean implementadoEnBackend) {
        this.idealFilterType = idealFilterType;
        this.valorApi = valorApi;
        this.etiqueta = etiqueta;
        this.implementadoEnBackend = implementadoEnBackend;
    }

    /** Traduce el entero de IdealFilter.getType() de vuelta a este enum. */
    public static TipoFiltro fromIdealFilterType(int idealFilterType) {
        for (TipoFiltro tipo : values()) {
            if (tipo.idealFilterType == idealFilterType) {
                return tipo;
            }
        }
        throw new IllegalArgumentException("Tipo de IdealFilter desconocido: " + idealFilterType);
    }

    @Override
    public String toString() {
        return etiqueta;
    }
}
