package model;

/**
 * Algoritmos de optimización que la API expondrá. Hoy (ver
 * GeneticController.SERVICE_MAP en el backend) solo ALGORITMO_GENETICO
 * está registrado; los otros tres son para cuando el backend los agregue.
 *
 * `valorApi` es lo que viaja en el JSON ("algoritmo"). Se mantiene en
 * minúsculas snake_case por consistencia con el único valor ya verificado
 * contra el backend real ("algoritmo_genetico"); si el backend termina
 * usando otro formato para los nuevos, solo hay que tocar esta línea.
 */
public enum Algoritmo {
    ALGORITMO_GENETICO("algoritmo_genetico", "Genetic algorithm", true),
    OPTIMIZACION_BAYESIANA("optimizacion_bayesiana", "Bayesian optimization", false),
    RECOCIDO_SIMULADO("recocido_simulado", "Simulated annealing", false),
    ENJAMBRE_PARTICULAS("enjambre_particulas", "Particle swarm", false);

    public final String valorApi;
    public final String etiqueta;
    public final boolean implementadoEnBackend;

    Algoritmo(String valorApi, String etiqueta, boolean implementadoEnBackend) {
        this.valorApi = valorApi;
        this.etiqueta = etiqueta;
        this.implementadoEnBackend = implementadoEnBackend;
    }

    /** JComboBox<Algoritmo> usa esto automáticamente para mostrar cada opción. */
    @Override
    public String toString() {
        return etiqueta;
    }
}
