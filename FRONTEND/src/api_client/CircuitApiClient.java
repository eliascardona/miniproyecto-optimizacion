package api_client;

import dto.ComponenteDTO;
import dto.OptimizationResult;
import model.Circuit;
import model.IdealFilter;
import model.Simulation;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Cliente HTTP hacia la API de optimización de circuitos (FastAPI + algoritmo
 * genético en Python).
 *
 * Usa java.net.http.HttpClient (incluido en el JDK desde la versión 11, no
 * requiere ninguna librería externa) porque este proyecto no tiene
 * Maven/Gradle configurado (ver FinalProject.iml: solo JDK heredado).
 */
public class CircuitApiClient {

    /** Se lanza cuando la API responde con error (4xx/5xx), o con un cuerpo inesperado. */
    public static class ApiException extends Exception {
        public ApiException(String message) {
            super(message);
        }

        public ApiException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    private final HttpClient httpClient;

    public CircuitApiClient() {
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(ApiConfig.CONNECT_TIMEOUT_SECONDS))
                .build();
    }

    /**
     * Solicita la optimización de un filtro pasa-altas Sallen-Key vía algoritmo genético.
     *
     * Los valores de entorno (voltaje/resistencias/barrido) se toman de
     * circuit.getSimulation(), y las frecuencias objetivo de
     * circuit.getIdealFilter(). Ambos ya existen hoy en la UI de "Generate
     * circuit" (GenerateCircuitPanel actualiza esos mismos objetos por
     * referencia), así que no se le pide nada nuevo al usuario.
     */
    public OptimizationResult optimizarPasaAltas(Circuit circuit) throws ApiException {
        IdealFilter filtro = circuit.getIdealFilter();
        Simulation simulacion = circuit.getSimulation();

        if (filtro.getType() != 1) {
            // type == 0 -> "Low Passes" en GenerateCircuitPanel.type. Hoy el backend
            // solo tiene registrado el servicio "pasa_altas" en GeneticController.SERVICE_MAP
            // (la entrada de "pasa_bajas" está comentada / no implementada). Evitamos
            // mandar una petición que el backend va a rechazar con un error confuso.
            throw new ApiException(
                    "La API todavía no soporta filtros 'Low Passes' (pasa bajas); " +
                            "solo está implementado 'High Passes' (pasa altas). " +
                            "Cambia el tipo de filtro o ajusta las frecuencias para que " +
                            "quede seleccionado 'High Passes'.");
        }

        Map<String, Object> body = construirCuerpoPeticion(filtro, simulacion);
        String requestJson = MiniJsonParser.write(body);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(ApiConfig.BASE_URL + ApiConfig.OPTIMIZE_ENDPOINT))
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(ApiConfig.REQUEST_TIMEOUT_SECONDS))
                .POST(HttpRequest.BodyPublishers.ofString(requestJson))
                .build();

        HttpResponse<String> response;
        try {
            response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (IOException e) {
            throw new ApiException(
                    "No se pudo conectar con la API en " + ApiConfig.BASE_URL +
                            ". ¿Está corriendo el servidor?", e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ApiException("La petición a la API fue interrumpida.", e);
        }

        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new ApiException(
                    "La API respondió con error " + response.statusCode() + ": " + response.body());
        }

        try {
            return parsearRespuesta(response.body());
        } catch (RuntimeException e) {
            throw new ApiException(
                    "La respuesta de la API no tiene el formato esperado: " + e.getMessage(), e);
        }
    }

    // ------------------------------------------------------------------
    // Construcción del cuerpo de la petición
    // ------------------------------------------------------------------

    private Map<String, Object> construirCuerpoPeticion(IdealFilter filtro, Simulation simulacion) {
        // OJO: este "entorno" interno corresponde a PasaAltasConfiguration
        // (el objeto que validate_json_config valida), que a su vez viaja
        // dentro del campo "entorno" del request de nivel superior. El doble
        // anidado ("entorno" dentro de "entorno") no es un error de este
        // cliente: así lo lee _build_run_context en el backend
        // (cfg["entorno"]["v_fuente"], etc.).
        Map<String, Object> entornoFisico = new LinkedHashMap<>();
        entornoFisico.put("v_fuente", simulacion.getSupplyVoltage());
        entornoFisico.put("r_fuente", simulacion.getSupplyResistance());
        entornoFisico.put("r_carga", simulacion.getLoadResistance());

        Map<String, Object> barridoAc = new LinkedHashMap<>();
        barridoAc.put("f_inicial", simulacion.getInitialFrequency());
        barridoAc.put("f_final", simulacion.getFinalFrequency());

        List<Object> parametrosOptimizador = new ArrayList<>();
        parametrosOptimizador.add(claveValor("tam_poblacion", ApiConfig.DEFAULT_TAM_POBLACION));
        parametrosOptimizador.add(claveValor("num_generaciones", ApiConfig.DEFAULT_NUM_GENERACIONES));
        parametrosOptimizador.add(claveValor("prob_cruce", ApiConfig.DEFAULT_PROB_CRUCE));
        parametrosOptimizador.add(claveValor("prob_mutacion", ApiConfig.DEFAULT_PROB_MUTACION));
        parametrosOptimizador.add(claveValor("elitismo", ApiConfig.DEFAULT_ELITISMO));
        parametrosOptimizador.add(claveValor("torneo_k", ApiConfig.DEFAULT_TORNEO_K));

        List<Object> frecuencias = new ArrayList<>();
        frecuencias.add(claveValor("f_paso", filtro.getPassageFrequency()));
        frecuencias.add(claveValor("f_aten", filtro.getAttenuationFrequency()));

        Map<String, Object> pasaAltasConfiguration = new LinkedHashMap<>();
        pasaAltasConfiguration.put("modo", ApiConfig.MODO_PASO_ATENUACION);
        pasaAltasConfiguration.put("entorno", entornoFisico);
        pasaAltasConfiguration.put("barrido_ac", barridoAc);
        pasaAltasConfiguration.put("parametros_optimizador", parametrosOptimizador);
        pasaAltasConfiguration.put("frecuencias", frecuencias);

        Map<String, Object> peticion = new LinkedHashMap<>();
        peticion.put("filtro", ApiConfig.FILTRO_PASA_ALTAS);
        peticion.put("algoritmo", ApiConfig.ALGORITMO_GENETICO);
        peticion.put("entorno", pasaAltasConfiguration);
        return peticion;
    }

    private Map<String, Object> claveValor(String clave, Object valor) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("clave", clave);
        item.put("valor", valor);
        return item;
    }

    // ------------------------------------------------------------------
    // Parseo de la respuesta
    // ------------------------------------------------------------------

    @SuppressWarnings("unchecked")
    private OptimizationResult parsearRespuesta(String json) {
        Map<String, Object> root = MiniJsonParser.parseObject(json);

        OptimizationResult result = new OptimizationResult();
        result.fitness = numero(root.get("fitness"), "fitness");

        List<Object> frecuenciasObtenidas = (List<Object>) root.get("frecuencias_obtenidas");
        if (frecuenciasObtenidas != null) {
            for (Object item : frecuenciasObtenidas) {
                Map<String, Object> par = (Map<String, Object>) item;
                String clave = (String) par.get("clave");
                double valor = numero(par.get("valor"), "frecuencias_obtenidas[].valor");
                result.frecuenciasObtenidas.put(clave, valor);
            }
        }

        List<Object> componentesOptimizados = (List<Object>) root.get("componentes_optimizados");
        List<ComponenteDTO> componentes = new ArrayList<>();
        if (componentesOptimizados != null) {
            for (Object item : componentesOptimizados) {
                Map<String, Object> c = (Map<String, Object>) item;

                ComponenteDTO dto = new ComponenteDTO();
                dto.nombre = (String) c.get("nombre");
                dto.tipo = (String) c.get("tipo");
                dto.valor = numero(c.get("valor"), "componentes_optimizados[].valor");
                dto.conexionTierra = Boolean.TRUE.equals(c.get("conexion_tierra"));
                componentes.add(dto);
            }
        }
        result.componentesOptimizados = componentes;

        result.graficaPngBase64 = (String) root.get("grafica_png_base64");

        return result;
    }

    private double numero(Object value, String campo) {
        if (!(value instanceof Number)) {
            throw new IllegalArgumentException("Se esperaba un número en '" + campo + "' y llegó: " + value);
        }
        return ((Number) value).doubleValue();
    }
}