package model;

/** Los dos modos del menú inicial de "Generate circuit". */
public enum ModoEjecucion {
    /** Backend corre los 4 algoritmos y devuelve el que dio mejor resultado. Aún no implementado. */
    TODOS_LOS_ALGORITMOS,
    /** El usuario elige un algoritmo puntual. */
    ALGORITMO_ESPECIFICO
}
