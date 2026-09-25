package api_client;

/**
 * Configuración del cliente HTTP hacia la API de optimización en Python.
 *
 * IMPORTANTE — valores que debes confirmar tú, porque no forman parte de
 * ningún código que me hayas mostrado (nunca vi tu main.py/router de FastAPI
 * ni la clase Pydantic PasaAltasConfiguration completa):
 *
 *   - BASE_URL / OPTIMIZE_ENDPOINT: la ruta real que expone tu FastAPI.
 *     Ajusta estos dos valores a donde realmente corre tu servidor.
 *
 *   - MODO_PASO_ATENUACION: el literal exacto que espera tu Pydantic para el
 *     modo distinto de "BASICO". En PasaAltasPreparationService._build_run_context
 *     solo vi el branch `if modo == "BASICO": ... else: ...`; nunca vi el
 *     valor literal que activa ese 'else' (el que usa f_paso/f_aten, que es
 *     el que corresponde a este flujo porque IdealFilter en Java siempre
 *     maneja frecuencia de paso Y de atenuación, nunca una sola "fc").
 *     Revisa tu enum/Literal de "modo" en PasaAltasConfiguration y corrige
 *     el valor de abajo si no coincide.
 *
 * Los hiperparámetros del algoritmo genético (tamaño de población, etc.) no
 * existen hoy en la UI de Java (GenerateCircuitPanel solo pide filtro y
 * entorno físico), así que quedan aquí como constantes. Si más adelante
 * quieres que el usuario pueda ajustarlos desde la interfaz, es un cambio
 * aparte en GenerateCircuitPanel/GenerateCircuitController.
 */
public final class ApiConfig {
    private ApiConfig() {}

    // --- Conexión ---
    public static final String BASE_URL = "http://localhost:8082"; // TODO: confirmar host/puerto real
    public static final String OPTIMIZE_ENDPOINT = "/api/optimizar"; // TODO: confirmar ruta real

    // --- Contrato de negocio (debe coincidir con GeneticController.SERVICE_MAP) ---
    public static final String FILTRO_PASA_ALTAS = "pasa_altas";
    public static final String ALGORITMO_GENETICO = "algoritmo_genetico";

    public static final String MODO_BASICO = "BASICO";
    public static final String MODO_PASO_ATENUACION = "PASO_ATENUACION"; // TODO: confirmar literal exacto

    // --- Hiperparámetros por defecto del AG (no expuestos aún en la UI) ---
    public static final int DEFAULT_TAM_POBLACION = 60;
    public static final int DEFAULT_NUM_GENERACIONES = 80;
    public static final double DEFAULT_PROB_CRUCE = 0.85;
    public static final double DEFAULT_PROB_MUTACION = 0.05;
    public static final int DEFAULT_ELITISMO = 2;
    public static final int DEFAULT_TORNEO_K = 3;

    // --- Timeouts ---
    public static final int CONNECT_TIMEOUT_SECONDS = 10;
    // El AG corre de forma síncrona en el servidor y puede tardar varios
    // minutos según num_generaciones/tam_poblacion; por eso el timeout de
    // la petición completa es mucho mayor que el de conexión.
    public static final int REQUEST_TIMEOUT_SECONDS = 600;
}