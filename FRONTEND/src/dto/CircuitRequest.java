package dto;

/**
 * DTO que agrupa TODOS los valores necesarios para construir el JSON que
 * espera la API de optimización (ver api_client.CircuitApiClient).
 *
 * Antes, CircuitApiClient.construirCuerpoPeticion tomaba los hiperparámetros
 * del AG (tam_poblacion, num_generaciones, prob_cruce, prob_mutacion,
 * elitismo, torneo_k) de forma fija desde ApiConfig.DEFAULT_*, sin que el
 * usuario pudiera cambiarlos desde la interfaz. Esta clase reemplaza esa
 * fuente "estática": se llena con los valores que el usuario ingresó en el
 * formulario (view.GenerateCircuitPanel) y es lo único que CircuitApiClient
 * necesita para armar la petición — ya no depende directamente de
 * model.Circuit, model.IdealFilter ni model.Simulation.
 *
 * Es inmutable (todos los campos son "public final") y se llena por
 * constructor, en el mismo orden en el que aparecen en el JSON de salida:
 *
 * {
 *     "algoritmo": "algoritmo_genetico",
 *     "filtro": "pasa_altas",
 *     "entorno": {
 *         "modo": "AVANZADO",
 *         "entorno": { "v_fuente": ..., "r_fuente": ..., "r_carga": ... },
 *         "barrido_ac": { "f_inicial": ..., "f_final": ... },
 *         "parametros_optimizador": [
 *             { "clave": "tam_poblacion", "valor": ... },
 *             { "clave": "num_generaciones", "valor": ... },
 *             { "clave": "prob_cruce", "valor": ... },
 *             { "clave": "prob_mutacion", "valor": ... },
 *             { "clave": "elitismo", "valor": ... },
 *             { "clave": "torneo_k", "valor": ... }
 *         ],
 *         "frecuencias": [
 *             { "clave": "f_aten", "valor": ... },
 *             { "clave": "f_paso", "valor": ... }
 *         ]
 *     }
 * }
 *
 * El constructor tiene 16 parámetros (uno por cada valor del JSON). Es una
 * lista larga a propósito: es un espejo 1 a 1 del contrato, no una
 * conveniencia. Si en algún punto se vuelve incómodo de invocar (varios
 * parámetros seguidos comparten tipo: rFuente/rCarga, fInicial/fFinal,
 * fAten/fPaso, tamPoblacion/numGeneraciones, probCruce/probMutacion,
 * elitismo/torneoK — el compilador no detecta un orden intercambiado entre
 * dos int o dos double), considera un builder; aquí se optó por el
 * constructor simple porque así se pidió explícitamente.
 */
public class CircuitRequest {

    // --- Nivel superior del JSON ---
    public final String algoritmo;
    public final String filtro;
    public final String modo;

    // --- entorno.entorno (ambiente físico) ---
    public final double vFuente;
    public final int rFuente;
    public final int rCarga;

    // --- entorno.barrido_ac ---
    public final int fInicial;
    public final int fFinal;

    // --- entorno.frecuencias ---
    public final int fAten;
    public final int fPaso;

    // --- entorno.parametros_optimizador (hiperparámetros del AG) ---
    public final int tamPoblacion;
    public final int numGeneraciones;
    public final double probCruce;
    public final double probMutacion;
    public final int elitismo;
    public final int torneoK;

    public CircuitRequest(
            String algoritmo,
            String filtro,
            String modo,
            double vFuente,
            int rFuente,
            int rCarga,
            int fInicial,
            int fFinal,
            int fAten,
            int fPaso,
            int tamPoblacion,
            int numGeneraciones,
            double probCruce,
            double probMutacion,
            int elitismo,
            int torneoK
    ) {
        if (algoritmo == null || algoritmo.isBlank()) {
            throw new IllegalArgumentException("algoritmo no puede estar vacío.");
        }
        if (filtro == null || filtro.isBlank()) {
            throw new IllegalArgumentException("filtro no puede estar vacío.");
        }
        if (modo == null || modo.isBlank()) {
            throw new IllegalArgumentException("modo no puede estar vacío.");
        }
        if (fInicial <= 0 || fFinal <= 0) {
            throw new IllegalArgumentException("Las frecuencias del barrido deben ser mayores que 0.");
        }
        if (fInicial >= fFinal) {
            throw new IllegalArgumentException("f_inicial debe ser menor que f_final.");
        }
        if (fAten <= 0 || fPaso <= 0) {
            throw new IllegalArgumentException("f_aten y f_paso deben ser mayores que 0.");
        }
        if (tamPoblacion <= 0) {
            throw new IllegalArgumentException("tam_poblacion debe ser mayor que 0.");
        }
        if (numGeneraciones <= 0) {
            throw new IllegalArgumentException("num_generaciones debe ser mayor que 0.");
        }
        if (probCruce < 0.0 || probCruce > 1.0) {
            throw new IllegalArgumentException("prob_cruce debe estar entre 0.0 y 1.0.");
        }
        if (probMutacion < 0.0 || probMutacion > 1.0) {
            throw new IllegalArgumentException("prob_mutacion debe estar entre 0.0 y 1.0.");
        }
        if (elitismo < 0 || elitismo > tamPoblacion) {
            throw new IllegalArgumentException("elitismo debe estar entre 0 y tam_poblacion.");
        }
        if (torneoK <= 0 || torneoK > tamPoblacion) {
            throw new IllegalArgumentException("torneo_k debe estar entre 1 y tam_poblacion.");
        }

        this.algoritmo = algoritmo;
        this.filtro = filtro;
        this.modo = modo;
        this.vFuente = vFuente;
        this.rFuente = rFuente;
        this.rCarga = rCarga;
        this.fInicial = fInicial;
        this.fFinal = fFinal;
        this.fAten = fAten;
        this.fPaso = fPaso;
        this.tamPoblacion = tamPoblacion;
        this.numGeneraciones = numGeneraciones;
        this.probCruce = probCruce;
        this.probMutacion = probMutacion;
        this.elitismo = elitismo;
        this.torneoK = torneoK;
    }
}
