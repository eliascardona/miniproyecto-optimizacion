package api_client;

import dto.CircuitRequest;
import dto.ComponenteDTO;
import dto.OptimizationResult;

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
 * Maven/Gradle configurado.
 *
 * A partir de esta versión, este cliente YA NO conoce model.Circuit ni
 * model.IdealFilter ni model.Simulation, y YA NO lee nada de
 * ApiConfig.DEFAULT_*: todo lo que necesita para armar la petición llega
 * empaquetado en un dto.CircuitRequest, que ya trae los valores que el
 * usuario ingresó en el formulario (ver controller.MainController). Esto
 * desacopla el cliente HTTP de los modelos de Swing/dibujo del circuito.
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
     * Solicita la optimización de un filtro pasa-altas Sallen-Key vía
     * algoritmo genético, con los valores ya empaquetados en `request`.
     *
     * La validación de "¿el filtro seleccionado es 'High Passes'?" ya NO se
     * hace aquí: CircuitRequest no carga el tipo de filtro (idealFilter.type)
     * porque el JSON de salida siempre manda "filtro": "pasa_altas" fijo. Esa
     * validación ahora vive en MainController, ANTES de construir el
     * CircuitRequest, para fallar rápido sin abrir siquiera el diálogo de
     * carga.
     */
    public OptimizationResult optimizarPasaAltas(CircuitRequest request) throws ApiException {
        Map<String, Object> body = construirCuerpoPeticion(request);
        String requestJson = MiniJsonParser.write(body);

        HttpRequest httpRequest = HttpRequest.newBuilder()
                .uri(URI.create(ApiConfig.BASE_URL + ApiConfig.OPTIMIZE_ENDPOINT))
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(ApiConfig.REQUEST_TIMEOUT_SECONDS))
                .POST(HttpRequest.BodyPublishers.ofString(requestJson))
                .build();

        HttpResponse<String> response;
        try {
            response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());
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
    // Construcción del cuerpo de la petición (ahora 100% desde CircuitRequest)
    // ------------------------------------------------------------------

    private Map<String, Object> construirCuerpoPeticion(CircuitRequest request) {
        // OJO: este "entorno" interno corresponde a PasaAltasConfiguration,
        // que a su vez viaja dentro del campo "entorno" del request de nivel
        // superior. El doble anidado ("entorno" dentro de "entorno") no es un
        // error: así lo lee _build_run_context en el backend
        // (cfg["entorno"]["v_fuente"], etc.).
        Map<String, Object> entornoFisico = new LinkedHashMap<>();
        entornoFisico.put("v_fuente", request.vFuente);
        entornoFisico.put("r_fuente", request.rFuente);
        entornoFisico.put("r_carga", request.rCarga);

        Map<String, Object> barridoAc = new LinkedHashMap<>();
        barridoAc.put("f_inicial", request.fInicial);
        barridoAc.put("f_final", request.fFinal);

        List<Object> parametrosOptimizador = new ArrayList<>();
        parametrosOptimizador.add(claveValor("tam_poblacion", request.tamPoblacion));
        parametrosOptimizador.add(claveValor("num_generaciones", request.numGeneraciones));
        parametrosOptimizador.add(claveValor("prob_cruce", request.probCruce));
        parametrosOptimizador.add(claveValor("prob_mutacion", request.probMutacion));
        parametrosOptimizador.add(claveValor("elitismo", request.elitismo));
        parametrosOptimizador.add(claveValor("torneo_k", request.torneoK));

        List<Object> frecuencias = new ArrayList<>();
        frecuencias.add(claveValor("f_aten", request.fAten));
        frecuencias.add(claveValor("f_paso", request.fPaso));

        Map<String, Object> pasaAltasConfiguration = new LinkedHashMap<>();
        pasaAltasConfiguration.put("modo", request.modo);
        pasaAltasConfiguration.put("entorno", entornoFisico);
        pasaAltasConfiguration.put("barrido_ac", barridoAc);
        pasaAltasConfiguration.put("parametros_optimizador", parametrosOptimizador);
        pasaAltasConfiguration.put("frecuencias", frecuencias);

        Map<String, Object> peticion = new LinkedHashMap<>();
        peticion.put("algoritmo", request.algoritmo);
        peticion.put("filtro", request.filtro);
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
    // Parseo de la respuesta (sin cambios)
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
