package api_client;

/**
 * Configuración del cliente HTTP hacia la API de optimización en Python.
 *
 * BASE_URL / OPTIMIZE_ENDPOINT: ya ajustados por el equipo a donde corre
 * el servidor real (localhost:8082 / /api/optimizar).
 *
 * Qué filtros, algoritmos, modos y parámetros existen YA NO se escribe aquí
 * ni en ninguna otra parte del cliente: lo entrega el backend en
 * GET {CATALOG_ENDPOINT} (ver catalogo.Catalogo). Por eso desaparecieron de
 * este archivo los valores iniciales del algoritmo genético (DEFAULT_*) y
 * los literales de modo (MODO_BASICO / MODO_AVANZADO): ahora salen del
 * catálogo, y valen para los cuatro algoritmos y los cuatro filtros.
 */
public final class ApiConfig {
    private ApiConfig() {}

    // --- Contrato de negocio ---
    // FILTRO_PASA_ALTAS y ALGORITMO_GENETICO se movieron a model.TipoFiltro y
    // model.Algoritmo respectivamente (cada valor de esos enum trae su propio
    // valorApi), para que el filtro y el algoritmo puedan variar según lo que
    // el usuario elija en el menú inicial de "Generate circuit" en vez de
    // quedar fijos aquí.
    public static final String MODO_BASICO = "BASICO";
    public static final String MODO_AVANZADO = "AVANZADO";

    // --- Valores iniciales del formulario (el usuario puede cambiarlos antes de generar) ---
    public static final int DEFAULT_TAM_POBLACION = 30;
    public static final int DEFAULT_NUM_GENERACIONES = 30;
    public static final double DEFAULT_PROB_CRUCE = 0.8;
    public static final double DEFAULT_PROB_MUTACION = 0.3;
    public static final int DEFAULT_ELITISMO = 3;
    public static final int DEFAULT_TORNEO_K = 3;

    // --- Conexión ---
    public static final String BASE_URL = "http://localhost:8082";
    public static final String OPTIMIZE_ENDPOINT = "/api/optimizar";
    /** GET {CIRCUITS_ENDPOINT}/{filtro}: esquema (dibujo) del filtro con los valores base de su plantilla. */
    public static final String CIRCUITS_ENDPOINT = "/api/circuitos";
    /** GET: qué filtros × algoritmos × modos existen, qué pide cada uno y con qué límites. */
    public static final String CATALOG_ENDPOINT = "/api/catalogo";

    // --- Timeouts ---
    public static final int CONNECT_TIMEOUT_SECONDS = 10;
    // La optimización corre de forma síncrona en el servidor y puede tardar
    // varios minutos según los hiperparámetros del algoritmo; por eso el
    // timeout de la petición completa es mucho mayor que el de conexión.
    public static final int REQUEST_TIMEOUT_SECONDS = 1200;
}