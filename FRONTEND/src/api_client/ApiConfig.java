package api_client;

/**
 * Configuración del cliente HTTP hacia la API de optimización en Python.
 *
 * BASE_URL / OPTIMIZE_ENDPOINT: ya ajustados por el equipo a donde corre
 * el servidor real (localhost:8082 / /api/optimizar).
 *
 * MODO_AVANZADO: literal confirmado como "AVANZADO" (antes era un
 * placeholder "PASO_ATENUACION" con un TODO pendiente de confirmar).
 *
 * IMPORTANTE — los hiperparámetros DEFAULT_* YA NO se inyectan de forma fija
 * en cada petición. Ahora son solo los valores INICIALES que se muestran en
 * los spinners de "Optimizer properties" dentro de GenerateCircuitPanel; el
 * usuario los puede cambiar antes de generar. El valor que realmente viaja
 * en cada petición se arma en dto.CircuitRequest, a partir de lo que haya en
 * esos spinners al momento de aceptar el diálogo (ver
 * MainController.construirCircuitRequest).
 */
public final class ApiConfig {
    private ApiConfig() {}

    // --- Conexión ---
    public static final String BASE_URL = "http://localhost:8082";
    public static final String OPTIMIZE_ENDPOINT = "/api/optimizar";

    // --- Contrato de negocio (debe coincidir con GeneticController.SERVICE_MAP) ---
    public static final String FILTRO_PASA_ALTAS = "pasa_altas";
    public static final String ALGORITMO_GENETICO = "algoritmo_genetico";

    public static final String MODO_BASICO = "BASICO";
    public static final String MODO_AVANZADO = "AVANZADO";

    // --- Valores iniciales del formulario (el usuario puede cambiarlos antes de generar) ---
    public static final int DEFAULT_TAM_POBLACION = 30;
    public static final int DEFAULT_NUM_GENERACIONES = 30;
    public static final double DEFAULT_PROB_CRUCE = 0.8;
    public static final double DEFAULT_PROB_MUTACION = 0.3;
    public static final int DEFAULT_ELITISMO = 3;
    public static final int DEFAULT_TORNEO_K = 3;

    // --- Timeouts ---
    public static final int CONNECT_TIMEOUT_SECONDS = 10;
    // El AG corre de forma síncrona en el servidor y puede tardar varios
    // minutos según num_generaciones/tam_poblacion; por eso el timeout de
    // la petición completa es mucho mayor que el de conexión.
    public static final int REQUEST_TIMEOUT_SECONDS = 600;
}
